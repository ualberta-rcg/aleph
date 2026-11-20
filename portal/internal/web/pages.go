package web

import (
	"errors"
	"fmt"
	"html/template"
	"log"
	"net/http"
	"net/url"
	"sort"
	"strconv"
	"strings"
	"time"

	"github.com/ualberta-rcg/aleph/portal/internal/catalog"
	"github.com/ualberta-rcg/aleph/portal/internal/source"
)

const reportPlatform = "the University of Alberta Research Computing inference platform"

var statusMeanings = map[int]string{
	400: "The request was malformed or exceeded the model's context window.",
	401: "The API key was missing or rejected.",
	403: "The API key is not permitted to call this model or endpoint.",
	404: "The requested model ID or sub-endpoint was not found.",
	408: "The request timed out before the model produced a response.",
	413: "The request payload exceeded the gateway size limit.",
	422: "One or more request parameters were invalid for this model.",
	429: "Rate limit exceeded. Spread requests out or retry with backoff.",
	499: "The client closed the connection before generation completed (for example a cancelled stream).",
	500: "The model backend failed while processing the request.",
	502: "The gateway could not reach the model backend or received an invalid upstream response.",
	503: "The model was unavailable (non-wake 503). Scale-from-zero 503 responses are counted separately.",
	504: "An upstream proxy or gateway read timed out while waiting for the model.",
}

type modelRow struct {
	Model string
	source.Agg
}

type endpointRow struct {
	Endpoint string
	source.Agg
}

type statusRow struct {
	Status  string
	Meaning string
	Count   int64
	Models  string
}

type dayPoint struct {
	Day        string
	Incomplete bool
	Tokens     int64
	GPUSeconds float64
	Requests   int64
}

type cardChange struct {
	Tokens, Requests, GPU string
}

type view struct {
	// Shared layout & session state.
	Site              string
	User              string
	Authenticated     bool
	IsMockOIDC        bool
	ScopedToSingleKey bool
	CSRFToken         string
	Title             string
	Path              string
	Nav               []navLink
	From, To          string
	CSVHref           string
	Ready             bool
	Coverage          coverage
	ReadErrors        bool
	Oldest            time.Time
	Newest            time.Time
	RefreshedAt       time.Time
	PageClass         string
	FromLong          string
	ToLong            string
	ModelsHref        string
	ErrorsHref        string
	OverviewHref      string

	// Login view.
	Next            string
	LoginError      string
	MockOIDCEnabled bool

	// Error view.
	ErrorHeading string
	ErrorMessage string

	// Usage range summaries.
	Totals    source.Agg
	Models    []modelRow
	Endpoints []endpointRow
	Days      []dayPoint

	// Overview.
	Change     cardChange
	Periods    []chartPeriod
	PeriodUnit string
	TokenChart template.HTML
	GPUChart   template.HTML

	// Models.
	NearLimit []modelRow

	// Errors.
	Statuses  []statusRow
	ErrorRate string

	// Report.
	Statement     string
	ReportSpan    string
	RequestedLong string
	TodayLeftOut  bool

	// Connect.
	APIBaseURL        string
	WebUIURL          string
	Catalog           catalog.Snapshot
	SnippetEnv        string
	SnippetChatCurl   string
	SnippetChatPython string
	SnippetAnthropic  string
	SnippetEmbed      string
	SnippetTasks      string

	// Account (/keys).
	AccountAuthLabel  string
	AccountScopeLabel string
	SubjectAccount    string
	SubjectKeyFP      string
	BackendMode       string
	CanRotateKey      bool
	SnippetKeyCheck   string
	SnippetCSVCurl    string
}

