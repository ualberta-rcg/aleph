package ledger

import (
	"context"
	"fmt"
	"os"
	"path/filepath"
	"strings"
	"sync"
	"testing"
)

// TestConcurrentRefreshAndQueries runs the production pattern: one goroutine
// refreshes while the gateway appends and rotates, and many requests query at
// the same time. Run it with -race; it also checks that readers never see a
// half-merged bucket and that the final totals are exact.
func TestConcurrentRefreshAndQueries(t *testing.T) {
	const (
		pods      = 4
		perPod    = 150 // records per pod and user
		rotateAt  = perPod / 2
		readers   = 8
		aliceToks = 10 // every alice record has 10 tokens
		bobToks   = 7
	)
	root := t.TempDir()
	logs := make([]string, pods)
	for i := range logs {
		logs[i] = filepath.Join(root, fmt.Sprintf("pod-%d", i), "usage.log")
		write(t, logs[i], "")
	}
	src := NewFileSource(root, 0)
	mustRefresh(t, src)

	// Inode tracking keeps usage monotonic across rotation. The path fallback
	// (non-Unix) briefly drops a rotated file's usage between its two files'
	// updates, so only check monotonic totals where inodes are in use.
	info, err := os.Stat(logs[0])
	if err != nil {
		t.Fatal(err)
	}
	monotonic := !strings.HasPrefix(fileID(logs[0], info), "path:")

	done := make(chan struct{})
	errs := make(chan error, readers+1)
	var wg sync.WaitGroup
	for range readers {
		wg.Add(1)
		go func() {
			defer wg.Done()
			var last int64
			for {
				select {
				case <-done:
					return
				default:
				}
				report, err := src.Usage(context.Background(), "alice", day1, day9)
				if err != nil {
					errs <- err
					return
				}
				var total, reqs int64
				for _, row := range report.Rows {
					if row.TotalTokens != aliceToks*row.Requests {
						errs <- fmt.Errorf("inconsistent bucket %s/%s: %d tokens for %d requests", row.Day, row.Model, row.TotalTokens, row.Requests)
						return
					}
					total += row.TotalTokens
					reqs += row.Requests
				}
				if written := int64(pods * perPod * aliceToks); total > written {
					errs <- fmt.Errorf("alice total %d exceeds the %d written", total, written)
					return
				}
				if monotonic && total < last {
					errs <- fmt.Errorf("alice total went down from %d to %d", last, total)
					return
				}
				last = total
				_ = src.Ready()
				_ = src.Skipped()
			}
		}()
	}

	// Writer: the gateway appending, plus the single refresher.
	for n := 0; n < perPod; n++ {
		for i, log := range logs {
			if n == rotateAt {
				if err := os.Rename(log, log+".1"); err != nil {
					t.Fatal(err)
				}
				write(t, log, "")
			}
			day := fmt.Sprintf("2026-11-0%dT10:00:00Z", 1+(n+i)%8)
			aliceLine := rec(day, "alice", "user", fmt.Sprintf("m%d", n%3), 200, false, aliceToks, 0, 0.5)
			if n%7 == 0 {
				// Write the line in two parts so some refreshes see half a line.
				appendTo(t, log, aliceLine[:len(aliceLine)/2])
				if _, err := src.Refresh(); err != nil {
					t.Fatal(err)
				}
				appendTo(t, log, aliceLine[len(aliceLine)/2:])
			} else {
				appendTo(t, log, aliceLine)
			}
			appendTo(t, log, rec(day, "bob", "user", "m0", 200, false, bobToks, 0, 0.5))
		}
		if _, err := src.Refresh(); err != nil {
			t.Fatal(err)
		}
	}
	close(done)
	wg.Wait()
	close(errs)
	for err := range errs {
		t.Error(err)
	}

	mustRefresh(t, src)
	if got := totals(t, src, "alice"); got.Requests != pods*perPod || got.TotalTokens != pods*perPod*aliceToks {
		t.Fatalf("alice final: %+v, want %d requests and %d tokens", got, pods*perPod, pods*perPod*aliceToks)
	}
	if got := totals(t, src, "bob"); got.Requests != pods*perPod || got.TotalTokens != pods*perPod*bobToks {
		t.Fatalf("bob final: %+v, want %d requests and %d tokens", got, pods*perPod, pods*perPod*bobToks)
	}
}
