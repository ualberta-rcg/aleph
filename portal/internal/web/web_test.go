package web_test

import (
	"net/http"
	"net/http/httptest"
	"net/url"
	"os"
	"path/filepath"
	"strings"
	"testing"
	"time"

	"github.com/ualberta-rcg/aleph/portal/internal/auth"
	"github.com/ualberta-rcg/aleph/portal/internal/catalog"
	"github.com/ualberta-rcg/aleph/portal/internal/fake"
	"github.com/ualberta-rcg/aleph/portal/internal/source"
	"github.com/ualberta-rcg/aleph/portal/internal/web"
)

func setupTestPortal(t *testing.T) (*web.Server, *source.LedgerSource, string) {
	t.Helper()
	logDir := t.TempDir()
	now := time.Date(2026, 11, 20, 14, 0, 0, 0, time.UTC)
	if err := fake.Generate(fake.Options{
		Out:          logDir,
		Users:        []string{"alice", "Kevin"},
		Days:         10,
		End:          now,
		PerDay:       12,
		LivePods:     2,
		Retired:      1,
		Seed:         42,
		MaxFileBytes: 1 << 20,
		Backups:      5,
	}); err != nil {
		t.Fatalf("fake.Generate: %v", err)
	}
	// Add a formula-prefixed model row to verify CSV injection defense.
	extraPath := filepath.Join(logDir, "model-gateway-extra", "usage.log")
	if err := os.MkdirAll(filepath.Dir(extraPath), 0o755); err != nil {
		t.Fatal(err)
	}
	aliceFP := source.ComputeKeyFP(fake.SyntheticKey("alice"))
	evilRow := `{"ts":"2026-11-19T12:00:00Z","identity":"alice","identity_type":"user","account":"def-pi","key_fp":{"sha256_8":"` + aliceFP.SHA256_8 + `","last4":"` + aliceFP.Last4 + `"},"endpoint":"/v1/chat/completions","model":"=SUM(A1:A2)","status":200,"latency_ms":500,"tokens":{"prompt":10,"completion":20,"total":30,"detail":{"completion_tokens_details":{"reasoning_tokens":5}}},"context_window":32768,"derived":{"gpu_seconds":1.0}}` + "\n"
	if err := os.WriteFile(extraPath, []byte(evilRow), 0o644); err != nil {
		t.Fatal(err)
	}

	ledger := source.NewLedgerSource(source.LedgerConfig{
		Root:               logDir,
		Backups:            5,
		MaxConcurrentScans: 1,
	})
	ledger.Now = func() time.Time { return now }
	if _, err := ledger.Refresh(); err != nil {
		t.Fatalf("ledger.Refresh: %v", err)
	}

	// Mock Tyk server accepting alice's synthetic key.
	aliceKey := fake.SyntheticKey("alice")
	tykSrv := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		if r.Header.Get("Authorization") == "Bearer "+aliceKey {
			w.WriteHeader(http.StatusOK)
			_, _ = w.Write([]byte(`{"object":"list","data":[]}`))
			return
		}
		w.WriteHeader(http.StatusUnauthorized)
	}))
	t.Cleanup(tykSrv.Close)

	tykValidator, err := auth.NewTykValidator(tykSrv.URL+"/v1/models", 2*time.Second)
	if err != nil {
		t.Fatalf("NewTykValidator: %v", err)
	}

	// Mock live catalog server with dynamic model IDs.
	catSrv := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, _ *http.Request) {
		w.Header().Set("Content-Type", "application/json")
		_, _ = w.Write([]byte(`{"object":"list","data":[
			{"id":"live-chat-alpha","type":"chat","mode":"both","ready":true,"scaled_up":true,"scaling":{"scale_to_zero":false}},
			{"id":"live-embed-beta","type":"embeddings","mode":"api","ready":true,"scaled_up":true,"scaling":{"scale_to_zero":false}}
		]}`))
	}))
	t.Cleanup(catSrv.Close)
	catClient := catalog.NewClient(catSrv.URL+"/v1/models?all=true", 5*time.Minute)

	mgr, err := auth.NewManager(auth.Config{
		SessionSecret:     []byte("0123456789abcdef0123456789abcdef"),
		PublicOrigin:      "http://localhost:30080",
		AllowInsecureHTTP: true,
		MockOIDCEnabled:   true,
		AllowMockOIDC:     auth.MockOIDCGuardPhrase,
	})
	if err != nil {
		t.Fatalf("auth.NewManager: %v", err)
	}
	mgr.Now = func() time.Time { return now }

	srv, err := web.New(web.Config{
		Source:     ledger,
		Auth:       mgr,
		Tyk:        tykValidator,
		Catalog:    catClient,
		SiteName:   "Aleph",
		APIBaseURL: "https://inference.vulcan.alliancecan.ca",
		WebUIURL:   "https://llm.vulcan.alliancecan.ca",
		Now:        func() time.Time { return now },
	})
	if err != nil {
		t.Fatalf("web.New: %v", err)
	}
	return srv, ledger, aliceKey
}

