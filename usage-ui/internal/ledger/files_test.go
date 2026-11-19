package ledger

import (
	"context"
	"fmt"
	"io"
	"io/fs"
	"log"
	"os"
	"path/filepath"
	"reflect"
	"strings"
	"testing"
	"time"
)

func rec(ts, identity, identityType, model string, status int, cold bool, prompt, completion int, gpuSeconds float64) string {
	return fmt.Sprintf(`{"ts":%q,"site":"aleph","identity":%q,"identity_type":%q,"account":%q,"endpoint":"/v1/chat/completions","api":"openai","model":%q,"status":%d,"stream":false,"cold_start":%t,"latency_ms":1000,"tokens":{"prompt":%d,"completion":%d,"total":%d,"detail":{}},"derived":{"gpu_seconds":%g}}`+"\n",
		ts, identity, identityType, identity, model, status, cold, prompt, completion, prompt+completion, gpuSeconds)
}

func write(t *testing.T, path, content string) {
	t.Helper()
	if err := os.MkdirAll(filepath.Dir(path), 0o755); err != nil {
		t.Fatal(err)
	}
	if err := os.WriteFile(path, []byte(content), 0o644); err != nil {
		t.Fatal(err)
	}
}

func appendTo(t *testing.T, path, content string) {
	t.Helper()
	file, err := os.OpenFile(path, os.O_APPEND|os.O_WRONLY, 0o644)
	if err != nil {
		t.Fatal(err)
	}
	defer file.Close()
	if _, err := file.WriteString(content); err != nil {
		t.Fatal(err)
	}
}

var (
	day1 = time.Date(2026, 11, 1, 0, 0, 0, 0, time.UTC)
	day9 = time.Date(2026, 11, 9, 0, 0, 0, 0, time.UTC)
)

func totals(t *testing.T, src *FileSource, user string) Agg {
	t.Helper()
	report, err := src.Usage(context.Background(), user, day1, day9)
	if err != nil {
		t.Fatal(err)
	}
	var sum Agg
	for _, row := range report.Rows {
		sum.Merge(&row.Agg)
	}
	return sum
}

func mustRefresh(t *testing.T, src *FileSource) {
	t.Helper()
	if _, err := src.Refresh(); err != nil {
		t.Fatal(err)
	}
}

// rowTotal is the part of a report row the reader's tests check.
type rowTotal struct {
	Day      string
	Model    string
	Requests int64
	Tokens   int64
}

// rowsOf returns user's rows from 1 to 9 November 2026.
func rowsOf(t *testing.T, src *FileSource, user string) []rowTotal {
	t.Helper()
	report, err := src.Usage(context.Background(), user, day1, day9)
	if err != nil {
		t.Fatal(err)
	}
	out := []rowTotal{}
	for _, row := range report.Rows {
		out = append(out, rowTotal{row.Day, row.Model, row.Requests, row.TotalTokens})
	}
	return out
}

func assertRows(t *testing.T, src *FileSource, user string, want []rowTotal) {
	t.Helper()
	if got := rowsOf(t, src, user); !reflect.DeepEqual(got, want) {
		t.Errorf("%s's rows:\n got %+v\nwant %+v", user, got, want)
	}
}

// sharedLedger holds alice's and bob's usage and a service key's.
func sharedLedger(t *testing.T) *FileSource {
	t.Helper()
	root := t.TempDir()
	write(t, filepath.Join(root, "pod-a", "usage.log"),
		rec("2026-11-02T10:00:00Z", "alice", "user", "m1", 200, false, 10, 5, 1)+
			rec("2026-11-02T11:00:00Z", "bob", "user", "m2", 200, false, 100, 50, 2)+
			rec("2026-11-02T12:00:00Z", "service-webui", "service", "m3", 200, false, 999, 999, 9)+
			rec("2026-11-02T13:00:00Z", "alice", "service", "m4", 200, false, 888, 888, 9))
	src := NewFileSource(root, 0)
	mustRefresh(t, src)
	return src
}

