package web

import (
	"context"
	"fmt"
	"io/fs"
	"net/http"
	"net/http/httptest"
	"os"
	"path/filepath"
	"reflect"
	"strings"
	"testing"
	"time"

	"github.com/ualberta-rcg/aleph/usage-ui/internal/history"
	"github.com/ualberta-rcg/aleph/usage-ui/internal/ledger"
)

// The service's guarantees, end to end through HTTP with a real ledger
// directory. Each is proven by the subtest of the same name below:
//
//   - a signed-in user sees only their own usage on every page and in the CSV
//   - service-key usage never appears
//   - a request without a trusted identity is refused
//   - the service never writes to the ledger directory
//   - every incomplete day in a range is reported as incomplete and marked in the CSV
//   - the report never counts an incomplete day or today and never names a future date
func TestWebInvariants(t *testing.T) {
	t.Run("a signed-in user sees only their own usage on every page and in the CSV", usersSeeOnlyTheirOwnUsage)
	t.Run("service-key usage never appears", serviceKeyUsageNeverAppears)
	t.Run("a request without a trusted identity is refused", requestsWithoutTrustedIdentityAreRefused)
	t.Run("the service never writes to the ledger directory", ledgerDirectoryIsNeverWritten)
	t.Run("every incomplete day in a range is reported as incomplete and marked in the CSV", everyIncompleteDayIsMarked)
	t.Run("the report never counts an incomplete day or today and never names a future date", reportCountsOnlyFinishedCompleteDays)
}

// userPaths are every path that shows a user's usage.
var userPaths = []string{"/", "/models", "/errors", "/report", "/usage.csv"}

// failedRecord is one request that failed with status 500 after 100 ms.
func failedRecord(ts, identity, model string) string {
	return fmt.Sprintf(`{"ts":%q,"identity":%q,"identity_type":"user","endpoint":"/v1/chat/completions","model":%q,"status":500,"latency_ms":100,"tokens":{"prompt":0,"completion":0,"total":0},"derived":{"gpu_seconds":0}}`+"\n",
		ts, identity, model)
}

func usersSeeOnlyTheirOwnUsage(t *testing.T) {
	// Each user has one failure too, so the Errors page names their model.
	handler := newTestServerWith(t, map[string]string{
		"pod-a/usage.log": userRecord("2026-11-10T10:00:00Z", "alice", "user", "alice-only-model", 111) +
			failedRecord("2026-11-10T10:30:00Z", "alice", "alice-only-model") +
			userRecord("2026-11-10T11:00:00Z", "bob", "user", "bob-only-model", 777777) +
			failedRecord("2026-11-10T11:30:00Z", "bob", "bob-only-model"),
		"pod-b/usage.log": userRecord("2026-11-11T10:00:00Z", "bob", "user", "bob-second-model", 222),
	})
	for _, viewer := range []struct{ user, own, other string }{
		{"alice", "alice-only-model", "bob"},
		{"bob", "bob-only-model", "alice"},
	} {
		for _, path := range userPaths {
			// A user parameter in the URL must not change whose usage is shown.
			_, body := get(t, handler, path+"?from=2026-11-08&to=2026-11-14&user="+viewer.other+"&identity="+viewer.other, viewer.user)
			if !strings.Contains(body, viewer.own) {
				t.Errorf("%s on %s: own model %s missing", viewer.user, path, viewer.own)
			}
			if strings.Contains(body, viewer.other) {
				t.Errorf("%s on %s: shows %q", viewer.user, path, viewer.other)
			}
		}
	}
	_, aliceCSV := get(t, handler, "/usage.csv?from=2026-11-08&to=2026-11-14", "alice")
	assertCSV(t, aliceCSV, csvHeader+"2026-11-10,yes,alice-only-model,/v1/chat/completions,2,1,0,111,0,,0,111,0.500,0.000139,100\n")
	_, bobCSV := get(t, handler, "/usage.csv?from=2026-11-08&to=2026-11-14", "bob")
	assertCSV(t, bobCSV, csvHeader+
		"2026-11-10,yes,bob-only-model,/v1/chat/completions,2,1,0,777777,0,,0,777777,0.500,0.000139,100\n"+
		"2026-11-11,yes,bob-second-model,/v1/chat/completions,1,0,0,222,0,,0,222,0.500,0.000139,100\n")
}