func (s *Server) baseView(r *http.Request, subj source.Subject, csrfToken, title, path string) (view, time.Time, time.Time) {
	from, to := s.dateRange(r)
	fromStr, toStr := from.Format(source.DayLayout), to.Format(source.DayLayout)
	rangeQuery := url.Values{"from": {fromStr}, "to": {toStr}}.Encode()
	page := view{
		Site:              s.SiteName,
		User:              subj.DisplayName(),
		Authenticated:     subj.Valid(),
		IsMockOIDC:        subj.AuthMethod == source.AuthMethodMockOIDC,
		ScopedToSingleKey: subj.Scope == source.ScopeKeyFP,
		CSRFToken:         csrfToken,
		Title:             title,
		Path:              path,
		Nav:               buildNav(path, rangeQuery),
		From:              fromStr,
		To:                toStr,
		FromLong:          formatLongDate(from),
		ToLong:            formatLongDate(to),
		Ready:             s.src.Ready(),
		PageClass:         "page-" + strings.ToLower(strings.ReplaceAll(title, " ", "-")),
		OverviewHref:      "/?" + rangeQuery,
		ModelsHref:        "/models?" + rangeQuery,
		ErrorsHref:        "/errors?" + rangeQuery,
		CSVHref:           "/usage.csv?" + rangeQuery,
	}
	return page, from, to
}

func (s *Server) renderError(w http.ResponseWriter, status int, subj source.Subject, csrfToken, heading, message string) {
	page := view{
		Site:          s.SiteName,
		User:          subj.DisplayName(),
		Authenticated: subj.Valid(),
		IsMockOIDC:    subj.AuthMethod == source.AuthMethodMockOIDC,
		CSRFToken:     csrfToken,
		Title:         heading,
		PageClass:     "page-error",
		Nav:           buildNav("", ""),
		ErrorHeading:  heading,
		ErrorMessage:  message,
	}
	w.Header().Set("Content-Type", "text/html; charset=utf-8")
	w.WriteHeader(status)
	if err := s.tmpl.ExecuteTemplate(w, "error.html", page); err != nil {
		log.Printf("render error.html: %v", err)
	}
}

func (s *Server) loadUsage(w http.ResponseWriter, r *http.Request, subj source.Subject, csrfToken, title, path string) (view, source.Report, bool) {
	page, from, to := s.baseView(r, subj, csrfToken, title, path)
	report, err := s.src.Usage(r.Context(), subj, from, to)
	if err != nil {
		log.Printf("usage query failed (%s): %v", s.src.Mode(), err)
		msg := "Usage records are temporarily unavailable. Please try again in a moment."
		if errors.Is(err, source.ErrPrometheusNotReady) {
			msg = err.Error()
		}
		s.renderError(w, http.StatusServiceUnavailable, subj, csrfToken, "Usage data unavailable", msg)
		return view{}, report, false
	}
	page.Oldest = report.Oldest
	page.Newest = report.Newest
	page.RefreshedAt = report.RefreshedAt
	page.Coverage = newCoverage(from, to, report.Incomplete)
	page.ReadErrors = report.ReadErrors
	page.summarize(report, from, to)
	return page, report, true
}

func (page *view) summarize(report source.Report, from, to time.Time) {
	byModel := map[string]*source.Agg{}
	byEndpoint := map[string]*source.Agg{}
	byDay := map[string]*dayPoint{}
	for _, row := range report.Rows {
		page.Totals.Merge(&row.Agg)
		modelTotal := byModel[row.Model]
		if modelTotal == nil {
			modelTotal = &source.Agg{}
			byModel[row.Model] = modelTotal
		}
		modelTotal.Merge(&row.Agg)
		endpointTotal := byEndpoint[row.Endpoint]
		if endpointTotal == nil {
			endpointTotal = &source.Agg{}
			byEndpoint[row.Endpoint] = endpointTotal
		}
		endpointTotal.Merge(&row.Agg)
		dayTotal := byDay[row.Day]
		if dayTotal == nil {
			dayTotal = &dayPoint{Day: row.Day}
			byDay[row.Day] = dayTotal
		}
		dayTotal.Tokens += row.TotalTokens
		dayTotal.GPUSeconds += row.GPUSeconds
		dayTotal.Requests += row.Requests
	}
	for name, agg := range byModel {
		page.Models = append(page.Models, modelRow{Model: name, Agg: *agg})
	}
	sort.Slice(page.Models, func(i, j int) bool {
		left, right := page.Models[i], page.Models[j]
		if left.TotalTokens != right.TotalTokens {
			return left.TotalTokens > right.TotalTokens
		}
		if left.GPUSeconds != right.GPUSeconds {
			return left.GPUSeconds > right.GPUSeconds
		}
		if left.Requests != right.Requests {
			return left.Requests > right.Requests
		}
		return left.Model < right.Model
	})
	for name, agg := range byEndpoint {
		page.Endpoints = append(page.Endpoints, endpointRow{Endpoint: name, Agg: *agg})
	}
	sort.Slice(page.Endpoints, func(i, j int) bool {
		if page.Endpoints[i].Requests != page.Endpoints[j].Requests {
			return page.Endpoints[i].Requests > page.Endpoints[j].Requests
		}
		return page.Endpoints[i].Endpoint < page.Endpoints[j].Endpoint
	})
	for day := from; !day.After(to); day = day.AddDate(0, 0, 1) {
		key := day.Format(source.DayLayout)
		point := dayPoint{Day: key}
		if found := byDay[key]; found != nil {
			point = *found
		}
		point.Incomplete = report.IsIncomplete(key)
		page.Days = append(page.Days, point)
	}
}

