// Package source reads per-subject usage summaries from the Aleph usage ledger
// (or a future Prometheus backend) without persisting per-user rows on disk or
// holding full-cluster per-user tables in memory.
package source

import (
	"bytes"
	"context"
	"crypto/sha256"
	"encoding/hex"
	"encoding/json"
	"fmt"
	"sort"
	"strings"
	"time"
)

// TimeLayout is the primary UTC timestamp format written by gateway/app/usage.py.
const TimeLayout = "2006-01-02T15:04:05Z"

// DayLayout is the UTC day key used for daily buckets (YYYY-MM-DD).
const DayLayout = "2006-01-02"

// DefaultDeniedIdentities lists shared platform service identities that must
// never be exposed as personal accounts in the portal.
const DefaultDeniedIdentities = "openwebui,service-webui,deepthought,task-worker,litellm,anonymous,unknown"

// Scope determines how usage records are matched to the signed-in principal.
type Scope string

const (
	// ScopeIdentity attributes non-service records (identity_type "user" and
	// historical "poc") across key rotations for a known user identity.
	ScopeIdentity Scope = "identity"
	// ScopeKeyFP attributes records strictly matching one key_fp object
	// ({"sha256_8","last4"}), isolating admin-minted type:service researcher
	// keys and brand-new unindexed keys to that single key.
	ScopeKeyFP Scope = "key_fp"
)

// AuthMethod records how the current session authenticated.
type AuthMethod string

const (
	AuthMethodAPIKey   AuthMethod = "api_key"
	AuthMethodMockOIDC AuthMethod = "mock_oidc"
	AuthMethodOIDC     AuthMethod = "oidc"
)

// KeyFP mirrors gateway/app/gateway.py:_key_fingerprint():
//
//	{"sha256_8": sha256(key).hexdigest()[-8:], "last4": key[-4:]}
type KeyFP struct {
	SHA256_8 string `json:"sha256_8"`
	Last4    string `json:"last4"`
}

// ComputeKeyFP computes the exact gateway fingerprint for a raw API key.
func ComputeKeyFP(rawKey string) KeyFP {
	if rawKey == "" {
		return KeyFP{}
	}
	sum := sha256.Sum256([]byte(rawKey))
	hexDigest := hex.EncodeToString(sum[:])
	last4 := rawKey
	if len(last4) > 4 {
		last4 = last4[len(last4)-4:]
	}
	return KeyFP{
		SHA256_8: hexDigest[len(hexDigest)-8:],
		Last4:    last4,
	}
}

// Valid reports whether the fingerprint has a valid 8-hex-character sha256 tail
// and a 1..4 byte printable last4 suffix.
func (fp KeyFP) Valid() bool {
	if len(fp.SHA256_8) != 8 || len(fp.Last4) == 0 || len(fp.Last4) > 4 {
		return false
	}
	for i := 0; i < len(fp.SHA256_8); i++ {
		c := fp.SHA256_8[i]
		if !((c >= '0' && c <= '9') || (c >= 'a' && c <= 'f')) {
			return false
		}
	}
	for i := 0; i < len(fp.Last4); i++ {
		c := fp.Last4[i]
		if c <= 0x20 || c >= 0x7f {
			return false
		}
	}
	return true
}

// Display formats a non-reversible label for Account/UI display.
func (fp KeyFP) Display() string {
	if !fp.Valid() {
		return "none"
	}
	return fmt.Sprintf("…%s (sha256:…%s)", fp.Last4, fp.SHA256_8)
}

