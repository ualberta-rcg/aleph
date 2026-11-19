//go:build proxycheck

package proxycheck

import (
	"fmt"
	"io"
	"net/http"
	"net/url"
	"os"
	"regexp"
	"strings"
	"testing"
	"time"
)

// Forged identities are valid usernames (they pass the app's username rule) so
// that a pass means the proxy removed them, not that the app rejected their
// format. They are not expected to belong to anyone.
const (
	forged  = "proxycheck-forged"
	forged2 = "proxycheck-forged2"
)

var usernameRE = regexp.MustCompile(`^[a-z_][a-z0-9._-]{1,31}$`)

type config struct {
	base   *url.URL
	header string // identity header name the app reads
}

func load(t *testing.T) config {
	t.Helper()
	raw := os.Getenv("USAGE_UI_URL")
	if raw == "" {
		t.Fatal("USAGE_UI_URL is not set. This check fails until the usage UI is deployed behind its SAML proxy; set USAGE_UI_URL to its public URL (see usage-ui/README.md, Deploy).")
	}
	target, err := url.Parse(raw)
	// https only: over plain http the session cookie would be sent in the
	// clear, and a plain http-to-https redirect could pass for a sign-in
	// redirect.
	if err != nil || target.Scheme != "https" || target.Host == "" {
		t.Fatalf("USAGE_UI_URL must be the https URL of the usage UI, got %q", raw)
	}
	target.Path = strings.TrimSuffix(target.Path, "/")
	headerName := os.Getenv("USAGE_UI_AUTH_HEADER")
	if headerName == "" {
		headerName = "X-Remote-User"
	}
	return config{base: target, header: headerName}
}

// signedIn returns the operator's expected username and session cookie, or
// fails: this half of the check cannot pass without a real sign-in.
func signedIn(t *testing.T) (user, cookie string) {
	t.Helper()
	user = os.Getenv("USAGE_UI_EXPECT_USER")
	cookie = os.Getenv("USAGE_UI_SESSION_COOKIE")
	if user == "" || cookie == "" {
		t.Fatal("USAGE_UI_EXPECT_USER and USAGE_UI_SESSION_COOKIE must be set: sign in through the proxy in a browser, copy the Cookie request header for the usage UI, and set your own username.")
	}
	if !usernameRE.MatchString(user) || user == forged || user == forged2 {
		t.Fatalf("USAGE_UI_EXPECT_USER %q is not a usable username", user)
	}
	return user, cookie
}

// variant is one way a client might try to assert an identity.
type variant struct {
	name string
	set  func(headers http.Header, headerName, self string)
}

func variants() []variant {
	return []variant{
		{"single forged header", func(headers http.Header, headerName, _ string) {
			headers[http.CanonicalHeaderKey(headerName)] = []string{forged}
		}},
		{"two forged headers", func(headers http.Header, headerName, _ string) {
			headers[http.CanonicalHeaderKey(headerName)] = []string{forged, forged2}
		}},
		{"own name then forged, one line", func(headers http.Header, headerName, self string) {
			if self == "" {
				self = forged2
			}
			headers[http.CanonicalHeaderKey(headerName)] = []string{self + ", " + forged}
		}},
		// Some proxies and servers treat underscores and hyphens alike.
		// Sent verbatim (non-canonical key) so the underscore survives.
		{"underscore spelling", func(headers http.Header, headerName, _ string) {
			headers[strings.ReplaceAll(headerName, "-", "_")] = []string{forged}
		}},
	}
}

// paths are every route that shows a user's usage. Each must be protected.
var paths = []struct{ name, path string }{
	{"overview", "/"},
	{"models", "/models"},
	{"errors", "/errors"},
	{"report", "/report"},
	{"csv", "/usage.csv"},
}

func client() *http.Client {
	return &http.Client{
		Timeout: 30 * time.Second,
		// Report the proxy's own answer (usually a redirect to the IdP).
		CheckRedirect: func(*http.Request, []*http.Request) error { return http.ErrUseLastResponse },
	}
}

func fetch(t *testing.T, cfg config, path string, prepare func(http.Header)) (*http.Response, string) {
	t.Helper()
	target := *cfg.base
	target.Path += path
	req, err := http.NewRequest(http.MethodGet, target.String(), nil)
	if err != nil {
		t.Fatal(err)
	}
	prepare(req.Header)
	resp, err := client().Do(req)
	if err != nil {
		t.Fatalf("GET %s: %v", target.Redacted(), err)
	}
	defer resp.Body.Close()
	body, _ := io.ReadAll(io.LimitReader(resp.Body, 1<<20))
	return resp, string(body)
}

