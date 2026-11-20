//go:build !unix

package source

import "os"

func fileID(path string, _ os.FileInfo) string {
	return "path:" + path
}
