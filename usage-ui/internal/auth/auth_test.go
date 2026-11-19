package auth

import (
	"errors"
	"net/http"
	"net/http/httptest"
	"testing"
)

// realmHeader trusts 10.42.0.0/16 and 127.0.0.1 and accepts the realm
// ualberta.ca.
func realmHeader(t *testing.T) Header {
	t.Helper()
	trusted, err := ParsePrefixes("10.42.0.0/16, 127.0.0.1")
	if err != nil {
		t.Fatal(err)
	}
	return Header{Name: "X-Remote-User", Realm: "ualberta.ca", TrustedFrom: trusted}
}

func requestFrom(remote string, values ...string) *http.Request {
	r := httptest.NewRequest("GET", "/", nil)
	r.RemoteAddr = remote
	for _, value := range values {
		r.Header.Add("X-Remote-User", value)
	}
	return r
}

func TestHeaderAcceptsAUsernameFromATrustedProxy(t *testing.T) {
	for _, tc := range []struct {
		name, remote, value, want string
	}{
		{"a bare username", "10.42.3.4:5555", "alice", "alice"},
		{"the accepted realm in any case, with spaces and capitals trimmed", "127.0.0.1:1", " Alice@UAlberta.ca ", "alice"},
	} {
		t.Run(tc.name, func(t *testing.T) {
			got, err := realmHeader(t).User(requestFrom(tc.remote, tc.value))
			if err != nil || got != tc.want {
				t.Errorf("User = %q, %v; want %q, nil", got, err, tc.want)
			}
		})
	}
}

func TestHeaderRefusesAnUnacceptableIdentity(t *testing.T) {
	for _, tc := range []struct {
		name, remote string
		values       []string
	}{
		{"another realm", "10.42.3.4:1", []string{"alice@other.example"}},
		{"a realm that only ends like the accepted one", "10.42.3.4:1", []string{"alice@evil-ualberta.ca"}},
		{"two realms", "10.42.3.4:1", []string{"alice@ualberta.ca@ualberta.ca"}},
		{"a realm with no username", "10.42.3.4:1", []string{"@ualberta.ca"}},
		{"a Kelvin sign that lowercases to k", "10.42.3.4:1", []string{"Kate"}},
		{"a non-ASCII letter", "10.42.3.4:1", []string{"alïce"}},
		{"no header", "10.42.3.4:1", nil},
		{"the header twice", "10.42.3.4:1", []string{"alice", "bob"}},
		{"characters a username cannot have", "10.42.3.4:1", []string{"alice;rm"}},
		{"a peer that is not a trusted proxy", "192.168.1.5:1", []string{"alice"}},
	} {
		t.Run(tc.name, func(t *testing.T) {
			got, err := realmHeader(t).User(requestFrom(tc.remote, tc.values...))
			if got != "" || !errors.Is(err, ErrNoUser) {
				t.Errorf("User = %q, %v; want no user and ErrNoUser", got, err)
			}
		})
	}
}

// With no realm configured, only bare usernames are accepted.
func TestHeaderWithoutARealmAcceptsOnlyBareUsernames(t *testing.T) {
	header := Header{Name: "X-Remote-User", AnyPeer: true}
	for value, want := range map[string]string{"alice": "alice", "Alice": "alice", "alice@ualberta.ca": "", "alice@": ""} {
		got, err := header.User(requestFrom("192.0.2.1:1", value))
		if want == "" && (got != "" || !errors.Is(err, ErrNoUser)) {
			t.Errorf("%q: got %q, %v; want no user and ErrNoUser", value, got, err)
		}
		if want != "" && (err != nil || got != want) {
			t.Errorf("%q: got %q, %v; want %q", value, got, err, want)
		}
	}
}

