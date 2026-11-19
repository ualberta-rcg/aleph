package web

import (
	"fmt"
	"html/template"
	"strings"
	"time"

	"github.com/ualberta-rcg/aleph/usage-ui/internal/ledger"
)

// coverage describes which days of the selected range have incomplete
// records. The gateway's logs rotate, and a day the service could not save
// before that is partly lost. Such days can fall anywhere in a range, not
// only at its start. Every page shows them as a picture, not only as a
// sentence: a bar across the range in the notice, hatched bars in the
// charts, a badge on the total cards, and marked rows in the daily table.
type coverage struct {
	Partial        bool // some days in the range have incomplete records
	AllIncomplete  bool // every day in the range does
	IncompleteDays int64
	TotalDays      int64
	Spans          []daySpan     // runs of consecutive incomplete days, in order
	List           string        // the spans in words: "20 Oct – 3 Nov 2026 and 9 Nov 2026"
	Text           string        // the notice above the page content
	Bar            template.HTML // the range drawn as incomplete and complete parts
}

// daySpan is a run of consecutive days, inclusive.
type daySpan struct{ From, To time.Time }

// maxListedSpans is how many separate runs of incomplete days are written
// out by date; more are summarised as a count, and the bar shows each one.
const maxListedSpans = 3

// newCoverage works out the coverage of the range from to to, given the
// days with incomplete records (YYYY-MM-DD, in order).
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
		result.Text = "Every day in this range has incomplete records: part of their usage rotated out of the gateway's logs before it could be kept."
	} else {
		result.Text = fmt.Sprintf("Records are incomplete for %s of the %d days in this range (%s). Part of their usage rotated out of the gateway's logs before it could be kept, so those days may show less than you actually used.",
			countOf(result.IncompleteDays, "day", "days"), result.TotalDays, result.List)
	}
	result.Bar = coverageBar(from, result.Spans, result.TotalDays)
	return result
}

// spansOf groups days (YYYY-MM-DD, in order) into runs of consecutive days.
func spansOf(days []string) []daySpan {
	var spans []daySpan
	for _, key := range days {
		day, err := time.Parse(ledger.DayLayout, key)
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

// spanList writes spans in words: "9 Nov 2026", "20 Oct – 3 Nov 2026 and
// 9 Nov 2026", or, past maxListedSpans, "5 separate periods, 2 Oct –
// 9 Nov 2026".
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

// coverageBar draws the range as one strip: green for complete days, gold
// for each run of incomplete ones. It is SVG because the page's CSP forbids
// inline styles, and SVG attributes can carry the positions.
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

// formatSpan writes a day range compactly, always with the year, since it
// appears on printed statements: "4 – 18 Nov 2026", "20 Oct – 3 Nov 2026",
// or "30 Dec 2025 – 2 Jan 2026" across a year boundary. One day is
// "4 Nov 2026".
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