func TestUsageHoldsOnlyTheRequestedUsersRecords(t *testing.T) {
	src := sharedLedger(t)
	assertRows(t, src, "alice", []rowTotal{{"2026-11-02", "m1", 1, 15}})
	assertRows(t, src, "bob", []rowTotal{{"2026-11-02", "m2", 1, 150}})
}

// Only identity_type user is reported: a service key's records never are,
// even under its own identity or one that matches a user's.
func TestServiceKeyRecordsAreNeverReported(t *testing.T) {
	src := sharedLedger(t)
	assertRows(t, src, "service-webui", []rowTotal{})
	assertRows(t, src, "alice", []rowTotal{{"2026-11-02", "m1", 1, 15}})
}

func TestUnknownUserHasNoUsage(t *testing.T) {
	assertRows(t, sharedLedger(t), "nobody", []rowTotal{})
}

func TestHalfWrittenLineIsCountedOnlyOnceComplete(t *testing.T) {
	root := t.TempDir()
	log := filepath.Join(root, "pod-a", "usage.log")
	write(t, log, rec("2026-11-02T10:00:00Z", "alice", "user", "m1", 200, false, 10, 0, 1))
	src := NewFileSource(root, 0)
	mustRefresh(t, src)

	full := rec("2026-11-02T11:00:00Z", "alice", "user", "m1", 200, false, 20, 0, 1)
	appendTo(t, log, full[:40])
	mustRefresh(t, src)
	assertRows(t, src, "alice", []rowTotal{{"2026-11-02", "m1", 1, 10}})

	appendTo(t, log, full[40:])
	mustRefresh(t, src)
	assertRows(t, src, "alice", []rowTotal{{"2026-11-02", "m1", 2, 30}})
}

// The gateway renames usage.log to usage.log.1 and starts a new usage.log.
func TestRotationCountsEveryRecordOnce(t *testing.T) {
	root := t.TempDir()
	log := filepath.Join(root, "pod-a", "usage.log")
	write(t, log, rec("2026-11-02T10:00:00Z", "alice", "user", "m1", 200, false, 10, 0, 1))
	src := NewFileSource(root, 0)
	mustRefresh(t, src)

	if err := os.Rename(log, log+".1"); err != nil {
		t.Fatal(err)
	}
	write(t, log, rec("2026-11-03T09:00:00Z", "alice", "user", "m2", 200, false, 5, 0, 1))
	mustRefresh(t, src)
	assertRows(t, src, "alice", []rowTotal{{"2026-11-02", "m1", 1, 10}, {"2026-11-03", "m2", 1, 5}})
}

// When rotation deletes the oldest file, its usage leaves the report once
// the file has been missing for dropAfterMissedRefreshes refreshes.
func TestDeletedFilesUsageLeavesTheReport(t *testing.T) {
	root := t.TempDir()
	pod := filepath.Join(root, "pod-a")
	write(t, filepath.Join(pod, "usage.log.1"), rec("2026-11-02T10:00:00Z", "alice", "user", "m1", 200, false, 10, 0, 1))
	write(t, filepath.Join(pod, "usage.log"), rec("2026-11-03T09:00:00Z", "alice", "user", "m2", 200, false, 5, 0, 1))
	src := NewFileSource(root, 0)
	mustRefresh(t, src)

	if err := os.Remove(filepath.Join(pod, "usage.log.1")); err != nil {
		t.Fatal(err)
	}
	refreshUntilDropped(t, src)
	assertRows(t, src, "alice", []rowTotal{{"2026-11-03", "m2", 1, 5}})
}

// refreshUntilDropped refreshes enough times for a file deleted since the
// last refresh to be dropped.
func refreshUntilDropped(t *testing.T, src *FileSource) {
	t.Helper()
	for range dropAfterMissedRefreshes {
		mustRefresh(t, src)
	}
}

