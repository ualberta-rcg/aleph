package history

import (
	"bytes"
	"compress/gzip"
	"context"
	"encoding/json"
	"fmt"
	"io"
	"os"
	"path/filepath"
	"reflect"
	"testing"
	"time"

	"github.com/ualberta-rcg/aleph/usage-ui/internal/ledger"
)

// refreshTime is when the ledger refreshes in most tests: midday on
// 18 November 2026, so 17 November is the last day that is over.
var refreshTime = time.Date(2026, 11, 18, 12, 0, 0, 0, time.UTC)

func day(month time.Month, date, hour int) time.Time {
	return time.Date(2026, month, date, hour, 0, 0, 0, time.UTC)
}

// record is one ledger line: a successful chat request by user with the
// given total tokens.
func record(ts time.Time, user string, tokens int) string {
	return fmt.Sprintf(`{"ts":%q,"identity":%q,"identity_type":"user","endpoint":"/v1/chat/completions","model":"m","status":200,"latency_ms":100,"tokens":{"prompt":%d,"completion":0,"total":%d},"derived":{"gpu_seconds":0.1}}`+"\n",
		ts.UTC().Format(ledger.TimeLayout), user, tokens, tokens)
}

// writeLedger writes ledger files, by path relative to a new root, and
// returns the root.
func writeLedger(t *testing.T, files map[string]string) string {
	t.Helper()
	root := t.TempDir()
	for name, content := range files {
		path := filepath.Join(root, filepath.FromSlash(name))
		if err := os.MkdirAll(filepath.Dir(path), 0o755); err != nil {
			t.Fatal(err)
		}
		if err := os.WriteFile(path, []byte(content), 0o644); err != nil {
			t.Fatal(err)
		}
	}
	return root
}

// readLedger reads the ledger at root with one refresh that starts and
// finishes at refreshed.
func readLedger(t *testing.T, root string, refreshed time.Time) *ledger.FileSource {
	t.Helper()
	src := ledger.NewFileSource(root, 0)
	src.Now = func() time.Time { return refreshed }
	if _, err := src.Refresh(); err != nil {
		t.Fatal(err)
	}
	return src
}

// ledgerWith writes ledger files and reads them with a refresh at
// refreshTime.
func ledgerWith(t *testing.T, files map[string]string) *ledger.FileSource {
	t.Helper()
	return readLedger(t, writeLedger(t, files), refreshTime)
}

func openStore(t *testing.T, dir string, keepDays int) *Store {
	t.Helper()
	store, err := Open(dir, keepDays)
	if err != nil {
		t.Fatal(err)
	}
	return store
}

func chatRow(day string, requests, tokens int64) ledger.Row {
	return ledger.Row{Day: day, Model: "m", Endpoint: "/v1/chat/completions", Agg: ledger.Agg{Requests: requests, TotalTokens: tokens}}
}

func aliceRows(day string, tokens int64) map[string][]ledger.Row {
	return map[string][]ledger.Row{"alice": {chatRow(day, 1, tokens)}}
}

func gzipped(t *testing.T, content string) []byte {
	t.Helper()
	var buffer bytes.Buffer
	zipped := gzip.NewWriter(&buffer)
	if _, err := zipped.Write([]byte(content)); err != nil {
		t.Fatal(err)
	}
	if err := zipped.Close(); err != nil {
		t.Fatal(err)
	}
	return buffer.Bytes()
}

func writeDayFile(t *testing.T, dir, day string, content []byte) string {
	t.Helper()
	path := filepath.Join(dir, day+fileSuffix)
	if err := os.WriteFile(path, content, 0o600); err != nil {
		t.Fatal(err)
	}
	return path
}

func readFile(t *testing.T, path string) []byte {
	t.Helper()
	content, err := os.ReadFile(path)
	if err != nil {
		t.Fatal(err)
	}
	return content
}

func assertMissing(t *testing.T, path string) {
	t.Helper()
	if _, err := os.Stat(path); !os.IsNotExist(err) {
		t.Errorf("%s should not exist (stat error %v)", filepath.Base(path), err)
	}
}

// usageRow is the part of a report row these tests check.
type usageRow struct {
	Day      string
	Model    string
	Requests int64
	Tokens   int64
}

func usageRows(rows []ledger.Row) []usageRow {
	out := []usageRow{}
	for _, row := range rows {
		out = append(out, usageRow{row.Day, row.Model, row.Requests, row.TotalTokens})
	}
	return out
}

