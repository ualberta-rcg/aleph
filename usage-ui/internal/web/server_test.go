package web

import (
	"context"
	"fmt"
	"html"
	"io"
	"net/http"
	"net/http/httptest"
	"os"
	"path/filepath"
	"regexp"
	"strings"
	"testing"
	"time"

	"github.com/ualberta-rcg/aleph/usage-ui/internal/auth"
	"github.com/ualberta-rcg/aleph/usage-ui/internal/ledger"
)

// testNow is the clock for every web test: midday on 16 November 2026, so
// 16 November is today and not over.
var testNow = time.Date(2026, 11, 16, 12, 0, 0, 0, time.UTC)

// ledgerLines is the default fixture. The oldest record is alice's at
// midnight on 1 November, in a rotated file, so records are complete from
// 1 November exactly. A 7-day range from 8 November therefore has a fully
// covered previous period, and the 14-day default (3 to 16 November) does
// not. On 10 November alice has two qwen35-122b chat requests (one of them
// a 429) and one ancient-greek-bert embedding; bob and a service key also
// have usage.
const ledgerLines = `{"ts":"2026-11-01T00:00:00Z","identity":"alice","identity_type":"user","endpoint":"/v1/chat/completions","model":"qwen35-122b","status":200,"latency_ms":800,"tokens":{"prompt":500,"completion":117,"total":617,"detail":{}},"context_window":131072,"derived":{"gpu_seconds":2.0}}
{"ts":"2026-11-10T10:00:00Z","identity":"alice","identity_type":"user","account":"alice","endpoint":"/v1/chat/completions","model":"qwen35-122b","status":200,"cold_start":false,"latency_ms":1000,"tokens":{"prompt":1000,"completion":234,"total":1234,"detail":{"completion_tokens_details":{"reasoning_tokens":100}}},"context_window":131072,"derived":{"gpu_seconds":4.0}}
{"ts":"2026-11-10T10:30:00Z","identity":"alice","identity_type":"user","endpoint":"/v1/embeddings","model":"ancient-greek-bert","status":200,"latency_ms":100,"tokens":{"prompt":480,"completion":0,"total":480,"detail":{"prompt_tokens":480}},"context_window":512,"derived":{"gpu_seconds":0.1}}
{"ts":"2026-11-10T10:45:00Z","identity":"alice","identity_type":"user","endpoint":"/v1/chat/completions","model":"qwen35-122b","status":429,"latency_ms":5,"tokens":{"prompt":0,"completion":0,"total":0,"detail":{}},"context_window":131072,"derived":{"gpu_seconds":0}}
{"ts":"2026-11-10T11:00:00Z","identity":"bob","identity_type":"user","account":"bob","endpoint":"/v1/secret-endpoint-of-bob","model":"secret-model-of-bob","status":503,"cold_start":false,"latency_ms":500,"tokens":{"prompt":77,"completion":0,"total":77},"derived":{"gpu_seconds":0.5}}
{"ts":"2026-11-10T12:00:00Z","identity":"service-webui","identity_type":"service","account":"service-webui","model":"gpt-oss-120b","status":200,"cold_start":false,"latency_ms":500,"tokens":{"prompt":5,"completion":5,"total":10},"derived":{"gpu_seconds":1}}
`

// userRecord is one successful chat request: prompt tokens only, 100 ms,
// and 0.5 GPU-seconds.
func userRecord(ts, identity, identityType, model string, tokens int) string {
	return fmt.Sprintf(`{"ts":%q,"identity":%q,"identity_type":%q,"endpoint":"/v1/chat/completions","model":%q,"status":200,"latency_ms":100,"tokens":{"prompt":%d,"completion":0,"total":%d},"derived":{"gpu_seconds":0.5}}`+"\n",
		ts, identity, identityType, model, tokens, tokens)
}

var pages = []struct{ path, label string }{
	{"/", "Overview"},
	{"/models", "Models"},
	{"/errors", "Errors"},
	{"/report", "Report"},
}

// csvHeader is the first line of every CSV download.
const csvHeader = "day_utc,records_complete,model,endpoint,requests,errors,cold_starts,prompt_tokens,completion_tokens,reasoning_tokens,reasoning_reported_requests,total_tokens,gpu_seconds_estimate,gpu_hours_estimate,avg_latency_ms\n"

