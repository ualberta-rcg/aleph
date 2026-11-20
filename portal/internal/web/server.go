// Package web serves the Aleph user portal. Pages are rendered on the server
// with progressive-enhancement JS only, strict Content-Security-Policy, and
// per-subject isolation enforced by signed session cookies.
package web

import (
	"embed"
	"encoding/csv"
	"errors"
	"fmt"
	"html/template"
	"io/fs"
	"log"
	"net"
	"net/http"
	"net/netip"
	"net/url"
	"strconv"
	"strings"
	"time"

	"github.com/ualberta-rcg/aleph/portal/internal/auth"
	"github.com/ualberta-rcg/aleph/portal/internal/catalog"
	"github.com/ualberta-rcg/aleph/portal/internal/source"
)

//go:embed templates/*.html
var templateFS embed.FS

//go:embed static/*
var staticFS embed.FS

const (
	defaultDays  = 14
	maxDays      = 366
	maxLoginBody = 8192
)

// Config configures the portal HTTP server.
type Config struct {
	Source         source.Backend
	Auth           *auth.Manager
	Tyk            *auth.TykValidator
	Catalog        *catalog.Client
	SiteName       string
	APIBaseURL     string
	WebUIURL       string
	PrivateNetOnly bool
	Now            func() time.Time
}

// Server holds the portal HTTP handlers and templates.
type Server struct {
	src            source.Backend
	auth           *auth.Manager
	tyk            *auth.TykValidator
	catalog        *catalog.Client
	tmpl           *template.Template
	static         assets
	originHost     string
	privateNetOnly bool
	Now            func() time.Time
	SiteName       string
	APIBaseURL     string
	WebUIURL       string
}

// New constructs a Server and parses all embedded assets and HTML templates.
func New(cfg Config) (*Server, error) {
	if cfg.Source == nil {
		return nil, errors.New("web: Source backend is required")
	}
	if cfg.Auth == nil {
		return nil, errors.New("web: Auth manager is required")
	}
	staticFiles, err := fs.Sub(staticFS, "static")
	if err != nil {
		return nil, err
	}
	static, err := loadAssets(staticFiles)
	if err != nil {
		return nil, err
	}
	tmpl, err := template.New("").Funcs(template.FuncMap{
		"asset":     static.URL,
		"num":       formatInt,
		"num64":     func(n int) string { return formatInt(int64(n)) },
		"gpuh":      formatGPUHours,
		"speed":     formatSpeed,
		"count":     countOf,
		"ts":        formatTS,
		"longdate":  formatLongDate,
		"share":     share,
		"nearLimit": nearLimitPercent,
	}).ParseFS(templateFS, "templates/*.html")
	if err != nil {
		return nil, err
	}
	siteName := strings.TrimSpace(cfg.SiteName)
	if siteName == "" {
		siteName = "Aleph"
	}
	apiBase := strings.TrimRight(strings.TrimSpace(cfg.APIBaseURL), "/")
	if apiBase == "" {
		apiBase = "https://inference.vulcan.alliancecan.ca"
	}
	webUI := strings.TrimRight(strings.TrimSpace(cfg.WebUIURL), "/")
	if webUI == "" {
		webUI = "https://llm.vulcan.alliancecan.ca"
	}
	nowFn := cfg.Now
	if nowFn == nil {
		nowFn = time.Now
	}
	var originHost string
	if u, err := url.Parse(cfg.Auth.PublicOrigin()); err == nil {
		originHost = u.Host
	}
	return &Server{
		src:            cfg.Source,
		auth:           cfg.Auth,
		tyk:            cfg.Tyk,
		catalog:        cfg.Catalog,
		tmpl:           tmpl,
		static:         static,
		originHost:     originHost,
		privateNetOnly: cfg.PrivateNetOnly,
		Now:            nowFn,
		SiteName:       siteName,
		APIBaseURL:     apiBase,
		WebUIURL:       webUI,
	}, nil
}

