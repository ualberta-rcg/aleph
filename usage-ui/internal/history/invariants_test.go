package history

import (
	"bytes"
	"os"
	"path/filepath"
	"reflect"
	"testing"
	"time"

	"github.com/ualberta-rcg/aleph/usage-ui/internal/ledger"
)

// The daily history's guarantees. Each is proven by the subtest of the same
// name below:
//
//   - a day is saved only after a refresh starts five minutes past its end
//   - a day the ledger holds only in part is never saved
//   - nothing is saved before the ledger has been read
//   - a saved day is never rewritten
//   - an unreadable day file stays on disk until it passes the retention period
//   - a day is incomplete unless the ledger holds it in full or it was saved
func TestHistoryInvariants(t *testing.T) {
	t.Run("a day is saved only after a refresh starts five minutes past its end", daySavedOnlyOnceOver)
	t.Run("a day the ledger holds only in part is never saved", partlyHeldDayNeverSaved)
	t.Run("nothing is saved before the ledger has been read", nothingSavedBeforeLedgerRead)
	t.Run("a saved day is never rewritten", savedDayNeverRewritten)
	t.Run("an unreadable day file stays on disk until it passes the retention period", unreadableFileKeptUntilRetention)
	t.Run("a day is incomplete unless the ledger holds it in full or it was saved", incompleteUnlessHeldOrSaved)
}

func daySavedOnlyOnceOver(t *testing.T) {
	root := writeLedger(t, map[string]string{"pod/usage.log": record(day(11, 16, 9), "alice", 5) +
		record(time.Date(2026, 11, 17, 23, 59, 0, 0, time.UTC), "alice", 6)})
	store := openStore(t, t.TempDir(), 366)

	// A slow refresh that began before midnight and finished well after it
	// has not read the whole of 17 November.
	slow := ledger.NewFileSource(root, 0)
	stamps := []time.Time{time.Date(2026, 11, 17, 23, 59, 30, 0, time.UTC), time.Date(2026, 11, 18, 0, 10, 0, 0, time.UTC)}
	slow.Now = func() time.Time {
		stamp := stamps[0]
		stamps = stamps[1:]
		return stamp
	}
	if _, err := slow.Refresh(); err != nil {
		t.Fatal(err)
	}
	if _, err := (Source{Ledger: slow, Store: store}).SaveCompleteDays(refreshTime); err != nil {
		t.Fatal(err)
	}
	if !store.Has("2026-11-16") || store.Has("2026-11-17") {
		t.Fatalf("after a refresh started at 23:59:30: 16 November saved %v (want true), 17 November saved %v (want false)",
			store.Has("2026-11-16"), store.Has("2026-11-17"))
	}

	early := readLedger(t, root, time.Date(2026, 11, 18, 0, 4, 59, 0, time.UTC))
	if _, err := (Source{Ledger: early, Store: store}).SaveCompleteDays(refreshTime); err != nil {
		t.Fatal(err)
	}
	if store.Has("2026-11-17") {
		t.Fatal("17 November was saved by a refresh that started 4m59s after it ended")
	}

	settled := readLedger(t, root, time.Date(2026, 11, 18, 0, 5, 0, 0, time.UTC))
	if _, err := (Source{Ledger: settled, Store: store}).SaveCompleteDays(refreshTime); err != nil {
		t.Fatal(err)
	}
	if !store.Has("2026-11-17") {
		t.Error("17 November should be saved by a refresh that started 5 minutes after it ended")
	}
}

func partlyHeldDayNeverSaved(t *testing.T) {
	// A rotated file starting mid-afternoon on 15 November: records from
	// that morning may have been deleted.
	src := ledgerWith(t, map[string]string{"pod/usage.log.1": record(day(11, 15, 13), "alice", 5) + record(day(11, 16, 9), "alice", 6)})
	dir := t.TempDir()
	store := openStore(t, dir, 366)
	if _, err := (Source{Ledger: src, Store: store}).SaveCompleteDays(refreshTime); err != nil {
		t.Fatal(err)
	}
	assertMissing(t, filepath.Join(dir, "2026-11-15"+fileSuffix))
	if store.Has("2026-11-15") {
		t.Error("15 November counts as saved")
	}
	if !store.Has("2026-11-16") || !store.Has("2026-11-17") {
		t.Error("16 and 17 November are held in full and over, so they should be saved")
	}
}