func (s *Server) render(w http.ResponseWriter, name string, page view) {
	w.Header().Set("Content-Type", "text/html; charset=utf-8")
	if err := s.tmpl.ExecuteTemplate(w, name, page); err != nil {
		log.Printf("render %s: %v", name, err)
	}
}

func (s *Server) overviewPage(w http.ResponseWriter, r *http.Request, subj source.Subject, csrfToken string) {
	page, report, ok := s.loadUsage(w, r, subj, csrfToken, "Overview", "/")
	if !ok {
		return
	}
	page.Change = s.previousPeriod(r, subj, report, page.Totals)
	page.Periods, page.PeriodUnit = chartPeriods(page.Days)
	tokenPoints := make([]barPoint, len(page.Periods))
	gpuPoints := make([]barPoint, len(page.Periods))
	for i, period := range page.Periods {
		suffix := ""
		switch {
		case period.Days == 1 && period.Incomplete():
			suffix = " (incomplete records)"
		case period.Incomplete():
			suffix = fmt.Sprintf(" (includes %s)", countOf(period.IncompleteDays, "incomplete day", "incomplete days"))
		}
		tokenPoints[i] = barPoint{
			Label: period.Start, Hover: period.Label, Value: float64(period.Tokens),
			Text: formatInt(period.Tokens) + " tokens" + suffix, Incomplete: period.Incomplete(),
		}
		gpuPoints[i] = barPoint{
			Label: period.Start, Hover: period.Label, Value: period.GPUSeconds / 3600,
			Text: formatGPUHours(period.GPUSeconds) + " est. GPU-hours" + suffix, Incomplete: period.Incomplete(),
		}
	}
	page.TokenChart = barChart("tokens", "Tokens per "+page.PeriodUnit, tokenPoints, formatCompact)
	page.GPUChart = barChart("gpu", "Estimated GPU-hours per "+page.PeriodUnit, gpuPoints, formatCompact)
	s.render(w, "overview.html", page)
}

func (s *Server) previousPeriod(r *http.Request, subj source.Subject, report source.Report, current source.Agg) cardChange {
	if !s.src.Ready() || report.Oldest.IsZero() || len(report.Incomplete) > 0 {
		return cardChange{}
	}
	from, to := report.From.UTC(), report.To.UTC()
	days := daysInRange(from, to)
	previousFrom := from.AddDate(0, 0, -days)
	previousTo := from.AddDate(0, 0, -1)
	previous, err := s.src.Usage(r.Context(), subj, previousFrom, previousTo)
	if err != nil || len(previous.Incomplete) > 0 {
		return cardChange{}
	}
	var before source.Agg
	for _, row := range previous.Rows {
		before.Merge(&row.Agg)
	}
	return cardChange{
		Tokens:   changeText(float64(current.TotalTokens), float64(before.TotalTokens), days),
		Requests: changeText(float64(current.Requests), float64(before.Requests), days),
		GPU:      changeText(current.GPUSeconds, before.GPUSeconds, days),
	}
}

