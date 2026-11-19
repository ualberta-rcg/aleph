package web

import (
	"net/http"
	"testing"

	"github.com/ualberta-rcg/aleph/usage-ui/internal/ledger"
)

// getCSV downloads the CSV as alice and fails unless it is served.
func getCSV(t *testing.T, handler http.Handler, query string) (*http.Response, string) {
	t.Helper()
	res, body := get(t, handler, "/usage.csv?"+query, "alice")
	if res.StatusCode != http.StatusOK {
		t.Fatalf("status %d: %s", res.StatusCode, body)
	}
	return res, body
}

func assertCSV(t *testing.T, got, want string) {
	t.Helper()
	if got != want {
		t.Errorf("csv:\n got:\n%s\nwant:\n%s", got, want)
	}
}

// One line per day, model, and endpoint. ancient-greek-bert reports no
// thinking, so its reasoning_tokens is empty, not 0; qwen35-122b's two
// requests include the 429.
func TestCSVHasALineForEachDayModelAndEndpoint(t *testing.T) {
	_, body := getCSV(t, newTestServer(t), "from=2026-11-08&to=2026-11-16")
	assertCSV(t, body, csvHeader+
		"2026-11-10,yes,ancient-greek-bert,/v1/embeddings,1,0,0,480,0,,0,480,0.100,0.000028,100\n"+
		"2026-11-10,yes,qwen35-122b,/v1/chat/completions,2,1,0,1000,234,100,1,1234,4.000,0.001111,502\n")
}

func TestCSVIsADownloadNamedForTheUserAndRange(t *testing.T) {
	res, _ := getCSV(t, newTestServer(t), "from=2026-11-08&to=2026-11-14")
	if got := res.Header.Get("Content-Type"); got != "text/csv; charset=utf-8" {
		t.Errorf("Content-Type = %q", got)
	}
	if got, want := res.Header.Get("Content-Disposition"), `attachment; filename="aleph-usage-alice-2026-11-08-to-2026-11-14.csv"`; got != want {
		t.Errorf("Content-Disposition = %q, want %q", got, want)
	}
}

// midDayLedger is a rotated file starting at 13:00 on 5 November, so
// 5 November is incomplete and 6 November onward is complete.
var midDayLedger = map[string]string{"pod/usage.log.1": `{"ts":"2026-11-05T13:00:00Z","identity":"alice","identity_type":"user","endpoint":"/v1/chat/completions","model":"m","status":200,"latency_ms":800,"tokens":{"prompt":9,"completion":1,"total":10},"derived":{"gpu_seconds":1}}
{"ts":"2026-11-06T10:00:00Z","identity":"alice","identity_type":"user","endpoint":"/v1/chat/completions","model":"m","status":200,"latency_ms":800,"tokens":{"prompt":4,"completion":1,"total":5},"derived":{"gpu_seconds":1}}
`}

func TestCSVMarksAnIncompleteDaysUsageAsIncomplete(t *testing.T) {
	_, body := getCSV(t, newTestServerWith(t, midDayLedger), "from=2026-11-05&to=2026-11-06")
	assertCSV(t, body, csvHeader+
		"2026-11-05,no,m,/v1/chat/completions,1,0,0,9,1,,0,10,1.000,0.000278,800\n"+
		"2026-11-06,yes,m,/v1/chat/completions,1,0,0,4,1,,0,5,1.000,0.000278,800\n")
}

// An incomplete day with no usage still gets a line, in day order, so the
// file tells a day whose records were lost from a day with no usage.
// 7 November is complete and has no usage, so it has no line.
func TestCSVWritesALineForEachIncompleteDayWithoutUsage(t *testing.T) {
	_, body := getCSV(t, newTestServerWith(t, midDayLedger), "from=2026-11-03&to=2026-11-07")
	assertCSV(t, body, csvHeader+
		"2026-11-03,no,,,0,0,0,0,0,,0,0,0.000,0.000000,0\n"+
		"2026-11-04,no,,,0,0,0,0,0,,0,0,0.000,0.000000,0\n"+
		"2026-11-05,no,m,/v1/chat/completions,1,0,0,9,1,,0,10,1.000,0.000278,800\n"+
		"2026-11-06,yes,m,/v1/chat/completions,1,0,0,4,1,,0,5,1.000,0.000278,800\n")
}

func TestCSVMarksOnlyTheIncompleteDayInsideARange(t *testing.T) {
	handler := serve(t, dayStub{
		rows:       []ledger.Row{stubRow("2026-11-08", 100), stubRow("2026-11-09", 5000), stubRow("2026-11-10", 200)},
		incomplete: []string{"2026-11-09"},
	})
	_, body := getCSV(t, handler, "from=2026-11-07&to=2026-11-11")
	assertCSV(t, body, csvHeader+
		"2026-11-08,yes,m,/v1/chat/completions,1,0,0,0,0,,0,100,3600.000,1.000000,0\n"+
		"2026-11-09,no,m,/v1/chat/completions,1,0,0,0,0,,0,5000,3600.000,1.000000,0\n"+
		"2026-11-10,yes,m,/v1/chat/completions,1,0,0,0,0,,0,200,3600.000,1.000000,0\n")
}

// A model name a spreadsheet would run as a formula is written as text.
func TestCSVWritesAFormulaLikeModelNameAsText(t *testing.T) {
	handler := newTestServerWith(t, map[string]string{"pod/usage.log": userRecord("2026-11-10T10:00:00Z", "alice", "user", "=1+2", 7)})
	_, body := getCSV(t, handler, "from=2026-11-10&to=2026-11-10")
	assertCSV(t, body, csvHeader+"2026-11-10,yes,'=1+2,/v1/chat/completions,1,0,0,7,0,,0,7,0.500,0.000139,100\n")
}

func TestCSVSafePrefixesEveryFormulaStartingCharacter(t *testing.T) {
	for value, want := range map[string]string{
		"=cmd": "'=cmd", "+cmd": "'+cmd", "-cmd": "'-cmd", "@cmd": "'@cmd", "\tcmd": "'\tcmd", "\rcmd": "'\rcmd",
		"qwen": "qwen", "": "", "a=b": "a=b",
	} {
		if got := csvSafe(value); got != want {
			t.Errorf("csvSafe(%q) = %q, want %q", value, got, want)
		}
	}
}
