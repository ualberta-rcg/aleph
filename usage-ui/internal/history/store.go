// Package history keeps one year of daily usage totals, so usage stays
// visible after the gateway's ledger rotates it away.
//
// Once a UTC day is over and the ledger holds every record of it, the
// service writes that day's totals for every user to one small file,
// <dir>/YYYY-MM-DD.jsonl.gz: one line per user, model, and endpoint, holding
// counts only (no prompts, no content). The file's existence means "this day
// was saved complete"; a day with no usage gets an empty file. Files older
// than the retention period are deleted.
//
// A file that cannot be read, for whatever reason, counts as not saved. It
// is written over if the ledger still holds that day, and otherwise left
// until it passes the retention period. Nothing else ever deletes a file.
//
// This is not a database: the files are plain gzipped JSON lines that an
// operator can read with zcat.
package history

import (
	"bufio"
	"compress/gzip"
	"encoding/json"
	"errors"
	"fmt"
	"io/fs"
	"log"
	"os"
	"path/filepath"
	"strings"
	"sync"
	"time"

	"github.com/ualberta-rcg/aleph/usage-ui/internal/ledger"
)

const fileSuffix = ".jsonl.gz"

// Store holds the saved days in memory and on disk. It is safe for
// concurrent use; only one process may write to a directory (the Deployment
// runs one replica, with the Recreate strategy, on its own claim).
type Store struct {
	dir      string
	keepDays int

	mu   sync.RWMutex
	days map[string]map[string][]ledger.Row // day -> user -> rows
}

// Open loads every saved day from dir, creating dir if needed, and checks
// that dir can be written to. keepDays is how many days to keep; Prune
// deletes older files.
func Open(dir string, keepDays int) (*Store, error) {
	if keepDays < 1 {
		return nil, fmt.Errorf("history: keepDays must be at least 1, got %d", keepDays)
	}
	// The files hold every user's totals, so only the service may read them.
	if err := os.MkdirAll(dir, 0o700); err != nil {
		return nil, fmt.Errorf("history: %w", err)
	}
	if err := checkWritable(dir); err != nil {
		return nil, fmt.Errorf("history: %s is not writable, so no day could be saved: %w", dir, err)
	}
	store := &Store{dir: dir, keepDays: keepDays, days: make(map[string]map[string][]ledger.Row)}
	entries, err := os.ReadDir(dir)
	if err != nil {
		return nil, fmt.Errorf("history: %w", err)
	}
	for _, entry := range entries {
		name := entry.Name()
		if strings.HasSuffix(name, ".tmp") {
			// Left by a write that was interrupted before its rename; the
			// day was never saved and will be written again.
			_ = os.Remove(filepath.Join(dir, name))
			continue
		}
		day, ok := dayOfFile(name)
		if !ok || !entry.Type().IsRegular() {
			continue
		}
		rows, err := readDay(filepath.Join(dir, name), day)
		if err != nil {
			log.Printf("history: cannot read %s, so that day counts as not saved: %v", name, err)
			continue
		}
		store.days[day] = rows
	}
	return store, nil
}

// checkWritable writes, syncs, and removes a small file, so a volume that is
// mounted read-only or with the wrong owner stops the service at startup
// rather than failing every save while the pod looks healthy.
func checkWritable(dir string) error {
	path := filepath.Join(dir, ".write-check.tmp")
	file, err := os.OpenFile(path, os.O_CREATE|os.O_TRUNC|os.O_WRONLY, 0o600)
	if err != nil {
		return err
	}
	_, writeErr := file.WriteString("ok\n")
	syncErr := file.Sync()
	closeErr := file.Close()
	removeErr := os.Remove(path)
	return errors.Join(writeErr, syncErr, closeErr, removeErr)
}

// dayOfFile returns the day a file name holds, for names like
// 2026-11-04.jsonl.gz.
func dayOfFile(name string) (string, bool) {
	day, ok := strings.CutSuffix(name, fileSuffix)
	if !ok {
		return "", false
	}
	if _, err := time.Parse(ledger.DayLayout, day); err != nil {
		return "", false
	}
	return day, true
}

func readDay(path, day string) (map[string][]ledger.Row, error) {
	file, err := os.Open(path)
	if err != nil {
		return nil, err
	}
	defer file.Close()
	unzipped, err := gzip.NewReader(file)
	if err != nil {
		return nil, err
	}
	defer unzipped.Close()
	rows := make(map[string][]ledger.Row)
	scanner := bufio.NewScanner(unzipped)
	scanner.Buffer(make([]byte, 64<<10), 1<<20)
	for scanner.Scan() {
		var saved line
		if err := json.Unmarshal(scanner.Bytes(), &saved); err != nil {
			return nil, err
		}
		if saved.Day != day {
			return nil, fmt.Errorf("line for %s in the file for %s", saved.Day, day)
		}
		row, err := saved.row()
		if err != nil {
			return nil, err
		}
		rows[saved.User] = append(rows[saved.User], row)
	}
	if err := scanner.Err(); err != nil {
		return nil, err
	}
	return rows, nil
}