func usage(t *testing.T, source Source, user string, from, to time.Time) ledger.Report {
	t.Helper()
	report, err := source.Usage(context.Background(), user, from, to)
	if err != nil {
		t.Fatal(err)
	}
	return report
}

// Every field of ledger.Agg must survive a save and load, or a saved day
// would show different figures from the ones the pages showed live. Each
// field gets a distinct value, so a field that is dropped or swapped fails.
// (line.go names this test.)
func TestLineKeepsEveryAggField(t *testing.T) {
	var agg ledger.Agg
	value := reflect.ValueOf(&agg).Elem()
	next := int64(1)
	for index := 0; index < value.NumField(); index++ {
		field := value.Field(index)
		switch field.Kind() {
		case reflect.Int64:
			field.SetInt(next)
		case reflect.Float64:
			field.SetFloat(float64(next) + 0.5)
		case reflect.Array:
			for bucket := 0; bucket < field.Len(); bucket++ {
				field.Index(bucket).SetInt(next * 100 * int64(bucket+1))
			}
		default:
			t.Fatalf("Agg.%s has kind %s; teach line.go and this test about it", value.Type().Field(index).Name, field.Kind())
		}
		next++
	}
	original := ledger.Row{Day: "2026-11-04", Model: "m", Endpoint: "/v1/chat/completions", Agg: agg}

	encoded, err := json.Marshal(lineFromRow("alice", original))
	if err != nil {
		t.Fatal(err)
	}
	var decoded line
	if err := json.Unmarshal(encoded, &decoded); err != nil {
		t.Fatal(err)
	}
	got, err := decoded.row()
	if err != nil {
		t.Fatal(err)
	}
	if !reflect.DeepEqual(got, original) {
		t.Fatalf("round trip changed the row:\n got %+v\nwant %+v", got, original)
	}
	if decoded.User != "alice" {
		t.Errorf("user = %q, want alice", decoded.User)
	}
}

func TestSavedDayIsReadBackAfterReopening(t *testing.T) {
	dir := t.TempDir()
	alice := []ledger.Row{
		chatRow("2026-11-04", 2, 40),
		{Day: "2026-11-04", Model: "n", Endpoint: "/v1/embeddings", Agg: ledger.Agg{Requests: 1, PromptTokens: 9, TotalTokens: 9, GPUSeconds: 1.5}},
	}
	bob := []ledger.Row{chatRow("2026-11-04", 1, 7)}
	if err := openStore(t, dir, 366).Save("2026-11-04", map[string][]ledger.Row{"alice": alice, "bob": bob}); err != nil {
		t.Fatal(err)
	}

	reopened := openStore(t, dir, 366)
	if got, want := reopened.userDays("alice", "2026-11-04", "2026-11-04"), map[string][]ledger.Row{"2026-11-04": alice}; !reflect.DeepEqual(got, want) {
		t.Errorf("alice's saved rows:\n got %+v\nwant %+v", got, want)
	}
	if got, want := reopened.userDays("bob", "2026-11-04", "2026-11-04"), map[string][]ledger.Row{"2026-11-04": bob}; !reflect.DeepEqual(got, want) {
		t.Errorf("bob's saved rows:\n got %+v\nwant %+v", got, want)
	}
}

// A day with no usage gets a file too, so "saved with no usage" differs
// from "not saved".
func TestDayWithNoUsageIsSavedWithNoRows(t *testing.T) {
	dir := t.TempDir()
	if err := openStore(t, dir, 366).Save("2026-11-05", nil); err != nil {
		t.Fatal(err)
	}
	reopened := openStore(t, dir, 366)
	if !reopened.Has("2026-11-05") {
		t.Fatal("a day saved with no usage should count as saved")
	}
	if got, want := reopened.userDays("alice", "2026-11-05", "2026-11-05"), map[string][]ledger.Row{"2026-11-05": nil}; !reflect.DeepEqual(got, want) {
		t.Errorf("saved rows = %+v, want %+v", got, want)
	}
}

func TestInterruptedWriteIsRemovedWhenTheStoreOpens(t *testing.T) {
	dir := t.TempDir()
	temporary := filepath.Join(dir, "2026-11-06.jsonl.gz.tmp")
	if err := os.WriteFile(temporary, []byte("partial"), 0o600); err != nil {
		t.Fatal(err)
	}
	store := openStore(t, dir, 366)
	if store.Has("2026-11-06") {
		t.Error("an interrupted write must not count as saved")
	}
	assertMissing(t, temporary)
}