// UnmarshalJSON decodes {"sha256_8":"...","last4":"..."} while tolerating null,
// empty strings, or legacy synthetic string forms so a non-standard key_fp
// never causes ParseRecord to drop a valid usage record.
func (fp *KeyFP) UnmarshalJSON(data []byte) error {
	trimmed := bytes.TrimSpace(data)
	if len(trimmed) == 0 || bytes.Equal(trimmed, []byte("null")) {
		*fp = KeyFP{}
		return nil
	}
	if trimmed[0] == '"' {
		*fp = KeyFP{}
		return nil
	}
	var obj struct {
		SHA256_8 string `json:"sha256_8"`
		Last4    string `json:"last4"`
	}
	if err := json.Unmarshal(trimmed, &obj); err != nil {
		*fp = KeyFP{}
		return nil
	}
	fp.SHA256_8 = strings.ToLower(obj.SHA256_8)
	fp.Last4 = obj.Last4
	return nil
}

// Subject identifies who a portal query is scoped to.
type Subject struct {
	Scope        Scope      `json:"scope"`
	AuthMethod   AuthMethod `json:"auth_method"`
	Identity     string     `json:"identity,omitempty"`
	Account      string     `json:"account,omitempty"`
	IdentityType string     `json:"identity_type,omitempty"`
	KeyFP        KeyFP      `json:"key_fp,omitempty"`
}

// Valid reports whether Subject satisfies its Scope's invariants.
func (s Subject) Valid() bool {
	switch s.Scope {
	case ScopeIdentity:
		return ValidLedgerIdentity(s.Identity)
	case ScopeKeyFP:
		if !s.KeyFP.Valid() {
			return false
		}
		if s.Identity != "" && !ValidLedgerIdentity(s.Identity) {
			return false
		}
		return true
	default:
		return false
	}
}

// DisplayName returns the safe principal name shown in the UI header.
func (s Subject) DisplayName() string {
	if s.Identity != "" {
		return s.Identity
	}
	if s.KeyFP.Valid() {
		return "key …" + s.KeyFP.Last4
	}
	return "unknown"
}

// CSVSlug returns a safe ASCII filename token for exported CSV files.
func (s Subject) CSVSlug() string {
	if s.Scope == ScopeIdentity && ValidLedgerIdentity(s.Identity) {
		return sanitizeFilenameSlug(s.Identity)
	}
	if s.KeyFP.Valid() {
		if s.Identity != "" && ValidLedgerIdentity(s.Identity) {
			return sanitizeFilenameSlug(s.Identity) + "-" + s.KeyFP.SHA256_8
		}
		return "key-" + s.KeyFP.SHA256_8
	}
	return "usage"
}

func sanitizeFilenameSlug(in string) string {
	var b strings.Builder
	b.Grow(len(in))
	for i := 0; i < len(in); i++ {
		c := in[i]
		if (c >= 'a' && c <= 'z') || (c >= 'A' && c <= 'Z') || (c >= '0' && c <= '9') || c == '-' || c == '_' || c == '.' {
			b.WriteByte(c)
		} else {
			b.WriteByte('_')
		}
	}
	return b.String()
}

// CacheKey uniquely identifies the principal's attribution scope in the
// short-lived in-memory query cache.
func (s Subject) CacheKey() string {
	switch s.Scope {
	case ScopeIdentity:
		return "id:" + s.Identity
	case ScopeKeyFP:
		return "fp:" + s.KeyFP.SHA256_8 + ":" + s.KeyFP.Last4
	default:
		return ""
	}
}

// KeyMeta holds the lightweight metadata observed for a KeyFP in the ledger.
type KeyMeta struct {
	Identity     string
	Account      string
	IdentityType string
	LastSeen     time.Time
}

// Backend answers per-subject usage queries from a telemetry store.
type Backend interface {
	Usage(ctx context.Context, subj Subject, from, to time.Time) (Report, error)
	LookupKeyFP(fp KeyFP) (KeyMeta, bool)
	EvictSubject(subj Subject)
	Ready() bool
	Mode() string
}

// Row is one UTC day, model, and endpoint bucket.
type Row struct {
	Day      string `json:"day"`
	Model    string `json:"model"`
	Endpoint string `json:"endpoint"`
	Agg
}

