//go:build !unix

package ledger

import "os"

// fileID falls back to the path on platforms without inodes. This is fine for
// local development against generated logs; production runs on Linux, where
// fileid_unix.go tracks files across rotation.
func fileID(path string, _ os.FileInfo) string {
	return "path:" + path
}
