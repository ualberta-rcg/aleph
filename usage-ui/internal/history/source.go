package history

import (
	"context"
	"log"
	"time"

	"github.com/ualberta-rcg/aleph/usage-ui/internal/ledger"
)

// settleTime is how long after a day ends a refresh must have started before
// that day is saved. The gateway writes each record when its request
// finishes, so a refresh that starts a few minutes after midnight reads
// every record of the day before; the margin allows for clock differences
// and write buffering.
const settleTime = 5 * time.Minute

// Source answers usage questions from the live ledger, and from saved days
// for days the ledger no longer holds completely.
type Source struct {
	Ledger *ledger.FileSource
	Store  *Store
}

// Ready implements ledger.Source.
func (s Source) Ready() bool { return s.Ledger.Ready() }

// Usage implements ledger.Source. Each day the ledger does not hold in full
// is taken from the saved days when it was saved, replacing the ledger's
// partial rows. A day is complete when the ledger holds it in full or it was
// saved; every other day in the range is listed in Report.Incomplete.
func (s Source) Usage(ctx context.Context, user string, from, to time.Time) (ledger.Report, error) {
	report, err := s.Ledger.Usage(ctx, user, from, to)
	if err != nil {
		return report, err
	}
	saved := s.Store.userDays(user, report.From.UTC().Format(ledger.DayLayout), report.To.UTC().Format(ledger.DayLayout))

	// The ledger lists the days it does not hold in full; keep those that
	// were not saved, and take the saved ones from the history.
	fromSaved := map[string]bool{}
	var incomplete []string
	for _, day := range report.Incomplete {
		if _, ok := saved[day]; ok {
			fromSaved[day] = true
		} else {
			incomplete = append(incomplete, day)
		}
	}
	report.Incomplete = incomplete
	if len(fromSaved) > 0 {
		kept := report.Rows[:0]
		for _, row := range report.Rows {
			if !fromSaved[row.Day] {
				kept = append(kept, row)
			}
		}
		for day := range fromSaved {
			kept = append(kept, saved[day]...)
		}
		report.Rows = kept
		ledger.SortRows(report.Rows)
		report.SavedDays = len(fromSaved)
	}
	if oldest := s.Store.Oldest(); oldest != "" {
		day, _ := time.Parse(ledger.DayLayout, oldest)
		if report.Oldest.IsZero() || day.Before(report.Oldest) {
			report.Oldest = day
		}
	}
	return report, nil
}

// lastSettledDay is the last day that ended at least settleTime before a
// refresh began, so that refresh read all of its records.
func lastSettledDay(refreshStarted time.Time) time.Time {
	return ledger.DayOf(refreshStarted.Add(-settleTime)).AddDate(0, 0, -1)
}

// SaveCompleteDays saves every day that is over, fully held by the ledger,
// within the retention period, and not saved yet. It returns how many days
// it saved.
//
// It must not run while the ledger refreshes: call it from the ledger's
// OnRefresh hook, or after a Refresh call has returned. It saves nothing
// while the ledger is loading or could not be read in full, since a day
// saved then could be missing records for good.
func (s Source) SaveCompleteDays(now time.Time) (int, error) {
	snap := s.Ledger.Snapshot()
	if !snap.Ready || snap.ReadErrors || snap.Oldest.IsZero() {
		return 0, nil
	}
	// The ledger holds every day from its first complete day; when nothing
	// has rotated away, from the day of its oldest record.
	first := ledger.FirstCompleteDay(snap.CompleteFrom)
	if first.IsZero() {
		first = ledger.DayOf(snap.Oldest)
	}
	if retention := s.Store.retentionStart(now); first.Before(retention) {
		first = retention
	}
	last := lastSettledDay(snap.RefreshStarted)

	saved := 0
	for day := first; !day.After(last); day = day.AddDate(0, 0, 1) {
		key := day.Format(ledger.DayLayout)
		if s.Store.Has(key) {
			continue
		}
		if err := s.Store.Save(key, s.Ledger.DayRows(key)); err != nil {
			return saved, err
		}
		saved++
	}
	return saved, nil
}

// Updater returns the function to set as the ledger's OnRefresh hook. After
// each refresh it saves the days that are complete, and once a day it
// deletes days past the retention period.
func (s Source) Updater(now func() time.Time) func() {
	lastPruned := ""
	return func() {
		current := now()
		saved, err := s.SaveCompleteDays(current)
		if err != nil {
			log.Printf("%v", err)
		}
		if saved > 0 {
			log.Printf("history: saved %d complete day(s)", saved)
		}
		if today := current.UTC().Format(ledger.DayLayout); today != lastPruned {
			s.Store.Prune(current)
			lastPruned = today
		}
	}
}
