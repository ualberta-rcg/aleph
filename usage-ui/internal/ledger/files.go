package ledger

import (
	"bufio"
	"bytes"
	"context"
	"errors"
	"io"
	"io/fs"
	"log"
	"os"
	"path/filepath"
	"strconv"
	"strings"
	"sync"
	"sync/atomic"
	"time"
)

// bucketKey identifies one daily bucket for one model and endpoint.
type bucketKey struct {
	day      string
	model    string
	endpoint string
}

// userBuckets maps a user to that user's daily buckets.
type userBuckets map[string]map[bucketKey]*Agg

func (u userBuckets) add(user string, key bucketKey, rec Record) {
	byKey := u[user]
	if byKey == nil {
		byKey = make(map[bucketKey]*Agg)
		u[user] = byKey
	}
	agg := byKey[key]
	if agg == nil {
		agg = &Agg{}
		byKey[key] = agg
	}
	agg.Add(rec)
}

// fileState is what the reader knows about one ledger file. Buckets are kept
// per file so that when the gateway's rotation deletes a file, its usage
// leaves the report too: the UI shows exactly what the ledger still holds.
type fileState struct {
	path   string // where the file was last found
	offset int64
	// head is the start of the file as last read, up to fileHeadLength
	// bytes. If the file with this ID no longer starts the same way, it is a
	// different file (see refreshFile) and is read from the beginning.
	head []byte
	// missedRefreshes counts consecutive refreshes that did not find the
	// file. See dropAfterMissedRefreshes.
	missedRefreshes int
	buckets         userBuckets
	oldest          time.Time
	newest          time.Time
}

// dropAfterMissedRefreshes is how many consecutive refreshes must miss a file
// before its usage is dropped.
//
// A single miss does not prove the file is gone. The gateway's
// RotatingFileHandler renames usage.log.4 to .5, then .3 to .4, and so on,
// one rename at a time. A refresh that lists the directory before a rename
// and opens the file after it gets "not found", although the file still
// exists under its next name. Checking the old name again (Lstat) cannot
// settle this: the old name can be missing while the file lives on under the
// new one. A file that was really deleted is missing from the next listing
// too, so waiting one more refresh drops only files that are gone. The cost
// is that a deleted file's usage stays visible for one extra refresh
// interval.
const dropAfterMissedRefreshes = 2

// fileHeadLength is how much of the start of a file is kept to tell apart
// two files that have the same ID. A ledger line begins with its timestamp,
// identity, and account, so two different files practically never share
// their first bytes. The check matters because the filesystem can reuse a
// deleted file's device and inode for a new file, and a deleted file's state
// is kept for an extra refresh (dropAfterMissedRefreshes).
const fileHeadLength = 256

// FileSource reads the gateway usage ledger from a directory tree:
//
//	<root>/<pod-name>/usage.log
//	<root>/<pod-name>/usage.log.1 ...
//
// Files directly under root are read too. It is read-only: it never writes to
// the ledger volume and keeps no state beyond process memory.
type FileSource struct {
	root    string
	backups int // the gateway's rotation count, or 0 if unknown

	mu             sync.RWMutex
	files          map[string]*fileState // by fileID
	refreshedAt    time.Time
	refreshStarted time.Time // when the refresh that finished at refreshedAt began
	// lastRefreshPartial is true when the last refresh could not read some
	// directory or file. Usage already held for those files is kept, but new
	// records in them were not read.
	lastRefreshPartial bool

	// modelEndpoints are the model-specific endpoint names kept so far. Only
	// the refresh goroutine touches it.
	modelEndpoints map[string]bool

	// OnRefresh, if set before Run starts, is called on Run's goroutine after
	// every refresh that returned no error. The daily history saves finished
	// days from it, so a save never runs while the ledger is half refreshed.
	OnRefresh func()

	// Now stamps when each refresh starts and finishes. It is time.Now;
	// tests replace it, since the daily history decides which days are over
	// from these times.
	Now func() time.Time

	ready   atomic.Bool
	skipped atomic.Int64 // malformed lines seen, for diagnostics
	// skippedLogged is the skipped count when refreshLogged last reported
	// it. Only the refresh goroutine touches it.
	skippedLogged int64

	// readDir and openFile are os.ReadDir and os.Open. Tests replace them to
	// simulate read errors, which file permissions cannot produce portably.
	readDir  func(name string) ([]os.DirEntry, error)
	openFile func(name string) (*os.File, error)
}

