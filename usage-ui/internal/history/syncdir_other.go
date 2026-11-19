//go:build !unix

package history

// syncDir does nothing where directories cannot be synced (Windows, used
// only for development); the service runs on Linux.
func syncDir(string) error { return nil }