func extractCSRF(t *testing.T, handler http.Handler) (*http.Cookie, string) {
	t.Helper()
	req := httptest.NewRequest(http.MethodGet, "http://localhost:30080/login", nil)
	rec := httptest.NewRecorder()
	handler.ServeHTTP(rec, req)
	if rec.Code != http.StatusOK {
		t.Fatalf("GET /login = %d, want 200", rec.Code)
	}
	var csrfCookie *http.Cookie
	for _, c := range rec.Result().Cookies() {
		if c.Name == "aleph_csrf" {
			csrfCookie = c
		}
	}
	if csrfCookie == nil {
		t.Fatal("missing aleph_csrf cookie on GET /login")
	}
	return csrfCookie, csrfCookie.Value
}

func TestUnauthenticatedRedirectsAndSafeNext(t *testing.T) {
	srv, _, _ := setupTestPortal(t)
	h := srv.Handler()

	req := httptest.NewRequest(http.MethodGet, "http://localhost:30080/models?from=2026-11-10&to=2026-11-20", nil)
	rec := httptest.NewRecorder()
	h.ServeHTTP(rec, req)
	if rec.Code != http.StatusSeeOther {
		t.Fatalf("GET /models unauth = %d, want 303", rec.Code)
	}
	if loc := rec.Header().Get("Location"); !strings.HasPrefix(loc, "/login?next=") {
		t.Fatalf("unexpected redirect location: %q", loc)
	}

	// Open-redirect attempt on /login?next=//evil.example must sanitize to /.
	csrfCookie, token := extractCSRF(t, h)
	form := url.Values{
		"csrf_token": {token},
		"username":   {"alice"},
		"next":       {"//evil.example/phish"},
	}
	post := httptest.NewRequest(http.MethodPost, "http://localhost:30080/login/mock-oidc", strings.NewReader(form.Encode()))
	post.Host = "localhost:30080"
	post.Header.Set("Content-Type", "application/x-www-form-urlencoded")
	post.Header.Set("Origin", "http://localhost:30080")
	post.AddCookie(csrfCookie)
	postRec := httptest.NewRecorder()
	h.ServeHTTP(postRec, post)
	if postRec.Code != http.StatusSeeOther || postRec.Header().Get("Location") != "/" {
		t.Fatalf("open redirect not sanitized: status=%d loc=%q", postRec.Code, postRec.Header().Get("Location"))
	}
}

