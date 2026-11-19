// Package auth decides who the current user is.
//
// The service does not implement SAML itself. In production a SAML service
// provider in front of it (for example mod_auth_mellon, Shibboleth SP, or an
// SSO proxy) authenticates the user and passes the LDAP username in a header.
// That keeps the protocol out of the app and switching SAML for OIDC doesn't
// require any code change, just a change to the proxy.
package auth

import (
	"errors"
	"fmt"
	"net"
	"net/http"
	"net/netip"
	"regexp"
	"strings"
	"unicode/utf8"
)

// ErrNoUser means the request carries no acceptable identity. Every error
// from an Authenticator wraps it.
var ErrNoUser = errors.New("not authenticated")

// ErrUntrustedPeer means a peer that is not a trusted proxy sent an identity
// header. It wraps ErrNoUser. It is worth logging: either the proxy's
// addresses are configured wrongly, or something other than the proxy can
// reach the app and is trying to choose an identity.
var ErrUntrustedPeer = fmt.Errorf("%w: identity header from untrusted peer", ErrNoUser)

// usernameRE matches the identities the Vulcan PAM hook gives Tyk keys
// (ww-overlays/.../tyk-pam-cmd): ^[a-z_][a-z0-9._-]{1,31}$.
var usernameRE = regexp.MustCompile(`^[a-z_][a-z0-9._-]{1,31}$`)

// ValidUsername reports whether name is a username the ledger can contain.
func ValidUsername(name string) bool { return usernameRE.MatchString(name) }

// Authenticator returns the LDAP username for a request.
type Authenticator interface {
	User(r *http.Request) (string, error)
	Mode() string
}

// AnyPeerAck is the only accepted value of AUTH_ALLOW_ANY_PEER. Setting it
// states that something outside the app, normally a NetworkPolicy, admits
// nothing but the SAML proxy, so the app need not check the peer address.
const AnyPeerAck = "yes-networkpolicy-admits-only-the-proxy"

// Header trusts a username header set by an authenticating proxy.
//
// It fails closed: a request is accepted only from a peer in TrustedFrom, or
// from any peer when AnyPeer is set. Build it with NewHeader, which enforces
// that one of the two is configured.
type Header struct {
	Name string // e.g. X-Remote-User
	// Realm is the one realm accepted in "user@realm" values, compared
	// without regard to case, and removed. Empty accepts bare usernames only.
	// See normalize.
	Realm       string
	TrustedFrom []netip.Prefix // peers allowed to assert identity
	AnyPeer     bool           // accept any peer; access is restricted elsewhere
}

// HeaderConfig is the raw configuration for header authentication.
type HeaderConfig struct {
	Name           string // header name
	Realm          string // AUTH_REALM: the one accepted realm, or empty
	TrustedProxies string // comma-separated CIDRs or addresses
	AllowAnyPeer   string // must be empty or AnyPeerAck
}

// NewHeader validates cfg and returns a Header. It refuses a configuration in
// which any client that can reach the pod could choose its own identity.
func NewHeader(cfg HeaderConfig) (Header, error) {
	if strings.TrimSpace(cfg.Name) == "" {
		return Header{}, errors.New("AUTH_HEADER must not be empty")
	}
	realm := strings.TrimSpace(cfg.Realm)
	if realm != "" && !realmRE.MatchString(realm) {
		return Header{}, fmt.Errorf("AUTH_REALM must be a domain such as example.org (without \"@\"), got %q", cfg.Realm)
	}
	trusted, err := ParsePrefixes(cfg.TrustedProxies)
	if err != nil {
		return Header{}, fmt.Errorf("AUTH_TRUSTED_PROXIES: %w", err)
	}
	var anyPeer bool
	switch cfg.AllowAnyPeer {
	case "":
	case AnyPeerAck:
		anyPeer = true
	default:
		return Header{}, fmt.Errorf("AUTH_ALLOW_ANY_PEER must be empty or %q", AnyPeerAck)
	}
	for _, prefix := range trusted {
		if prefix.Bits() == 0 && !anyPeer {
			return Header{}, fmt.Errorf("AUTH_TRUSTED_PROXIES contains %s, which trusts every peer; list the proxy's addresses, or set AUTH_ALLOW_ANY_PEER=%s if a NetworkPolicy admits only the proxy", prefix, AnyPeerAck)
		}
	}
	if len(trusted) == 0 && !anyPeer {
		return Header{}, fmt.Errorf("header auth needs AUTH_TRUSTED_PROXIES (the SAML proxy's addresses), or AUTH_ALLOW_ANY_PEER=%s when a NetworkPolicy admits only the proxy; without one, any client that reaches the pod can choose its identity", AnyPeerAck)
	}
	return Header{Name: cfg.Name, Realm: realm, TrustedFrom: trusted, AnyPeer: anyPeer}, nil
}