// Handler returns the routed, security-header-hardened HTTP handler.
func (s *Server) Handler() http.Handler {
	mux := http.NewServeMux()
	mux.Handle("GET /assets/{hash}/{name}", s.static)
	mux.HandleFunc("GET /favicon.ico", func(w http.ResponseWriter, _ *http.Request) {
		w.WriteHeader(http.StatusNoContent)
	})
	mux.HandleFunc("GET /healthz", func(w http.ResponseWriter, _ *http.Request) {
		w.WriteHeader(http.StatusOK)
		_, _ = w.Write([]byte("ok\n"))
	})
	mux.HandleFunc("GET /readyz", func(w http.ResponseWriter, _ *http.Request) {
		if !s.src.Ready() {
			http.Error(w, "backend not ready", http.StatusServiceUnavailable)
			return
		}
		w.WriteHeader(http.StatusOK)
		_, _ = w.Write([]byte("ready\n"))
	})

	mux.HandleFunc("GET /login", s.loginPage)
	mux.HandleFunc("POST /login", s.loginAPIKey)
	mux.HandleFunc("POST /login/mock-oidc", s.loginMockOIDC)
	mux.HandleFunc("POST /logout", s.logout)

	mux.HandleFunc("GET /{$}", s.withSubject(s.overviewPage))
	mux.HandleFunc("GET /models", s.withSubject(s.modelsPage))
	mux.HandleFunc("GET /errors", s.withSubject(s.errorsPage))
	mux.HandleFunc("GET /report", s.withSubject(s.reportPage))
	mux.HandleFunc("GET /connect", s.withSubject(s.connectPage))
	mux.HandleFunc("GET /keys", s.withSubject(s.keysPage))
	mux.HandleFunc("GET /usage.csv", s.csvHandler)

	h := secureHeaders(s.auth.SecureCookies(), mux)
	if s.privateNetOnly {
		h = privateNetGuard(s.originHost, h)
	}
	return h
}

func privateNetGuard(expectedHost string, next http.Handler) http.Handler {
	return http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		if !isPrivateOrLoopbackAddr(r.RemoteAddr) {
			http.Error(w, "forbidden: internal network access only", http.StatusForbidden)
			return
		}
		if r.URL.Path != "/healthz" && r.URL.Path != "/readyz" && expectedHost != "" && !strings.EqualFold(r.Host, expectedHost) {
			http.Error(w, "forbidden: unexpected host", http.StatusForbidden)
			return
		}
		next.ServeHTTP(w, r)
	})
}

func isPrivateOrLoopbackAddr(remoteAddr string) bool {
	host := strings.TrimSpace(remoteAddr)
	if h, _, err := net.SplitHostPort(host); err == nil {
		host = h
	}
	if i := strings.IndexByte(host, '%'); i >= 0 {
		host = host[:i]
	}
	addr, err := netip.ParseAddr(host)
	if err != nil {
		return false
	}
	addr = addr.Unmap()
	return addr.IsLoopback() || addr.IsPrivate()
}

func sanitizeLogToken(raw string) string {
	raw = strings.TrimSpace(raw)
	if len(raw) > 80 {
		raw = raw[:80]
	}
	var b strings.Builder
	b.Grow(len(raw))
	for i := 0; i < len(raw); i++ {
		c := raw[i]
		if c >= 0x21 && c <= 0x7e {
			b.WriteByte(c)
		} else {
			b.WriteByte('_')
		}
	}
	return b.String()
}

func secureHeaders(hsts bool, next http.Handler) http.Handler {
	return http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		headers := w.Header()
		headers.Set("Content-Security-Policy", "default-src 'none'; script-src 'self'; style-src 'self'; img-src 'self'; form-action 'self'; frame-ancestors 'none'; base-uri 'none'")
		headers.Set("X-Content-Type-Options", "nosniff")
		headers.Set("Referrer-Policy", "same-origin")
		headers.Set("X-Frame-Options", "DENY")
		if hsts {
			headers.Set("Strict-Transport-Security", "max-age=31536000; includeSubDomains")
		}
		if !strings.HasPrefix(r.URL.Path, "/assets/") {
			headers.Set("Cache-Control", "no-store")
		}
		next.ServeHTTP(w, r)
	})
}

type subjectHandler func(w http.ResponseWriter, r *http.Request, subj source.Subject, csrfToken string)