// failingReads makes src's directory listing or file opening fail for the
// paths that fail returns true for, as unreadable NFS entries would.
func failingReads(src *FileSource, failDir, failOpen func(path string) bool) {
	readDir, openFile := src.readDir, src.openFile
	src.readDir = func(name string) ([]os.DirEntry, error) {
		if failDir != nil && failDir(name) {
			return nil, &fs.PathError{Op: "open", Path: name, Err: fs.ErrPermission}
		}
		return readDir(name)
	}
	src.openFile = func(name string) (*os.File, error) {
		if failOpen != nil && failOpen(name) {
			return nil, &fs.PathError{Op: "open", Path: name, Err: fs.ErrPermission}
		}
		return openFile(name)
	}
}

// twoPodLedger has 10 of alice's tokens in pod-a and 20 in pod-b.
func twoPodLedger(t *testing.T) (src *FileSource, podA string) {
	t.Helper()
	root := t.TempDir()
	podA = filepath.Join(root, "pod-a")
	write(t, filepath.Join(podA, "usage.log"), rec("2026-11-02T10:00:00Z", "alice", "user", "m1", 200, false, 10, 0, 1))
	write(t, filepath.Join(root, "pod-b", "usage.log"), rec("2026-11-02T11:00:00Z", "alice", "user", "m1", 200, false, 20, 0, 1))
	src = NewFileSource(root, 0)
	mustRefresh(t, src)
	return src, podA
}

// A pod directory that cannot be listed, or a file that cannot be opened,
// keeps the usage already read from it, however many refreshes fail, and
// the report says the refresh was partial.
func TestUnreadablePartOfTheLedgerKeepsItsUsage(t *testing.T) {
	for _, tc := range []struct {
		name string
		fail func(src *FileSource, podA string)
	}{
		{"a pod directory that cannot be listed", func(src *FileSource, podA string) {
			failingReads(src, func(path string) bool { return path == podA }, nil)
		}},
		{"a file that cannot be opened", func(src *FileSource, podA string) {
			failingReads(src, nil, func(path string) bool { return filepath.Dir(path) == podA })
		}},
	} {
		t.Run(tc.name, func(t *testing.T) {
			src, podA := twoPodLedger(t)
			tc.fail(src, podA)
			for range dropAfterMissedRefreshes + 1 {
				mustRefresh(t, src)
			}
			assertRows(t, src, "alice", []rowTotal{{"2026-11-02", "m1", 2, 30}})
			report, err := src.Usage(context.Background(), "alice", day1, day9)
			if err != nil {
				t.Fatal(err)
			}
			if !src.LastRefreshPartial() || !report.ReadErrors {
				t.Errorf("LastRefreshPartial %v, Report.ReadErrors %v; want both true", src.LastRefreshPartial(), report.ReadErrors)
			}
		})
	}
}

func TestCleanRefreshIsNotPartial(t *testing.T) {
	src, _ := twoPodLedger(t)
	if src.LastRefreshPartial() {
		t.Error("a clean refresh was marked partial")
	}
}

// Once reads work again, the partial flag clears and nothing is counted
// twice.
func TestRecoveryFromReadErrorsClearsTheFlagWithoutDoubleCounting(t *testing.T) {
	src, podA := twoPodLedger(t)
	readDir, openFile := src.readDir, src.openFile
	failingReads(src, func(path string) bool { return path == podA }, nil)
	mustRefresh(t, src)
	src.readDir, src.openFile = readDir, openFile
	mustRefresh(t, src)
	if src.LastRefreshPartial() {
		t.Error("LastRefreshPartial stayed true after a clean refresh")
	}
	assertRows(t, src, "alice", []rowTotal{{"2026-11-02", "m1", 2, 30}})
}

