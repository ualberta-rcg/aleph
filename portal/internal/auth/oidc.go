package auth

import (
	"strings"

	"github.com/ualberta-rcg/aleph/portal/internal/source"
)

// OIDCConfig holds Phase 2B institutional OIDC configuration. When IssuerURL
// and ClientID are unset, OIDC login and self-service Tyk key rotation remain
// cleanly disabled.
type OIDCConfig struct {
	IssuerURL string
	ClientID  string
}

// Enabled reports whether institutional OIDC is configured.
func (c OIDCConfig) Enabled() bool {
	return strings.TrimSpace(c.IssuerURL) != "" && strings.TrimSpace(c.ClientID) != ""
}

// CanRotateKey reports whether subj is permitted to rotate personal Tyk keys.
// Key rotation is strictly gated on real institutional OIDC authentication so
// neither a leaked API key nor a local Mock OIDC session can mint/revoke keys.
func (m *Manager) CanRotateKey(subj source.Subject) bool {
	return m.oidc.Enabled() &&
		subj.AuthMethod == source.AuthMethodOIDC &&
		subj.Scope == source.ScopeIdentity &&
		source.ValidPOSIXUsername(subj.Identity)
}
