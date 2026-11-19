//go:build unix

package ledger

import (
	"os"
	"path/filepath"
	"strings"
	"testing"
)

// TestRotationTrackedByInode covers the production case: RotatingFileHandler
// renames full files down the chain (usage.log -> .1 -> .2) and every rotated
// file is about the same size. Tracking by path would see "usage.log.1" at the
// same size as before and keep stale usage while missing the new file's lines.
// Only tracking by device and inode gets these totals right.
func TestRotationTrackedByInode(t *testing.T) {
	root := t.TempDir()
	log := filepath.Join(root, "pod-a", "usage.log")
	// Same byte length on purpose: 10, 20, and 30 tokens all have two digits.
	first := rec("2026-11-02T10:00:00Z", "alice", "user", "m1", 200, false, 10, 0, 1)
	second := rec("2026-11-03T10:00:00Z", "alice", "user", "m1", 200, false, 20, 0, 1)
	third := rec("2026-11-04T10:00:00Z", "alice", "user", "m1", 200, false, 30, 0, 1)
	if len(first) != len(second) || len(second) != len(third) {
		t.Fatal("test records must have equal length")
	}

	write(t, log, first)
	src := NewFileSource(root, 0)
	mustRefresh(t, src)
	info, err := os.Stat(log)
	if err != nil {
		t.Fatal(err)
	}
	if id := fileID(log, info); strings.HasPrefix(id, "path:") {
		t.Fatalf("fileID fell back to the path (%s); inode tracking is not active", id)
	}

	rotate := func(next string) {
		t.Helper()
		for _, step := range [][2]string{{log + ".1", log + ".2"}, {log, log + ".1"}} {
			if _, err := os.Stat(step[0]); err == nil {
				if err := os.Rename(step[0], step[1]); err != nil {
					t.Fatal(err)
				}
			}
		}
		write(t, log, next)
	}

	rotate(second)
	mustRefresh(t, src)
	if got := totals(t, src, "alice"); got.TotalTokens != 30 || got.Requests != 2 {
		t.Fatalf("after first rotation: %+v", got)
	}

	rotate(third)
	mustRefresh(t, src)
	if got := totals(t, src, "alice"); got.TotalTokens != 60 || got.Requests != 3 {
		t.Fatalf("after second rotation: %+v", got)
	}

	// Oldest file deleted by rotation: its 10 tokens leave the report once
	// it has been missing for dropAfterMissedRefreshes refreshes.
	if err := os.Remove(log + ".2"); err != nil {
		t.Fatal(err)
	}
	refreshUntilDropped(t, src)
	if got := totals(t, src, "alice"); got.TotalTokens != 50 || got.Requests != 2 {
		t.Fatalf("after deleting the oldest file: %+v", got)
	}
}
