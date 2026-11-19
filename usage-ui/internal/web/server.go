// Package web serves the usage pages. Everything is rendered on the server:
// no JavaScript, no external assets, and every query is scoped to the
// authenticated user.
package web

import (
	"embed"
	"encoding/csv"
	"errors"
	"fmt"
	"html/template"
	"io/fs"
	"log"
	"net/http"
	"strconv"
	"strings"
	"time"

	"github.com/ualberta-rcg/aleph/usage-ui/internal/auth"
	"github.com/ualberta-rcg/aleph/usage-ui/internal/ledger"
)

//go:embed templates/*.html
var templateFS embed.FS

//go:embed static/*
var staticFS embed.FS

const (
	defaultDays = 14
	maxDays     = 366
)

// Server holds the HTTP handlers.
type Server struct {
	src  ledger.Source
	auth auth.Authenticator
	tmpl *template.Template
	// static serves the stylesheet at content-hashed URLs.
	static assets
	// Now is replaceable in tests.
	Now func() time.Time
	// SiteName is shown in the page title.
	SiteName string
}

// New builds a server.
func New(src ledger.Source, authn auth.Authenticator) (*Server, error) {
	staticFiles, err := fs.Sub(staticFS, "static")
	if err != nil {
		return nil, err
	}
	static, err := loadAssets(staticFiles)
	if err != nil {
		return nil, err
	}
	tmpl, err := template.New("").Funcs(template.FuncMap{
		"asset":    static.URL,
		"num":      formatInt,
		"gpuh":     formatGPUHours,
		"speed":    formatSpeed,
		"count":    countOf,
		"ts":       formatTS,
		"longdate": formatLongDate,
		"share":    share,
		// nearLimit is the context-window share, in percent, at which a
		// prompt counts as near the limit.
		"nearLimit": nearLimitPercent,
	}).ParseFS(templateFS, "templates/*.html")
	if err != nil {
		return nil, err
	}
	return &Server{src: src, auth: authn, tmpl: tmpl, static: static, Now: time.Now, SiteName: "Aleph"}, nil
}

// Handler returns the routed, header-hardened handler.
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
			http.Error(w, "loading ledger", http.StatusServiceUnavailable)
			return
		}
		_, _ = w.Write([]byte("ready\n"))
	})
	mux.HandleFunc("GET /{$}", s.withUser(s.overviewPage))
	mux.HandleFunc("GET /models", s.withUser(s.modelsPage))
	mux.HandleFunc("GET /errors", s.withUser(s.errorsPage))
	mux.HandleFunc("GET /report", s.withUser(s.reportPage))
	mux.HandleFunc("GET /usage.csv", s.withUser(s.csv))
	return secureHeaders(mux)
}

func secureHeaders(next http.Handler) http.Handler {
	return http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		headers := w.Header()
		headers.Set("Content-Security-Policy", "default-src 'none'; script-src 'self'; style-src 'self'; img-src 'self'; form-action 'self'; frame-ancestors 'none'; base-uri 'none'")
		headers.Set("X-Content-Type-Options", "nosniff")
		headers.Set("Referrer-Policy", "no-referrer")
		headers.Set("X-Frame-Options", "DENY")
		// Pages hold personal usage data and must never be cached. Hashed
		// assets set their own long-lived caching.
		if !strings.HasPrefix(r.URL.Path, "/assets/") {
			headers.Set("Cache-Control", "no-store")
		}
		next.ServeHTTP(w, r)
	})
}

type userHandler func(w http.ResponseWriter, r *http.Request, user string)

// withUser resolves the user from the authenticator only. No handler accepts
// a username from the query string, form, or path.
func (s *Server) withUser(next userHandler) http.HandlerFunc {
	return func(w http.ResponseWriter, r *http.Request) {
		user, err := s.auth.User(r)
		if err != nil {
			switch {
			case errors.Is(err, auth.ErrUntrustedPeer):
				// Never log the header value: it is whatever identity the
				// peer tried to claim.
				log.Printf("auth: identity header from untrusted peer %s", r.RemoteAddr)
			case !errors.Is(err, auth.ErrNoUser):
				log.Printf("auth: %v", err)
			}
			http.Error(w, "Not signed in. Sign in through your institution's login and try again.", http.StatusUnauthorized)
			return
		}
		next(w, r, user)
	}
}

// daysInRange counts the days from from to to, both included. Both must be
// UTC midnights.
func daysInRange(from, to time.Time) int {
	return int(to.Sub(from)/(24*time.Hour)) + 1
}

// dateRange parses ?from=&to= (YYYY-MM-DD, UTC, inclusive). The date
// pickers always send valid dates, so anything else came from an edited URL
// and is simply ignored: a missing or invalid date takes its default (the
// end is today, the start is defaultDays before the end), a start after the
// end is treated as missing, an end after today is cut to today, and a
// range over maxDays keeps the maxDays ending on the end date. The page and
// the CSV file name always show the range actually used.
func (s *Server) dateRange(r *http.Request) (from, to time.Time) {
	today := ledger.DayOf(s.Now())
	parse := func(key string) (time.Time, bool) {
		day, err := time.Parse(ledger.DayLayout, r.URL.Query().Get(key))
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

// csv downloads the user's daily rows for the range dateRange settles on;
// the file name carries that range.
func (s *Server) csv(w http.ResponseWriter, r *http.Request, user string) {
	from, to := s.dateRange(r)
	report, err := s.src.Usage(r.Context(), user, from, to)
	if err != nil {
		http.Error(w, "Usage data is unavailable right now.", http.StatusServiceUnavailable)
		return
	}
	filename := fmt.Sprintf("aleph-usage-%s-%s-to-%s.csv", user, from.Format(ledger.DayLayout), to.Format(ledger.DayLayout))
	w.Header().Set("Content-Type", "text/csv; charset=utf-8")
	w.Header().Set("Content-Disposition", `attachment; filename="`+filename+`"`)
	out := csv.NewWriter(w)
	// The file carries the same caveats as the pages, since it outlives them:
	// records_complete says whether the day's records are all on hand, and
	// reasoning_tokens is empty, not 0, when no request reported thinking.
	_ = out.Write([]string{"day_utc", "records_complete", "model", "endpoint", "requests", "errors", "cold_starts",
		"prompt_tokens", "completion_tokens", "reasoning_tokens", "reasoning_reported_requests", "total_tokens",
		"gpu_seconds_estimate", "gpu_hours_estimate", "avg_latency_ms"})
	// An incomplete day with no rows still gets a line, so the file can tell
	// a day whose records were lost from a day with no usage.
	rows := report.Rows
	hasRows := make(map[string]bool, len(rows))
	for _, row := range rows {
		hasRows[row.Day] = true
	}
	for _, day := range report.Incomplete {
		if !hasRows[day] {
			rows = append(rows, ledger.Row{Day: day})
		}
	}
	ledger.SortRows(rows)
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

// csvSafe stops spreadsheet formula injection through model names.
func csvSafe(value string) string {
	if value != "" && strings.ContainsRune("=+-@\t\r", rune(value[0])) {
		return "'" + value
	}
	return value
}
