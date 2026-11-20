package auth

import (
	"context"
	"errors"
	"fmt"
	"io"
	"net"
	"net/http"
	"strings"
	"sync"
	"time"

	"github.com/ualberta-rcg/aleph/portal/internal/source"
)

var (
	ErrInvalidKeyFormat = errors.New("enter a valid Aleph API key")
	ErrKeyRejected      = errors.New(" that API key was not accepted by the gateway")
	ErrKeyRateLimited   = errors.New("too many failed sign-in attempts or gateway rate limit reached; wait a minute and try again")
	ErrTykUnavailable   = errors.New("could not reach the authentication gateway right now; try again shortly")
)

const (
	maxRawKeyLength    = 512
	loginFailureWindow = 5 * time.Minute
	maxLoginFailures   = 10
	maxTrackedIPs      = 1024
)

// CleanAPIKeyInput extracts the raw API key from pasted user input, accepting
// bare keys, "Bearer <key>", "Authorization: Bearer <key>", or lines copied
// from ~/.aleph_tyk.env (such as `export TYK_KEY="..."`).
func CleanAPIKeyInput(input string) ([]byte, error) {
	candidate := strings.TrimSpace(input)
	if candidate == "" {
		return nil, ErrInvalidKeyFormat
	}
	if strings.ContainsAny(candidate, "\r\n") {
		var picked string
		for _, line := range strings.Split(candidate, "\n") {
			line = strings.TrimSpace(line)
			if line == "" || strings.HasPrefix(line, "#") {
				continue
			}
			if strings.HasPrefix(line, "export TYK_KEY=") || strings.HasPrefix(line, "TYK_KEY=") {
				picked = line
				break
			}
			if picked == "" {
				picked = line
			}
		}
		candidate = picked
	}
	candidate = strings.TrimSpace(candidate)
	if after, ok := strings.CutPrefix(candidate, "export "); ok {
		candidate = strings.TrimSpace(after)
	}
	for _, envPrefix := range []string{"TYK_KEY=", "OPENAI_API_KEY=", "ANTHROPIC_API_KEY="} {
		if after, ok := strings.CutPrefix(candidate, envPrefix); ok {
			candidate = strings.TrimSpace(after)
			break
		}
	}
	if len(candidate) >= 2 {
		if (candidate[0] == '"' && candidate[len(candidate)-1] == '"') ||
			(candidate[0] == '\'' && candidate[len(candidate)-1] == '\'') {
			candidate = strings.TrimSpace(candidate[1 : len(candidate)-1])
		}
	}
	lower := strings.ToLower(candidate)
	if strings.HasPrefix(lower, "authorization:") {
		candidate = strings.TrimSpace(candidate[len("authorization:"):])
		lower = strings.ToLower(candidate)
	}
	if strings.HasPrefix(lower, "bearer ") {
		candidate = strings.TrimSpace(candidate[len("bearer "):])
	}
	if len(candidate) == 0 || len(candidate) > maxRawKeyLength {
		return nil, ErrInvalidKeyFormat
	}
	for i := 0; i < len(candidate); i++ {
		c := candidate[i]
		if c <= 0x20 || c >= 0x7f {
			return nil, ErrInvalidKeyFormat
		}
	}
	return []byte(candidate), nil
}

// ZeroBytes overwrites sensitive byte slices in memory.
func ZeroBytes(b []byte) {
	for i := range b {
		b[i] = 0
	}
}

// TykValidator validates user API keys against Tyk and resolves Subject scope.
type TykValidator struct {
	validateURL string
	client      *http.Client
	Now         func() time.Time

	mu       sync.Mutex
	failures map[string][]time.Time
}

// NewTykValidator returns a TykValidator targeting validateURL (for example
// http://gateway-svc-tyk-oss-tyk-gateway.tyk.svc.cluster.local:8080/v1/models).
func NewTykValidator(validateURL string, timeout time.Duration) (*TykValidator, error) {
	validateURL = strings.TrimSpace(validateURL)
	if validateURL == "" {
		return nil, errors.New("TYK_VALIDATE_URL is required")
	}
	if timeout <= 0 {
		timeout = 5 * time.Second
	}
	return &TykValidator{
		validateURL: validateURL,
		client: &http.Client{
			Timeout: timeout,
			CheckRedirect: func(_ *http.Request, _ []*http.Request) error {
				return http.ErrUseLastResponse
			},
		},
		Now:      time.Now,
		failures: make(map[string][]time.Time),
	}, nil
}