// Has reports whether day (YYYY-MM-DD) was saved and can be read.
func (s *Store) Has(day string) bool {
	s.mu.RLock()
	defer s.mu.RUnlock()
	_, ok := s.days[day]
	return ok
}

// userDays returns which days from fromDay to toDay are saved, with one
// user's rows for each. It reads under one lock, so a prune at the same
// moment cannot make a day look saved but empty.
func (s *Store) userDays(user, fromDay, toDay string) map[string][]ledger.Row {
	s.mu.RLock()
	defer s.mu.RUnlock()
	saved := make(map[string][]ledger.Row)
	for day, users := range s.days {
		if day >= fromDay && day <= toDay {
			saved[day] = users[user]
		}
	}
	return saved
}

// Oldest returns the earliest saved day, or "" if none.
func (s *Store) Oldest() string {
	s.mu.RLock()
	defer s.mu.RUnlock()
	oldest := ""
	for day := range s.days {
		if oldest == "" || day < oldest {
			oldest = day
		}
	}
	return oldest
}

// Save writes one day's totals for every user and remembers them. The file
// is written under a temporary name, synced, and renamed over any unreadable
// file for that day, and the directory is synced, so a crash never leaves a
// half-written day that looks saved. Saving a day that is already saved is
// an error: a saved day is final.
func (s *Store) Save(day string, rows map[string][]ledger.Row) error {
	if _, err := time.Parse(ledger.DayLayout, day); err != nil {
		return fmt.Errorf("history: bad day %q", day)
	}
	if s.Has(day) {
		return fmt.Errorf("history: %s is already saved", day)
	}
	final := filepath.Join(s.dir, day+fileSuffix)
	temporary := final + ".tmp"
	if err := writeDay(temporary, day, rows); err != nil {
		_ = os.Remove(temporary)
		return fmt.Errorf("history: write %s: %w", day, err)
	}
	if err := os.Rename(temporary, final); err != nil {
		_ = os.Remove(temporary)
		return fmt.Errorf("history: save %s: %w", day, err)
	}
	s.mu.Lock()
	s.days[day] = rows
	s.mu.Unlock()
	// The file is in place and readable; a failed directory sync only means
	// a crash of the node could still lose the rename. The day stays saved,
	// so later days are not held up retrying it.
	if err := syncDir(s.dir); err != nil {
		log.Printf("history: saved %s, but syncing %s failed: %v", day, s.dir, err)
	}
	return nil
}

func writeDay(path, day string, rows map[string][]ledger.Row) error {
	file, err := os.OpenFile(path, os.O_CREATE|os.O_EXCL|os.O_WRONLY, 0o600)
	if err != nil {
		return err
	}
	zipped := gzip.NewWriter(file)
	encoder := json.NewEncoder(zipped)
	for user, userRows := range rows {
		for _, row := range userRows {
			if row.Day != day {
				return errors.Join(fmt.Errorf("row for %s in day %s", row.Day, day), file.Close())
			}
			if err := encoder.Encode(lineFromRow(user, row)); err != nil {
				return errors.Join(err, file.Close())
			}
		}
	}
	if err := zipped.Close(); err != nil {
		return errors.Join(err, file.Close())
	}
	// Flush to disk before the rename makes the day count as saved.
	if err := file.Sync(); err != nil {
		return errors.Join(err, file.Close())
	}
	return file.Close()
}

// retentionStart is the oldest day kept, counted back from today (UTC).
func (s *Store) retentionStart(today time.Time) time.Time {
	return ledger.DayOf(today).AddDate(0, 0, -(s.keepDays - 1))
}

// Prune deletes every day file older than the retention period, going by
// the dates in the file names, so unreadable files go on time too. The lock
// is held only to update memory, not while files are removed.
func (s *Store) Prune(today time.Time) {
	oldestKept := s.retentionStart(today).Format(ledger.DayLayout)
	entries, err := os.ReadDir(s.dir)
	if err != nil {
		log.Printf("history: cannot list %s to delete old days: %v", s.dir, err)
		return
	}
	for _, entry := range entries {
		day, ok := dayOfFile(entry.Name())
		if !ok || day >= oldestKept {
			continue
		}
		err := os.Remove(filepath.Join(s.dir, entry.Name()))
		if err != nil && !errors.Is(err, fs.ErrNotExist) {
			log.Printf("history: cannot delete %s: %v", entry.Name(), err)
			continue
		}
		s.mu.Lock()
		delete(s.days, day)
		s.mu.Unlock()
	}
}
