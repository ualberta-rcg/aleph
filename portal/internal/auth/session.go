// Package auth manages signed stateless portal sessions, double-submit CSRF
// tokens, Tyk API-key validation, local-only Mock OIDC login, and the OIDC seam.
package auth

import (
	"crypto/hmac"
	"crypto/rand"
	"crypto/sha256"
	"crypto/subtle"
	"encoding/base64"
	"encoding/hex"
	"encoding/json"
	"errors"
	"fmt"
	"net/http"
	"net/url"
	"strings"
	"time"

	"github.com/ualberta-rcg/aleph/portal/internal/source"
)

const (
	MockOIDCGuardPhrase = "yes-local-testing-only"
	DefaultSessionTTL   = 12 * time.Hour
)

var (
	ErrUnauthenticated = errors.New("not signed in")
	ErrInvalidCSRF     = errors.New("invalid or missing CSRF token")
	ErrDeniedIdentity  = errors.New("shared service identities are not permitted in the user portal")
)

// Config configures the portal authentication Manager.
type Config struct {
	SessionSecret     []byte
	PublicOrigin      string
	AllowInsecureHTTP bool
	MockOIDCEnabled   bool
	AllowMockOIDC     string
	SessionTTL        time.Duration
	DeniedIdentities  map[string]bool
	OIDC              OIDCConfig
}

// ParseSessionSecret accepts either a >=64-char hex secret or a >=32-byte raw secret.
func ParseSessionSecret(raw string) ([]byte, error) {
	trimmed := strings.TrimSpace(raw)
	if len(trimmed) >= 64 {
		if decoded, err := hex.DecodeString(trimmed); err == nil && len(decoded) >= 32 {
			return decoded, nil
		}
	}
	if len(trimmed) < 32 {
		return nil, errors.New("PORTAL_SESSION_SECRET must be at least 32 bytes (or 64 hex chars)")
	}
	return []byte(trimmed), nil
}

// Manager issues and verifies portal sessions and CSRF tokens.
type Manager struct {
	secret          []byte
	publicOrigin    string
	secureCookies   bool
	mockOIDCEnabled bool
	ttl             time.Duration
	denied          map[string]bool
	oidc            OIDCConfig
	Now             func() time.Time
}

// NewManager validates security invariants (failing closed on unsafe combinations)
// and returns a configured Manager.
func NewManager(cfg Config) (*Manager, error) {
	if len(cfg.SessionSecret) < 32 {
		return nil, errors.New("session secret must be at least 32 bytes")
	}
	origin := strings.TrimRight(strings.TrimSpace(cfg.PublicOrigin), "/")
	if origin == "" {
		return nil, errors.New("PUBLIC_ORIGIN is required")
	}
	parsed, err := url.Parse(origin)
	if err != nil || parsed.Host == "" || (parsed.Scheme != "http" && parsed.Scheme != "https") {
		return nil, fmt.Errorf("PUBLIC_ORIGIN %q must be a valid http:// or https:// origin", cfg.PublicOrigin)
	}
	if parsed.Path != "" || parsed.RawQuery != "" {
		return nil, fmt.Errorf("PUBLIC_ORIGIN %q must not include a path or query", cfg.PublicOrigin)
	}
	isHTTPS := parsed.Scheme == "https"
	if !isHTTPS && !cfg.AllowInsecureHTTP {
		return nil, errors.New("http:// PUBLIC_ORIGIN requires ALLOW_INSECURE_HTTP=true (local testing only)")
	}
	if cfg.MockOIDCEnabled {
		if isHTTPS {
			return nil, errors.New("MOCK_OIDC_ENABLED=true is forbidden when PUBLIC_ORIGIN uses https://")
		}
		if cfg.AllowMockOIDC != MockOIDCGuardPhrase {
			return nil, fmt.Errorf("MOCK_OIDC_ENABLED=true requires ALLOW_MOCK_OIDC=%s", MockOIDCGuardPhrase)
		}
	}
	ttl := cfg.SessionTTL
	if ttl <= 0 {
		ttl = DefaultSessionTTL
	}
	denied := cfg.DeniedIdentities
	if denied == nil {
		denied = source.ParseDeniedIdentities(source.DefaultDeniedIdentities)
	}
	return &Manager{
		secret:          append([]byte(nil), cfg.SessionSecret...),
		publicOrigin:    origin,
		secureCookies:   isHTTPS,
		mockOIDCEnabled: cfg.MockOIDCEnabled,
		ttl:             ttl,
		denied:          denied,
		oidc:            cfg.OIDC,
		Now:             time.Now,
	}, nil
}