// A day file that cannot be read, for any reason, counts as not saved, and
// opening the store leaves it on disk unchanged.
func TestUnreadableDayFileCountsAsNotSaved(t *testing.T) {
	valid := gzipped(t, `{"v":1,"day":"2026-11-04","user":"alice","model":"m","endpoint":"/v1/chat/completions","requests":1}`+"\n")
	for _, tc := range []struct {
		name    string
		content []byte
	}{
		{"a file that is not gzip", []byte("not gzip")},
		{"a gzip file cut short", valid[:len(valid)-6]},
		{"a line that is not JSON", gzipped(t, "{broken\n")},
		{"a line in a newer format version", gzipped(t, `{"v":2,"day":"2026-11-04","user":"alice"}`+"\n")},
		{"a line for another day", gzipped(t, `{"v":1,"day":"2026-11-03","user":"alice"}`+"\n")},
		{"an unknown error status", gzipped(t, `{"v":1,"day":"2026-11-04","user":"alice","status_counts":{"teapot":1}}`+"\n")},
	} {
		t.Run(tc.name, func(t *testing.T) {
			dir := t.TempDir()
			path := writeDayFile(t, dir, "2026-11-04", tc.content)
			store := openStore(t, dir, 366)
			if store.Has("2026-11-04") {
				t.Error("the day counts as saved")
			}
			if got := store.userDays("alice", "2026-11-01", "2026-11-30"); len(got) != 0 {
				t.Errorf("saved days = %+v, want none", got)
			}
			if oldest := store.Oldest(); oldest != "" {
				t.Errorf("oldest saved day = %q, want none", oldest)
			}
			if !bytes.Equal(readFile(t, path), tc.content) {
				t.Error("opening the store changed the file")
			}
		})
	}
}

func TestUnreadableDayFileIsWrittenOverWhileTheLedgerHoldsTheDay(t *testing.T) {
	// Nothing has rotated, so the ledger holds every day from 16 November.
	src := ledgerWith(t, map[string]string{"pod/usage.log": record(day(11, 16, 9), "alice", 42) + record(day(11, 17, 9), "alice", 5)})
	dir := t.TempDir()
	path := writeDayFile(t, dir, "2026-11-16", []byte("not gzip"))
	store := openStore(t, dir, 366)

	saved, err := Source{Ledger: src, Store: store}.SaveCompleteDays(refreshTime)
	if err != nil {
		t.Fatal(err)
	}
	if saved != 2 {
		t.Errorf("saved %d days, want 2 (16 and 17 November)", saved)
	}
	rows, err := readDay(path, "2026-11-16")
	if err != nil {
		t.Fatalf("the file should now be readable: %v", err)
	}
	if got, want := usageRows(rows["alice"]), []usageRow{{"2026-11-16", "m", 1, 42}}; !reflect.DeepEqual(got, want) {
		t.Errorf("rows in the rewritten file = %+v, want %+v", got, want)
	}
}

// Keeping 3 days on 7 November keeps 5, 6, and 7 November. Pruning goes by
// the date in the file name, so files that cannot be read go on time too.
func TestPruneDeletesDayFilesOlderThanTheRetentionPeriod(t *testing.T) {
	dir := t.TempDir()
	store := openStore(t, dir, 3)
	for _, saved := range []string{"2026-11-03", "2026-11-04", "2026-11-05"} {
		if err := store.Save(saved, aliceRows(saved, 1)); err != nil {
			t.Fatal(err)
		}
	}
	unreadableOld := writeDayFile(t, dir, "2026-11-01", []byte("not gzip"))
	unreadableKept := writeDayFile(t, dir, "2026-11-06", []byte("not gzip"))

	store.Prune(time.Date(2026, 11, 7, 12, 0, 0, 0, time.UTC))

	for _, gone := range []string{"2026-11-03", "2026-11-04"} {
		if store.Has(gone) {
			t.Errorf("%s is still held after pruning", gone)
		}
		assertMissing(t, filepath.Join(dir, gone+fileSuffix))
	}
	assertMissing(t, unreadableOld)
	if !store.Has("2026-11-05") {
		t.Error("5 November is the first day of the retention period and should be kept")
	}
	if _, err := os.Stat(unreadableKept); err != nil {
		t.Errorf("an unreadable file within the retention period should be kept: %v", err)
	}
}