// NewFileSource returns a source rooted at the ledger volume mount.
//
// backups is the number of rotated files the gateway keeps
// (GATEWAY_USAGE_LOG_BACKUPS). Pass 0 when it is not known: any rotation is
// then treated as a possible loss of older records, which can understate
// coverage but never overstates it.
func NewFileSource(root string, backups int) *FileSource {
	return &FileSource{
		root:           root,
		backups:        backups,
		files:          make(map[string]*fileState),
		modelEndpoints: make(map[string]bool),
		readDir:        os.ReadDir,
		openFile:       os.Open,
		Now:            time.Now,
	}
}

// Ready reports whether the first full scan has completed.
func (s *FileSource) Ready() bool { return s.ready.Load() }

// Skipped returns the number of malformed lines ignored so far.
func (s *FileSource) Skipped() int64 { return s.skipped.Load() }

// LastRefreshPartial reports whether the last refresh failed to read some
// directory or file, so the usage shown may be missing recent records.
func (s *FileSource) LastRefreshPartial() bool {
	s.mu.RLock()
	defer s.mu.RUnlock()
	return s.lastRefreshPartial
}

// Run refreshes immediately and then on every interval until ctx ends.
func (s *FileSource) Run(ctx context.Context, interval time.Duration) {
	s.refreshLogged()
	ticker := time.NewTicker(interval)
	defer ticker.Stop()
	for {
		select {
		case <-ctx.Done():
			return
		case <-ticker.C:
			s.refreshLogged()
		}
	}
}

func (s *FileSource) refreshLogged() {
	start := time.Now()
	lines, err := s.Refresh()
	if err != nil {
		log.Printf("ledger refresh: %v", err)
		return
	}
	defer func() {
		if s.OnRefresh != nil {
			s.OnRefresh()
		}
	}()
	if elapsed := time.Since(start); elapsed > 5*time.Second {
		log.Printf("ledger refresh read %d new lines in %s", lines, elapsed.Round(time.Millisecond))
	}
	// Malformed lines are skipped while parsing. A rising count usually
	// means the gateway's record format changed, and those requests are
	// missing from every report, so say so. Line content is never logged:
	// it holds other users' identities.
	if skipped := s.skipped.Load(); skipped > s.skippedLogged {
		log.Printf("ledger: skipped %d malformed lines (total %d); a gateway format change?", skipped-s.skippedLogged, skipped)
		s.skippedLogged = skipped
	}
}

// isLedgerFile matches usage.log and its numbered rotations.
func isLedgerFile(name string) bool {
	_, ok := rotationNumber(name)
	return ok
}

// rotationNumber returns 0 for usage.log and N for usage.log.N.
func rotationNumber(name string) (int, bool) {
	if name == "usage.log" {
		return 0, true
	}
	suffix, ok := strings.CutPrefix(name, "usage.log.")
	if !ok || suffix == "" {
		return 0, false
	}
	for _, digit := range suffix {
		if digit < '0' || digit > '9' {
			return 0, false
		}
	}
	number, err := strconv.Atoi(suffix)
	return number, err == nil
}

// ledgerListing is what one listing of the ledger tree found.
type ledgerListing struct {
	paths []string
	// unreadableDirs are pod directories that could not be listed. Their
	// files were not seen, but may well still exist.
	unreadableDirs map[string]bool
}

// ledgerFiles lists ledger files at root and one directory level below it.
// Only a failure to list root itself is an error. A pod directory that
// cannot be listed is logged and returned in unreadableDirs.
func (s *FileSource) ledgerFiles() (ledgerListing, error) {
	listing := ledgerListing{unreadableDirs: make(map[string]bool)}
	entries, err := s.readDir(s.root)
	if err != nil {
		return listing, err
	}
	for _, entry := range entries {
		entryPath := filepath.Join(s.root, entry.Name())
		switch {
		case entry.IsDir():
			podEntries, err := s.readDir(entryPath)
			if err != nil {
				log.Printf("ledger: cannot list %s, keeping its last known usage: %v", entry.Name(), err)
				listing.unreadableDirs[entryPath] = true
				continue
			}
			for _, file := range podEntries {
				if file.Type().IsRegular() && isLedgerFile(file.Name()) {
					listing.paths = append(listing.paths, filepath.Join(entryPath, file.Name()))
				}
			}
		case entry.Type().IsRegular() && isLedgerFile(entry.Name()):
			listing.paths = append(listing.paths, entryPath)
		}
	}
	return listing, nil
}