func (s *Server) withSubject(next subjectHandler) http.HandlerFunc {
	return func(w http.ResponseWriter, r *http.Request) {
		subj, err := s.auth.CurrentSubject(r)
		if err != nil {
			target := "/login"
			if nextPath := safeNextPath(r.URL.RequestURI()); nextPath != "/" {
				target += "?next=" + url.QueryEscape(nextPath)
			}
			http.Redirect(w, r, target, http.StatusSeeOther)
			return
		}
		csrfToken, err := s.auth.EnsureCSRF(w, r)
		if err != nil {
			log.Printf("csrf token generation error: %v", err)
			s.renderError(w, http.StatusInternalServerError, subj, "", "Session error", "Could not initialize CSRF protection. Refresh and try again.")
			return
		}
		next(w, r, subj, csrfToken)
	}
}

func safeNextPath(raw string) string {
	raw = strings.TrimSpace(raw)
	if raw == "" || !strings.HasPrefix(raw, "/") || strings.HasPrefix(raw, "//") {
		return "/"
	}
	if strings.ContainsAny(raw, "\\\r\n") {
		return "/"
	}
	if strings.HasPrefix(raw, "/login") || strings.HasPrefix(raw, "/logout") {
		return "/"
	}
	return raw
}

func (s *Server) loginPage(w http.ResponseWriter, r *http.Request) {
	nextPath := safeNextPath(r.URL.Query().Get("next"))
	if subj, err := s.auth.CurrentSubject(r); err == nil && subj.Valid() {
		http.Redirect(w, r, nextPath, http.StatusSeeOther)
		return
	}
	s.renderLogin(w, r, http.StatusOK, nextPath, "")
}

func (s *Server) renderLogin(w http.ResponseWriter, r *http.Request, status int, nextPath, loginErr string) {
	csrfToken, err := s.auth.EnsureCSRF(w, r)
	if err != nil {
		http.Error(w, "Session initialization failed.", http.StatusInternalServerError)
		return
	}
	page := view{
		Site:            s.SiteName,
		Title:           "Sign in",
		PageClass:       "page-login",
		CSRFToken:       csrfToken,
		Next:            safeNextPath(nextPath),
		LoginError:      loginErr,
		MockOIDCEnabled: s.auth.MockOIDCEnabled(),
	}
	w.Header().Set("Content-Type", "text/html; charset=utf-8")
	w.WriteHeader(status)
	if err := s.tmpl.ExecuteTemplate(w, "login.html", page); err != nil {
		log.Printf("render login.html: %v", err)
	}
}

func (s *Server) loginAPIKey(w http.ResponseWriter, r *http.Request) {
	r.Body = http.MaxBytesReader(w, r.Body, maxLoginBody)
	if err := r.ParseForm(); err != nil {
		s.renderLogin(w, r, http.StatusBadRequest, "/", "Login request was malformed or too large.")
		return
	}
	nextPath := safeNextPath(r.PostFormValue("next"))
	if err := s.auth.VerifyCSRF(r, r.PostFormValue("csrf_token")); err != nil {
		log.Printf("auth csrf rejected: path=%s host=%s origin=%s sfs=%s err=%v", sanitizeLogToken(r.URL.Path), sanitizeLogToken(r.Host), sanitizeLogToken(r.Header.Get("Origin")), sanitizeLogToken(r.Header.Get("Sec-Fetch-Site")), err)
		s.renderLogin(w, r, http.StatusForbidden, nextPath, "Your login form expired or failed origin verification. Please submit again.")
		return
	}
	if s.tyk == nil {
		s.renderLogin(w, r, http.StatusServiceUnavailable, nextPath, "API-key login is not configured on this portal instance.")
		return
	}
	subj, err := s.tyk.Authenticate(r.Context(), r.RemoteAddr, r.PostFormValue("api_key"), s.src, s.auth)
	if err != nil {
		status := http.StatusUnauthorized
		reason := "key_rejected"
		msg := "That API key was not accepted. Paste your personal TYK_KEY from ~/.aleph_tyk.env and try again."
		switch {
		case errors.Is(err, auth.ErrInvalidKeyFormat):
			status = http.StatusBadRequest
			reason = "invalid_key_format"
			msg = "Could not find a valid API key in that input. Paste your TYK_KEY value or the output of cat ~/.aleph_tyk.env."
		case errors.Is(err, auth.ErrKeyRateLimited):
			status = http.StatusTooManyRequests
			reason = "rate_limited"
			msg = "Too many failed sign-in attempts from your address. Wait a minute and try again."
		case errors.Is(err, auth.ErrDeniedIdentity):
			status = http.StatusForbidden
			reason = "denied_identity"
			msg = "Shared platform or service keys cannot sign in to the personal usage portal."
		case errors.Is(err, auth.ErrTykUnavailable):
			status = http.StatusBadGateway
			reason = "tyk_unavailable"
			msg = "Could not reach the Tyk gateway to verify your key right now. Try again shortly."
		}
		log.Printf("auth api-key login failed: status=%d reason=%s", status, reason)
		s.renderLogin(w, r, status, nextPath, msg)
		return
	}
	if err := s.auth.IssueSession(w, subj); err != nil {
		log.Printf("issue session failed: %v", err)
		s.renderLogin(w, r, http.StatusInternalServerError, nextPath, "Could not start your session.")
		return
	}
	http.Redirect(w, r, nextPath, http.StatusSeeOther)
}