func newTestServer(t *testing.T) http.Handler {
	t.Helper()
	return newTestServerWith(t, map[string]string{"pod/usage.log.1": ledgerLines})
}

// newTestServerWith serves a ledger made of the given files, by path
// relative to the ledger root.
func newTestServerWith(t *testing.T, files map[string]string) http.Handler {
	t.Helper()
	return serve(t, readLedger(t, writeLedger(t, files)))
}

// writeLedger writes ledger files under a new root and returns it.
func writeLedger(t *testing.T, files map[string]string) string {
	t.Helper()
	root := t.TempDir()
	for name, content := range files {
		path := filepath.Join(root, filepath.FromSlash(name))
		if err := os.MkdirAll(filepath.Dir(path), 0o755); err != nil {
			t.Fatal(err)
		}
		if err := os.WriteFile(path, []byte(content), 0o644); err != nil {
			t.Fatal(err)
		}
	}
	return root
}

// readLedger reads the ledger at root with one refresh at testNow.
func readLedger(t *testing.T, root string) *ledger.FileSource {
	t.Helper()
	src := ledger.NewFileSource(root, 0)
	src.Now = func() time.Time { return testNow }
	if _, err := src.Refresh(); err != nil {
		t.Fatal(err)
	}
	return src
}

// serve returns the routed handler over src. httptest.NewRequest gives
// every request RemoteAddr 192.0.2.1, so exactly that peer is trusted, as a
// production configuration trusts only the proxy.
func serve(t *testing.T, src ledger.Source) http.Handler {
	t.Helper()
	authn, err := auth.NewHeader(auth.HeaderConfig{Name: "X-Remote-User", TrustedProxies: "192.0.2.1"})
	if err != nil {
		t.Fatal(err)
	}
	srv, err := New(src, authn)
	if err != nil {
		t.Fatal(err)
	}
	srv.Now = func() time.Time { return testNow }
	return srv.Handler()
}

func get(t *testing.T, handler http.Handler, path, user string) (*http.Response, string) {
	t.Helper()
	request := httptest.NewRequest("GET", path, nil)
	if user != "" {
		request.Header.Set("X-Remote-User", user)
	}
	recorder := httptest.NewRecorder()
	handler.ServeHTTP(recorder, request)
	body, _ := io.ReadAll(recorder.Result().Body)
	return recorder.Result(), string(body)
}

// pageText returns a page as a reader sees its characters: html/template
// writes "+" as "&#43;" and "<" as "&lt;".
func pageText(t *testing.T, handler http.Handler, path string) string {
	t.Helper()
	res, body := get(t, handler, path, "alice")
	if res.StatusCode != http.StatusOK {
		t.Fatalf("%s: status %d: %s", path, res.StatusCode, body)
	}
	return html.UnescapeString(body)
}

func assertContains(t *testing.T, text string, wants ...string) {
	t.Helper()
	for _, want := range wants {
		if !strings.Contains(text, want) {
			t.Errorf("missing %q", want)
		}
	}
}

func assertNotContains(t *testing.T, text string, unwanted ...string) {
	t.Helper()
	for _, bad := range unwanted {
		if strings.Contains(text, bad) {
			t.Errorf("should not contain %q", bad)
		}
	}
}

var (
	fromPattern = regexp.MustCompile(`name="from" value="([^"]*)"`)
	toPattern   = regexp.MustCompile(`name="to" value="([^"]*)"`)
)

// shownRange returns the dates in a page's range form.
func shownRange(t *testing.T, body string) (from, to string) {
	t.Helper()
	fromMatch, toMatch := fromPattern.FindStringSubmatch(body), toPattern.FindStringSubmatch(body)
	if fromMatch == nil || toMatch == nil {
		t.Fatal("the page has no range form")
	}
	return fromMatch[1], toMatch[1]
}

// dayStub serves fixed rows and incomplete days, cut to the asked range,
// as the daily history does for days it could not save. It makes gaps the
// file reader alone cannot produce.
type dayStub struct {
	rows       []ledger.Row
	incomplete []string
}

func (stub dayStub) Ready() bool { return true }

