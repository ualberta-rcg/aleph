package ledger

import (
	"sort"
	"time"
)

// DayOf returns the start of the UTC day t falls on.
func DayOf(t time.Time) time.Time {
	return t.UTC().Truncate(24 * time.Hour)
}

// FirstCompleteDay returns the first UTC day that starts at or after
// completeFrom, so every record of that day is on hand. The day completeFrom
// falls on is not complete unless completeFrom is exactly midnight, since
// records from earlier that day may be missing. A zero completeFrom means
// nothing is missing and gives zero.
func FirstCompleteDay(completeFrom time.Time) time.Time {
	if completeFrom.IsZero() {
		return time.Time{}
	}
	day := DayOf(completeFrom)
	if day.Before(completeFrom) {
		day = day.AddDate(0, 0, 1)
	}
	return day
}

// Snapshot is what the ledger can say about itself at one moment. The daily
// history uses it to decide which days are safe to save.
type Snapshot struct {
	Oldest       time.Time // earliest record on hand, across every user
	CompleteFrom time.Time // see Report.CompleteFrom
	RefreshedAt  time.Time // when the last refresh finished
	// RefreshStarted is when the last refresh began. Every record written
	// before it is on hand, so the daily history judges whether a day is
	// over by it, not by RefreshedAt: a slow refresh that began before
	// midnight can finish after it without having read the day's last
	// records.
	RefreshStarted time.Time
	Ready          bool // the first full read has finished
	ReadErrors     bool // the last refresh could not read part of the ledger
}

// Snapshot returns the ledger's current coverage and refresh state.
func (s *FileSource) Snapshot() Snapshot {
	s.mu.RLock()
	defer s.mu.RUnlock()
	oldest, complete := s.coverage()
	return Snapshot{
		Oldest:         oldest,
		CompleteFrom:   complete,
		RefreshedAt:    s.refreshedAt,
		RefreshStarted: s.refreshStarted,
		Ready:          s.ready.Load(),
		ReadErrors:     s.lastRefreshPartial,
	}
}

// DayRows returns every user's rows for one UTC day (YYYY-MM-DD), merged
// across all ledger files and sorted by model, then endpoint. Days with no
// usage give an empty map. Only the daily history calls this; pages always
// ask for one user.
func (s *FileSource) DayRows(day string) map[string][]Row {
	merged := make(map[string]map[bucketKey]*Agg)
	s.mu.RLock()
	for _, state := range s.files {
		for user, buckets := range state.buckets {
			for key, agg := range buckets {
				if key.day != day {
					continue
				}
				byKey := merged[user]
				if byKey == nil {
					byKey = make(map[bucketKey]*Agg)
					merged[user] = byKey
				}
				total := byKey[key]
				if total == nil {
					total = &Agg{}
					byKey[key] = total
				}
				total.Merge(agg)
			}
		}
	}
	s.mu.RUnlock()

	rows := make(map[string][]Row, len(merged))
	for user, byKey := range merged {
		for key, agg := range byKey {
			rows[user] = append(rows[user], Row{Day: key.day, Model: key.model, Endpoint: key.endpoint, Agg: *agg})
		}
		SortRows(rows[user])
	}
	return rows
}

// SortRows orders rows by day, then model, then endpoint, the order every
// Report uses.
func SortRows(rows []Row) {
	sort.Slice(rows, func(i, j int) bool {
		if rows[i].Day != rows[j].Day {
			return rows[i].Day < rows[j].Day
		}
		if rows[i].Model != rows[j].Model {
			return rows[i].Model < rows[j].Model
		}
		return rows[i].Endpoint < rows[j].Endpoint
	})
}