func TestMockOIDCAllSixTabsAndLogout(t *testing.T) {
	srv, _, _ := setupTestPortal(t)
	h := srv.Handler()

	csrfCookie, token := extractCSRF(t, h)
	form := url.Values{
		"csrf_token": {token},
		"username":   {"alice"},
		"next":       {"/"},
	}
	post := httptest.NewRequest(http.MethodPost, "http://localhost:30080/login/mock-oidc", strings.NewReader(form.Encode()))
	post.Host = "localhost:30080"
	post.Header.Set("Content-Type", "application/x-www-form-urlencoded")
	post.Header.Set("Origin", "http://localhost:30080")
	post.AddCookie(csrfCookie)
	postRec := httptest.NewRecorder()
	h.ServeHTTP(postRec, post)
	if postRec.Code != http.StatusSeeOther {
		t.Fatalf("POST /login/mock-oidc = %d, want 303", postRec.Code)
	}
	var sessionCookie *http.Cookie
	for _, c := range postRec.Result().Cookies() {
		if c.Name == "aleph_portal" {
			sessionCookie = c
		}
	}
	if sessionCookie == nil {
		t.Fatal("missing aleph_portal session cookie")
	}

	paths := []struct {
		path string
		want string
	}{
		{"/", "MOCK OIDC"},
		{"/models", "Speed and context"},
		{"/errors", "Recorded gateway errors"},
		{"/report", "allocated GPUs × request duration"},
		{"/connect", "live-chat-alpha"},
		{"/keys", "Disabled until institutional OIDC login is active"},
	}
	for _, tc := range paths {
		req := httptest.NewRequest(http.MethodGet, "http://localhost:30080"+tc.path, nil)
		req.AddCookie(sessionCookie)
		req.AddCookie(csrfCookie)
		rec := httptest.NewRecorder()
		h.ServeHTTP(rec, req)
		if rec.Code != http.StatusOK {
			t.Fatalf("GET %s = %d, want 200", tc.path, rec.Code)
		}
		if csp := rec.Header().Get("Content-Security-Policy"); !strings.Contains(csp, "default-src 'none'") {
			t.Fatalf("GET %s missing strict CSP: %q", tc.path, csp)
		}
		if cc := rec.Header().Get("Cache-Control"); cc != "no-store" {
			t.Fatalf("GET %s Cache-Control = %q, want no-store", tc.path, cc)
		}
		body := rec.Body.String()
		if !strings.Contains(body, tc.want) {
			t.Fatalf("GET %s body missing %q", tc.path, tc.want)
		}
	}

	// Sign out clears session cookie.
	logoutForm := url.Values{"csrf_token": {token}}
	logoutReq := httptest.NewRequest(http.MethodPost, "http://localhost:30080/logout", strings.NewReader(logoutForm.Encode()))
	logoutReq.Host = "localhost:30080"
	logoutReq.Header.Set("Content-Type", "application/x-www-form-urlencoded")
	logoutReq.Header.Set("Origin", "http://localhost:30080")
	logoutReq.AddCookie(sessionCookie)
	logoutReq.AddCookie(csrfCookie)
	logoutRec := httptest.NewRecorder()
	h.ServeHTTP(logoutRec, logoutReq)
	if logoutRec.Code != http.StatusSeeOther || logoutRec.Header().Get("Location") != "/login" {
		t.Fatalf("POST /logout = %d loc=%q", logoutRec.Code, logoutRec.Header().Get("Location"))
	}
}

func TestAPIKeyLoginAndBearerCSVFormulaProtection(t *testing.T) {
	srv, _, aliceKey := setupTestPortal(t)
	h := srv.Handler()

	// Unauthenticated CSV without Bearer returns 401.
	unauthCSV := httptest.NewRequest(http.MethodGet, "http://localhost:30080/usage.csv", nil)
	unauthRec := httptest.NewRecorder()
	h.ServeHTTP(unauthRec, unauthCSV)
	if unauthRec.Code != http.StatusUnauthorized {
		t.Fatalf("unauth GET /usage.csv = %d, want 401", unauthRec.Code)
	}

	// Direct CLI Bearer CSV export succeeds and escapes '=SUM(A1:A2)' as "'=SUM(A1:A2)".
	csvReq := httptest.NewRequest(http.MethodGet, "http://localhost:30080/usage.csv?from=2026-11-15&to=2026-11-20", nil)
	csvReq.Header.Set("Authorization", "Bearer "+aliceKey)
	csvRec := httptest.NewRecorder()
	h.ServeHTTP(csvRec, csvReq)
	if csvRec.Code != http.StatusOK {
		t.Fatalf("Bearer GET /usage.csv = %d, want 200", csvRec.Code)
	}
	csvBody := csvRec.Body.String()
	if !strings.Contains(csvBody, "'=SUM(A1:A2)") {
		t.Fatalf("CSV did not escape formula-prefixed model name:\n%s", csvBody)
	}

	// Browser form login with pasted `export TYK_KEY='...'` succeeds.
	csrfCookie, token := extractCSRF(t, h)
	form := url.Values{
		"csrf_token": {token},
		"api_key":    {"export TYK_KEY='" + aliceKey + "'"},
		"next":       {"/keys"},
	}
	post := httptest.NewRequest(http.MethodPost, "http://localhost:30080/login", strings.NewReader(form.Encode()))
	post.Host = "localhost:30080"
	post.Header.Set("Content-Type", "application/x-www-form-urlencoded")
	post.Header.Set("Origin", "http://localhost:30080")
	post.AddCookie(csrfCookie)
	postRec := httptest.NewRecorder()
	h.ServeHTTP(postRec, post)
	if postRec.Code != http.StatusSeeOther || postRec.Header().Get("Location") != "/keys" {
		t.Fatalf("POST /login = %d loc=%q, want 303 /keys", postRec.Code, postRec.Header().Get("Location"))
	}
}

