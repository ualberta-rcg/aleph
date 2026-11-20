package source

import (
	"bufio"
	"bytes"
	"context"
	"errors"
	"fmt"
	"io"
	"io/fs"
	"log"
	"maps"
	"os"
	"path/filepath"
	"strconv"
	"strings"
	"sync"
	"sync/atomic"
	"time"
)

// ErrDeniedSubject is returned when a subject is invalid or matches DENIED_IDENTITIES.
var ErrDeniedSubject = errors.New("subject is invalid or denied")

const (
	dropAfterMissedRefreshes = 2
	fileHeadLength           = 256
	maxModelEndpoints        = 256
	maxFPIndexEntries        = 16384
	defaultCacheEntries      = 64
	defaultCacheTTL          = 60 * time.Second
)

// LedgerConfig configures LedgerSource.
type LedgerConfig struct {
	Root               string
	Backups            int
	MaxConcurrentScans int
	CacheTTL           time.Duration
	MaxCacheEntries    int
	DeniedIdentities   map[string]bool
}

type bucketKey struct {
	day      string
	model    string
	endpoint string
}

// fileMeta holds only lightweight file bounds and rotation identity (~hundreds
// of bytes per file). No per-user rows are kept in indexer memory or on disk.
type fileMeta struct {
	id              string
	path            string
	offset          int64
	head            []byte
	missedRefreshes int
	oldest          time.Time
	newest          time.Time
}

type candidateFile struct {
	id     string
	path   string
	offset int64
	head   []byte
}

type cacheEntry struct {
	subjectKey string
	expiresAt  time.Time
	report     Report
}

// LedgerSource indexes file bounds and key_fp metadata in the background and
// scans matching usage records on demand per signed-in subject.
type LedgerSource struct {
	root    string
	backups int
	denied  map[string]bool
	scanSem chan struct{}

	refreshMu sync.Mutex

	mu                 sync.RWMutex
	files              map[string]*fileMeta
	fpIndex            map[KeyFP]KeyMeta
	modelEndpoints     map[string]bool
	refreshedAt        time.Time
	refreshStarted     time.Time
	lastRefreshPartial bool

	cacheMu         sync.Mutex
	cache           map[string]cacheEntry
	cacheTTL        time.Duration
	maxCacheEntries int

	Now func() time.Time

	ready         atomic.Bool
	skipped       atomic.Int64
	skippedLogged int64

	readDir  func(name string) ([]os.DirEntry, error)
	openFile func(name string) (*os.File, error)
}

// NewLedgerSource builds an on-demand LedgerSource rooted at cfg.Root.
func NewLedgerSource(cfg LedgerConfig) *LedgerSource {
	maxScans := cfg.MaxConcurrentScans
	if maxScans < 1 {
		maxScans = 1
	}
	cacheTTL := cfg.CacheTTL
	if cacheTTL <= 0 {
		cacheTTL = defaultCacheTTL
	}
	maxCache := cfg.MaxCacheEntries
	if maxCache < 1 {
		maxCache = defaultCacheEntries
	}
	denied := cfg.DeniedIdentities
	if denied == nil {
		denied = ParseDeniedIdentities(DefaultDeniedIdentities)
	}
	return &LedgerSource{
		root:            cfg.Root,
		backups:         cfg.Backups,
		denied:          denied,
		scanSem:         make(chan struct{}, maxScans),
		files:           make(map[string]*fileMeta),
		fpIndex:         make(map[KeyFP]KeyMeta),
		modelEndpoints:  make(map[string]bool),
		cache:           make(map[string]cacheEntry),
		cacheTTL:        cacheTTL,
		maxCacheEntries: maxCache,
		Now:             time.Now,
		readDir:         os.ReadDir,
		openFile:        os.Open,
	}
}

// Mode returns the Backend mode identifier.
func (s *LedgerSource) Mode() string { return "ledger" }

// Ready reports whether the initial file-bounds index pass has completed.
func (s *LedgerSource) Ready() bool { return s.ready.Load() }

// Skipped returns the count of malformed JSONL lines ignored during indexing.
func (s *LedgerSource) Skipped() int64 { return s.skipped.Load() }