func (m *Manager) PublicOrigin() string    { return m.publicOrigin }
func (m *Manager) SecureCookies() bool     { return m.secureCookies }
func (m *Manager) MockOIDCEnabled() bool   { return m.mockOIDCEnabled }
func (m *Manager) OIDCEnabled() bool       { return m.oidc.Enabled() }
func (m *Manager) SessionTTL() time.Duration { return m.ttl }

func (m *Manager) ModeDescription() string {
	parts := []string{"api-key"}
	if m.mockOIDCEnabled {
		parts = append(parts, "mock-oidc(local)")
	}
	if m.oidc.Enabled() {
		parts = append(parts, "oidc")
	}
	return strings.Join(parts, "+")
}

// IsDeniedIdentity reports whether identity is blocked from personal portal access.
func (m *Manager) IsDeniedIdentity(identity string) bool {
	if identity == "" {
		return false
	}
	return m.denied[strings.ToLower(identity)]
}

func (m *Manager) SessionCookieName() string {
	if m.secureCookies {
		return "__Host-aleph_portal"
	}
	return "aleph_portal"
}

func (m *Manager) CSRFCookieName() string {
	if m.secureCookies {
		return "__Host-aleph_csrf"
	}
	return "aleph_csrf"
}

type sessionClaims struct {
	Version   int            `json:"v"`
	Subject   source.Subject `json:"sub"`
	IssuedAt  int64          `json:"iat"`
	ExpiresAt int64          `json:"exp"`
	Nonce     string         `json:"jti"`
}

// IssueSession writes an HMAC-SHA256 signed stateless session cookie.
func (m *Manager) IssueSession(w http.ResponseWriter, subj source.Subject) error {
	if !subj.Valid() || m.IsDeniedIdentity(subj.Identity) {
		return ErrDeniedIdentity
	}
	nonce, err := randomHex(8)
	if err != nil {
		return err
	}
	now := m.Now().UTC()
	claims := sessionClaims{
		Version:   1,
		Subject:   subj,
		IssuedAt:  now.Unix(),
		ExpiresAt: now.Add(m.ttl).Unix(),
		Nonce:     nonce,
	}
	payload, err := json.Marshal(claims)
	if err != nil {
		return err
	}
	encodedPayload := base64.RawURLEncoding.EncodeToString(payload)
	sig := m.sign(encodedPayload)
	token := "v1." + encodedPayload + "." + base64.RawURLEncoding.EncodeToString(sig)

	http.SetCookie(w, &http.Cookie{
		Name:     m.SessionCookieName(),
		Value:    token,
		Path:     "/",
		MaxAge:   int(m.ttl.Seconds()),
		HttpOnly: true,
		Secure:   m.secureCookies,
		SameSite: http.SameSiteLaxMode,
	})
	return nil
}

// ClearSession expires both the session and CSRF cookies.
func (m *Manager) ClearSession(w http.ResponseWriter) {
	for _, name := range []string{m.SessionCookieName(), m.CSRFCookieName()} {
		http.SetCookie(w, &http.Cookie{
			Name:     name,
			Value:    "",
			Path:     "/",
			MaxAge:   -1,
			HttpOnly: true,
			Secure:   m.secureCookies,
			SameSite: http.SameSiteLaxMode,
		})
	}
}

