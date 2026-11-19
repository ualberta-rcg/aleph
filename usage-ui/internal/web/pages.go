package web

import (
	"fmt"
	"html/template"
	"log"
	"net/http"
	"net/url"
	"sort"
	"strconv"
	"strings"
	"time"

	"github.com/ualberta-rcg/aleph/usage-ui/internal/ledger"
)

// reportPlatform completes the report sentence after the site name.
const reportPlatform = "the University of Alberta Research Computing inference platform"

// navPages are the pages in the header navigation, in order.
var navPages = []struct{ Label, Path string }{
	{"Overview", "/"},
	{"Models", "/models"},
	{"Errors", "/errors"},
	{"Report", "/report"},
}

// statusMeanings explains each tracked error status in plain words.
var statusMeanings = map[int]string{
	400: "The request was malformed or too long for the model.",
	401: "The API key was missing or not accepted.",
	403: "The key has no access to this model or endpoint.",
	404: "The model or endpoint does not exist. Check the model ID.",
	408: "The request timed out before the model answered.",
	413: "The request was too large to accept.",
	422: "A parameter was invalid for this model.",
	429: "You hit your rate limit. Slow down or spread requests out.",
	499: "Your client closed the connection before the response finished, often a cancelled stream.",
	500: "The model failed while handling the request.",
	502: "The gateway could not reach the model's backend, or the backend took too long to answer.",
	503: "The model was unavailable: out of capacity or not ready. Wake-ups are counted separately.",
	504: "A component in front of the model timed out before the model answered.",
}

type navLink struct {
	Label   string
	Href    string
	Current bool
}

type modelRow struct {
	Model string
	ledger.Agg
}

type endpointRow struct {
	Endpoint string
	ledger.Agg
}

type statusRow struct {
	Status  string
	Meaning string
	Count   int64
	Models  string // "qwen35-122b (3), gpt-oss-120b (1)"
}

type dayPoint struct {
	Day        string
	Incomplete bool // the day's records may be partly missing
	Tokens     int64
	GPUSeconds float64
	Requests   int64
}

// cardChange holds the previous-period comparison for the overview cards.
// Empty strings mean no comparison is shown.
type cardChange struct {
	Tokens, Requests, GPU string
}

// view is everything a page template can use. Each handler fills the parts
// its page shows; the layout fields are always set.
type view struct {
	// Layout.
	Site, User   string
	Title        string
	Path         string // form action for the date range
	Nav          []navLink
	From, To     string
	CSVHref      string
	Ready        bool
	Coverage     coverage // which days of the range have incomplete records
	ReadErrors   bool     // some ledger files could not be read on the last refresh
	SavedDays    int64    // days in the range shown from the daily history
	Oldest       time.Time
	Newest       time.Time
	RefreshedAt  time.Time
	PageClass    string
	FromLong     string
	ToLong       string
	ModelsHref   string
	ErrorsHref   string
	OverviewHref string

	// Summary of the range.
	Totals    ledger.Agg
	Models    []modelRow
	Endpoints []endpointRow
	Days      []dayPoint

	// Overview.
	Change     cardChange
	Periods    []chartPeriod // the charts' bars and the table beneath them
	PeriodUnit string        // "day" or "week"
	TokenChart template.HTML
	GPUChart   template.HTML

	// Models.
	NearLimit []modelRow

	// Errors.
	Statuses  []statusRow
	ErrorRate string

	// Report.
	Statement     string
	ReportSpan    string // the days the statement and table cover, "4 – 18 Nov"
	RequestedLong string // the requested range, shown in print when it differs
	TodayLeftOut  bool   // the range reaches today, which the statement leaves out
}

