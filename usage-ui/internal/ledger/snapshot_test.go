package ledger

import (
	"testing"
	"time"
)

// A day is complete only if every record of it is on hand, so records
// complete from any moment after midnight make the next day the first.
func TestFirstCompleteDayIsTheFirstMidnightAtOrAfterCompleteFrom(t *testing.T) {
	for _, tc := range []struct {
		name               string
		completeFrom, want time.Time
	}{
		{"nothing lost gives no first day", time.Time{}, time.Time{}},
		{"complete from midnight starts that day", time.Date(2026, 11, 5, 0, 0, 0, 0, time.UTC), time.Date(2026, 11, 5, 0, 0, 0, 0, time.UTC)},
		{"complete from the afternoon starts the next day", time.Date(2026, 11, 5, 13, 0, 0, 0, time.UTC), time.Date(2026, 11, 6, 0, 0, 0, 0, time.UTC)},
		{"complete from one second past midnight starts the next day", time.Date(2026, 11, 5, 0, 0, 1, 0, time.UTC), time.Date(2026, 11, 6, 0, 0, 0, 0, time.UTC)},
	} {
		t.Run(tc.name, func(t *testing.T) {
			if got := FirstCompleteDay(tc.completeFrom); !got.Equal(tc.want) {
				t.Errorf("FirstCompleteDay(%v) = %v, want %v", tc.completeFrom, got, tc.want)
			}
		})
	}
}
