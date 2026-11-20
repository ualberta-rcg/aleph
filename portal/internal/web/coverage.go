package web

import (
	"fmt"
	"html/template"
	"strings"
	"time"

	"github.com/ualberta-rcg/aleph/portal/internal/source"
)

type coverage struct {
	Partial        bool
	AllIncomplete  bool
	IncompleteDays int64
	TotalDays      int64
	Spans          []daySpan
	List           string
	Text           string
	Bar            template.HTML
}

type daySpan struct{ From, To time.Time }

const maxListedSpans = 3

func newCoverage(from, to time.Time, incomplete []string) coverage {
	if len(incomplete) == 0 {
		return coverage{}
	}
	result := coverage{
		Partial:        true,
		IncompleteDays: int64(len(incomplete)),
		TotalDays:      int64(daysInRange(from, to)),
		Spans:          spansOf(incomplete),
	}
	result.AllIncomplete = result.IncompleteDays == result.TotalDays
	result.List = spanList(result.Spans)
	if result.AllIncomplete {
		result.Text = "Every day in this range has incomplete records: part of their usage rotated out of the gateway's logs before it could be read."
	} else {
		result.Text = fmt.Sprintf("Records are incomplete for %s of the %d days in this range (%s). Part of their usage rotated out of the gateway's logs, so those days may show less than you actually used.",
			countOf(result.IncompleteDays, "day", "days"), result.TotalDays, result.List)
	}
	result.Bar = coverageBar(from, result.Spans, result.TotalDays)
	return result
}

func spansOf(days []string) []daySpan {
	var spans []daySpan
	for _, key := range days {
		day, err := time.Parse(source.DayLayout, key)
		if err != nil {
			continue
		}
		if n := len(spans); n > 0 && spans[n-1].To.AddDate(0, 0, 1).Equal(day) {
			spans[n-1].To = day
			continue
		}
		spans = append(spans, daySpan{From: day, To: day})
	}
	return spans
}

func spanList(spans []daySpan) string {
	switch n := len(spans); {
	case n == 0:
		return ""
	case n > maxListedSpans:
		return fmt.Sprintf("%d separate periods, %s", n, formatSpan(spans[0].From, spans[n-1].To))
	default:
		parts := make([]string, n)
		for i, span := range spans {
			parts[i] = formatSpan(span.From, span.To)
		}
		if n == 1 {
			return parts[0]
		}
		return strings.Join(parts[:n-1], ", ") + " and " + parts[n-1]
	}
}

func coverageBar(from time.Time, spans []daySpan, totalDays int64) template.HTML {
	const width = 1000.0
	dayWidth := width / float64(totalDays)
	var bar strings.Builder
	fmt.Fprintf(&bar, `<svg class="coverage-bar" viewBox="0 0 %.0f 10" preserveAspectRatio="none" aria-hidden="true" focusable="false">`, width)
	fmt.Fprintf(&bar, `<rect class="coverage-complete" x="0" y="0" width="%.0f" height="10"/>`, width)
	for _, span := range spans {
		start := float64(daysInRange(from, span.From) - 1)
		length := float64(daysInRange(span.From, span.To))
		fmt.Fprintf(&bar, `<rect class="coverage-missing" x="%.1f" y="0" width="%.1f" height="10"/>`, start*dayWidth, length*dayWidth)
	}
	bar.WriteString(`</svg>`)
	return template.HTML(bar.String())
}

func formatSpan(from, to time.Time) string {
	from, to = from.UTC(), to.UTC()
	switch {
	case from.Equal(to):
		return from.Format("2 Jan 2006")
	case from.Year() != to.Year():
		return from.Format("2 Jan 2006") + " – " + to.Format("2 Jan 2006")
	case from.Month() != to.Month():
		return from.Format("2 Jan") + " – " + to.Format("2 Jan 2006")
	default:
		return from.Format("2") + " – " + to.Format("2 Jan 2006")
	}
}