// IsDeniedIdentity reports whether identity is in DENIED_IDENTITIES.
func (s *LedgerSource) IsDeniedIdentity(identity string) bool {
	if identity == "" {
		return false
	}
	return s.denied[strings.ToLower(identity)]
}

// LookupKeyFP resolves a validated key fingerprint to its observed ledger metadata.
func (s *LedgerSource) LookupKeyFP(fp KeyFP) (KeyMeta, bool) {
	if !fp.Valid() {
		return KeyMeta{}, false
	}
	s.mu.RLock()
	meta, ok := s.fpIndex[fp]
	s.mu.RUnlock()
	return meta, ok
}

// EvictSubject removes any cached query reports for subj (called on POST /logout).
func (s *LedgerSource) EvictSubject(subj Subject) {
	prefix := subj.CacheKey()
	if prefix == "" {
		return
	}
	s.cacheMu.Lock()
	for k, v := range s.cache {
		if v.subjectKey == prefix {
			delete(s.cache, k)
		}
	}
	s.cacheMu.Unlock()
}

// Run performs an initial index pass immediately and then every interval until ctx ends.
func (s *LedgerSource) Run(ctx context.Context, interval time.Duration) {
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

func (s *LedgerSource) refreshLogged() {
	start := time.Now()
	lines, err := s.Refresh()
	if err != nil {
		log.Printf("ledger refresh: %v", err)
		return
	}
	if elapsed := time.Since(start); elapsed > 5*time.Second {
		log.Printf("ledger index scanned %d new lines in %s", lines, elapsed.Round(time.Millisecond))
	}
	if skipped := s.skipped.Load(); skipped > s.skippedLogged {
		log.Printf("ledger: skipped %d malformed lines (total %d)", skipped-s.skippedLogged, skipped)
		s.skippedLogged = skipped
	}
}

func isLedgerFile(name string) bool {
	_, ok := rotationNumber(name)
	return ok
}

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

type ledgerListing struct {
	paths          []string
	unreadableDirs map[string]bool
}

func (s *LedgerSource) ledgerFiles() (ledgerListing, error) {
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
				log.Printf("ledger: cannot list %s, keeping last known bounds: %v", entry.Name(), err)
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

// Refresh incrementally advances file bounds, fpIndex, and modelEndpoints.
func (s *LedgerSource) Refresh() (int, error) {
	s.refreshMu.Lock()
	defer s.refreshMu.Unlock()

	started := s.Now().UTC()
	listing, err := s.ledgerFiles()
	if err != nil {
		s.mu.Lock()
		s.lastRefreshPartial = true
		s.mu.Unlock()
		return 0, err
	}
	partial := len(listing.unreadableDirs) > 0
	found := make(map[string]bool, len(listing.paths))
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
			// Rotated or unlinked since directory listing; next file/pass catches it.
		default:
			log.Printf("ledger: cannot read %s, keeping last known bounds: %v", path, err)
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

	s.ready.Store(true)
	return total, nil
}

type indexDelta struct {
	oldest    time.Time
	newest    time.Time
	fpUpdates map[KeyFP]KeyMeta
	routes    map[string]bool
}

func (s *LedgerSource) refreshFile(path string) (string, int, error) {
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
	var prevOffset int64
	var prevHead []byte
	var prevPath string
	hasState := state != nil
	if hasState {
		prevOffset = state.offset
		prevHead = state.head
		prevPath = state.path
	}
	s.mu.RUnlock()

	offset := int64(0)
	reset := false
	if hasState {
		offset = prevOffset
		if info.Size() < offset || !bytes.HasPrefix(head, prevHead) {
			offset, reset = 0, true
		}
	}
	if hasState && !reset && info.Size() == offset {
		if prevPath != path {
			s.mu.Lock()
			if cur := s.files[id]; cur != nil {
				cur.path = path
			}
			s.mu.Unlock()
		}
		return id, 0, nil
	}

	delta, newOffset, records, err := s.indexFrom(file, offset)
	if err != nil {
		return id, 0, err
	}

	s.mu.Lock()
	cur := s.files[id]
	if cur == nil || reset {
		cur = &fileMeta{id: id}
		s.files[id] = cur
	}
	cur.path = path
	cur.offset = newOffset
	cur.head = head
	if !delta.oldest.IsZero() && (cur.oldest.IsZero() || delta.oldest.Before(cur.oldest)) {
		cur.oldest = delta.oldest
	}
	if delta.newest.After(cur.newest) {
		cur.newest = delta.newest
	}
	for fp, meta := range delta.fpUpdates {
		existing, ok := s.fpIndex[fp]
		if !ok || !meta.LastSeen.Before(existing.LastSeen) {
			if !ok && len(s.fpIndex) >= maxFPIndexEntries {
				s.evictOldestFPLocked()
			}
			s.fpIndex[fp] = meta
		}
	}
	for route := range delta.routes {
		if !s.modelEndpoints[route] && len(s.modelEndpoints) < maxModelEndpoints {
			s.modelEndpoints[route] = true
		}
	}
	s.mu.Unlock()
	return id, records, nil
}

func (s *LedgerSource) evictOldestFPLocked() {
	var oldestKey KeyFP
	var oldestTS time.Time
	first := true
	for k, v := range s.fpIndex {
		if first || v.LastSeen.Before(oldestTS) {
			oldestKey = k
			oldestTS = v.LastSeen
			first = false
		}
	}
	if !first {
		delete(s.fpIndex, oldestKey)
	}
}

func readHead(file *os.File, size int64) ([]byte, error) {
	head := make([]byte, min(size, fileHeadLength))
	n, err := file.ReadAt(head, 0)
	if err != nil && !errors.Is(err, io.EOF) {
		return nil, err
	}
	return head[:n], nil
}

func (s *LedgerSource) indexFrom(file *os.File, offset int64) (indexDelta, int64, int, error) {
	delta := indexDelta{
		fpUpdates: make(map[KeyFP]KeyMeta),
		routes:    make(map[string]bool),
	}
	if _, err := file.Seek(offset, io.SeekStart); err != nil {
		return delta, offset, 0, err
	}
	reader := bufio.NewReaderSize(file, 256<<10)
	records := 0
	for {
		line, err := reader.ReadSlice('\n')
		if errors.Is(err, bufio.ErrBufferFull) {
			consumed := int64(len(line))
			for errors.Is(err, bufio.ErrBufferFull) {
				line, err = reader.ReadSlice('\n')
				consumed += int64(len(line))
			}
			if err != nil {
				return delta, offset, records, nil
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
		if rec.KeyFP.Valid() {
			prev, ok := delta.fpUpdates[rec.KeyFP]
			if !ok || !ts.Before(prev.LastSeen) {
				delta.fpUpdates[rec.KeyFP] = KeyMeta{
					Identity:     rec.Identity,
					Account:      rec.Account,
					IdentityType: rec.IdentityType,
					LastSeen:     ts,
				}
			}
		}
		if rec.EndpointKind == EndpointModelRoute && rec.Succeeded() {
			delta.routes[rec.Endpoint] = true
		}
	}
}

// Usage scans candidate files overlapping [from, to] for subj, guarded by the
// cold-scan concurrency semaphore and a short-lived bounded LRU cache.
func (s *LedgerSource) Usage(ctx context.Context, subj Subject, from, to time.Time) (Report, error) {
	if !subj.Valid() || s.IsDeniedIdentity(subj.Identity) {
		return Report{}, ErrDeniedSubject
	}
	from = DayOf(from)
	to = DayOf(to)
	fromDay := from.Format(DayLayout)
	toDay := to.Format(DayLayout)

	cacheKey := subj.CacheKey() + "|" + fromDay + "|" + toDay
	if cached, ok := s.getCached(cacheKey); ok {
		return cached, nil
	}

	select {
	case s.scanSem <- struct{}{}:
		defer func() { <-s.scanSem }()
	case <-ctx.Done():
		return Report{}, ctx.Err()
	}

	if cached, ok := s.getCached(cacheKey); ok {
		return cached, nil
	}

	report, rotated, err := s.scanSubject(ctx, subj, from, to, fromDay, toDay)
	if err != nil {
		return Report{}, err
	}
	if rotated {
		// RotatingFileHandler renamed a candidate file between the last index
		// pass and open; re-index once and retry so reports never drop a rotated file.
		if _, refreshErr := s.Refresh(); refreshErr == nil {
			report2, rotated2, err2 := s.scanSubject(ctx, subj, from, to, fromDay, toDay)
			if err2 != nil {
				return Report{}, err2
			}
			if rotated2 {
				report2.ReadErrors = true
			}
			report = report2
		} else {
			report.ReadErrors = true
		}
	}

	if !report.ReadErrors && s.Ready() {
		s.putCached(cacheKey, subj.CacheKey(), report)
	}
	return report, nil
}

func (s *LedgerSource) getCached(cacheKey string) (Report, bool) {
	now := s.Now()
	s.cacheMu.Lock()
	defer s.cacheMu.Unlock()
	entry, ok := s.cache[cacheKey]
	if !ok {
		return Report{}, false
	}
	if !now.Before(entry.expiresAt) {
		delete(s.cache, cacheKey)
		return Report{}, false
	}
	return cloneReport(entry.report), true
}

func (s *LedgerSource) putCached(cacheKey, subjectKey string, report Report) {
	now := s.Now()
	s.cacheMu.Lock()
	defer s.cacheMu.Unlock()
	for k, v := range s.cache {
		if !now.Before(v.expiresAt) {
			delete(s.cache, k)
		}
	}
	if len(s.cache) >= s.maxCacheEntries {
		var oldestK string
		var oldestExp time.Time
		first := true
		for k, v := range s.cache {
			if first || v.expiresAt.Before(oldestExp) {
				oldestK = k
				oldestExp = v.expiresAt
				first = false
			}
		}
		if !first {
			delete(s.cache, oldestK)
		}
	}
	s.cache[cacheKey] = cacheEntry{
		subjectKey: subjectKey,
		expiresAt:  now.Add(s.cacheTTL),
		report:     cloneReport(report),
	}
}

func cloneReport(in Report) Report {
	out := in
	if len(in.Rows) > 0 {
		out.Rows = make([]Row, len(in.Rows))
		copy(out.Rows, in.Rows)
	}
	if len(in.Incomplete) > 0 {
		out.Incomplete = make([]string, len(in.Incomplete))
		copy(out.Incomplete, in.Incomplete)
	}
	return out
}

func (s *LedgerSource) scanSubject(ctx context.Context, subj Subject, from, to time.Time, fromDay, toDay string) (Report, bool, error) {
	report := Report{Subject: subj, From: from, To: to}

	s.mu.RLock()
	report.Oldest, report.CompleteFrom = s.coverageLocked()
	report.RefreshedAt = s.refreshedAt
	report.ReadErrors = s.lastRefreshPartial
	knownRoutes := maps.Clone(s.modelEndpoints)
	var candidates []candidateFile
	for _, state := range s.files {
		if state.newest.After(report.Newest) {
			report.Newest = state.newest
		}
		if state.oldest.IsZero() || state.offset <= 0 {
			continue
		}
		if DayOf(state.newest).Before(from) || DayOf(state.oldest).After(to) {
			continue
		}
		headCopy := make([]byte, len(state.head))
		copy(headCopy, state.head)
		candidates = append(candidates, candidateFile{
			id:     state.id,
			path:   state.path,
			offset: state.offset,
			head:   headCopy,
		})
	}
	s.mu.RUnlock()

	report.Incomplete = DaysBefore(from, to, FirstCompleteDay(report.CompleteFrom))

	needle := prefilterNeedle(subj)
	merged := make(map[bucketKey]*Agg)
	rotated := false

	for _, cand := range candidates {
		if err := ctx.Err(); err != nil {
			return Report{}, false, err
		}
		fileRotated, fileReadErr, err := s.scanCandidateFile(ctx, cand, subj, needle, fromDay, toDay, knownRoutes, merged)
		if err != nil {
			return Report{}, false, err
		}
		if fileRotated {
			rotated = true
			break
		}
		if fileReadErr {
			report.ReadErrors = true
		}
	}
	if rotated {
		return report, true, nil
	}

	report.Rows = make([]Row, 0, len(merged))
	for key, agg := range merged {
		report.Rows = append(report.Rows, Row{
			Day:      key.day,
			Model:    key.model,
			Endpoint: key.endpoint,
			Agg:      *agg,
		})
	}
	SortRows(report.Rows)
	return report, false, nil
}

func prefilterNeedle(subj Subject) []byte {
	switch subj.Scope {
	case ScopeIdentity:
		return []byte(`"` + subj.Identity + `"`)
	case ScopeKeyFP:
		return []byte(`"` + subj.KeyFP.SHA256_8 + `"`)
	default:
		return nil
	}
}

func (s *LedgerSource) scanCandidateFile(
	ctx context.Context,
	cand candidateFile,
	subj Subject,
	needle []byte,
	fromDay, toDay string,
	knownRoutes map[string]bool,
	merged map[bucketKey]*Agg,
) (rotated bool, readErr bool, fatalErr error) {
	file, err := s.openFile(cand.path)
	if err != nil {
		if errors.Is(err, fs.ErrNotExist) {
			return true, false, nil
		}
		log.Printf("ledger scan: cannot open %s: %v", cand.path, err)
		return false, true, nil
	}
	defer file.Close()

	info, err := file.Stat()
	if err != nil {
		log.Printf("ledger scan: cannot stat %s: %v", cand.path, err)
		return false, true, nil
	}
	if fileID(cand.path, info) != cand.id || info.Size() < cand.offset {
		return true, false, nil
	}
	if len(cand.head) > 0 {
		head, headErr := readHead(file, info.Size())
		if headErr != nil {
			return false, true, nil
		}
		if !bytes.HasPrefix(head, cand.head) {
			return true, false, nil
		}
	}

	section := io.NewSectionReader(file, 0, cand.offset)
	reader := bufio.NewReaderSize(section, 256<<10)
	lineNo := 0
	for {
		if lineNo&0x3ff == 0 {
			if err := ctx.Err(); err != nil {
				return false, false, err
			}
		}
		lineNo++

		line, err := reader.ReadSlice('\n')
		if errors.Is(err, bufio.ErrBufferFull) {
			for errors.Is(err, bufio.ErrBufferFull) {
				_, err = reader.ReadSlice('\n')
			}
			if err != nil && !errors.Is(err, io.EOF) {
				return false, true, nil
			}
			continue
		}
		if err != nil {
			if errors.Is(err, io.EOF) {
				break
			}
			log.Printf("ledger scan: read error on %s: %v", cand.path, err)
			return false, true, nil
		}
		trimmed := bytes.TrimSpace(line)
		if len(trimmed) == 0 {
			continue
		}
		if len(needle) > 0 && !bytes.Contains(trimmed, needle) {
			continue
		}
		rec, ts, parseErr := ParseRecord(trimmed)
		if parseErr != nil {
			continue
		}
		if !s.matchesSubject(rec, subj) {
			continue
		}
		day := ts.UTC().Format(DayLayout)
		if day < fromDay || day > toDay {
			continue
		}
		endpoint := resolveEndpointLabel(rec, knownRoutes)
		key := bucketKey{day: day, model: rec.Model, endpoint: endpoint}
		agg := merged[key]
		if agg == nil {
			agg = &Agg{}
			merged[key] = agg
		}
		agg.Add(rec)
	}
	return false, false, nil
}

func (s *LedgerSource) matchesSubject(rec Record, subj Subject) bool {
	if s.IsDeniedIdentity(rec.Identity) {
		return false
	}
	switch subj.Scope {
	case ScopeIdentity:
		// Includes PAM "user" and historical "poc" records across key rotations,
		// while excluding shared/service keys.
		return rec.Identity == subj.Identity && rec.IdentityType != "service"
	case ScopeKeyFP:
		return rec.KeyFP.Valid() && rec.KeyFP == subj.KeyFP
	default:
		return false
	}
}

func resolveEndpointLabel(rec Record, knownRoutes map[string]bool) string {
	if rec.EndpointKind != EndpointModelRoute {
		return rec.Endpoint
	}
	if rec.Succeeded() || knownRoutes[rec.Endpoint] {
		return rec.Endpoint
	}
	return EndpointOther
}

func (s *LedgerSource) coverageLocked() (oldest, complete time.Time) {
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

// ValidateLedgerRoot verifies root exists and is a readable directory.
func ValidateLedgerRoot(root string) error {
	info, err := os.Stat(root)
	if err != nil {
		return fmt.Errorf("USAGE_LOG_ROOT %q: %w", root, err)
	}
	if !info.IsDir() {
		return fmt.Errorf("USAGE_LOG_ROOT %q is not a directory", root)
	}
	return nil
}