func TestPruneLeavesFilesThatAreNotDayFiles(t *testing.T) {
	dir := t.TempDir()
	other := filepath.Join(dir, "notes.txt")
	if err := os.WriteFile(other, []byte("operator notes"), 0o600); err != nil {
		t.Fatal(err)
	}
	openStore(t, dir, 3).Prune(time.Date(2026, 11, 7, 12, 0, 0, 0, time.UTC))
	if !bytes.Equal(readFile(t, other), []byte("operator notes")) {
		t.Error("a file that is not a day file was changed")
	}
}

func TestOldestIsTheEarliestSavedDay(t *testing.T) {
	store := openStore(t, t.TempDir(), 366)
	if oldest := store.Oldest(); oldest != "" {
		t.Errorf("empty store: oldest = %q, want none", oldest)
	}
	for _, saved := range []string{"2026-11-05", "2026-11-02", "2026-11-09"} {
		if err := store.Save(saved, nil); err != nil {
			t.Fatal(err)
		}
	}
	if oldest := store.Oldest(); oldest != "2026-11-02" {
		t.Errorf("oldest = %q, want 2026-11-02", oldest)
	}
}

func TestOpenRefusesADirectoryItCannotCreate(t *testing.T) {
	notADir := filepath.Join(t.TempDir(), "file")
	if err := os.WriteFile(notADir, nil, 0o600); err != nil {
		t.Fatal(err)
	}
	if _, err := Open(filepath.Join(notADir, "history"), 366); err == nil {
		t.Error("Open should fail when the history directory cannot be made")
	}
}

func TestOpenRefusesARetentionOfZeroDays(t *testing.T) {
	if _, err := Open(t.TempDir(), 0); err == nil {
		t.Error("Open should refuse a retention of 0 days")
	}
}

func TestSaveRefusesARowForAnotherDayAndLeavesNoFile(t *testing.T) {
	dir := t.TempDir()
	store := openStore(t, dir, 366)
	if err := store.Save("2026-11-04", aliceRows("2026-11-03", 1)); err == nil {
		t.Fatal("Save accepted a row dated 3 November in the file for 4 November")
	}
	if store.Has("2026-11-04") {
		t.Error("the refused day counts as saved")
	}
	entries, err := os.ReadDir(dir)
	if err != nil {
		t.Fatal(err)
	}
	if len(entries) != 0 {
		t.Errorf("files left behind: %v", entries)
	}
}

// Saved files are plain gzipped JSON lines an operator can read with zcat,
// one per user, model, and endpoint, holding counts only.
func TestSavedFileIsGzippedJSONLinesOfCountsOnly(t *testing.T) {
	dir := t.TempDir()
	row := chatRow("2026-11-04", 3, 40)
	row.Errors = 1
	row.StatusCounts[ledger.StatusBucket(429)] = 1
	if err := openStore(t, dir, 366).Save("2026-11-04", map[string][]ledger.Row{"alice": {row}}); err != nil {
		t.Fatal(err)
	}
	file, err := os.Open(filepath.Join(dir, "2026-11-04.jsonl.gz"))
	if err != nil {
		t.Fatal(err)
	}
	defer file.Close()
	unzipped, err := gzip.NewReader(file)
	if err != nil {
		t.Fatal(err)
	}
	content, err := io.ReadAll(unzipped)
	if err != nil {
		t.Fatal(err)
	}
	want := `{"v":1,"day":"2026-11-04","user":"alice","model":"m","endpoint":"/v1/chat/completions",` +
		`"requests":3,"errors":1,"cold_starts":0,"prompt_tokens":0,"completion_tokens":0,"reasoning_tokens":0,` +
		`"reasoning_reported":0,"total_tokens":40,"gpu_seconds":0,"latency_ms_sum":0,"status_counts":{"429":1},` +
		`"speed_completion_tokens":0,"speed_latency_ms":0,"max_prompt_tokens":0,"max_prompt_window":0,"near_limit_prompts":0}` + "\n"
	if string(content) != want {
		t.Errorf("file content:\n got %s\nwant %s", content, want)
	}
}

