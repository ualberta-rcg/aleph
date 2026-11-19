package web

import (
	"testing"
)

// The pages and the CSV use the same range, worked out from ?from=&to= with
// today being 16 November 2026. Anything unusable is ignored rather than
// refused, and both show the range actually used: the pages in their date
// form, the CSV in its file name.
func TestDateRangeUsedForPagesAndCSV(t *testing.T) {
	for _, tc := range []struct {
		name, query, from, to string
	}{
		{"no dates give the 14 days ending today", "", "2026-11-03", "2026-11-16"},
		{"dates that do not parse give the default range", "from=yesterday&to=2026-13-40", "2026-11-03", "2026-11-16"},
		{"an end date alone gives the 14 days ending that day", "to=2026-01-01", "2025-12-19", "2026-01-01"},
		{"a start date alone runs to today", "from=2026-11-10", "2026-11-10", "2026-11-16"},
		{"a start after the end is ignored", "from=2026-11-20&to=2026-11-01", "2026-10-19", "2026-11-01"},
		{"an end after today is cut to today", "from=2026-11-08&to=2026-11-20", "2026-11-08", "2026-11-16"},
		{"a range starting after today gives the default range", "from=2026-11-17&to=2026-11-20", "2026-11-03", "2026-11-16"},
		{"a range of exactly 366 days is kept", "from=2025-11-15&to=2026-11-15", "2025-11-15", "2026-11-15"},
		{"a range of 367 days keeps the 366 days ending on the end date", "from=2025-11-14&to=2026-11-15", "2025-11-15", "2026-11-15"},
	} {
		t.Run(tc.name, func(t *testing.T) {
			handler := newTestServer(t)
			for _, page := range pages {
				_, body := get(t, handler, page.path+"?"+tc.query, "alice")
				if from, to := shownRange(t, body); from != tc.from || to != tc.to {
					t.Errorf("%s shows %s to %s, want %s to %s", page.label, from, to, tc.from, tc.to)
				}
			}
			res, _ := getCSV(t, handler, tc.query)
			want := `attachment; filename="aleph-usage-alice-` + tc.from + `-to-` + tc.to + `.csv"`
			if got := res.Header.Get("Content-Disposition"); got != want {
				t.Errorf("CSV Content-Disposition = %q, want %q", got, want)
			}
		})
	}
}
