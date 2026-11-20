package web

import (
	"fmt"
	"time"

	"github.com/ualberta-rcg/aleph/portal/internal/source"
)

const maxDailyBars = 62

type chartPeriod struct {
	Start          string
	Label          string
	Days           int64
	IncompleteDays int64
	Tokens         int64
	GPUSeconds     float64
	Requests       int64
}

func (period chartPeriod) Incomplete() bool { return period.IncompleteDays > 0 }

func chartPeriods(days []dayPoint) ([]chartPeriod, string) {
	if len(days) <= maxDailyBars {
		periods := make([]chartPeriod, len(days))
		for i, day := range days {
			periods[i] = chartPeriod{
				Start: day.Day, Label: day.Day, Days: 1,
				Tokens: day.Tokens, GPUSeconds: day.GPUSeconds, Requests: day.Requests,
			}
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
		first, _ := time.Parse(source.DayLayout, days[start].Day)
		last, _ := time.Parse(source.DayLayout, days[end-1].Day)
		period.Label = formatSpan(first, last)
		if period.Days < 7 {
			period.Label += fmt.Sprintf(" (%s)", countOf(period.Days, "day", "days"))
		}
		periods = append([]chartPeriod{period}, periods...)
	}
	return periods, "week"
}