// load runs the range query and fills the layout and summary. It writes the
// error response itself and returns false when the page cannot be shown.
func (s *Server) load(w http.ResponseWriter, r *http.Request, user, title, path string) (view, ledger.Report, bool) {
	from, to := s.dateRange(r)
	report, err := s.src.Usage(r.Context(), user, from, to)
	if err != nil {
		log.Printf("usage query: %v", err)
		http.Error(w, "Usage data is unavailable right now.", http.StatusServiceUnavailable)
		return view{}, report, false
	}
	page := view{
		Site: s.SiteName, User: user, Title: title, Path: path,
		From: from.Format(ledger.DayLayout), To: to.Format(ledger.DayLayout),
		FromLong: formatLongDate(from), ToLong: formatLongDate(to),
		Oldest: report.Oldest, Newest: report.Newest, RefreshedAt: report.RefreshedAt,
		Ready:     s.src.Ready(),
		PageClass: "page-" + strings.ToLower(title),
	}
	page.Coverage = newCoverage(from, to, report.Incomplete)
	page.ReadErrors = report.ReadErrors
	page.SavedDays = int64(report.SavedDays)
	rangeQuery := url.Values{"from": {page.From}, "to": {page.To}}.Encode()
	for _, item := range navPages {
		page.Nav = append(page.Nav, navLink{Label: item.Label, Href: item.Path + "?" + rangeQuery, Current: item.Path == path})
	}
	page.OverviewHref = "/?" + rangeQuery
	page.ModelsHref = "/models?" + rangeQuery
	page.ErrorsHref = "/errors?" + rangeQuery
	page.CSVHref = "/usage.csv?" + rangeQuery
	page.summarize(report, from, to)
	return page, report, true
}