// Refresh reads new lines from every ledger file and drops state for files
// that no longer exist. It returns the number of records read.
//
// A read error never drops usage. A listed file that cannot be opened, and
// every file in a pod directory that cannot be listed, keeps the usage
// already read from it, and the refresh is marked partial (see
// LastRefreshPartial and Report.ReadErrors). Only a file that is cleanly
// absent for dropAfterMissedRefreshes refreshes in a row is dropped. If root
// itself cannot be listed, the refresh is marked partial, nothing else
// changes, and the error is returned.
//
// Only Run's goroutine (or a single caller) may call Refresh; queries may run
// concurrently with it.
func (s *FileSource) Refresh() (int, error) {
	started := s.Now().UTC()
	listing, err := s.ledgerFiles()
	if err != nil {
		s.mu.Lock()
		s.lastRefreshPartial = true
		s.mu.Unlock()
		return 0, err
	}
	partial := len(listing.unreadableDirs) > 0
	found := make(map[string]bool, len(listing.paths)) // IDs of files read
	// unreadablePaths are listed files that could not be opened, so their
	// ID is unknown. The state last found at the same path is kept.
	unreadablePaths := make(map[string]bool)
	total := 0
	for _, path := range listing.paths {
		id, records, err := s.refreshFile(path)
		if id != "" {
			found[id] = true
		}
		total += records
		switch {
		case err == nil:
		case errors.Is(err, fs.ErrNotExist):
			// Renamed or deleted since the listing. Not a read error: the
			// file is found under its new name, or if it was deleted, it is
			// dropped after dropAfterMissedRefreshes.
		default:
			log.Printf("ledger: cannot read %s, keeping its last known usage: %v", path, err)
			partial = true
			if id == "" {
				unreadablePaths[path] = true
			}
		}
	}

	s.mu.Lock()
	for id, state := range s.files {
		switch {
		case found[id]:
			state.missedRefreshes = 0
		case unreadablePaths[state.path], listing.unreadableDirs[filepath.Dir(state.path)]:
			// Not looked at, which is not the same as missing.
		default:
			state.missedRefreshes++
			if state.missedRefreshes >= dropAfterMissedRefreshes {
				delete(s.files, id)
			}
		}
	}
	s.refreshedAt = s.Now().UTC()
	s.refreshStarted = started
	s.lastRefreshPartial = partial
	s.mu.Unlock()

	// Ready even when partial: what could be read is shown, and each report
	// says that part of the ledger could not be read.
	s.ready.Store(true)
	return total, nil
}

// refreshFile reads the new part of one ledger file. It returns the file's ID
// (empty if the file could not be opened) and the number of records read.
//
// The file is opened once, and both its identity and its content come from
// that handle. Looking it up again by name could reach a different file if
// the gateway rotates between the two steps.
func (s *FileSource) refreshFile(path string) (string, int, error) {
	file, err := s.openFile(path)
	if err != nil {
		return "", 0, err
	}
	defer file.Close()
	info, err := file.Stat()
	if err != nil {
		return "", 0, err
	}
	id := fileID(path, info)
	head, err := readHead(file, info.Size())
	if err != nil {
		return id, 0, err
	}

	s.mu.RLock()
	state := s.files[id]
	s.mu.RUnlock()

	offset := int64(0)
	reset := false
	if state != nil {
		offset = state.offset
		// Smaller than what was read: truncated or replaced in place. A
		// different start: a new file that reuses a deleted file's ID, or,
		// with path IDs, another file renamed to this path.
		if info.Size() < offset || !bytes.HasPrefix(head, state.head) {
			offset, reset = 0, true
		}
	}
	if state != nil && !reset && info.Size() == offset {
		if state.path != path {
			s.mu.Lock()
			state.path = path
			s.mu.Unlock()
		}
		return id, 0, nil
	}

	delta, newOffset, records, err := s.readFrom(file, offset)
	if err != nil {
		return id, 0, err
	}

	s.mu.Lock()
	if state == nil || reset {
		state = &fileState{buckets: make(userBuckets)}
		s.files[id] = state
	}
	state.path = path
	state.offset = newOffset
	state.head = head
	mergeInto(state, delta)
	s.mu.Unlock()
	return id, records, nil
}