func nothingSavedBeforeLedgerRead(t *testing.T) {
	for _, tc := range []struct {
		name string
		src  *ledger.FileSource
	}{
		{"a ledger that has not been refreshed", ledger.NewFileSource(writeLedger(t, map[string]string{"pod/usage.log": record(day(11, 16, 9), "alice", 5)}), 0)},
		{"a ledger with no records", readLedger(t, t.TempDir(), refreshTime)},
	} {
		t.Run(tc.name, func(t *testing.T) {
			dir := t.TempDir()
			saved, err := Source{Ledger: tc.src, Store: openStore(t, dir, 366)}.SaveCompleteDays(refreshTime)
			if err != nil || saved != 0 {
				t.Errorf("saved %d days with error %v, want 0 and no error", saved, err)
			}
			entries, err := os.ReadDir(dir)
			if err != nil {
				t.Fatal(err)
			}
			if len(entries) != 0 {
				t.Errorf("files written: %v", entries)
			}
		})
	}
}

func savedDayNeverRewritten(t *testing.T) {
	root := writeLedger(t, map[string]string{"pod/usage.log": record(day(11, 16, 9), "alice", 42)})
	dir := t.TempDir()
	store := openStore(t, dir, 366)
	if _, err := (Source{Ledger: readLedger(t, root, refreshTime), Store: store}).SaveCompleteDays(refreshTime); err != nil {
		t.Fatal(err)
	}
	path := filepath.Join(dir, "2026-11-16"+fileSuffix)
	original := readFile(t, path)

	// A record for 16 November turns up in the ledger later.
	late, err := os.OpenFile(filepath.Join(root, "pod", "usage.log"), os.O_APPEND|os.O_WRONLY, 0)
	if err != nil {
		t.Fatal(err)
	}
	if _, err := late.WriteString(record(day(11, 16, 22), "alice", 1000)); err != nil {
		t.Fatal(err)
	}
	if err := late.Close(); err != nil {
		t.Fatal(err)
	}
	if _, err := (Source{Ledger: readLedger(t, root, refreshTime.AddDate(0, 0, 1)), Store: store}).SaveCompleteDays(refreshTime.AddDate(0, 0, 1)); err != nil {
		t.Fatal(err)
	}
	if err := store.Save("2026-11-16", aliceRows("2026-11-16", 7)); err == nil {
		t.Error("saving 16 November a second time was accepted")
	}

	if !bytes.Equal(readFile(t, path), original) {
		t.Error("the saved file for 16 November changed")
	}
	want := map[string][]usageRow{"2026-11-16": {{"2026-11-16", "m", 1, 42}}}
	got := map[string][]usageRow{}
	for savedDay, rows := range openStore(t, dir, 366).userDays("alice", "2026-11-16", "2026-11-16") {
		got[savedDay] = usageRows(rows)
	}
	if !reflect.DeepEqual(got, want) {
		t.Errorf("saved rows after reopening = %+v, want %+v", got, want)
	}
}

func unreadableFileKeptUntilRetention(t *testing.T) {
	// The ledger holds 16 November onward in full, so the unreadable
	// 10 November file cannot be written over.
	src := ledgerWith(t, map[string]string{"pod/usage.log.1": record(day(11, 15, 13), "alice", 5)})
	dir := t.TempDir()
	path := writeDayFile(t, dir, "2026-11-10", []byte("not gzip"))
	store := openStore(t, dir, 366)
	combined := Source{Ledger: src, Store: store}

	combined.Updater(func() time.Time { return refreshTime })()
	if !bytes.Equal(readFile(t, path), []byte("not gzip")) {
		t.Fatal("the unreadable file was changed or deleted within the retention period")
	}
	report := usage(t, combined, "alice", day(11, 10, 0), day(11, 10, 0))
	if want := []string{"2026-11-10"}; !reflect.DeepEqual(report.Incomplete, want) {
		t.Errorf("incomplete = %v, want %v", report.Incomplete, want)
	}

	// Keeping 366 days on 11 November 2027 keeps 11 November 2026 onward.
	store.Prune(time.Date(2027, 11, 11, 12, 0, 0, 0, time.UTC))
	assertMissing(t, path)
}

func incompleteUnlessHeldOrSaved(t *testing.T) {
	// The ledger holds 6 November onward in full; 3 November was saved.
	src := ledgerWith(t, map[string]string{"pod/usage.log.1": record(day(11, 5, 13), "alice", 7)})
	store := openStore(t, t.TempDir(), 366)
	if err := store.Save("2026-11-03", aliceRows("2026-11-03", 300)); err != nil {
		t.Fatal(err)
	}
	report := usage(t, Source{Ledger: src, Store: store}, "alice", day(11, 1, 0), day(11, 8, 0))
	if want := []string{"2026-11-01", "2026-11-02", "2026-11-04", "2026-11-05"}; !reflect.DeepEqual(report.Incomplete, want) {
		t.Errorf("incomplete = %v, want %v", report.Incomplete, want)
	}
	want := []usageRow{{"2026-11-03", "m", 1, 300}, {"2026-11-05", "m", 1, 7}}
	if got := usageRows(report.Rows); !reflect.DeepEqual(got, want) {
		t.Errorf("rows = %+v, want %+v", got, want)
	}
}