// CurrentSubject validates the signed session cookie and returns its Subject.
func (m *Manager) CurrentSubject(r *http.Request) (source.Subject, error) {
	cookie, err := r.Cookie(m.SessionCookieName())
	if err != nil || cookie.Value == "" {
		return source.Subject{}, ErrUnauthenticated
	}
	parts := strings.Split(cookie.Value, ".")
	if len(parts) != 3 || parts[0] != "v1" {
		return source.Subject{}, ErrUnauthenticated
	}
	gotSig, err := base64.RawURLEncoding.DecodeString(parts[2])
	if err != nil {
		return source.Subject{}, ErrUnauthenticated
	}
	wantSig := m.sign(parts[1])
	if !hmac.Equal(gotSig, wantSig) {
		return source.Subject{}, ErrUnauthenticated
	}
	rawPayload, err := base64.RawURLEncoding.DecodeString(parts[1])
	if err != nil {
		return source.Subject{}, ErrUnauthenticated
	}
	var claims sessionClaims
	if err := json.Unmarshal(rawPayload, &claims); err != nil || claims.Version != 1 {
		return source.Subject{}, ErrUnauthenticated
	}
	now := m.Now().UTC().Unix()
	if now >= claims.ExpiresAt {
		return source.Subject{}, ErrUnauthenticated
	}
	if !claims.Subject.Valid() || m.IsDeniedIdentity(claims.Subject.Identity) {
		return source.Subject{}, ErrUnauthenticated
	}
	return claims.Subject, nil
}

// EnsureCSRF returns the request's existing CSRF token or sets a fresh 32-byte hex cookie.
func (m *Manager) EnsureCSRF(w http.ResponseWriter, r *http.Request) (string, error) {
	if c, err := r.Cookie(m.CSRFCookieName()); err == nil && isHexToken(c.Value, 32) {
		return c.Value, nil
	}
	tok, err := randomHex(16)
	if err != nil {
		return "", err
	}
	http.SetCookie(w, &http.Cookie{
		Name:     m.CSRFCookieName(),
		Value:    tok,
		Path:     "/",
		MaxAge:   int(m.ttl.Seconds()),
		HttpOnly: true,
		Secure:   m.secureCookies,
		SameSite: http.SameSiteLaxMode,
	})
	return tok, nil
}

// VerifyCSRF checks Sec-Fetch-Site, Origin, and double-submit token equality.
func (m *Manager) VerifyCSRF(r *http.Request, formToken string) error {
	if sfs := strings.ToLower(strings.TrimSpace(r.Header.Get("Sec-Fetch-Site"))); sfs != "" {
		if sfs != "same-origin" && sfs != "none" {
			return ErrInvalidCSRF
		}
	}
	if origin := strings.TrimSpace(r.Header.Get("Origin")); origin != "" {
		origin = strings.TrimRight(origin, "/")
		if m.secureCookies {
			if !strings.EqualFold(origin, m.publicOrigin) {
				return ErrInvalidCSRF
			}
		} else {
			parsed, err := url.Parse(origin)
			if err != nil || parsed.Scheme != "http" || !strings.EqualFold(parsed.Host, r.Host) {
				return ErrInvalidCSRF
			}
		}
	}
	cookie, err := r.Cookie(m.CSRFCookieName())
	if err != nil || !isHexToken(cookie.Value, 32) || !isHexToken(formToken, 32) {
		return ErrInvalidCSRF
	}
	if subtle.ConstantTimeCompare([]byte(cookie.Value), []byte(formToken)) != 1 {
		return ErrInvalidCSRF
	}
	return nil
}

func (m *Manager) sign(encodedPayload string) []byte {
	mac := hmac.New(sha256.New, m.secret)
	_, _ = mac.Write([]byte("aleph-portal-v1:"))
	_, _ = mac.Write([]byte(encodedPayload))
	return mac.Sum(nil)
}

func randomHex(nBytes int) (string, error) {
	buf := make([]byte, nBytes)
	if _, err := rand.Read(buf); err != nil {
		return "", err
	}
	return hex.EncodeToString(buf), nil
}

func isHexToken(s string, exactLen int) bool {
	if len(s) != exactLen {
		return false
	}
	for i := 0; i < len(s); i++ {
		c := s[i]
		if !((c >= '0' && c <= '9') || (c >= 'a' && c <= 'f')) {
			return false
		}
	}
	return true
}
