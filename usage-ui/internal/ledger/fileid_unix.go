//go:build unix

package ledger

import (
	"fmt"
	"os"
	"syscall"
)

// fileID identifies a file across renames. RotatingFileHandler renames
// usage.log to usage.log.1, so tracking by device and inode lets the reader
// keep its offset instead of re-reading rotated data.
func fileID(path string, info os.FileInfo) string {
	if stat, ok := info.Sys().(*syscall.Stat_t); ok {
		return fmt.Sprintf("%d:%d", stat.Dev, stat.Ino)
	}
	return "path:" + path
}
