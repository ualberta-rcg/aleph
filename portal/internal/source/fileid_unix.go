//go:build unix

package source

import (
	"fmt"
	"os"
	"syscall"
)

// fileID identifies a file across RotatingFileHandler renames using device+inode.
func fileID(path string, info os.FileInfo) string {
	if stat, ok := info.Sys().(*syscall.Stat_t); ok {
		return fmt.Sprintf("%d:%d", stat.Dev, stat.Ino)
	}
	return "path:" + path
}
