//go:build unix

package history

import (
	"os"
	"path/filepath"
	"testing"
)

// The files hold every user's totals, so only the service's own account may
// read them.
func TestHistoryFilesAreReadableOnlyByTheService(t *testing.T) {
	dir := filepath.Join(t.TempDir(), "history")
	store, err := Open(dir, 366)
	if err != nil {
		t.Fatal(err)
	}
	if err := store.Save("2026-11-04", aliceRows("2026-11-04", 40)); err != nil {
		t.Fatal(err)
	}
	for path, want := range map[string]os.FileMode{dir: 0o700, filepath.Join(dir, "2026-11-04.jsonl.gz"): 0o600} {
		info, err := os.Stat(path)
		if err != nil {
			t.Fatal(err)
		}
		if got := info.Mode().Perm(); got&^want != 0 {
			t.Errorf("%s has mode %o, want at most %o", path, got, want)
		}
	}
}

// A directory the service cannot write to stops it at startup. Root can
// write anywhere, so the check cannot be shown when the tests run as root.
func TestOpenRefusesAReadOnlyDirectory(t *testing.T) {
	if os.Geteuid() == 0 {
		t.Skip("running as root, which can write to any directory")
	}
	dir := t.TempDir()
	if err := os.Chmod(dir, 0o500); err != nil {
		t.Fatal(err)
	}
	defer os.Chmod(dir, 0o700)
	if _, err := Open(dir, 366); err == nil {
		t.Error("Open should fail on a directory it cannot write to")
	}
}
