package web

import (
	"testing"

	"github.com/ualberta-rcg/aleph/usage-ui/internal/ledger"
)

// Any of the ways the overview can phrase a previous-period change.
var previousPeriodPhrases = []string{"vs the previous", "none in the previous", "same as the previous"}

// 8 to 14 November against 1 to 7 November, both complete: 1,714 tokens
// against 617, 3 requests against 1, 4.1 GPU-seconds against 2.0.
func TestPreviousPeriodChangeIsShownWhenBothPeriodsAreComplete(t *testing.T) {
	text := pageText(t, newTestServer(t), "/?from=2026-11-08&to=2026-11-14")
	assertContains(t, text,
		`<div class="delta">+178% vs the previous 7 days</div>`,
		`<div class="delta">+200% vs the previous 7 days</div>`,
		`<div class="delta">+105% vs the previous 7 days</div>`)
}

// The default range, 3 to 16 November, is complete, but the 14 days before
// it start on 20 October, before the records do.
func TestPreviousPeriodChangeIsHiddenWhenTheEarlierPeriodIsIncomplete(t *testing.T) {
	assertNotContains(t, pageText(t, newTestServer(t), "/"), previousPeriodPhrases...)
}

// The earlier period, 1 to 7 November, is complete; the current range has
// one incomplete day. Without that gap the same usage is compared.
func TestPreviousPeriodChangeIsHiddenWhenTheCurrentRangeHasAnIncompleteDay(t *testing.T) {
	rows := []ledger.Row{stubRow("2026-11-03", 100), stubRow("2026-11-10", 200)}
	complete := pageText(t, serve(t, dayStub{rows: rows}), "/?from=2026-11-08&to=2026-11-14")
	assertContains(t, complete, `<div class="delta">+100% vs the previous 7 days</div>`)

	withGap := pageText(t, serve(t, dayStub{rows: rows, incomplete: []string{"2026-11-12"}}), "/?from=2026-11-08&to=2026-11-14")
	assertNotContains(t, withGap, previousPeriodPhrases...)
}