// summarize totals the report by model, endpoint, and day.
func (page *view) summarize(report ledger.Report, from, to time.Time) {
	byModel := map[string]*ledger.Agg{}
	byEndpoint := map[string]*ledger.Agg{}
	byDay := map[string]*dayPoint{}
	for _, row := range report.Rows {
		page.Totals.Merge(&row.Agg)
		modelTotal := byModel[row.Model]
		if modelTotal == nil {
			modelTotal = &ledger.Agg{}
			byModel[row.Model] = modelTotal
		}
		modelTotal.Merge(&row.Agg)
		endpointTotal := byEndpoint[row.Endpoint]
		if endpointTotal == nil {
			endpointTotal = &ledger.Agg{}
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
	// One point per day in range, including days with no usage.
	for day := from; !day.After(to); day = day.AddDate(0, 0, 1) {
		key := day.Format(ledger.DayLayout)
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

func (s *Server) overviewPage(w http.ResponseWriter, r *http.Request, user string) {
	page, report, ok := s.load(w, r, user, "Overview", "/")
	if !ok {
		return
	}
	page.Change = s.previousPeriod(r, user, report, page.Totals)

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
		tokenPoints[i] = barPoint{Label: period.Start, Hover: period.Label, Value: float64(period.Tokens),
			Text: formatInt(period.Tokens) + " tokens" + suffix, Incomplete: period.Incomplete()}
		gpuPoints[i] = barPoint{Label: period.Start, Hover: period.Label, Value: period.GPUSeconds / 3600,
			Text: formatGPUHours(period.GPUSeconds) + " GPU-hours" + suffix, Incomplete: period.Incomplete()}
	}
	page.TokenChart = barChart("tokens", "Tokens per "+page.PeriodUnit, tokenPoints, formatCompact)
	page.GPUChart = barChart("gpu", "GPU-hours per "+page.PeriodUnit, gpuPoints, formatCompact)
	s.render(w, "overview.html", page)
}

// previousPeriod compares the totals with the same number of days just
// before the range. It shows nothing when any day of either period has
// incomplete records: a comparison against missing data would look like a
// real change.
func (s *Server) previousPeriod(r *http.Request, user string, report ledger.Report, current ledger.Agg) cardChange {
	if !s.src.Ready() || report.Oldest.IsZero() || len(report.Incomplete) > 0 {
		return cardChange{}
	}
	from, to := report.From.UTC(), report.To.UTC()
	days := daysInRange(from, to)
	previousFrom := from.AddDate(0, 0, -days)
	previousTo := from.AddDate(0, 0, -1)
	previous, err := s.src.Usage(r.Context(), user, previousFrom, previousTo)
	if err != nil {
		log.Printf("previous-period query: %v", err)
		return cardChange{}
	}
	if len(previous.Incomplete) > 0 {
		return cardChange{}
	}
	var before ledger.Agg
	for _, row := range previous.Rows {
		before.Merge(&row.Agg)
	}
	return cardChange{
		Tokens:   changeText(float64(current.TotalTokens), float64(before.TotalTokens), days),
		Requests: changeText(float64(current.Requests), float64(before.Requests), days),
		GPU:      changeText(current.GPUSeconds, before.GPUSeconds, days),
	}
}

func (s *Server) modelsPage(w http.ResponseWriter, r *http.Request, user string) {
	page, _, ok := s.load(w, r, user, "Models", "/models")
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

func (s *Server) errorsPage(w http.ResponseWriter, r *http.Request, user string) {
	page, _, ok := s.load(w, r, user, "Errors", "/errors")
	if !ok {
		return
	}
	if page.Totals.Requests > 0 {
		rate := float64(page.Totals.Errors) * 100 / float64(page.Totals.Requests)
		page.ErrorRate = strconv.FormatFloat(rate, 'f', 2, 64) + "%"
	}
	for bucket := 0; bucket < ledger.StatusBuckets; bucket++ {
		count := page.Totals.StatusCounts[bucket]
		if count == 0 {
			continue
		}
		row := statusRow{Count: count}
		switch bucket {
		case ledger.StatusOther4xx:
			row.Status, row.Meaning = "Other 4xx", "The gateway refused the request. Check the response body for details."
		case ledger.StatusOther5xx:
			row.Status, row.Meaning = "Other 5xx", "Something failed on the platform side."
		default:
			status := ledger.TrackedStatuses[bucket]
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

func (s *Server) reportPage(w http.ResponseWriter, r *http.Request, user string) {
	page, report, ok := s.load(w, r, user, "Report", "/report")
	if !ok {
		return
	}
	from, to := report.From.UTC(), report.To.UTC()
	// The statement covers finished days with complete records only. Today
	// is not over, so it is left out. Incomplete days at either end narrow
	// the dates, and those in between are left out and counted; the notice
	// above lists them. Nothing claims the whole range.
	first, last := from, to
	if today := ledger.DayOf(s.Now()); !last.Before(today) {
		last = today.AddDate(0, 0, -1)
		page.TodayLeftOut = true
	}
	for !first.After(last) && report.IsIncomplete(first.Format(ledger.DayLayout)) {
		first = first.AddDate(0, 0, 1)
	}
	for !last.Before(first) && report.IsIncomplete(last.Format(ledger.DayLayout)) {
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
		page.Totals, page.Models, page.Endpoints, page.Days = ledger.Agg{}, nil, nil, nil
		s.render(w, "report.html", page)
		return
	}
	var between []string
	for _, day := range report.Incomplete {
		if day > first.Format(ledger.DayLayout) && day < last.Format(ledger.DayLayout) {
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

// summarizeComplete replaces the page's summary with one of the complete
// days from from to to only, so that the statement and the table below it
// agree.
func (page *view) summarizeComplete(report ledger.Report, from, to time.Time) {
	fromDay, toDay := from.Format(ledger.DayLayout), to.Format(ledger.DayLayout)
	kept := report
	kept.Rows = nil
	for _, row := range report.Rows {
		if row.Day >= fromDay && row.Day <= toDay && !report.IsIncomplete(row.Day) {
			kept.Rows = append(kept.Rows, row)
		}
	}
	page.Totals, page.Models, page.Endpoints, page.Days = ledger.Agg{}, nil, nil, nil
	page.summarize(kept, from, to)
}

// reportStatement is the sentence offered for grant and progress reports.
// fromLong and toLong must be the first and last complete days, excluded the
// number of incomplete days between them, and totals must cover only the
// complete days. models counts the models with at least one successful
// request.
func reportStatement(site, fromLong, toLong string, excluded int64, totals ledger.Agg, models int) string {
	excluding := ""
	if excluded > 0 {
		excluding = fmt.Sprintf(", excluding %s with incomplete records", countOf(excluded, "day", "days"))
	}
	if totals.Requests == 0 {
		return fmt.Sprintf("No %s usage was recorded between %s and %s%s.", site, fromLong, toLong, excluding)
	}
	return fmt.Sprintf("Between %s and %s%s, I used an estimated %s GPU-hours and %s tokens across %s on %s, %s.",
		fromLong, toLong, excluding, formatGPUHours(totals.GPUSeconds), formatTokenWords(totals.TotalTokens),
		countOf(int64(models), "model", "models"), site, reportPlatform)
}
