package web

import (
	"net/http"
	"net/http/httptest"
	"strings"
	"testing"
)

// Any other version, an unknown file, or the old unversioned path is a 404,
// so an outdated URL can never be cached with new content.
func TestStaleOrUnknownAssetsAre404(t *testing.T) {
	handler := newTestServer(t)
	for _, target := range []string{
		"/assets/000000000000/style.css",
		"/assets/" + strings.Repeat("a", 12) + "/missing.css",
		"/static/style.css",
	} {
		recorder := httptest.NewRecorder()
		handler.ServeHTTP(recorder, httptest.NewRequest("GET", target, nil))
		if recorder.Code != http.StatusNotFound {
			t.Errorf("%s: status %d, want 404", target, recorder.Code)
		}
		if recorder.Header().Get("Cache-Control") != "no-store" {
			t.Errorf("%s: a 404 must not be cached", target)
		}
	}
}