// Report is a subject's usage plus ledger coverage metadata.
type Report struct {
	Subject    Subject
	From       time.Time
	To         time.Time
	Rows       []Row
	Oldest     time.Time
	Incomplete []string
	// CompleteFrom is the timestamp from which all live gateway directories
	// hold complete unrotated history; zero means no file could have been lost.
	CompleteFrom time.Time
	Newest       time.Time
	RefreshedAt  time.Time
	ReadErrors   bool
}

// IsIncomplete reports whether day (YYYY-MM-DD) is in r.Incomplete.
func (r Report) IsIncomplete(day string) bool {
	i := sort.SearchStrings(r.Incomplete, day)
	return i < len(r.Incomplete) && r.Incomplete[i] == day
}

// DayOf returns the start of the UTC day t falls on.
func DayOf(t time.Time) time.Time {
	return t.UTC().Truncate(24 * time.Hour)
}

// FirstCompleteDay returns the first UTC day that starts at or after
// completeFrom, so every record of that day is on hand.
func FirstCompleteDay(completeFrom time.Time) time.Time {
	if completeFrom.IsZero() {
		return time.Time{}
	}
	day := DayOf(completeFrom)
	if day.Before(completeFrom) {
		day = day.AddDate(0, 0, 1)
	}
	return day
}

// DaysBefore lists the days from from to to, inclusive, that fall before first.
func DaysBefore(from, to, first time.Time) []string {
	var days []string
	if first.IsZero() {
		return days
	}
	for day := from.UTC(); !day.After(to.UTC()) && day.Before(first); day = day.AddDate(0, 0, 1) {
		days = append(days, day.Format(DayLayout))
	}
	return days
}

// SortRows orders rows by day, then model, then endpoint.
func SortRows(rows []Row) {
	sort.Slice(rows, func(i, j int) bool {
		if rows[i].Day != rows[j].Day {
			return rows[i].Day < rows[j].Day
		}
		if rows[i].Model != rows[j].Model {
			return rows[i].Model < rows[j].Model
		}
		return rows[i].Endpoint < rows[j].Endpoint
	})
}

// ValidLedgerIdentity validates a Tyk/ledger identity: 1..64 ASCII characters
// from [A-Za-z0-9._@-], starting with an ASCII letter or digit, preserving
// exact case (supporting both POSIX logins and admin-minted aliases).
func ValidLedgerIdentity(s string) bool {
	if len(s) == 0 || len(s) > 64 {
		return false
	}
	first := s[0]
	if !((first >= 'a' && first <= 'z') || (first >= 'A' && first <= 'Z') || (first >= '0' && first <= '9')) {
		return false
	}
	for i := 1; i < len(s); i++ {
		c := s[i]
		ok := (c >= 'a' && c <= 'z') ||
			(c >= 'A' && c <= 'Z') ||
			(c >= '0' && c <= '9') ||
			c == '.' || c == '_' || c == '@' || c == '-'
		if !ok {
			return false
		}
	}
	return true
}

// ValidPOSIXUsername validates strict Alliance/POSIX login claims for OIDC
// login mapping (^[a-z_][a-z0-9_-]{0,31}$).
func ValidPOSIXUsername(s string) bool {
	if len(s) == 0 || len(s) > 32 {
		return false
	}
	first := s[0]
	if !((first >= 'a' && first <= 'z') || first == '_') {
		return false
	}
	for i := 1; i < len(s); i++ {
		c := s[i]
		if !((c >= 'a' && c <= 'z') || (c >= '0' && c <= '9') || c == '_' || c == '-') {
			return false
		}
	}
	return true
}

// ParseDeniedIdentities parses a comma-separated denylist into a lowercase set.
func ParseDeniedIdentities(csv string) map[string]bool {
	out := make(map[string]bool)
	for _, raw := range strings.Split(csv, ",") {
		name := strings.ToLower(strings.TrimSpace(raw))
		if name != "" {
			out[name] = true
		}
	}
	return out
}
