package web

import (
	"crypto/sha256"
	"encoding/hex"
	"fmt"
	"io/fs"
	"net/http"
	"path"
)

// assets serves embedded static files at content-hashed URLs, e.g. /assets/3f2a9c01d4e7/style.css.
type assets struct {
	files map[string]asset
}

type asset struct {
	hash        string
	content     []byte
	contentType string
}

const assetHashLen = 12

var contentTypes = map[string]string{
	".css": "text/css; charset=utf-8",
	".js":  "text/javascript; charset=utf-8",
}

func loadAssets(static fs.FS) (assets, error) {
	loaded := assets{files: map[string]asset{}}
	entries, err := fs.ReadDir(static, ".")
	if err != nil {
		return loaded, err
	}
	for _, entry := range entries {
		if entry.IsDir() {
			continue
		}
		content, err := fs.ReadFile(static, entry.Name())
		if err != nil {
			return loaded, err
		}
		sum := sha256.Sum256(content)
		contentType, known := contentTypes[path.Ext(entry.Name())]
		if !known {
			contentType = "application/octet-stream"
		}
		loaded.files[entry.Name()] = asset{
			hash:        hex.EncodeToString(sum[:])[:assetHashLen],
			content:     content,
			contentType: contentType,
		}
	}
	return loaded, nil
}

func (a assets) URL(name string) string {
	file, ok := a.files[name]
	if !ok {
		panic(fmt.Sprintf("unknown static asset %q", name))
	}
	return "/assets/" + file.hash + "/" + name
}

func (a assets) ServeHTTP(w http.ResponseWriter, r *http.Request) {
	file, ok := a.files[r.PathValue("name")]
	if !ok || r.PathValue("hash") != file.hash {
		w.Header().Set("Cache-Control", "no-store")
		http.NotFound(w, r)
		return
	}
	headers := w.Header()
	headers.Set("Content-Type", file.contentType)
	headers.Set("Cache-Control", "public, max-age=31536000, immutable")
	headers.Set("ETag", `"`+file.hash+`"`)
	if r.Header.Get("If-None-Match") == `"`+file.hash+`"` {
		w.WriteHeader(http.StatusNotModified)
		return
	}
	_, _ = w.Write(file.content)
}
