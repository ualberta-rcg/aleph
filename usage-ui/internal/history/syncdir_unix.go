//go:build unix

package history

import "os"

// syncDir flushes a directory's entries to disk, so a rename into it
// survives a crash of the node.
func syncDir(dir string) error {
	handle, err := os.Open(dir)
	if err != nil {
		return err
	}
	syncErr := handle.Sync()
	if closeErr := handle.Close(); syncErr == nil {
		syncErr = closeErr
	}
	return syncErr
}