// If the root itself cannot be listed, Refresh fails, keeps every file's
// usage, and marks the refresh partial.
func TestRootReadErrorKeepsUsage(t *testing.T) {
	root := t.TempDir()
	write(t, filepath.Join(root, "pod-a", "usage.log"), rec("2026-11-02T10:00:00Z", "alice", "user", "m1", 200, false, 10, 0, 1))
	src := NewFileSource(root, 0)
	mustRefresh(t, src)
	failingReads(src, func(path string) bool { return path == root }, nil)
	if _, err := src.Refresh(); err == nil {
		t.Fatal("Refresh succeeded with an unreadable root")
	}
	if got := totals(t, src, "alice"); got.TotalTokens != 10 {
		t.Errorf("usage = %d tokens, want 10", got.TotalTokens)
	}
	if !src.LastRefreshPartial() {
		t.Error("LastRefreshPartial is false after the root could not be listed")
	}
}

// rotatingLedger has alice's 10 tokens in usage.log.1 and 20 in usage.log.
// hide makes usage.log.1 look absent (not found) to the reader, as a
// rotation in progress does; show undoes it.
func rotatingLedger(t *testing.T) (src *FileSource, hide, show func()) {
	t.Helper()
	root := t.TempDir()
	pod := filepath.Join(root, "pod-a")
	rotated := filepath.Join(pod, "usage.log.1")
	write(t, rotated, rec("2026-11-02T10:00:00Z", "alice", "user", "m1", 200, false, 10, 0, 1))
	write(t, filepath.Join(pod, "usage.log"), rec("2026-11-03T10:00:00Z", "alice", "user", "m1", 200, false, 20, 0, 1))
	src = NewFileSource(root, 0)
	mustRefresh(t, src)
	openFile := src.openFile
	hide = func() {
		src.openFile = func(name string) (*os.File, error) {
			if name == rotated {
				return nil, &fs.PathError{Op: "open", Path: name, Err: fs.ErrNotExist}
			}
			return openFile(name)
		}
	}
	show = func() { src.openFile = openFile }
	return src, hide, show
}

var bothRotatedFiles = []rowTotal{{"2026-11-02", "m1", 1, 10}, {"2026-11-03", "m1", 1, 20}}

// A rotation in progress can hide a file from one refresh: the listing
// names it before a rename and opening it fails after. One miss must not
// drop its usage, and is not a read error.
func TestFileMissingFromOneRefreshKeepsItsUsage(t *testing.T) {
	src, hide, _ := rotatingLedger(t)
	hide()
	mustRefresh(t, src)
	assertRows(t, src, "alice", bothRotatedFiles)
	if src.LastRefreshPartial() {
		t.Error("a file that was not found is not a read error")
	}
}

func TestFileMissingFromTwoRefreshesInARowIsDropped(t *testing.T) {
	src, hide, _ := rotatingLedger(t)
	hide()
	mustRefresh(t, src)
	mustRefresh(t, src)
	assertRows(t, src, "alice", []rowTotal{{"2026-11-03", "m1", 1, 20}})
}

// Found again, the miss is forgotten, so a later single miss is tolerated
// too.
func TestSeparateSingleMissesDoNotAddUp(t *testing.T) {
	src, hide, show := rotatingLedger(t)
	hide()
	mustRefresh(t, src)
	show()
	mustRefresh(t, src)
	hide()
	mustRefresh(t, src)
	assertRows(t, src, "alice", bothRotatedFiles)
}

// A file whose start changed is a different file, even with the same ID: it
// is read from the start instead of from the old file's offset. With inode
// IDs this is a reused inode; with path IDs, another file renamed into place.
func TestReplacedFileIsReadFromStart(t *testing.T) {
	root := t.TempDir()
	log := filepath.Join(root, "pod-a", "usage.log")
	write(t, log, rec("2026-11-02T10:00:00Z", "alice", "user", "m1", 200, false, 10, 0, 1))
	src := NewFileSource(root, 0)
	mustRefresh(t, src)

	// Rewrite in place (same inode) with two records, so the file is larger
	// than the old offset and a size check alone would miss the change.
	file, err := os.OpenFile(log, os.O_WRONLY|os.O_TRUNC, 0)
	if err != nil {
		t.Fatal(err)
	}
	_, err = file.WriteString(rec("2026-11-04T10:00:00Z", "alice", "user", "m1", 200, false, 40, 0, 1) +
		rec("2026-11-04T11:00:00Z", "alice", "user", "m1", 200, false, 50, 0, 1))
	file.Close()
	if err != nil {
		t.Fatal(err)
	}
	mustRefresh(t, src)
	assertRows(t, src, "alice", []rowTotal{{"2026-11-04", "m1", 2, 90}})
}