func (s *Server) loginMockOIDC(w http.ResponseWriter, r *http.Request) {
	if !s.auth.MockOIDCEnabled() {
		http.NotFound(w, r)
		return
	}
	r.Body = http.MaxBytesReader(w, r.Body, maxLoginBody)
	if err := r.ParseForm(); err != nil {
		s.renderLogin(w, r, http.StatusBadRequest, "/", "Login request was malformed or too large.")
		return
	}
	nextPath := safeNextPath(r.PostFormValue("next"))
	if err := s.auth.VerifyCSRF(r, r.PostFormValue("csrf_token")); err != nil {
		log.Printf("auth csrf rejected: path=%s host=%s origin=%s sfs=%s err=%v", sanitizeLogToken(r.URL.Path), sanitizeLogToken(r.Host), sanitizeLogToken(r.Header.Get("Origin")), sanitizeLogToken(r.Header.Get("Sec-Fetch-Site")), err)
		s.renderLogin(w, r, http.StatusForbidden, nextPath, "Your login form expired or failed origin verification. Please submit again.")
		return
	}
	subj, err := s.auth.AuthenticateMockOIDC(r.PostFormValue("username"))
	if err != nil {
		status := http.StatusBadRequest
		msg := "Enter a valid ledger identity (1–64 ASCII letters, digits, '.', '_', '@', or '-')."
		if errors.Is(err, auth.ErrDeniedIdentity) {
			status = http.StatusForbidden
			msg = "Shared platform identities (such as openwebui or task-worker) are denied."
		}
		s.renderLogin(w, r, status, nextPath, msg)
		return
	}
	if err := s.auth.IssueSession(w, subj); err != nil {
		log.Printf("issue mock-oidc session failed: %v", err)
		s.renderLogin(w, r, http.StatusInternalServerError, nextPath, "Could not start your session.")
		return
	}
	http.Redirect(w, r, nextPath, http.StatusSeeOther)
}

func (s *Server) logout(w http.ResponseWriter, r *http.Request) {
	r.Body = http.MaxBytesReader(w, r.Body, maxLoginBody)
	_ = r.ParseForm()
	if err := s.auth.VerifyCSRF(r, r.PostFormValue("csrf_token")); err != nil {
		log.Printf("auth csrf rejected: path=%s host=%s origin=%s sfs=%s err=%v", sanitizeLogToken(r.URL.Path), sanitizeLogToken(r.Host), sanitizeLogToken(r.Header.Get("Origin")), sanitizeLogToken(r.Header.Get("Sec-Fetch-Site")), err)
		http.Error(w, "Invalid logout request.", http.StatusForbidden)
		return
	}
	if subj, err := s.auth.CurrentSubject(r); err == nil {
		s.src.EvictSubject(subj)
	}
	s.auth.ClearSession(w)
	http.Redirect(w, r, "/login", http.StatusSeeOther)
}

func daysInRange(from, to time.Time) int {
	return int(to.Sub(from)/(24*time.Hour)) + 1
}