// readHead returns the first fileHeadLength bytes of file, or all of it if
// shorter. size is the file's size when it was opened. The gateway may
// rotate or truncate it meanwhile, so a short read is not an error.
func readHead(file *os.File, size int64) ([]byte, error) {
	head := make([]byte, min(size, fileHeadLength))
	n, err := file.ReadAt(head, 0)
	if err != nil && !errors.Is(err, io.EOF) {
		return nil, err
	}
	return head[:n], nil
}

// fileDelta is the usage parsed from one read of one file.
type fileDelta struct {
	buckets userBuckets
	oldest  time.Time
	newest  time.Time
}

func mergeInto(state *fileState, delta fileDelta) {
	for user, byKey := range delta.buckets {
		dst := state.buckets[user]
		if dst == nil {
			state.buckets[user] = byKey
			continue
		}
		for key, agg := range byKey {
			if existing := dst[key]; existing != nil {
				existing.Merge(agg)
			} else {
				dst[key] = agg
			}
		}
	}
	if !delta.oldest.IsZero() && (state.oldest.IsZero() || delta.oldest.Before(state.oldest)) {
		state.oldest = delta.oldest
	}
	if delta.newest.After(state.newest) {
		state.newest = delta.newest
	}
}

// readFrom parses complete lines from offset onward. A trailing line without
// a newline is left for the next refresh, since the gateway may still be
// writing it. Only user-type records are kept.
func (s *FileSource) readFrom(file *os.File, offset int64) (fileDelta, int64, int, error) {
	delta := fileDelta{buckets: make(userBuckets)}
	if _, err := file.Seek(offset, io.SeekStart); err != nil {
		return delta, offset, 0, err
	}
	// Real records are under 2 KiB; longer lines are skipped as malformed.
	reader := bufio.NewReaderSize(file, 256<<10)
	records := 0
	for {
		line, err := reader.ReadSlice('\n')
		if errors.Is(err, bufio.ErrBufferFull) {
			// Over-long line: consume it whole and skip it.
			consumed := int64(len(line))
			for errors.Is(err, bufio.ErrBufferFull) {
				line, err = reader.ReadSlice('\n')
				consumed += int64(len(line))
			}
			if err != nil {
				return delta, offset, records, nil // incomplete; retry next time
			}
			offset += consumed
			s.skipped.Add(1)
			continue
		}
		if err != nil {
			if errors.Is(err, io.EOF) {
				return delta, offset, records, nil
			}
			return delta, offset, records, err
		}
		offset += int64(len(line))
		trimmed := bytes.TrimSpace(line)
		if len(trimmed) == 0 {
			continue
		}
		rec, ts, parseErr := ParseRecord(trimmed)
		if parseErr != nil {
			s.skipped.Add(1)
			continue
		}
		records++
		if delta.oldest.IsZero() || ts.Before(delta.oldest) {
			delta.oldest = ts
		}
		if ts.After(delta.newest) {
			delta.newest = ts
		}
		if rec.IdentityType != "user" {
			continue
		}
		rec.Endpoint = s.endpointLabel(rec)
		delta.buckets.add(rec.Identity, bucketKey{day: ts.UTC().Format(DayLayout), model: rec.Model, endpoint: rec.Endpoint}, rec)
	}
}

