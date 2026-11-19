package web

import (
	"fmt"
	"time"

	"github.com/ualberta-rcg/aleph/usage-ui/internal/ledger"
)

// maxDailyBars is the longest range charted one bar per day. Past it, bars
// would be a few pixels wide in the 760-unit chart, so the range is charted
// by week: 9 to 53 bars up to the 366-day limit.
const maxDailyBars = 62

// chartPeriod is one bar in the overview charts and one row in the table
// beneath them: a day, or a week of days.
type chartPeriod struct {
	Start          string // first day, YYYY-MM-DD; the chart's axis label
	Label          string // the row heading and hover label
	Days           int64
	IncompleteDays int64
	Tokens         int64
	GPUSeconds     float64
	Requests       int64
}

// Incomplete reports whether any day in the period has incomplete records.
func (period chartPeriod) Incomplete() bool { return period.IncompleteDays > 0 }

// chartPeriods groups the range's days for charting. Up to maxDailyBars days
// it keeps one period per day. Longer ranges are grouped into 7-day weeks
// counted back from the last day, so every week is whole except possibly the
// first, whose label gives its length. Counting from the end keeps the most
// recent bars, the ones people look at, comparable. It returns the periods
// and their unit, "day" or "week".
func chartPeriods(days []dayPoint) ([]chartPeriod, string) {
	if len(days) <= maxDailyBars {
		periods := make([]chartPeriod, len(days))
		for i, day := range days {
			periods[i] = chartPeriod{Start: day.Day, Label: day.Day, Days: 1,
				Tokens: day.Tokens, GPUSeconds: day.GPUSeconds, Requests: day.Requests}
			if day.Incomplete {
				periods[i].IncompleteDays = 1
			}
		}
		return periods, "day"
	}
	var periods []chartPeriod
	for end := len(days); end > 0; end -= 7 {
		start := max(end-7, 0)
		period := chartPeriod{Start: days[start].Day, Days: int64(end - start)}
		for _, day := range days[start:end] {
			period.Tokens += day.Tokens
			period.GPUSeconds += day.GPUSeconds
			period.Requests += day.Requests
			if day.Incomplete {
				period.IncompleteDays++
			}
		}
		first, _ := time.Parse(ledger.DayLayout, days[start].Day)
		last, _ := time.Parse(ledger.DayLayout, days[end-1].Day)
		period.Label = formatSpan(first, last)
		if period.Days < 7 {
			period.Label += fmt.Sprintf(" (%s)", countOf(period.Days, "day", "days"))
		}
		periods = append([]chartPeriod{period}, periods...)
	}
	return periods, "week"
}