func (s *Server) modelsPage(w http.ResponseWriter, r *http.Request, subj source.Subject, csrfToken string) {
	page, _, ok := s.loadUsage(w, r, subj, csrfToken, "Models", "/models")
	if !ok {
		return
	}
	for _, model := range page.Models {
		if model.NearLimit() {
			page.NearLimit = append(page.NearLimit, model)
		}
	}
	s.render(w, "models.html", page)
}

func (s *Server) errorsPage(w http.ResponseWriter, r *http.Request, subj source.Subject, csrfToken string) {
	page, _, ok := s.loadUsage(w, r, subj, csrfToken, "Errors", "/errors")
	if !ok {
		return
	}
	if page.Totals.Requests > 0 {
		rate := float64(page.Totals.Errors) * 100 / float64(page.Totals.Requests)
		page.ErrorRate = strconv.FormatFloat(rate, 'f', 2, 64) + "%"
	}
	for bucket := 0; bucket < source.StatusBuckets; bucket++ {
		count := page.Totals.StatusCounts[bucket]
		if count == 0 {
			continue
		}
		row := statusRow{Count: count}
		switch bucket {
		case source.StatusOther4xx:
			row.Status, row.Meaning = "Other 4xx", "The gateway refused the request. Check the response body for details."
		case source.StatusOther5xx:
			row.Status, row.Meaning = "Other 5xx", "An upstream error occurred on the platform side."
		default:
			status := source.TrackedStatuses[bucket]
			row.Status, row.Meaning = strconv.Itoa(status), statusMeanings[status]
		}
		type modelCount struct {
			name  string
			count int64
		}
		var affected []modelCount
		for _, model := range page.Models {
			if n := model.StatusCounts[bucket]; n > 0 {
				affected = append(affected, modelCount{model.Model, n})
			}
		}
		sort.Slice(affected, func(i, j int) bool {
			if affected[i].count != affected[j].count {
				return affected[i].count > affected[j].count
			}
			return affected[i].name < affected[j].name
		})
		parts := make([]string, len(affected))
		for i, model := range affected {
			parts[i] = fmt.Sprintf("%s (%s)", model.name, formatInt(model.count))
		}
		row.Models = strings.Join(parts, ", ")
		page.Statuses = append(page.Statuses, row)
	}
	sort.SliceStable(page.Statuses, func(i, j int) bool { return page.Statuses[i].Count > page.Statuses[j].Count })
	s.render(w, "errors.html", page)
}

func (s *Server) reportPage(w http.ResponseWriter, r *http.Request, subj source.Subject, csrfToken string) {
	page, report, ok := s.loadUsage(w, r, subj, csrfToken, "Report", "/report")
	if !ok {
		return
	}
	from, to := report.From.UTC(), report.To.UTC()
	first, last := from, to
	if today := source.DayOf(s.Now()); !last.Before(today) {
		last = today.AddDate(0, 0, -1)
		page.TodayLeftOut = true
	}
	for !first.After(last) && report.IsIncomplete(first.Format(source.DayLayout)) {
		first = first.AddDate(0, 0, 1)
	}
	for !last.Before(first) && report.IsIncomplete(last.Format(source.DayLayout)) {
		last = last.AddDate(0, 0, -1)
	}
	if page.Coverage.Partial || page.TodayLeftOut {
		page.RequestedLong = page.FromLong + " to " + page.ToLong
	}
	if last.Before(first) {
		page.Statement = "No day in this range has finished yet, so there is nothing to report."
		page.ReportSpan = "no finished days"
		if page.Coverage.Partial {
			page.Statement = fmt.Sprintf("Complete usage records are not on hand for %s to %s.", page.FromLong, page.ToLong)
			page.ReportSpan = "no days with complete records"
			page.Coverage.Text = "No statement can be made for this range: every day in it has incomplete records."
		}
		page.Totals, page.Models, page.Endpoints, page.Days = source.Agg{}, nil, nil, nil
		s.render(w, "report.html", page)
		return
	}
	var between []string
	for _, day := range report.Incomplete {
		if day > first.Format(source.DayLayout) && day < last.Format(source.DayLayout) {
			between = append(between, day)
		}
	}
	page.summarizeComplete(report, first, last)
	page.ReportSpan = formatSpan(first, last)
	if len(between) > 0 {
		page.ReportSpan += ", excluding " + spanList(spansOf(between))
	}
	if page.Coverage.Partial {
		page.Coverage.Text = fmt.Sprintf("This statement leaves out the %s with incomplete records (%s), so it covers %s.",
			countOf(page.Coverage.IncompleteDays, "day", "days"), page.Coverage.List, page.ReportSpan)
	}
	usedModels := 0
	for _, model := range page.Models {
		if model.Requests > model.Errors {
			usedModels++
		}
	}
	page.Statement = reportStatement(page.Site, formatLongDate(first), formatLongDate(last), int64(len(between)), page.Totals, usedModels)
	s.render(w, "report.html", page)
}