func TestPrometheusBackendFailsClosedGracefully(t *testing.T) {
	prom, err := source.NewPrometheusSource("http://prometheus.monitoring.svc:9090")
	if err != nil {
		t.Fatalf("NewPrometheusSource: %v", err)
	}
	mgr, err := auth.NewManager(auth.Config{
		SessionSecret:     []byte("0123456789abcdef0123456789abcdef"),
		PublicOrigin:      "http://localhost:30080",
		AllowInsecureHTTP: true,
		MockOIDCEnabled:   true,
		AllowMockOIDC:     auth.MockOIDCGuardPhrase,
	})
	if err != nil {
		t.Fatal(err)
	}
	srv, err := web.New(web.Config{Source: prom, Auth: mgr})
	if err != nil {
		t.Fatal(err)
	}
	h := srv.Handler()

	// /readyz reports 503 when PrometheusSource is selected before subject metrics exist.
	readyRec := httptest.NewRecorder()
	h.ServeHTTP(readyRec, httptest.NewRequest(http.MethodGet, "http://localhost:30080/readyz", nil))
	if readyRec.Code != http.StatusServiceUnavailable {
		t.Fatalf("GET /readyz on Prometheus stub = %d, want 503", readyRec.Code)
	}
}

func TestPrivateNetAndHostGuard(t *testing.T) {
	srv, ledger, _ := setupTestPortal(t)
	mgr, err := auth.NewManager(auth.Config{
		SessionSecret:     []byte("0123456789abcdef0123456789abcdef"),
		PublicOrigin:      "http://localhost:30080",
		AllowInsecureHTTP: true,
		MockOIDCEnabled:   true,
		AllowMockOIDC:     auth.MockOIDCGuardPhrase,
	})
	if err != nil {
		t.Fatal(err)
	}
	guarded, err := web.New(web.Config{
		Source:         ledger,
		Auth:           mgr,
		PrivateNetOnly: true,
		Now:            srv.Now,
	})
	if err != nil {
		t.Fatal(err)
	}
	h := guarded.Handler()

	// Loopback + matching Host succeeds.
	okReq := httptest.NewRequest(http.MethodGet, "http://localhost:30080/login", nil)
	okReq.RemoteAddr = "127.0.0.1:54321"
	okRec := httptest.NewRecorder()
	h.ServeHTTP(okRec, okReq)
	if okRec.Code != http.StatusOK {
		t.Fatalf("loopback + matching host = %d, want 200", okRec.Code)
	}

	// RFC-1918 + pod IP Host on /readyz succeeds (kubelet probe behavior).
	probeReq := httptest.NewRequest(http.MethodGet, "http://10.42.0.99:8080/readyz", nil)
	probeReq.RemoteAddr = "10.42.0.1:41234"
	probeRec := httptest.NewRecorder()
	h.ServeHTTP(probeRec, probeReq)
	if probeRec.Code != http.StatusOK {
		t.Fatalf("kubelet private /readyz = %d, want 200", probeRec.Code)
	}

	// Public client IP is rejected 403 even with matching Host.
	pubReq := httptest.NewRequest(http.MethodGet, "http://localhost:30080/login", nil)
	pubReq.RemoteAddr = "8.8.8.8:54321"
	pubRec := httptest.NewRecorder()
	h.ServeHTTP(pubRec, pubReq)
	if pubRec.Code != http.StatusForbidden {
		t.Fatalf("public RemoteAddr = %d, want 403", pubRec.Code)
	}

	// Private client IP targeting wrong Host (e.g. secondary NIC) is rejected 403.
	wrongHostReq := httptest.NewRequest(http.MethodGet, "http://other-nic.example:30080/login", nil)
	wrongHostReq.RemoteAddr = "10.0.0.5:54321"
	wrongHostRec := httptest.NewRecorder()
	h.ServeHTTP(wrongHostRec, wrongHostReq)
	if wrongHostRec.Code != http.StatusForbidden {
		t.Fatalf("wrong Host = %d, want 403", wrongHostRec.Code)
	}
}
