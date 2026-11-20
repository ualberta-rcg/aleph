package auth

import (
	"errors"
	"strings"

	"github.com/ualberta-rcg/aleph/portal/internal/source"
)

var (
	ErrMockOIDCDisabled = errors.New("mock OIDC login is disabled")
	ErrInvalidIdentity  = errors.New("enter a valid Aleph identity (1–64 ASCII letters, digits, ., _, @, -)")
)

// AuthenticateMockOIDC builds a ScopeIdentity session subject for local .43
// testing when MOCK_OIDC_ENABLED=true and ALLOW_MOCK_OIDC=yes-local-testing-only.
func (m *Manager) AuthenticateMockOIDC(rawUsername string) (source.Subject, error) {
	if !m.mockOIDCEnabled {
		return source.Subject{}, ErrMockOIDCDisabled
	}
	identity := strings.TrimSpace(rawUsername)
	if !source.ValidLedgerIdentity(identity) {
		return source.Subject{}, ErrInvalidIdentity
	}
	if m.IsDeniedIdentity(identity) {
		return source.Subject{}, ErrDeniedIdentity
	}
	return source.Subject{
		Scope:        source.ScopeIdentity,
		AuthMethod:   source.AuthMethodMockOIDC,
		Identity:     identity,
		IdentityType: "user",
	}, nil
}