func serviceKeyUsageNeverAppears(t *testing.T) {
	// A service key's records, including one whose identity is a user's
	// name, are not that user's usage.
	handler := newTestServerWith(t, map[string]string{"pod/usage.log": userRecord("2026-11-10T10:00:00Z", "alice", "user", "alice-model", 5) +
		userRecord("2026-11-10T11:00:00Z", "service-webui", "service", "webui-model", 900) +
		userRecord("2026-11-10T12:00:00Z", "alice", "service", "service-named-alice-model", 800)})
	for _, path := range userPaths {
		_, body := get(t, handler, path+"?from=2026-11-08&to=2026-11-14", "alice")
		assertNotContains(t, body, "webui-model", "service-named-alice-model")
	}
	_, body := get(t, handler, "/usage.csv?from=2026-11-08&to=2026-11-14", "alice")
	assertCSV(t, body, csvHeader+"2026-11-10,yes,alice-model,/v1/chat/completions,1,0,0,5,0,,0,5,0.500,0.000139,100\n")
	for _, path := range userPaths {
		if _, body := get(t, handler, path+"?from=2026-11-08&to=2026-11-14", "service-webui"); strings.Contains(body, "webui-model") {
			t.Errorf("%s: a user named like the service key sees its usage", path)
		}
	}
}

func requestsWithoutTrustedIdentityAreRefused(t *testing.T) {
	handler := newTestServer(t)
	for _, tc := range []struct {
		name    string
		prepare func(r *http.Request)
	}{
		{"no identity header", func(r *http.Request) {}},
		{"an identity header from a peer that is not the proxy", func(r *http.Request) {
			r.RemoteAddr = "203.0.113.9:4242"
			r.Header.Set("X-Remote-User", "alice")
		}},
		{"the identity header twice", func(r *http.Request) {
			r.Header.Add("X-Remote-User", "alice")
			r.Header.Add("X-Remote-User", "bob")
		}},
		{"an identity that is not a valid username", func(r *http.Request) { r.Header.Set("X-Remote-User", "../../etc") }},
		{"an identity in another realm", func(r *http.Request) { r.Header.Set("X-Remote-User", "alice@other.example") }},
	} {
		t.Run(tc.name, func(t *testing.T) {
			for _, path := range userPaths {
				request := httptest.NewRequest("GET", path+"?from=2026-11-08&to=2026-11-14", nil)
				tc.prepare(request)
				recorder := httptest.NewRecorder()
				handler.ServeHTTP(recorder, request)
				want := "Not signed in. Sign in through your institution's login and try again.\n"
				if recorder.Code != http.StatusUnauthorized || recorder.Body.String() != want {
					t.Errorf("%s: status %d body %q, want 401 %q", path, recorder.Code, recorder.Body.String(), want)
				}
				if recorder.Header().Get("Content-Disposition") != "" {
					t.Errorf("%s: a refused request was offered a download", path)
				}
			}
		})
	}
}

// snapshotTree records every directory and file under root with its
// content.
func snapshotTree(t *testing.T, root string) map[string]string {
	t.Helper()
	tree := map[string]string{}
	err := filepath.WalkDir(root, func(path string, entry fs.DirEntry, err error) error {
		if err != nil {
			return err
		}
		rel, err := filepath.Rel(root, path)
		if err != nil {
			return err
		}
		if entry.IsDir() {
			tree[rel] = "directory"
			return nil
		}
		content, err := os.ReadFile(path)
		if err != nil {
			return err
		}
		tree[rel] = string(content)
		return nil
	})
	if err != nil {
		t.Fatal(err)
	}
	return tree
}

func ledgerDirectoryIsNeverWritten(t *testing.T) {
	root := writeLedger(t, map[string]string{
		"pod-a/usage.log.1": userRecord("2026-11-14T10:00:00Z", "alice", "user", "m", 5),
		"pod-a/usage.log":   userRecord("2026-11-16T10:00:00Z", "alice", "user", "m", 6) + `{"ts":"2026-11-16T11:00:00Z","partial`,
		"pod-b/usage.log":   "not json\n" + userRecord("2026-11-15T10:00:00Z", "bob", "user", "m", 7),
		"usage.log":         userRecord("2026-11-15T12:00:00Z", "alice", "user", "m", 8),
	})
	before := snapshotTree(t, root)

	// The production wiring: the ledger refreshes on Run's goroutine and the
	// daily history saves after each refresh.
	now := time.Date(2026, 11, 17, 12, 0, 0, 0, time.UTC)
	src := ledger.NewFileSource(root, 0)
	src.Now = func() time.Time { return now }
	store, err := history.Open(t.TempDir(), 366)
	if err != nil {
		t.Fatal(err)
	}
	combined := history.Source{Ledger: src, Store: store}
	update := combined.Updater(func() time.Time { return now })
	ctx, cancel := context.WithCancel(context.Background())
	refreshes := 0
	src.OnRefresh = func() {
		update()
		if refreshes++; refreshes == 2 {
			cancel()
		}
	}
	src.Run(ctx, time.Millisecond)
	if !store.Has("2026-11-16") {
		t.Fatal("the history saved nothing, so the check below proves less than it claims")
	}
	handler := serve(t, combined)
	for _, path := range userPaths {
		get(t, handler, path+"?from=2026-11-01&to=2026-11-16", "alice")
	}

	if after := snapshotTree(t, root); !reflect.DeepEqual(after, before) {
		t.Errorf("the ledger directory changed:\nbefore %q\n after %q", before, after)
	}
}