func (stub dayStub) Usage(_ context.Context, user string, from, to time.Time) (ledger.Report, error) {
	fromDay, toDay := from.Format(ledger.DayLayout), to.Format(ledger.DayLayout)
	report := ledger.Report{User: user, From: from, To: to, Oldest: time.Date(2026, 10, 1, 0, 0, 0, 0, time.UTC)}
	for _, row := range stub.rows {
		if row.Day >= fromDay && row.Day <= toDay {
			report.Rows = append(report.Rows, row)
		}
	}
	for _, day := range stub.incomplete {
		if day >= fromDay && day <= toDay {
			report.Incomplete = append(report.Incomplete, day)
		}
	}
	return report, nil
}

// stubRow is one day of chat use: one request with the given tokens and an
// hour of GPU time.
func stubRow(day string, tokens int64) ledger.Row {
	return ledger.Row{Day: day, Model: "m", Endpoint: "/v1/chat/completions",
		Agg: ledger.Agg{Requests: 1, TotalTokens: tokens, GPUSeconds: 3600}}
}

func TestEveryResponseSendsTheSecurityHeaders(t *testing.T) {
	handler := newTestServer(t)
	for _, path := range []string{"/", "/models", "/errors", "/report", "/usage.csv", "/nope"} {
		t.Run(path, func(t *testing.T) {
			res, _ := get(t, handler, path, "alice")
			for header, want := range map[string]string{
				"Content-Security-Policy": "default-src 'none'; script-src 'self'; style-src 'self'; img-src 'self'; form-action 'self'; frame-ancestors 'none'; base-uri 'none'",
				"X-Content-Type-Options":  "nosniff",
				"X-Frame-Options":         "DENY",
				"Referrer-Policy":         "no-referrer",
				"Cache-Control":           "no-store",
			} {
				if got := res.Header.Get(header); got != want {
					t.Errorf("%s = %q, want %q", header, got, want)
				}
			}
		})
	}
}

// The CSP allows scripts and styles from the site only, so the pages load
// the hashed preference script and stylesheet and nothing inline.
func TestPagesLoadOnlyTheSitesOwnScriptAndNoInlineCode(t *testing.T) {
	handler := newTestServer(t)
	scriptTag := regexp.MustCompile(`<script[^>]*>`)
	ownScript := regexp.MustCompile(`^<script src="/assets/[0-9a-f]{12}/site\.js">$`)
	inlineHandler := regexp.MustCompile(`\son[a-z]+=`)
	for _, page := range pages {
		t.Run(page.label, func(t *testing.T) {
			_, body := get(t, handler, page.path+"?from=2026-11-08&to=2026-11-14", "alice")
			tags := scriptTag.FindAllString(body, -1)
			if len(tags) != 1 || !ownScript.MatchString(tags[0]) {
				t.Errorf("script tags = %q, want only the hashed site.js", tags)
			}
			if strings.Contains(body, " style=") || inlineHandler.MatchString(body) {
				t.Error("the page has an inline style or event handler")
			}
		})
	}
}

// Kubernetes routes traffic only to a ready pod, so the pod must not be
// ready before the ledger has been read once.
func TestReadyzIsUnavailableUntilTheFirstRefresh(t *testing.T) {
	res, _ := get(t, serve(t, ledger.NewFileSource(t.TempDir(), 0)), "/readyz", "")
	if res.StatusCode != http.StatusServiceUnavailable {
		t.Errorf("status %d, want 503", res.StatusCode)
	}
}

func TestReadyzIsOKAfterTheFirstRefresh(t *testing.T) {
	res, body := get(t, newTestServer(t), "/readyz", "")
	if res.StatusCode != http.StatusOK || body != "ready\n" {
		t.Errorf("status %d body %q, want 200 \"ready\n\"", res.StatusCode, body)
	}
}

// The liveness probe does not depend on the ledger, so a slow first read
// does not get the pod restarted.
func TestHealthzIsOKBeforeTheFirstRefresh(t *testing.T) {
	res, body := get(t, serve(t, ledger.NewFileSource(t.TempDir(), 0)), "/healthz", "")
	if res.StatusCode != http.StatusOK || body != "ok\n" {
		t.Errorf("status %d body %q, want 200 \"ok\n\"", res.StatusCode, body)
	}
}