// Usage implements Source. Days are UTC and the range is inclusive.
func (s *FileSource) Usage(_ context.Context, user string, from, to time.Time) (Report, error) {
	fromDay := from.UTC().Format(DayLayout)
	toDay := to.UTC().Format(DayLayout)
	report := Report{User: user, From: from, To: to}

	merged := make(map[bucketKey]*Agg)
	s.mu.RLock()
	report.Oldest, report.CompleteFrom = s.coverage()
	for _, state := range s.files {
		if state.newest.After(report.Newest) {
			report.Newest = state.newest
		}
		for key, agg := range state.buckets[user] {
			if key.day < fromDay || key.day > toDay {
				continue
			}
			total := merged[key]
			if total == nil {
				total = &Agg{}
				merged[key] = total
			}
			total.Merge(agg)
		}
	}
	report.RefreshedAt = s.refreshedAt
	report.ReadErrors = s.lastRefreshPartial
	s.mu.RUnlock()
	report.Incomplete = DaysBefore(from, to, FirstCompleteDay(report.CompleteFrom))

	report.Rows = make([]Row, 0, len(merged))
	for key, agg := range merged {
		report.Rows = append(report.Rows, Row{Day: key.day, Model: key.model, Endpoint: key.endpoint, Agg: *agg})
	}
	SortRows(report.Rows)
	return report, nil
}

// maxModelEndpoints caps the distinct model-specific endpoint names kept.
// The platform's model cards declare about 60; the cap leaves room for
// growth while bounding memory if a backend answers arbitrary paths.
const maxModelEndpoints = 256

// endpointLabel returns the endpoint a record is reported under. Known
// routes and unnamed paths are labelled by NormalizeEndpoint already. A path
// that may be a model's own route is named only once a request to it has
// succeeded, which shows that a model really serves it. A successful request
// adds the name (up to maxModelEndpoints). A failed request keeps the name
// only when it was added before, so that the route's error count is right,
// and otherwise counts as EndpointOther, so that requests which fail cannot
// create endpoint names. A failure read before the route's first success
// therefore counts as EndpointOther.
func (s *FileSource) endpointLabel(rec Record) string {
	if rec.EndpointKind != EndpointModelRoute {
		return rec.Endpoint
	}
	if rec.Succeeded() {
		return s.keepModelEndpoint(rec.Endpoint)
	}
	if s.modelEndpoints[rec.Endpoint] {
		return rec.Endpoint
	}
	return EndpointOther
}

// keepModelEndpoint returns endpoint, or EndpointOther once the cap on
// distinct model-specific names is reached.
func (s *FileSource) keepModelEndpoint(endpoint string) string {
	if s.modelEndpoints[endpoint] {
		return endpoint
	}
	if len(s.modelEndpoints) >= maxModelEndpoints {
		return EndpointOther
	}
	s.modelEndpoints[endpoint] = true
	return endpoint
}

// coverage returns the oldest record on hand and the time from which the
// files on hand hold every record the gateway wrote. complete is zero when no
// file can have been deleted yet, so nothing has been lost. The caller holds
// s.mu.
//
// Each pod writes to its own directory and rotates on its own schedule, and
// retired pods' directories stay on the volume. The oldest record anywhere is
// therefore not a safe start: one old retired pod would make a range look
// complete after the live pods have rotated those days away. Instead, every
// directory that may have deleted a file contributes the start of what it
// still holds, and records are complete only after the latest such start. A
// directory that has never reached the deletion point has lost nothing.
func (s *FileSource) coverage() (oldest, complete time.Time) {
	type dirSpan struct {
		oldest      time.Time
		mayHaveLost bool
	}
	dirs := map[string]*dirSpan{}
	for _, state := range s.files {
		if state.oldest.IsZero() {
			continue
		}
		if oldest.IsZero() || state.oldest.Before(oldest) {
			oldest = state.oldest
		}
		dir := filepath.Dir(state.path)
		span := dirs[dir]
		if span == nil {
			span = &dirSpan{oldest: state.oldest}
			dirs[dir] = span
		}
		if state.oldest.Before(span.oldest) {
			span.oldest = state.oldest
		}
		number, _ := rotationNumber(filepath.Base(state.path))
		if number > 0 && (s.backups == 0 || number >= s.backups) {
			span.mayHaveLost = true
		}
	}
	for _, span := range dirs {
		if span.mayHaveLost && span.oldest.After(complete) {
			complete = span.oldest
		}
	}
	return oldest, complete
}