func (h Header) Mode() string {
	if h.AnyPeer {
		return "header (any peer; NetworkPolicy must restrict access)"
	}
	return "header (trusted proxies only)"
}

// User returns the username the proxy asserted. The error is ErrUntrustedPeer
// when a peer outside TrustedFrom sent the identity header, and otherwise
// wraps ErrNoUser.
func (h Header) User(r *http.Request) (string, error) {
	values := r.Header.Values(h.Name)
	if !h.AnyPeer && !h.peerTrusted(r.RemoteAddr) {
		if len(values) > 0 {
			return "", ErrUntrustedPeer
		}
		return "", ErrNoUser
	}
	if len(values) != 1 {
		return "", ErrNoUser
	}
	return normalize(values[0], h.Realm)
}

func (h Header) peerTrusted(remoteAddr string) bool {
	host, _, err := net.SplitHostPort(remoteAddr)
	if err != nil {
		host = remoteAddr
	}
	ip, err := netip.ParseAddr(host)
	if err != nil {
		return false
	}
	ip = ip.Unmap()
	for _, prefix := range h.TrustedFrom {
		if prefix.Contains(ip) {
			return true
		}
	}
	return false
}

// Dev signs every request in as one fixed user. Local development only.
type Dev struct{ Username string }

func (d Dev) Mode() string { return "dev" }

func (d Dev) User(*http.Request) (string, error) { return normalize(d.Username, "") }

// realmRE matches an AUTH_REALM value: a DNS-style domain, ASCII only.
var realmRE = regexp.MustCompile(`^[A-Za-z0-9]([A-Za-z0-9-]*[A-Za-z0-9])?(\.[A-Za-z0-9]([A-Za-z0-9-]*[A-Za-z0-9])?)*$`)

// normalize turns a header value into a ledger username.
//
// The value must be ASCII. Unicode case mapping would let a lookalike reach a
// real account: strings.ToLower turns U+212A KELVIN SIGN into ASCII "k", so
// "\u212Aate" would become "kate".
//
// A realm suffix is accepted only when it is exactly realm (ignoring case),
// and only that suffix is removed. Removing any realm would let
// alice@other-institution sign in as the local alice. With realm empty, any
// value containing "@" is refused. A bare username is accepted either way.
func normalize(value, realm string) (string, error) {
	value = strings.TrimSpace(value)
	for index := 0; index < len(value); index++ {
		if value[index] >= utf8.RuneSelf {
			return "", fmt.Errorf("%w: non-ASCII username", ErrNoUser)
		}
	}
	username := strings.ToLower(value)
	if local, valueRealm, hasRealm := strings.Cut(username, "@"); hasRealm {
		if realm == "" || !strings.EqualFold(valueRealm, realm) {
			return "", fmt.Errorf("%w: username realm not accepted", ErrNoUser)
		}
		username = local
	}
	if !ValidUsername(username) {
		return "", fmt.Errorf("%w: invalid username", ErrNoUser)
	}
	return username, nil
}

// ParsePrefixes parses a comma-separated list of CIDRs or bare addresses.
func ParsePrefixes(list string) ([]netip.Prefix, error) {
	var out []netip.Prefix
	for _, part := range strings.Split(list, ",") {
		part = strings.TrimSpace(part)
		if part == "" {
			continue
		}
		if !strings.Contains(part, "/") {
			addr, err := netip.ParseAddr(part)
			if err != nil {
				return nil, err
			}
			out = append(out, netip.PrefixFrom(addr, addr.BitLen()))
			continue
		}
		prefix, err := netip.ParsePrefix(part)
		if err != nil {
			return nil, err
		}
		out = append(out, prefix.Masked())
	}
	return out, nil
}
