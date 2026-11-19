package web

import (
	"reflect"
	"strings"
	"testing"
	"time"

	"github.com/ualberta-rcg/aleph/usage-ui/internal/ledger"
)

// daysFrom makes n consecutive days from 1 January 2026, each with 10
// tokens, 1 request, and 60 GPU-seconds; the days at the given positions
// have incomplete records.
func daysFrom(n int, incomplete ...int) []dayPoint {
	start := time.Date(2026, 1, 1, 0, 0, 0, 0, time.UTC)
	days := make([]dayPoint, n)
	for i := range days {
		days[i] = dayPoint{Day: start.AddDate(0, 0, i).Format(ledger.DayLayout), Tokens: 10, Requests: 1, GPUSeconds: 60}
	}
	for _, i := range incomplete {
		days[i].Incomplete = true
	}
	return days
}

func TestRangesUpToSixtyTwoDaysAreChartedByDay(t *testing.T) {
	periods, unit := chartPeriods(daysFrom(62, 61))
	if unit != "day" || len(periods) != 62 {
		t.Fatalf("got %d periods by %s, want 62 by day", len(periods), unit)
	}
	want := chartPeriod{Start: "2026-03-03", Label: "2026-03-03", Days: 1, IncompleteDays: 1, Tokens: 10, GPUSeconds: 60, Requests: 1}
	if periods[61] != want {
		t.Errorf("last day = %+v, want %+v", periods[61], want)
	}
}

// 65 days are 9 whole weeks counted back from the last day, plus a 2-day
// first week. Incomplete days are counted in the week they fall in.
func TestLongerRangesAreChartedByWeekCountedBackFromTheLastDay(t *testing.T) {
	periods, unit := chartPeriods(daysFrom(65, 1, 64))
	if unit != "week" || len(periods) != 10 {
		t.Fatalf("got %d periods by %s, want 10 by week", len(periods), unit)
	}
	first := chartPeriod{Start: "2026-01-01", Label: "1 – 2 Jan 2026 (2 days)", Days: 2, IncompleteDays: 1, Tokens: 20, GPUSeconds: 120, Requests: 2}
	second := chartPeriod{Start: "2026-01-03", Label: "3 – 9 Jan 2026", Days: 7, Tokens: 70, GPUSeconds: 420, Requests: 7}
	last := chartPeriod{Start: "2026-02-28", Label: "28 Feb – 6 Mar 2026", Days: 7, IncompleteDays: 1, Tokens: 70, GPUSeconds: 420, Requests: 7}
	for _, check := range []struct {
		got, want chartPeriod
	}{{periods[0], first}, {periods[1], second}, {periods[9], last}} {
		if !reflect.DeepEqual(check.got, check.want) {
			t.Errorf("got %+v, want %+v", check.got, check.want)
		}
	}
}

// A template error renders a page cut short, so a year with incomplete
// weeks must render to the end.
func TestAYearWithIncompleteWeeksRendersTheWholeOverview(t *testing.T) {
	text := pageText(t, newTestServer(t), "/?from=2025-11-17&to=2026-11-16")
	for _, want := range []string{"Tokens per week", "</html>"} {
		if !strings.Contains(text, want) {
			t.Errorf("overview for a year lacks %q", want)
		}
	}
	if !strings.Contains(text, `<span class="tag">7 incomplete days</span>`) {
		t.Error("a week of incomplete days should be tagged with its count")
	}
}