// refusal says whether resp is the proxy refusing a request without a
// session, and if not, why. Accepted are 401, 403, and a redirect to another
// host, normally the IdP's sign-in page. A redirect to the app's own host is
// not accepted, even to a login-looking path: an http-to-https or
// trailing-slash redirect would pass that test and prove nothing, and the
// path a proxy uses for its own sign-in handler varies too much to tell
// apart from the app's pages.
func refusal(cfg config, resp *http.Response) (ok bool, reason string) {
	switch resp.StatusCode {
	case http.StatusUnauthorized, http.StatusForbidden:
		return true, ""
	case http.StatusMovedPermanently, http.StatusFound, http.StatusSeeOther,
		http.StatusTemporaryRedirect, http.StatusPermanentRedirect:
		location, err := resp.Location()
		if err != nil {
			return false, fmt.Sprintf("status %d without a usable Location header", resp.StatusCode)
		}
		if strings.EqualFold(location.Hostname(), cfg.base.Hostname()) {
			return false, fmt.Sprintf("status %d redirects to %s on the app's own host, not to the IdP. If the proxy's sign-in handler is on this host, check by hand that following the redirect leads to the IdP", resp.StatusCode, location.Redacted())
		}
		return true, ""
	default:
		return false, fmt.Sprintf("status %d", resp.StatusCode)
	}
}

func leaksForged(resp *http.Response, body string) bool {
	text := body + " " + resp.Header.Get("Content-Disposition")
	return strings.Contains(text, forged)
}

// TestUnauthenticatedForgedHeaderIsRefused needs no credentials. Without a
// session, the proxy must answer itself (redirect to the IdP's host, or
// 401/403) no matter what identity header the client sends.
func TestUnauthenticatedForgedHeaderIsRefused(t *testing.T) {
	cfg := load(t)
	for _, route := range paths {
		for _, attempt := range variants() {
			path := route.path
			t.Run(fmt.Sprintf("%s %s", route.name, attempt.name), func(t *testing.T) {
				resp, body := fetch(t, cfg, path, func(headers http.Header) { attempt.set(headers, cfg.header, "") })
				if leaksForged(resp, body) {
					t.Fatalf("the response shows the forged identity %q: the proxy passes client identity headers through", forged)
				}
				if ok, reason := refusal(cfg, resp); !ok {
					t.Fatalf("%s without a session; expected a redirect to the IdP's host, or 401/403", reason)
				}
			})
		}
	}
}

// TestSignedInForgedHeaderIsIgnored needs the operator's own session. With a
// valid session, every forged header must be replaced by the operator's real
// identity.
func TestSignedInForgedHeaderIsIgnored(t *testing.T) {
	cfg := load(t)
	user, cookie := signedIn(t)
	attempts := append([]variant{{"no identity header", func(http.Header, string, string) {}}}, variants()...)
	for _, route := range paths {
		for _, attempt := range attempts {
			path := route.path
			t.Run(fmt.Sprintf("%s %s", route.name, attempt.name), func(t *testing.T) {
				resp, body := fetch(t, cfg, path, func(headers http.Header) {
					headers.Set("Cookie", cookie)
					attempt.set(headers, cfg.header, user)
				})
				if leaksForged(resp, body) {
					t.Fatalf("the response shows the forged identity %q: the proxy lets the client choose its identity", forged)
				}
				if resp.StatusCode != http.StatusOK {
					t.Fatalf("status %d with a valid session; expected 200 as %s. A 401 here usually means the proxy added its header next to the client's instead of replacing it; a redirect means the session cookie is missing or expired", resp.StatusCode, user)
				}
				if path == "/usage.csv" {
					if want := "aleph-usage-" + user + "-"; !strings.Contains(resp.Header.Get("Content-Disposition"), want) {
						t.Fatalf("CSV is not labelled for %q", user)
					}
				} else if want := "Signed in as <strong>" + user + "</strong>"; !strings.Contains(body, want) {
					t.Fatalf("page does not say it is signed in as %q", user)
				}
			})
		}
	}
}
