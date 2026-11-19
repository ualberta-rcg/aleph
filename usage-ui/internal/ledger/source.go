package ledger

import (
	"context"
	"sort"
	"time"
)

// Source answers usage questions for one user. The file-backed implementation
// reads the gateway ledger directly; a central-logging implementation can
// replace it without changing the web layer.
type Source interface {
	// Usage returns the user's usage for the inclusive UTC day range.
	Usage(ctx context.Context, user string, from, to time.Time) (Report, error)
	// Ready reports whether the source has completed its first load.
	Ready() bool
}

// Row is one day, model, and endpoint bucket.
type Row struct {
	Day      string `json:"day"`
	Model    string `json:"model"`
	Endpoint string `json:"endpoint"`
	Agg
}

// Report is a user's usage plus the window of data the source can see.
type Report struct {
	User string
	From time.Time
	To   time.Time
	// Rows are sorted by day, then model, then endpoint.
	Rows []Row
	// Oldest is the earliest record the source holds, across every user.
	Oldest time.Time
	// Incomplete lists, in order, the days in the range whose records may be
	// partly or wholly missing. Pages mark these days and leave them out of
	// the report statement. Days not listed have every record on hand.
	Incomplete []string
	// CompleteFrom is the time from which the ledger holds every record the
	// gateway wrote; zero means no ledger file can have been deleted. It
	// describes the ledger alone, and Incomplete already accounts for it, so
	// pages use Incomplete. The daily history uses it to fill lost days.
	CompleteFrom time.Time
	// Newest is the latest record the source holds.
	Newest      time.Time
	RefreshedAt time.Time
	// ReadErrors is true when the last refresh could not read part of the
	// ledger. Usage already read from those files is still included, but
	// newer records in them may be missing.
	ReadErrors bool
	// SavedDays counts the days in the range whose rows come from the daily
	// history rather than the ledger. Only history.Source sets it.
	SavedDays int
}

// IsIncomplete reports whether day (YYYY-MM-DD) is in r.Incomplete.
func (r Report) IsIncomplete(day string) bool {
	i := sort.SearchStrings(r.Incomplete, day)
	return i < len(r.Incomplete) && r.Incomplete[i] == day
}

// DaysBefore lists the days from from to to, inclusive, that fall before
// first. A zero first gives none.
func DaysBefore(from, to, first time.Time) []string {
	var days []string
	if first.IsZero() {
		return days
	}
	for day := from.UTC(); !day.After(to.UTC()) && day.Before(first); day = day.AddDate(0, 0, 1) {
		days = append(days, day.Format(DayLayout))
	}
	return days
}