// The ledger's only file is a rotated one starting mid-afternoon on
// 5 November, so it holds 6 November onward in full. Saved days fill the
// days it lost.
func TestSavedDaysFillDaysTheLedgerLost(t *testing.T) {
	src := ledgerWith(t, map[string]string{"pod/usage.log.1": record(day(11, 5, 13), "alice", 7) + record(day(11, 6, 10), "alice", 11)})
	store := openStore(t, t.TempDir(), 366)
	for _, saved := range []struct {
		day    string
		tokens int64
	}{{"2026-11-03", 300}, {"2026-11-04", 400}} {
		if err := store.Save(saved.day, aliceRows(saved.day, saved.tokens)); err != nil {
			t.Fatal(err)
		}
	}
	report := usage(t, Source{Ledger: src, Store: store}, "alice", day(11, 3, 0), day(11, 4, 0))
	want := []usageRow{{"2026-11-03", "m", 1, 300}, {"2026-11-04", "m", 1, 400}}
	if got := usageRows(report.Rows); !reflect.DeepEqual(got, want) {
		t.Errorf("rows = %+v, want %+v", got, want)
	}
	if report.SavedDays != 2 {
		t.Errorf("saved days = %d, want 2", report.SavedDays)
	}
}

// 5 November is only partly in the ledger (7 tokens from the afternoon); the
// saved day's full 500 replaces it, and 6 November still comes from the
// ledger.
func TestSavedDayReplacesTheLedgersPartialRows(t *testing.T) {
	src := ledgerWith(t, map[string]string{"pod/usage.log.1": record(day(11, 5, 13), "alice", 7) + record(day(11, 6, 10), "alice", 11)})
	store := openStore(t, t.TempDir(), 366)
	if err := store.Save("2026-11-05", aliceRows("2026-11-05", 500)); err != nil {
		t.Fatal(err)
	}
	report := usage(t, Source{Ledger: src, Store: store}, "alice", day(11, 5, 0), day(11, 6, 0))
	want := []usageRow{{"2026-11-05", "m", 1, 500}, {"2026-11-06", "m", 1, 11}}
	if got := usageRows(report.Rows); !reflect.DeepEqual(got, want) {
		t.Errorf("rows = %+v, want %+v", got, want)
	}
	if len(report.Incomplete) != 0 {
		t.Errorf("incomplete = %v, want none", report.Incomplete)
	}
}

func TestReportOldestReachesBackToTheEarliestSavedDay(t *testing.T) {
	src := ledgerWith(t, map[string]string{"pod/usage.log.1": record(day(11, 5, 13), "alice", 7)})
	store := openStore(t, t.TempDir(), 366)
	if err := store.Save("2026-11-03", nil); err != nil {
		t.Fatal(err)
	}
	report := usage(t, Source{Ledger: src, Store: store}, "alice", day(11, 1, 0), day(11, 10, 0))
	if !report.Oldest.Equal(day(11, 3, 0)) {
		t.Errorf("oldest = %v, want 3 November", report.Oldest)
	}
}

// A ledger that has never rotated has lost nothing, so every day counts as
// complete, even with saved days older than its first record.
func TestLedgerThatHasNeverRotatedIsTrustedForEveryDay(t *testing.T) {
	src := ledgerWith(t, map[string]string{"pod/usage.log": record(day(11, 8, 9), "alice", 7)})
	store := openStore(t, t.TempDir(), 366)
	if err := store.Save("2026-11-04", aliceRows("2026-11-04", 300)); err != nil {
		t.Fatal(err)
	}
	report := usage(t, Source{Ledger: src, Store: store}, "alice", day(11, 3, 0), day(11, 10, 0))
	if len(report.Incomplete) != 0 {
		t.Errorf("incomplete = %v, want none", report.Incomplete)
	}
}

func TestEveryFinishedDayIsSavedForEveryUser(t *testing.T) {
	// Nothing has rotated, so the ledger holds every day from 15 November.
	src := ledgerWith(t, map[string]string{"pod/usage.log": record(day(11, 15, 9), "alice", 5) +
		record(day(11, 16, 9), "bob", 6) + record(day(11, 16, 10), "alice", 8) + record(day(11, 18, 9), "alice", 7)})
	store := openStore(t, t.TempDir(), 366)
	saved, err := Source{Ledger: src, Store: store}.SaveCompleteDays(refreshTime)
	if err != nil {
		t.Fatal(err)
	}
	if saved != 3 {
		t.Errorf("saved %d days, want 3 (15, 16, and 17 November)", saved)
	}
	for _, user := range []struct {
		name string
		want map[string][]usageRow
	}{
		{"alice", map[string][]usageRow{
			"2026-11-15": {{"2026-11-15", "m", 1, 5}},
			"2026-11-16": {{"2026-11-16", "m", 1, 8}},
			"2026-11-17": {},
		}},
		{"bob", map[string][]usageRow{
			"2026-11-15": {},
			"2026-11-16": {{"2026-11-16", "m", 1, 6}},
			"2026-11-17": {},
		}},
	} {
		got := map[string][]usageRow{}
		for savedDay, rows := range store.userDays(user.name, "2026-11-01", "2026-11-30") {
			got[savedDay] = usageRows(rows)
		}
		if !reflect.DeepEqual(got, user.want) {
			t.Errorf("%s's saved days:\n got %+v\nwant %+v", user.name, got, user.want)
		}
	}
}

