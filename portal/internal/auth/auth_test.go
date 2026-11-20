package auth

import (
	"context"
	"errors"
	"net/http"
	"net/http/httptest"
	"strings"
	"testing"
	"time"

	"github.com/ualberta-rcg/aleph/portal/internal/source"
)

var testSecret = []byte("0123456789abcdef0123456789abcdef")

func TestStartupFailClosedGuards(t *testing.T) {
	// 1. Mock OIDC on HTTPS must fail closed even with guard phrase.
	_, err := NewManager(Config{
		SessionSecret:   testSecret,
		PublicOrigin:    "https://portal.inference.vulcan.alliancecan.ca",
		MockOIDCEnabled: true,
		AllowMockOIDC:   MockOIDCGuardPhrase,
	})
	if err == nil {
		t.Fatal("expected Mock OIDC on https:// to fail closed")
	}

	// 2. Mock OIDC on HTTP without ALLOW_MOCK_OIDC phrase must fail closed.
	_, err = NewManager(Config{
		SessionSecret:     testSecret,
		PublicOrigin:      "http://localhost:30080",
		AllowInsecureHTTP: true,
		MockOIDCEnabled:   true,
		AllowMockOIDC:     "wrong",
	})
	if err == nil {
		t.Fatal("expected Mock OIDC without guard phrase to fail closed")
	}

	// 3. HTTP origin without ALLOW_INSECURE_HTTP=true must fail closed.
	_, err = NewManager(Config{
		SessionSecret: testSecret,
		PublicOrigin:  "http://localhost:30080",
	})
	if err == nil {
		t.Fatal("expected http:// without ALLOW_INSECURE_HTTP to fail closed")
	}

	// 4. Valid HTTPS public config uses __Host- Secure cookies.
	httpsMgr, err := NewManager(Config{
		SessionSecret: testSecret,
		PublicOrigin:  "https://portal.inference.vulcan.alliancecan.ca",
	})
	if err != nil {
		t.Fatalf("valid HTTPS config failed: %v", err)
	}
	if !httpsMgr.SecureCookies() || httpsMgr.SessionCookieName() != "__Host-aleph_portal" {
		t.Fatalf("expected __Host- Secure cookie on HTTPS, got %s", httpsMgr.SessionCookieName())
	}

	// 5. Valid local NodePort config uses plain cookie name over HTTP.
	localMgr, err := NewManager(Config{
		SessionSecret:     testSecret,
		PublicOrigin:      "http://localhost:30080",
		AllowInsecureHTTP: true,
		MockOIDCEnabled:   true,
		AllowMockOIDC:     MockOIDCGuardPhrase,
	})
	if err != nil {
		t.Fatalf("valid local NodePort config failed: %v", err)
	}
	if localMgr.SecureCookies() || localMgr.SessionCookieName() != "aleph_portal" {
		t.Fatalf("expected non-__Host cookie on HTTP, got %s", localMgr.SessionCookieName())
	}
}

func TestSessionTamperExpiryAndCSRF(t *testing.T) {
	now := time.Date(2026, 11, 20, 12, 0, 0, 0, time.UTC)
	mgr, err := NewManager(Config{
		SessionSecret:     testSecret,
		PublicOrigin:      "http://localhost:30080",
		AllowInsecureHTTP: true,
		SessionTTL:        time.Hour,
	})
	if err != nil {
		t.Fatal(err)
	}
	mgr.Now = func() time.Time { return now }

	rec := httptest.NewRecorder()
	subj := source.Subject{Scope: source.ScopeIdentity, AuthMethod: source.AuthMethodAPIKey, Identity: "alice"}
	if err := mgr.IssueSession(rec, subj); err != nil {
		t.Fatalf("IssueSession: %v", err)
	}
	cookies := rec.Result().Cookies()
	if len(cookies) != 1 {
		t.Fatalf("expected 1 session cookie, got %d", len(cookies))
	}

	req := httptest.NewRequest(http.MethodGet, "http://localhost:30080/", nil)
	req.AddCookie(cookies[0])
	got, err := mgr.CurrentSubject(req)
	if err != nil || got.Identity != "alice" {
		t.Fatalf("CurrentSubject = %+v, %v", got, err)
	}

	// Tampered signature must fail.
	tampered := *cookies[0]
	tampered.Value = tampered.Value[:len(tampered.Value)-2] + "aa"
	reqBad := httptest.NewRequest(http.MethodGet, "http://localhost:30080/", nil)
	reqBad.AddCookie(&tampered)
	if _, err := mgr.CurrentSubject(reqBad); !errors.Is(err, ErrUnauthenticated) {
		t.Fatalf("expected tampered session rejection, got %v", err)
	}

	// Expired session must fail.
	now = now.Add(2 * time.Hour)
	if _, err := mgr.CurrentSubject(req); !errors.Is(err, ErrUnauthenticated) {
		t.Fatalf("expected expired session rejection, got %v", err)
	}

	// CSRF double-submit + Origin validation (including localhost SSH tunnel).
	csrfRec := httptest.NewRecorder()
	csrfTok, err := mgr.EnsureCSRF(csrfRec, httptest.NewRequest(http.MethodGet, "http://localhost:18080/login", nil))
	if err != nil {
		t.Fatal(err)
	}
	postReq := httptest.NewRequest(http.MethodPost, "http://localhost:18080/login", nil)
	postReq.Host = "localhost:18080"
	postReq.Header.Set("Origin", "http://localhost:18080")
	postReq.Header.Set("Sec-Fetch-Site", "same-origin")
	for _, c := range csrfRec.Result().Cookies() {
		postReq.AddCookie(c)
	}
	if err := mgr.VerifyCSRF(postReq, csrfTok); err != nil {
		t.Fatalf("VerifyCSRF valid tunnel request failed: %v", err)
	}
	postEvil := httptest.NewRequest(http.MethodPost, "http://localhost:18080/login", nil)
	postEvil.Host = "localhost:18080"
	postEvil.Header.Set("Origin", "http://evil.example")
	for _, c := range csrfRec.Result().Cookies() {
		postEvil.AddCookie(c)
	}
	if err := mgr.VerifyCSRF(postEvil, csrfTok); !errors.Is(err, ErrInvalidCSRF) {
		t.Fatalf("expected cross-origin CSRF rejection, got %v", err)
	}
}

