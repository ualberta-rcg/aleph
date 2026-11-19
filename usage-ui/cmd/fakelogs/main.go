// Command fakelogs writes a synthetic Aleph usage ledger for development.
//
//	go run ./cmd/fakelogs -out ./devdata
//
// The defaults give the layout a long-running site has: retired pod
// directories from an earlier rollout, and live pods whose logs have rotated
// often enough that their oldest records are gone. Run the UI with
// USAGE_LOG_BACKUPS set to the -backups value to see exact coverage.
//
// With -history-out, it also writes the daily totals the service would have
// saved while the ledger still held every day (see internal/history), so the
// pages can show saved days filling in what rotation removed:
//
//	go run ./cmd/fakelogs -out ./devdata -history-out ./devhistory -history-days 20
package main

import (
	"flag"
	"log"
	"os"
	"strings"
	"time"

	"github.com/ualberta-rcg/aleph/usage-ui/internal/fake"
	"github.com/ualberta-rcg/aleph/usage-ui/internal/history"
	"github.com/ualberta-rcg/aleph/usage-ui/internal/ledger"
)

func main() {
	out := flag.String("out", "./devdata", "ledger root to write")
	users := flag.String("users", "alice,bob,carol", "comma-separated usernames")
	days := flag.Int("days", 21, "days of history ending today (UTC)")
	perDay := flag.Int("per-day", 30, "average requests per user per day")
	live := flag.Int("live-pods", 3, "live gateway pod directories")
	retired := flag.Int("retired-pods", 2, "retired gateway pod directories")
	maxFileBytes := flag.Int("max-file-bytes", 256<<10, "rotate a pod's usage.log at this size, like GATEWAY_USAGE_LOG_MAX_BYTES (0: never rotate)")
	backups := flag.Int("backups", 3, "rotated files each pod keeps, like GATEWAY_USAGE_LOG_BACKUPS (0: never rotate)")
	seed := flag.Int64("seed", 1, "random seed")
	historyOut := flag.String("history-out", "", "also write saved daily totals here, as the service would have saved them (empty: none)")
	historyDays := flag.Int("history-days", 366, "days of saved totals to keep, like USAGE_HISTORY_DAYS")
	flag.Parse()

	var usernames []string
	for _, username := range strings.Split(*users, ",") {
		if username = strings.TrimSpace(username); username != "" {
			usernames = append(usernames, username)
		}
	}
	options := fake.Options{
		Out: *out, Users: usernames, Days: *days, End: time.Now().UTC(),
		PerDay: *perDay, LivePods: *live, Retired: *retired, Seed: *seed,
		MaxFileBytes: *maxFileBytes, Backups: *backups,
	}
	written, err := fake.Generate(options)
	if err != nil {
		log.Fatal(err)
	}
	log.Printf("wrote %d records under %s; run the UI with USAGE_LOG_BACKUPS=%d", written, *out, *backups)

	if *historyOut != "" {
		saved, err := writeHistory(options, *historyOut, *historyDays)
		if err != nil {
			log.Fatal(err)
		}
		log.Printf("saved %d days under %s; run the UI with USAGE_HISTORY_DIR=%s USAGE_HISTORY_DAYS=%d", saved, *historyOut, *historyOut, *historyDays)
	}
}

// writeHistory saves daily totals as the running service would have: it
// generates the same synthetic usage without rotation, so the ledger holds
// every day, and lets the history save each complete day from it.
func writeHistory(options fake.Options, dir string, keepDays int) (int, error) {
	fullLedger, err := os.MkdirTemp("", "fakelogs-full-")
	if err != nil {
		return 0, err
	}
	defer os.RemoveAll(fullLedger)
	options.Out, options.MaxFileBytes, options.Backups = fullLedger, 0, 0
	if _, err := fake.Generate(options); err != nil {
		return 0, err
	}
	src := ledger.NewFileSource(fullLedger, 0)
	if _, err := src.Refresh(); err != nil {
		return 0, err
	}
	store, err := history.Open(dir, keepDays)
	if err != nil {
		return 0, err
	}
	return history.Source{Ledger: src, Store: store}.SaveCompleteDays(time.Now())
}