// incompleteFixture is a ledger that holds 6 November onward in full, with
// usage on the incomplete 5 November, and a history that saved 3 November.
func incompleteFixture(t *testing.T) history.Source {
	t.Helper()
	src := readLedger(t, writeLedger(t, map[string]string{"pod/usage.log.1": userRecord("2026-11-05T13:00:00Z", "alice", "user", "m", 50) +
		userRecord("2026-11-06T10:00:00Z", "alice", "user", "m", 60)}))
	store, err := history.Open(t.TempDir(), 366)
	if err != nil {
		t.Fatal(err)
	}
	saved := ledger.Row{Day: "2026-11-03", Model: "m", Endpoint: "/v1/chat/completions", Agg: ledger.Agg{Requests: 1, TotalTokens: 300}}
	if err := store.Save("2026-11-03", map[string][]ledger.Row{"alice": {saved}}); err != nil {
		t.Fatal(err)
	}
	return history.Source{Ledger: src, Store: store}
}

func everyIncompleteDayIsMarked(t *testing.T) {
	source := incompleteFixture(t)
	from, to := time.Date(2026, 11, 1, 0, 0, 0, 0, time.UTC), time.Date(2026, 11, 8, 0, 0, 0, 0, time.UTC)
	report, err := source.Usage(context.Background(), "alice", from, to)
	if err != nil {
		t.Fatal(err)
	}
	if want := []string{"2026-11-01", "2026-11-02", "2026-11-04", "2026-11-05"}; !reflect.DeepEqual(report.Incomplete, want) {
		t.Errorf("incomplete days = %v, want %v", report.Incomplete, want)
	}
	_, body := getCSV(t, serve(t, source), "from=2026-11-01&to=2026-11-08")
	assertCSV(t, body, csvHeader+
		"2026-11-01,no,,,0,0,0,0,0,,0,0,0.000,0.000000,0\n"+
		"2026-11-02,no,,,0,0,0,0,0,,0,0,0.000,0.000000,0\n"+
		"2026-11-03,yes,m,/v1/chat/completions,1,0,0,0,0,,0,300,0.000,0.000000,0\n"+
		"2026-11-04,no,,,0,0,0,0,0,,0,0,0.000,0.000000,0\n"+
		"2026-11-05,no,m,/v1/chat/completions,1,0,0,50,0,,0,50,0.500,0.000139,100\n"+
		"2026-11-06,yes,m,/v1/chat/completions,1,0,0,60,0,,0,60,0.500,0.000139,100\n")
}

func reportCountsOnlyFinishedCompleteDays(t *testing.T) {
	// Records are complete from 6 November. 5 November (incomplete) and
	// 16 November (today) have usage that must not be counted; the request
	// runs to 25 November, after today.
	handler := newTestServerWith(t, map[string]string{"pod/usage.log.1": userRecord("2026-11-05T13:00:00Z", "alice", "user", "m", 500) +
		userRecord("2026-11-10T10:00:00Z", "alice", "user", "m", 40) +
		userRecord("2026-11-16T08:00:00Z", "alice", "user", "m", 9000)})
	text := pageText(t, handler, "/report?from=2026-11-04&to=2026-11-25")
	assertStatement(t, text, "Between 6 November 2026 and 15 November 2026, I used an estimated <0.001 GPU-hours and 40 tokens across 1 model on Aleph, the University of Alberta Research Computing inference platform.")
	for date := 17; date <= 30; date++ {
		assertNotContains(t, text, fmt.Sprintf("2026-11-%d", date), fmt.Sprintf("%d November 2026", date), fmt.Sprintf("%d Nov", date))
	}
}