func TestCleanAPIKeyInputAndTykAuth(t *testing.T) {
	pamBlock := "# Aleph Tyk API key for demo_user. Managed by aleph-tyk-key (PAM) — do not edit.\n# Rotated automatically if it is ever invalid; ask your Aleph admin to revoke.\nTYK_KEY=eyJvcmciOiIiLCJpZCI6ImRlbW8ta2V5LTEyMzQiLCJoIjoibXVybXVyMTI4In0="
	pamBlockNoHash := strings.TrimPrefix(pamBlock, "# ")
	pamFlattened := strings.ReplaceAll(pamBlockNoHash, "\n", " ")

	cases := map[string]string{
		"raw-token-1234":                              "raw-token-1234",
		"Bearer raw-token-1234":                       "raw-token-1234",
		"Authorization: Bearer raw-token-1234":        "raw-token-1234",
		"# comment\nexport TYK_KEY=\"env-key-5678\"\n": "env-key-5678",
		pamBlock:       "eyJvcmciOiIiLCJpZCI6ImRlbW8ta2V5LTEyMzQiLCJoIjoibXVybXVyMTI4In0=",
		pamBlockNoHash: "eyJvcmciOiIiLCJpZCI6ImRlbW8ta2V5LTEyMzQiLCJoIjoibXVybXVyMTI4In0=",
		pamFlattened:   "eyJvcmciOiIiLCJpZCI6ImRlbW8ta2V5LTEyMzQiLCJoIjoibXVybXVyMTI4In0=",
	}
	for input, want := range cases {
		got, err := CleanAPIKeyInput(input)
		if err != nil || string(got) != want {
			t.Fatalf("CleanAPIKeyInput(%q) = %q, %v; want %q", input, string(got), err, want)
		}
	}
	for _, bad := range []string{"", "   ", "# comment only\n", "Aleph Tyk API key prose without assignment", "TYK_KEY=\"\""} {
		if _, err := CleanAPIKeyInput(bad); !errors.Is(err, ErrInvalidKeyFormat) {
			t.Fatalf("CleanAPIKeyInput(%q) expected ErrInvalidKeyFormat, got %v", bad, err)
		}
	}

	const validRawKey = "valid-user-key-9876"
	tykSrv := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		if r.Header.Get("Authorization") == "Bearer "+validRawKey {
			w.WriteHeader(http.StatusOK)
			_, _ = w.Write([]byte(`{"data":[]}`))
			return
		}
		w.WriteHeader(http.StatusUnauthorized)
	}))
	defer tykSrv.Close()

	dir := t.TempDir()
	src := source.NewLedgerSource(source.LedgerConfig{Root: dir})
	mgr, err := NewManager(Config{
		SessionSecret:     testSecret,
		PublicOrigin:      "http://localhost:30080",
		AllowInsecureHTTP: true,
	})
	if err != nil {
		t.Fatal(err)
	}
	validator, err := NewTykValidator(tykSrv.URL+"/v1/models", 2*time.Second)
	if err != nil {
		t.Fatal(err)
	}

	// Brand-new key with 0 ledger records resolves to ScopeKeyFP cleanly.
	subj, err := validator.Authenticate(context.Background(), "127.0.0.1:50000", validRawKey, src, mgr)
	if err != nil {
		t.Fatalf("Authenticate valid unindexed key: %v", err)
	}
	if subj.Scope != source.ScopeKeyFP || subj.KeyFP != source.ComputeKeyFP(validRawKey) {
		t.Fatalf("unexpected unindexed subject: %+v", subj)
	}

	// Rate limit after 10 bad attempts from same IP.
	for i := 0; i < maxLoginFailures; i++ {
		_, err = validator.Authenticate(context.Background(), "127.0.0.2:50000", "wrong-key", src, mgr)
		if err == nil || strings.Contains(err.Error(), "too many") {
			t.Fatalf("attempt %d unexpected err: %v", i, err)
		}
	}
	_, err = validator.Authenticate(context.Background(), "127.0.0.2:50000", validRawKey, src, mgr)
	if !errors.Is(err, ErrKeyRateLimited) {
		t.Fatalf("expected ErrKeyRateLimited after %d failures, got %v", maxLoginFailures, err)
	}
}
