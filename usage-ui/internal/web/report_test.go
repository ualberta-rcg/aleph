package web

import (
	"regexp"
	"testing"

	"github.com/ualberta-rcg/aleph/usage-ui/internal/ledger"
)

var statementPattern = regexp.MustCompile(`(?s)<p class="statement" id="statement">(.*?)</p>`)

// statementOf returns the report's ready-to-copy sentence, as a reader sees
// it.
func statementOf(t *testing.T, text string) string {
	t.Helper()
	match := statementPattern.FindStringSubmatch(text)
	if match == nil {
		t.Fatal("the report has no statement")
	}
	return match[1]
}

func assertStatement(t *testing.T, text, want string) {
	t.Helper()
	if got := statementOf(t, text); got != want {
		t.Errorf("statement:\n got %q\nwant %q", got, want)
	}
}

// 8 to 14 November holds alice's 10 November use: 1,234 + 480 tokens and
// 4.1 GPU-seconds, on two models.
func TestReportStatementTotalsTheCompleteDaysInTheRange(t *testing.T) {
	text := pageText(t, newTestServer(t), "/report?from=2026-11-08&to=2026-11-14")
	assertStatement(t, text, "Between 8 November 2026 and 14 November 2026, I used an estimated 0.001 GPU-hours and 1,714 tokens across 2 models on Aleph, the University of Alberta Research Computing inference platform.")
	assertContains(t, text, "Prepared for alice, covering 8 – 14 Nov 2026 (UTC).")
}

// A model is counted only when at least one request to it succeeded.
func TestReportCountsOnlyModelsWithASuccessfulRequest(t *testing.T) {
	handler := newTestServerWith(t, map[string]string{"pod/usage.log": userRecord("2026-11-10T10:00:00Z", "alice", "user", "working-model", 40) +
		`{"ts":"2026-11-10T11:00:00Z","identity":"alice","identity_type":"user","endpoint":"/v1/chat/completions","model":"broken-model","status":500,"latency_ms":100,"tokens":{"prompt":0,"completion":0,"total":0},"derived":{"gpu_seconds":0}}` + "\n"})
	text := pageText(t, handler, "/report?from=2026-11-08&to=2026-11-14")
	assertStatement(t, text, "Between 8 November 2026 and 14 November 2026, I used an estimated <0.001 GPU-hours and 40 tokens across 1 model on Aleph, the University of Alberta Research Computing inference platform.")
}

// Records are complete from 1 November, so a range from 25 October is only
// partly covered: the statement, its total, and the printed header name
// the covered days, not the request.
func TestReportNarrowsToTheCompleteDaysAtTheStartOfTheRange(t *testing.T) {
	text := pageText(t, newTestServer(t), "/report?from=2026-10-25&to=2026-11-14")
	assertStatement(t, text, "Between 1 November 2026 and 14 November 2026, I used an estimated 0.002 GPU-hours and 2,331 tokens across 2 models on Aleph, the University of Alberta Research Computing inference platform.")
	assertContains(t, text, "covering 1 – 14 Nov 2026 (UTC); requested 25 October 2026 to 14 November 2026.")
}

// Records complete from mid-afternoon leave that morning possibly missing,
// so the statement starts the next day and leaves that day's 10,000 tokens
// out.
func TestReportStartsTheDayAfterRecordsBecomeCompleteMidDay(t *testing.T) {
	handler := newTestServerWith(t, map[string]string{"pod/usage.log.1": `{"ts":"2026-11-05T13:00:00Z","identity":"alice","identity_type":"user","endpoint":"/v1/chat/completions","model":"qwen35-122b","status":200,"latency_ms":800,"tokens":{"prompt":9000,"completion":1000,"total":10000},"derived":{"gpu_seconds":7200}}
{"ts":"2026-11-10T10:00:00Z","identity":"alice","identity_type":"user","endpoint":"/v1/chat/completions","model":"qwen35-122b","status":200,"latency_ms":800,"tokens":{"prompt":400,"completion":100,"total":500},"derived":{"gpu_seconds":3600}}
`})
	text := pageText(t, handler, "/report?from=2026-11-01&to=2026-11-14")
	assertStatement(t, text, "Between 6 November 2026 and 14 November 2026, I used an estimated 1.00 GPU-hours and 500 tokens across 1 model on Aleph, the University of Alberta Research Computing inference platform.")
}

// An incomplete day inside the range, for example one the history could not
// save, is left out of the totals and counted in the sentence; the days on
// both sides stay in.
func TestReportExcludesAnIncompleteDayInsideTheRange(t *testing.T) {
	handler := serve(t, dayStub{
		rows:       []ledger.Row{stubRow("2026-11-08", 100), stubRow("2026-11-09", 5000), stubRow("2026-11-10", 200)},
		incomplete: []string{"2026-11-09"},
	})
	text := pageText(t, handler, "/report?from=2026-11-07&to=2026-11-11")
	assertStatement(t, text, "Between 7 November 2026 and 11 November 2026, excluding 1 day with incomplete records, I used an estimated 2.00 GPU-hours and 300 tokens across 1 model on Aleph, the University of Alberta Research Computing inference platform.")
	assertContains(t, text, "covering 7 – 11 Nov 2026, excluding 9 Nov 2026 (UTC); requested 7 November 2026 to 11 November 2026.")
}

// Today (16 November) is not over, so its 9,000 tokens and hour of GPU time
// stay out of the statement, which ends yesterday.
func TestReportLeavesOutTodayUntilItIsOver(t *testing.T) {
	handler := newTestServerWith(t, map[string]string{"pod/usage.log.1": ledgerLines +
		`{"ts":"2026-11-16T08:00:00Z","identity":"alice","identity_type":"user","endpoint":"/v1/chat/completions","model":"qwen35-122b","status":200,"latency_ms":800,"tokens":{"prompt":9000,"completion":0,"total":9000},"derived":{"gpu_seconds":3600}}` + "\n"})
	text := pageText(t, handler, "/report?from=2026-11-10&to=2026-11-16")
	assertStatement(t, text, "Between 10 November 2026 and 15 November 2026, I used an estimated 0.001 GPU-hours and 1,714 tokens across 2 models on Aleph, the University of Alberta Research Computing inference platform.")
	assertContains(t, text, "Today is left out until it is over.", "covering 10 – 15 Nov 2026 (UTC); requested 10 November 2026 to 16 November 2026.")
}

func TestReportOfOnlyTodayHasNothingToReport(t *testing.T) {
	text := pageText(t, newTestServer(t), "/report?from=2026-11-16&to=2026-11-16")
	assertStatement(t, text, "No day in this range has finished yet, so there is nothing to report.")
}

func TestReportOfOnlyIncompleteDaysMakesNoClaim(t *testing.T) {
	text := pageText(t, newTestServer(t), "/report?from=2026-01-01&to=2026-01-31")
	assertStatement(t, text, "Complete usage records are not on hand for 1 January 2026 to 31 January 2026.")
}

func TestReportOfCompleteDaysWithoutUsageSaysNoneWasRecorded(t *testing.T) {
	text := pageText(t, newTestServer(t), "/report?from=2026-11-12&to=2026-11-14")
	assertStatement(t, text, "No Aleph usage was recorded between 12 November 2026 and 14 November 2026.")
}