func TestSavingAgainSavesNothingNew(t *testing.T) {
	src := ledgerWith(t, map[string]string{"pod/usage.log": record(day(11, 16, 9), "alice", 5)})
	combined := Source{Ledger: src, Store: openStore(t, t.TempDir(), 366)}
	if _, err := combined.SaveCompleteDays(refreshTime); err != nil {
		t.Fatal(err)
	}
	saved, err := combined.SaveCompleteDays(refreshTime)
	if err != nil || saved != 0 {
		t.Errorf("second run saved %d days with error %v, want 0 and no error", saved, err)
	}
}

// Keeping 3 days on 18 November keeps 16 to 18 November, so 15 November is
// not saved although the ledger holds it in full.
func TestDaysBeforeTheRetentionPeriodAreNotSaved(t *testing.T) {
	src := ledgerWith(t, map[string]string{"pod/usage.log": record(day(11, 15, 9), "alice", 5) + record(day(11, 16, 9), "alice", 6)})
	dir := t.TempDir()
	store := openStore(t, dir, 3)
	if _, err := (Source{Ledger: src, Store: store}).SaveCompleteDays(refreshTime); err != nil {
		t.Fatal(err)
	}
	assertMissing(t, filepath.Join(dir, "2026-11-15"+fileSuffix))
	for _, kept := range []string{"2026-11-16", "2026-11-17"} {
		if !store.Has(kept) {
			t.Errorf("%s is within retention and over, so it should be saved", kept)
		}
	}
}

// A day counts as over once a refresh has started at least 5 minutes after
// its end.
func TestDayIsOverFiveMinutesAfterItsEnd(t *testing.T) {
	for _, tc := range []struct {
		name    string
		started time.Time
		want    time.Time
	}{
		{"a refresh just before midnight leaves the day before last", time.Date(2026, 11, 17, 23, 59, 0, 0, time.UTC), day(11, 16, 0)},
		{"a refresh within 5 minutes of midnight does not end the day", time.Date(2026, 11, 18, 0, 4, 59, 0, time.UTC), day(11, 16, 0)},
		{"a refresh exactly 5 minutes after midnight ends the day", time.Date(2026, 11, 18, 0, 5, 0, 0, time.UTC), day(11, 17, 0)},
		{"a refresh later in the day ends the day before", time.Date(2026, 11, 18, 15, 0, 0, 0, time.UTC), day(11, 17, 0)},
	} {
		t.Run(tc.name, func(t *testing.T) {
			if got := lastSettledDay(tc.started); !got.Equal(tc.want) {
				t.Errorf("last day over after a refresh at %s = %s, want %s", tc.started, got, tc.want)
			}
		})
	}
}

// The updater deletes days past retention once per UTC day, not after every
// refresh.
func TestUpdaterPrunesOncePerDay(t *testing.T) {
	src := ledgerWith(t, map[string]string{"pod/usage.log": record(day(11, 16, 9), "alice", 5)})
	dir := t.TempDir()
	store := openStore(t, dir, 3)
	now := refreshTime
	update := Source{Ledger: src, Store: store}.Updater(func() time.Time { return now })

	first := writeDayFile(t, dir, "2026-11-01", []byte("old"))
	update()
	assertMissing(t, first)

	second := writeDayFile(t, dir, "2026-11-02", []byte("old"))
	now = refreshTime.Add(time.Hour)
	update()
	if _, err := os.Stat(second); err != nil {
		t.Errorf("a second refresh on the same day should not prune again: %v", err)
	}

	now = time.Date(2026, 11, 19, 0, 30, 0, 0, time.UTC)
	update()
	assertMissing(t, second)
}