func (page *view) summarizeComplete(report source.Report, from, to time.Time) {
	fromDay, toDay := from.Format(source.DayLayout), to.Format(source.DayLayout)
	kept := report
	kept.Rows = nil
	for _, row := range report.Rows {
		if row.Day >= fromDay && row.Day <= toDay && !report.IsIncomplete(row.Day) {
			kept.Rows = append(kept.Rows, row)
		}
	}
	page.Totals, page.Models, page.Endpoints, page.Days = source.Agg{}, nil, nil, nil
	page.summarize(kept, from, to)
}

func reportStatement(site, fromLong, toLong string, excluded int64, totals source.Agg, models int) string {
	excluding := ""
	if excluded > 0 {
		excluding = fmt.Sprintf(", excluding %s with incomplete records", countOf(excluded, "day", "days"))
	}
	if totals.Requests == 0 {
		return fmt.Sprintf("No direct %s API usage was recorded between %s and %s%s (async /v1/tasks batch jobs excluded).", site, fromLong, toLong, excluding)
	}
	return fmt.Sprintf("Between %s and %s%s, I used an estimated %s GPU-hours (allocated GPUs × request duration) and %s tokens across %s on %s, %s (excluding async /v1/tasks batch jobs).",
		fromLong, toLong, excluding, formatGPUHours(totals.GPUSeconds), formatTokenWords(totals.TotalTokens),
		countOf(int64(models), "model", "models"), site, reportPlatform)
}