// refreshLogged logs the malformed-line count only when it has grown, with
// the growth and the running total.
func TestMalformedLineCountIsLoggedOnlyWhenItGrows(t *testing.T) {
	root := t.TempDir()
	path := filepath.Join(root, "pod-a", "usage.log")
	write(t, path, "not json\n")
	src := NewFileSource(root, 0)
	var logged strings.Builder
	defer captureLog(&logged)()

	src.refreshLogged()
	src.refreshLogged()
	appendTo(t, path, "{\"also\":\"bad\"}\n")
	src.refreshLogged()
	want := "ledger: skipped 1 malformed lines (total 1); a gateway format change?\n" +
		"ledger: skipped 1 malformed lines (total 2); a gateway format change?\n"
	if got := logged.String(); got != want {
		t.Errorf("log:\n got %q\nwant %q", got, want)
	}
}

// captureLog sends the standard logger to w and returns a function that
// restores it.
func captureLog(w io.Writer) func() {
	writer, flags := log.Writer(), log.Flags()
	log.SetOutput(w)
	log.SetFlags(0)
	return func() {
		log.SetOutput(writer)
		log.SetFlags(flags)
	}
}

// Cold-start guard records (cold_start true, status 503) are model
// wake-ups: counted apart, and not as requests or errors.
func TestColdStartsCountAsWakeUpsNotRequests(t *testing.T) {
	root := t.TempDir()
	write(t, filepath.Join(root, "pod-a", "usage.log"),
		rec("2026-11-02T10:00:00Z", "alice", "user", "m1", 503, true, 0, 0, 0)+
			rec("2026-11-02T10:01:00Z", "alice", "user", "m1", 200, false, 10, 0, 1)+
			rec("2026-11-02T10:01:30Z", "alice", "user", "m1", 503, true, 0, 0, 0)+
			rec("2026-11-02T10:02:00Z", "alice", "user", "m1", 500, false, 0, 0, 0))
	src := NewFileSource(root, 0)
	mustRefresh(t, src)
	got := totals(t, src, "alice")
	if got.ColdStarts != 2 || got.Requests != 2 || got.Errors != 1 || got.TotalTokens != 10 {
		t.Errorf("wake-ups %d, requests %d, errors %d, tokens %d; want 2, 2, 1, 10", got.ColdStarts, got.Requests, got.Errors, got.TotalTokens)
	}
}

func TestMalformedLinesAreSkippedAndCounted(t *testing.T) {
	root := t.TempDir()
	write(t, filepath.Join(root, "pod-a", "usage.log"),
		"not json\n"+rec("2026-11-02T10:01:00Z", "alice", "user", "m1", 200, false, 10, 0, 1)+`{"ts":"yesterday"}`+"\n")
	src := NewFileSource(root, 0)
	mustRefresh(t, src)
	assertRows(t, src, "alice", []rowTotal{{"2026-11-02", "m1", 1, 10}})
	if src.Skipped() != 2 {
		t.Errorf("skipped = %d, want 2", src.Skipped())
	}
}

// Oldest is the earliest record the ledger holds, whatever range is asked
// for.
func TestOldestIsTheEarliestRecordOutsideTheRangeToo(t *testing.T) {
	root := t.TempDir()
	write(t, filepath.Join(root, "pod-a", "usage.log"),
		rec("2026-11-02T10:01:00Z", "alice", "user", "m1", 200, false, 10, 0, 1)+
			rec("2026-10-01T10:00:00Z", "alice", "user", "m1", 200, false, 1000, 0, 1))
	src := NewFileSource(root, 0)
	mustRefresh(t, src)
	report, err := src.Usage(context.Background(), "alice", day1, day9)
	if err != nil {
		t.Fatal(err)
	}
	if want := time.Date(2026, 10, 1, 10, 0, 0, 0, time.UTC); !report.Oldest.Equal(want) {
		t.Errorf("oldest = %v, want %v", report.Oldest, want)
	}
	assertRows(t, src, "alice", []rowTotal{{"2026-11-02", "m1", 1, 10}})
}

