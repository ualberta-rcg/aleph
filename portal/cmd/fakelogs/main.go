package main

import (
	"flag"
	"fmt"
	"log"
	"os"
	"strings"
	"time"

	"github.com/ualberta-rcg/aleph/portal/internal/fake"
	"github.com/ualberta-rcg/aleph/portal/internal/source"
)

func main() {
	outDir := flag.String("out", "", "Output directory for synthetic usage.log files (required)")
	usersCSV := flag.String("users", "alice,bob,Kevin", "Comma-separated synthetic ledger identities")
	days := flag.Int("days", 21, "Number of UTC days to synthesize")
	seed := flag.Int64("seed", 42, "Deterministic RNG seed")
	flag.Parse()

	if strings.TrimSpace(*outDir) == "" {
		fmt.Fprintln(os.Stderr, "usage: fakelogs -out <dir> [-users alice,bob] [-days 21]")
		os.Exit(2)
	}
	var users []string
	for _, u := range strings.Split(*usersCSV, ",") {
		if trimmed := strings.TrimSpace(u); trimmed != "" {
			users = append(users, trimmed)
		}
	}
	if err := fake.Generate(fake.Options{
		Out:          *outDir,
		Users:        users,
		Days:         *days,
		End:          time.Now().UTC(),
		PerDay:       20,
		LivePods:     3,
		Retired:      1,
		Seed:         *seed,
		MaxFileBytes: 512 << 10,
		Backups:      5,
	}); err != nil {
		log.Fatalf("fakelogs failed: %v", err)
	}
	fmt.Printf("wrote synthetic usage records to %s\n", *outDir)
	for _, u := range users {
		raw := fake.SyntheticKey(u)
		fp := source.ComputeKeyFP(raw)
		fmt.Printf("  user %-16s synthetic key=%s  fp=%s\n", u, raw, fp.Display())
	}
}