// Authenticate validates rawInput against Tyk, resolves its Subject against
// backend, and zeroes the raw key bytes before returning.
func (v *TykValidator) Authenticate(
	ctx context.Context,
	remoteAddr string,
	rawInput string,
	backend source.Backend,
	mgr *Manager,
) (source.Subject, error) {
	clientIP := extractIP(remoteAddr)
	if v.isRateLimited(clientIP) {
		return source.Subject{}, ErrKeyRateLimited
	}

	keyBytes, err := CleanAPIKeyInput(rawInput)
	if err != nil {
		v.recordFailure(clientIP)
		return source.Subject{}, ErrInvalidKeyFormat
	}
	defer ZeroBytes(keyBytes)

	fp := source.ComputeKeyFP(string(keyBytes))
	if !fp.Valid() {
		v.recordFailure(clientIP)
		return source.Subject{}, ErrInvalidKeyFormat
	}

	// Fast check: if already indexed as a denied platform service key, refuse
	// before even hitting Tyk.
	if meta, ok := backend.LookupKeyFP(fp); ok && mgr.IsDeniedIdentity(meta.Identity) {
		return source.Subject{}, ErrDeniedIdentity
	}

	req, err := http.NewRequestWithContext(ctx, http.MethodGet, v.validateURL, nil)
	if err != nil {
		return source.Subject{}, fmt.Errorf("build tyk validation request: %w", err)
	}
	req.Header.Set("Authorization", "Bearer "+string(keyBytes))
	req.Header.Set("Accept", "application/json")

	resp, err := v.client.Do(req)
	if err != nil {
		return source.Subject{}, ErrTykUnavailable
	}
	_, _ = io.Copy(io.Discard, io.LimitReader(resp.Body, 64<<10))
	_ = resp.Body.Close()

	switch {
	case resp.StatusCode >= 200 && resp.StatusCode < 300:
		// Validated by Tyk.
	case resp.StatusCode == http.StatusTooManyRequests:
		return source.Subject{}, ErrKeyRateLimited
	case resp.StatusCode == http.StatusUnauthorized || resp.StatusCode == http.StatusForbidden:
		v.recordFailure(clientIP)
		return source.Subject{}, errors.New(strings.TrimSpace(ErrKeyRejected.Error()))
	default:
		return source.Subject{}, ErrTykUnavailable
	}

	return ResolveKeySubject(fp, backend, mgr)
}

// ResolveKeySubject maps a Tyk-validated KeyFP to either ScopeIdentity (for
// PAM "user" and historical "poc" identities) or ScopeKeyFP (for "service"
// researcher/trial keys and brand-new unindexed keys).
func ResolveKeySubject(fp source.KeyFP, backend source.Backend, mgr *Manager) (source.Subject, error) {
	meta, found := backend.LookupKeyFP(fp)
	if found && mgr.IsDeniedIdentity(meta.Identity) {
		return source.Subject{}, ErrDeniedIdentity
	}
	if found && (meta.IdentityType == "user" || meta.IdentityType == "poc") && source.ValidLedgerIdentity(meta.Identity) {
		return source.Subject{
			Scope:        source.ScopeIdentity,
			AuthMethod:   source.AuthMethodAPIKey,
			Identity:     meta.Identity,
			Account:      meta.Account,
			IdentityType: meta.IdentityType,
			KeyFP:        fp,
		}, nil
	}
	identity := ""
	if found && source.ValidLedgerIdentity(meta.Identity) {
		identity = meta.Identity
	}
	return source.Subject{
		Scope:        source.ScopeKeyFP,
		AuthMethod:   source.AuthMethodAPIKey,
		Identity:     identity,
		Account:      meta.Account,
		IdentityType: meta.IdentityType,
		KeyFP:        fp,
	}, nil
}

func extractIP(remoteAddr string) string {
	host, _, err := net.SplitHostPort(strings.TrimSpace(remoteAddr))
	if err == nil && host != "" {
		return host
	}
	return strings.TrimSpace(remoteAddr)
}

func (v *TykValidator) isRateLimited(ip string) bool {
	if ip == "" {
		return false
	}
	now := v.Now()
	cutoff := now.Add(-loginFailureWindow)
	v.mu.Lock()
	defer v.mu.Unlock()
	kept := v.failures[ip][:0]
	for _, ts := range v.failures[ip] {
		if ts.After(cutoff) {
			kept = append(kept, ts)
		}
	}
	if len(kept) == 0 {
		delete(v.failures, ip)
		return false
	}
	v.failures[ip] = kept
	return len(kept) >= maxLoginFailures
}

func (v *TykValidator) recordFailure(ip string) {
	if ip == "" {
		return
	}
	now := v.Now()
	cutoff := now.Add(-loginFailureWindow)
	v.mu.Lock()
	defer v.mu.Unlock()
	if _, exists := v.failures[ip]; !exists && len(v.failures) >= maxTrackedIPs {
		for k := range v.failures {
			delete(v.failures, k)
			break
		}
	}
	kept := v.failures[ip][:0]
	for _, ts := range v.failures[ip] {
		if ts.After(cutoff) {
			kept = append(kept, ts)
		}
	}
	v.failures[ip] = append(kept, now)
}