func TestOnlyUsageLogAndNumberedRotationsAreLedgerFiles(t *testing.T) {
	for name, want := range map[string]bool{
		"usage.log": true, "usage.log.1": true, "usage.log.12": true,
		"usage.log.": false, "usage.log.bak": false, "app.log": false,
	} {
		if got := isLedgerFile(name); got != want {
			t.Errorf("isLedgerFile(%q) = %v, want %v", name, got, want)
		}
	}
}

// coverageOf refreshes a source over root and returns its coverage.
func coverageOf(t *testing.T, root string, backups int) (oldest, completeFrom time.Time) {
	t.Helper()
	src := NewFileSource(root, backups)
	mustRefresh(t, src)
	report, err := src.Usage(context.Background(), "alice", day1, day9)
	if err != nil {
		t.Fatal(err)
	}
	return report.Oldest, report.CompleteFrom
}

// A retired pod's never-rotated log reaches back further than any live pod,
// but it does not make those older days complete: the live pod has rotated,
// so records it wrote before its oldest remaining file may be gone.
func TestCoverageRetiredPodDoesNotExtendCompleteness(t *testing.T) {
	root := t.TempDir()
	write(t, filepath.Join(root, "gateway-old00", "usage.log"),
		rec("2026-10-12T08:00:00Z", "alice", "user", "m1", 200, false, 10, 5, 1)+
			rec("2026-10-20T08:00:00Z", "alice", "user", "m1", 200, false, 10, 5, 1))
	write(t, filepath.Join(root, "gateway-live00", "usage.log.1"),
		rec("2026-11-05T13:00:00Z", "alice", "user", "m1", 200, false, 10, 5, 1)+
			rec("2026-11-07T09:00:00Z", "alice", "user", "m1", 200, false, 10, 5, 1))
	write(t, filepath.Join(root, "gateway-live00", "usage.log"),
		rec("2026-11-08T10:00:00Z", "alice", "user", "m1", 200, false, 10, 5, 1))

	oldest, completeFrom := coverageOf(t, root, 1)
	if want := time.Date(2026, 10, 12, 8, 0, 0, 0, time.UTC); !oldest.Equal(want) {
		t.Errorf("oldest = %v, want %v", oldest, want)
	}
	if want := time.Date(2026, 11, 5, 13, 0, 0, 0, time.UTC); !completeFrom.Equal(want) {
		t.Errorf("complete from = %v, want %v", completeFrom, want)
	}
}

// Pods that have never rotated have lost nothing, however old their records.
func TestCoverageWithoutRotationIsComplete(t *testing.T) {
	root := t.TempDir()
	write(t, filepath.Join(root, "gateway-old00", "usage.log"),
		rec("2026-10-12T08:00:00Z", "alice", "user", "m1", 200, false, 10, 5, 1))
	write(t, filepath.Join(root, "gateway-live00", "usage.log"),
		rec("2026-11-05T13:00:00Z", "alice", "user", "m1", 200, false, 10, 5, 1))

	oldest, completeFrom := coverageOf(t, root, 0)
	if want := time.Date(2026, 10, 12, 8, 0, 0, 0, time.UTC); !oldest.Equal(want) {
		t.Errorf("oldest = %v, want %v", oldest, want)
	}
	if !completeFrom.IsZero() {
		t.Errorf("complete from = %v, want zero: no file can have been deleted", completeFrom)
	}
}