func (s *Server) connectPage(w http.ResponseWriter, r *http.Request, subj source.Subject, csrfToken string) {
	page, _, _ := s.baseView(r, subj, csrfToken, "Connect", "/connect")
	page.PageClass = "page-connect"
	page.APIBaseURL = s.APIBaseURL
	page.WebUIURL = s.WebUIURL

	var snap catalog.Snapshot
	if s.catalog != nil {
		snap = s.catalog.Get(r.Context())
	}
	page.Catalog = snap

	chatModel := nonEmptyModel(snap.ChatModel, "<CHAT_MODEL_ID>")
	anthropicModel := nonEmptyModel(snap.AnthropicModel, chatModel)
	embedModel := nonEmptyModel(snap.EmbedModel, "<EMBEDDING_MODEL_ID>")
	taskModel := nonEmptyModel(snap.TaskModel, chatModel)

	page.SnippetEnv = fmt.Sprintf(`source ~/.aleph_tyk.env
curl -fsSL "%s/v1/models" -H "Authorization: Bearer $TYK_KEY"
# Full catalog (embeddings, rerankers, vision, audio, science):
curl -fsSL "%s/v1/models?all=true" -H "Authorization: Bearer $TYK_KEY"`, s.APIBaseURL, s.APIBaseURL)

	page.SnippetChatCurl = fmt.Sprintf(`source ~/.aleph_tyk.env
curl -fsSL "%s/v1/chat/completions" \
  -H "Authorization: Bearer $TYK_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "model": %q,
    "messages": [{"role": "user", "content": "Summarize key trade-offs in mixed-precision training."}]
  }'`, s.APIBaseURL, chatModel)

	page.SnippetChatPython = fmt.Sprintf(`import os
from openai import OpenAI

client = OpenAI(
    base_url="%s/v1",
    api_key=os.environ["TYK_KEY"],
)

resp = client.chat.completions.create(
    model=%q,
    messages=[{"role": "user", "content": "Hello from Vulcan!"}],
)
print(resp.choices[0].message.content)`, s.APIBaseURL, chatModel)

	page.SnippetAnthropic = fmt.Sprintf(`source ~/.aleph_tyk.env
export ANTHROPIC_BASE_URL="%s/anthropic"
export ANTHROPIC_AUTH_TOKEN="$TYK_KEY"

curl -fsSL "$ANTHROPIC_BASE_URL/v1/messages" \
  -H "x-api-key: $TYK_KEY" \
  -H "anthropic-version: 2023-06-01" \
  -H "Content-Type: application/json" \
  -d '{
    "model": %q,
    "max_tokens": 512,
    "messages": [{"role": "user", "content": "Write a minimal Go table-driven test."}]
  }'`, s.APIBaseURL, anthropicModel)

	page.SnippetEmbed = fmt.Sprintf(`source ~/.aleph_tyk.env
curl -fsSL "%s/v1/embeddings" \
  -H "Authorization: Bearer $TYK_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "model": %q,
    "input": ["protein folding", "graph neural networks"]
  }'`, s.APIBaseURL, embedModel)

	page.SnippetTasks = fmt.Sprintf(`source ~/.aleph_tyk.env
curl -fsSL "%s/v1/tasks" \
  -H "Authorization: Bearer $TYK_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "model": %q,
    "endpoint": "/v1/chat/completions",
    "items": [
      {"messages": [{"role": "user", "content": "Classify sample A."}]},
      {"messages": [{"role": "user", "content": "Classify sample B."}]}
    ]
  }'`, s.APIBaseURL, taskModel)

	s.render(w, "connect.html", page)
}

func nonEmptyModel(id, placeholder string) string {
	if strings.TrimSpace(id) != "" {
		return id
	}
	return placeholder
}

func (s *Server) keysPage(w http.ResponseWriter, r *http.Request, subj source.Subject, csrfToken string) {
	page, _, _ := s.baseView(r, subj, csrfToken, "Account", "/keys")
	page.PageClass = "page-account"
	page.BackendMode = s.src.Mode()
	page.CanRotateKey = s.auth.CanRotateKey(subj)
	page.SubjectAccount = subj.Account
	if subj.KeyFP.Valid() {
		page.SubjectKeyFP = subj.KeyFP.Display()
	}

	switch subj.AuthMethod {
	case source.AuthMethodMockOIDC:
		page.AccountAuthLabel = "Mock OIDC (local .43 operator test)"
	case source.AuthMethodOIDC:
		page.AccountAuthLabel = "Institutional OIDC"
	default:
		page.AccountAuthLabel = "Personal API key (verified via Tyk)"
	}

	if subj.Scope == source.ScopeKeyFP {
		page.AccountScopeLabel = "Single API-key fingerprint (service or unindexed key)"
	} else {
		page.AccountScopeLabel = "Identity-wide across your personal user/poc keys"
	}

	page.SnippetKeyCheck = `# On any Vulcan login node:
ls -l ~/.aleph_tyk.env
source ~/.aleph_tyk.env
printf 'Key loaded (ends with ...%s)\n' "${TYK_KEY: -4}"`

	portalOrigin := s.auth.PublicOrigin()
	page.SnippetCSVCurl = fmt.Sprintf(`source ~/.aleph_tyk.env
curl -fsSL -H "Authorization: Bearer $TYK_KEY" \
  "%s/usage.csv?from=%s&to=%s" \
  -o aleph-usage-%s-to-%s.csv`, portalOrigin, page.From, page.To, page.From, page.To)

	s.render(w, "keys.html", page)
}