func (s *Server) dateRange(r *http.Request) (from, to time.Time) {
	today := source.DayOf(s.Now())
	parse := func(key string) (time.Time, bool) {
		day, err := time.Parse(source.DayLayout, r.URL.Query().Get(key))
		return day, err == nil
	}
	to, ok := parse("to")
	if !ok || to.After(today) {
		to = today
	}
	from, ok = parse("from")
	if !ok || from.After(to) {
		from = to.AddDate(0, 0, -(defaultDays - 1))
	}
	if daysInRange(from, to) > maxDays {
		from = to.AddDate(0, 0, -(maxDays - 1))
	}
	return from, to
}

// csvHandler serves daily model/endpoint rows for either an active browser
// session or a CLI caller supplying Authorization: Bearer <TYK_KEY>.
func (s *Server) csvHandler(w http.ResponseWriter, r *http.Request) {
	subj, err := s.auth.CurrentSubject(r)
	if err != nil {
		bearer := strings.TrimSpace(r.Header.Get("Authorization"))
		if bearer == "" || s.tyk == nil {
			http.Error(w, "Not signed in. Provide a valid session cookie or Authorization: Bearer <TYK_KEY>.", http.StatusUnauthorized)
			return
		}
		subj, err = s.tyk.Authenticate(r.Context(), r.RemoteAddr, bearer, s.src, s.auth)
		if err != nil {
			status := http.StatusUnauthorized
			if errors.Is(err, auth.ErrKeyRateLimited) {
				status = http.StatusTooManyRequests
			} else if errors.Is(err, auth.ErrDeniedIdentity) {
				status = http.StatusForbidden
			}
			http.Error(w, "API key authentication failed.", status)
			return
		}
	}

	from, to := s.dateRange(r)
	report, err := s.src.Usage(r.Context(), subj, from, to)
	if err != nil {
		log.Printf("csv usage query failed: %v", err)
		http.Error(w, "Usage data is unavailable right now.", http.StatusServiceUnavailable)
		return
	}
	filename := fmt.Sprintf("aleph-usage-%s-%s-to-%s.csv", subj.CSVSlug(), from.Format(source.DayLayout), to.Format(source.DayLayout))
	w.Header().Set("Content-Type", "text/csv; charset=utf-8")
	w.Header().Set("Content-Disposition", `attachment; filename="`+filename+`"`)
	out := csv.NewWriter(w)
	_ = out.Write([]string{
		"day_utc", "records_complete", "model", "endpoint", "requests", "errors", "cold_starts",
		"prompt_tokens", "completion_tokens", "reasoning_tokens", "reasoning_reported_requests", "total_tokens",
		"gpu_seconds_estimate", "gpu_hours_estimate", "avg_latency_ms",
	})
	rows := append([]source.Row(nil), report.Rows...)
	hasRows := make(map[string]bool, len(rows))
	for _, row := range rows {
		hasRows[row.Day] = true
	}
	for _, day := range report.Incomplete {
		if !hasRows[day] {
			rows = append(rows, source.Row{Day: day})
		}
	}
	source.SortRows(rows)
	for _, row := range rows {
		recordsComplete := "yes"
		if report.IsIncomplete(row.Day) {
			recordsComplete = "no"
		}
		reasoning := ""
		if row.ReasoningReported > 0 {
			reasoning = strconv.FormatInt(row.ReasoningTokens, 10)
		}
		_ = out.Write([]string{
			row.Day, recordsComplete, csvSafe(row.Model), csvSafe(row.Endpoint),
			strconv.FormatInt(row.Requests, 10), strconv.FormatInt(row.Errors, 10),
			strconv.FormatInt(row.ColdStarts, 10), strconv.FormatInt(row.PromptTokens, 10),
			strconv.FormatInt(row.CompletionTokens, 10), reasoning, strconv.FormatInt(row.ReasoningReported, 10),
			strconv.FormatInt(row.TotalTokens, 10), strconv.FormatFloat(row.GPUSeconds, 'f', 3, 64),
			strconv.FormatFloat(row.GPUHours(), 'f', 6, 64), strconv.FormatInt(row.AvgLatencyMs(), 10),
		})
	}
	out.Flush()
}

// csvSafe prevents spreadsheet formula injection through model or endpoint strings.
func csvSafe(value string) string {
	if value != "" && strings.ContainsRune("=+-@\t\r", rune(value[0])) {
		return "'" + value
	}
	return value
}