// With a known rotation count, a pod loses records only once its last
// backup exists; before that every file it wrote is still on the volume.
func TestCoverageWithKnownBackupCount(t *testing.T) {
	root := t.TempDir()
	pod := filepath.Join(root, "gateway-live00")
	write(t, filepath.Join(pod, "usage.log.2"), rec("2026-11-02T06:00:00Z", "alice", "user", "m1", 200, false, 10, 5, 1))
	write(t, filepath.Join(pod, "usage.log.1"), rec("2026-11-03T06:00:00Z", "alice", "user", "m1", 200, false, 10, 5, 1))
	write(t, filepath.Join(pod, "usage.log"), rec("2026-11-04T06:00:00Z", "alice", "user", "m1", 200, false, 10, 5, 1))

	if _, completeFrom := coverageOf(t, root, 5); !completeFrom.IsZero() {
		t.Errorf("with backups 5 and only .1 and .2 present, complete from = %v, want zero", completeFrom)
	}

	write(t, filepath.Join(pod, "usage.log.5"), rec("2026-10-28T06:00:00Z", "alice", "user", "m1", 200, false, 10, 5, 1))
	oldest, completeFrom := coverageOf(t, root, 5)
	want := time.Date(2026, 10, 28, 6, 0, 0, 0, time.UTC)
	if !completeFrom.Equal(want) || !oldest.Equal(want) {
		t.Errorf("with usage.log.5 present: oldest %v, complete from %v, want both %v", oldest, completeFrom, want)
	}
}

// clockOf returns a clock that gives each of times in turn.
func clockOf(t *testing.T, times ...time.Time) func() time.Time {
	return func() time.Time {
		if len(times) == 0 {
			t.Fatal("the clock was read more often than expected")
		}
		next := times[0]
		times = times[1:]
		return next
	}
}

var (
	refreshStart  = time.Date(2026, 11, 18, 0, 4, 0, 0, time.UTC)
	refreshFinish = time.Date(2026, 11, 18, 0, 6, 0, 0, time.UTC)
)

// The daily history judges whether a day is over by when the refresh began,
// so the snapshot keeps the start apart from the finish.
func TestSnapshotRecordsWhenTheLastRefreshStartedAndFinished(t *testing.T) {
	root := t.TempDir()
	write(t, filepath.Join(root, "pod", "usage.log"), rec("2026-11-04T10:00:00Z", "alice", "user", "m1", 200, false, 1, 0, 1))
	src := NewFileSource(root, 0)
	src.Now = clockOf(t, refreshStart, refreshFinish)
	mustRefresh(t, src)
	want := Snapshot{
		Oldest:         time.Date(2026, 11, 4, 10, 0, 0, 0, time.UTC),
		RefreshedAt:    refreshFinish,
		RefreshStarted: refreshStart,
		Ready:          true,
	}
	if got := src.Snapshot(); got != want {
		t.Errorf("snapshot:\n got %+v\nwant %+v", got, want)
	}
}

// OnRefresh runs on Run's goroutine after a refresh, once the refresh's
// state is in place, so the daily history never saves from a half-read
// ledger.
func TestOnRefreshSeesTheFinishedRefresh(t *testing.T) {
	root := t.TempDir()
	write(t, filepath.Join(root, "pod", "usage.log"), rec("2026-11-04T10:00:00Z", "alice", "user", "m1", 200, false, 1, 0, 1))
	src := NewFileSource(root, 0)
	src.Now = clockOf(t, refreshStart, refreshFinish)
	ctx, cancel := context.WithCancel(context.Background())
	var snap Snapshot
	src.OnRefresh = func() {
		snap = src.Snapshot()
		cancel()
	}
	src.Run(ctx, time.Hour) // returns once OnRefresh cancels
	want := Snapshot{
		Oldest:         time.Date(2026, 11, 4, 10, 0, 0, 0, time.UTC),
		RefreshedAt:    refreshFinish,
		RefreshStarted: refreshStart,
		Ready:          true,
	}
	if snap != want {
		t.Errorf("snapshot seen by OnRefresh:\n got %+v\nwant %+v", snap, want)
	}
}