// An untrusted peer that sends the identity header gets ErrUntrustedPeer, so
// the web layer can log it. Without the header it is an ordinary
// unauthenticated request. Both are ErrNoUser.
func TestUntrustedPeerSendingTheHeaderIsDistinguishable(t *testing.T) {
	trusted, err := ParsePrefixes("10.42.0.7")
	if err != nil {
		t.Fatal(err)
	}
	header := Header{Name: "X-Remote-User", TrustedFrom: trusted}
	if _, err := header.User(requestFrom("192.168.1.5:1")); !errors.Is(err, ErrNoUser) || errors.Is(err, ErrUntrustedPeer) {
		t.Errorf("no header: want plain ErrNoUser, got %v", err)
	}
	if _, err := header.User(requestFrom("192.168.1.5:1", "alice")); !errors.Is(err, ErrUntrustedPeer) || !errors.Is(err, ErrNoUser) {
		t.Errorf("header from untrusted peer: want ErrUntrustedPeer wrapping ErrNoUser, got %v", err)
	}
}

func TestNewHeaderRefusesAConfigurationThatTrustsAnyClient(t *testing.T) {
	for _, tc := range []struct {
		name string
		cfg  HeaderConfig
	}{
		{"no peer rule at all", HeaderConfig{Name: "X-Remote-User"}},
		{"an any-peer value other than the acknowledgement", HeaderConfig{Name: "X-Remote-User", AllowAnyPeer: "true"}},
		{"the IPv4 catch-all range", HeaderConfig{Name: "X-Remote-User", TrustedProxies: "0.0.0.0/0"}},
		{"the IPv6 catch-all range", HeaderConfig{Name: "X-Remote-User", TrustedProxies: "::/0"}},
		{"a proxy address that does not parse", HeaderConfig{Name: "X-Remote-User", TrustedProxies: "not-an-ip"}},
		{"an empty header name", HeaderConfig{Name: " ", TrustedProxies: "10.42.0.7"}},
		{"a realm written with @", HeaderConfig{Name: "X-Remote-User", TrustedProxies: "10.42.0.7", Realm: "@ualberta.ca"}},
	} {
		t.Run(tc.name, func(t *testing.T) {
			if _, err := NewHeader(tc.cfg); err == nil {
				t.Error("NewHeader accepted the configuration")
			}
		})
	}
}

func TestNewHeaderAcceptsAProxyListOrAnAcknowledgedNetworkPolicy(t *testing.T) {
	for _, tc := range []struct {
		name string
		cfg  HeaderConfig
	}{
		{"trusted proxies", HeaderConfig{Name: "X-Remote-User", TrustedProxies: "10.42.0.7"}},
		{"any peer, acknowledged", HeaderConfig{Name: "X-Remote-User", AllowAnyPeer: AnyPeerAck}},
		{"trusted proxies and a realm", HeaderConfig{Name: "X-Remote-User", TrustedProxies: "10.42.0.7", Realm: "ualberta.ca"}},
	} {
		t.Run(tc.name, func(t *testing.T) {
			if _, err := NewHeader(tc.cfg); err != nil {
				t.Errorf("NewHeader refused it: %v", err)
			}
		})
	}
}

// A Header built without NewHeader and with no peer rule trusts no one: the
// request-time check fails closed too.
func TestHeaderWithoutAPeerRuleTrustsNoPeer(t *testing.T) {
	got, err := (Header{Name: "X-Remote-User"}).User(requestFrom("10.42.3.4:1", "alice"))
	if got != "" || !errors.Is(err, ErrNoUser) {
		t.Errorf("User = %q, %v; want no user and ErrNoUser", got, err)
	}
}

func TestAnyPeerModeAcceptsTheHeaderFromAnyPeer(t *testing.T) {
	anyPeer, err := NewHeader(HeaderConfig{Name: "X-Remote-User", AllowAnyPeer: AnyPeerAck})
	if err != nil {
		t.Fatal(err)
	}
	if got, err := anyPeer.User(requestFrom("10.42.3.4:1", "alice")); err != nil || got != "alice" {
		t.Errorf("User = %q, %v; want alice, nil", got, err)
	}
}

func TestDevModeRefusesAnInvalidUsername(t *testing.T) {
	if got, err := (Dev{Username: "../etc"}).User(nil); got != "" || !errors.Is(err, ErrNoUser) {
		t.Errorf("User = %q, %v; want no user and ErrNoUser", got, err)
	}
}
