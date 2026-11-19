// Package ledger reads the Aleph gateway usage ledger and answers per-user
// usage questions.
//
// The ledger format is defined by gateway/app/usage.py and documented in
// docs/LOGGING.md: one JSON object per line, one directory per gateway pod,
// size-rotated as usage.log, usage.log.1, ... Only the fields needed for a
// user-facing usage summary are decoded; everything else is ignored.
package ledger

import (
	"bytes"
	"encoding/json"
	"fmt"
	"strings"
	"time"
)

// TimeLayout is the timestamp format written by usage.py.
const TimeLayout = "2006-01-02T15:04:05Z"

// DayLayout is the UTC day key used for daily buckets.
const DayLayout = "2006-01-02"

// Record is the subset of one usage-ledger line that the UI uses.
type Record struct {
	TS           string `json:"ts"`
	Identity     string `json:"identity"`
	IdentityType string `json:"identity_type"`
	Account      string `json:"account"`
	Endpoint     string `json:"endpoint"`
	API          string `json:"api"`
	Model        string `json:"model"`
	Status       int    `json:"status"`
	Stream       bool   `json:"stream"`
	ColdStart    bool   `json:"cold_start"`
	LatencyMs    int64  `json:"latency_ms"`
	Tokens       struct {
		Prompt     int64 `json:"prompt"`
		Completion int64 `json:"completion"`
		Total      int64 `json:"total"`
		// Detail is the upstream usage object, stored verbatim by the
		// gateway. Its shape varies by runtime, so it is decoded leniently
		// into ReasoningTokens and never fails the record.
		Detail json.RawMessage `json:"detail"`
	} `json:"tokens"`
	ContextWindow int64 `json:"context_window"`
	Derived       struct {
		GPUSeconds float64 `json:"gpu_seconds"`
	} `json:"derived"`

	// ReasoningTokens ("thinking") is the part of the completion the model
	// spent reasoning. ReasoningReported is false when the runtime did not
	// report a count, which is not the same as zero thinking. Set by
	// ParseRecord.
	ReasoningTokens   int64 `json:"-"`
	ReasoningReported bool  `json:"-"`
	// EndpointKind says what Endpoint is; see NormalizeEndpoint. For
	// EndpointModelRoute, Endpoint is the request path and the reader still
	// decides whether to report it by name. Set by ParseRecord.
	EndpointKind EndpointKind `json:"-"`
}

// Succeeded reports whether the request got a 2xx response.
func (rec Record) Succeeded() bool { return rec.Status >= 200 && rec.Status < 300 }

// ParseRecord decodes one ledger line and its timestamp.
func ParseRecord(line []byte) (Record, time.Time, error) {
	var rec Record
	if err := json.Unmarshal(line, &rec); err != nil {
		return rec, time.Time{}, err
	}
	ts, err := time.Parse(TimeLayout, rec.TS)
	if err != nil {
		return rec, time.Time{}, fmt.Errorf("bad ts %q: %w", rec.TS, err)
	}
	if rec.Identity == "" {
		return rec, ts, fmt.Errorf("record has no identity")
	}
	if rec.Model == "" {
		rec.Model = "unknown"
	}
	rec.Endpoint, rec.EndpointKind = NormalizeEndpoint(rec.Endpoint)
	rec.ReasoningTokens, rec.ReasoningReported = reasoningTokens(rec.Tokens.Detail, rec.Tokens.Completion)
	rec.Tokens.Detail = nil // decoded; do not keep the raw bytes
	return rec, ts, nil
}

// Endpoint labels for records whose path is not reported by name.
const (
	// EndpointUnknown is a record that names no endpoint.
	EndpointUnknown = "unknown"
	// EndpointOther is any path that is not reported by name.
	EndpointOther = "other"
)

// knownEndpoints are the routes the gateway serves itself
// (gateway/app/gateway.py and tasks.py) plus the standard OpenAI-compatible
// paths it forwards. They are always reported by name.
var knownEndpoints = map[string]bool{
	"/v1/chat/completions":      true,
	"/v1/completions":           true,
	"/v1/responses":             true,
	"/v1/embeddings":            true,
	"/v1/rerank":                true,
	"/v1/messages":              true,
	"/v1/messages/count_tokens": true,
	"/v1/audio/transcriptions":  true,
	"/v1/audio/speech":          true,
	"/v1/audio/clone":           true,
	"/v1/audio/voices":          true,
	"/v1/images/generations":    true,
	"/v1/images/edits":          true,
	"/v1/tasks":                 true,
}

// Limits for model-specific endpoints such as /v1/science/predict or
// /v1/biology/ipd/rfdiffusion/generate, which the gateway forwards through
// its catch-all route.
const (
	maxEndpointLength   = 64
	maxEndpointSegments = 5 // path segments after /v1
)

// EndpointKind classifies a logged request path.
type EndpointKind int

const (
	// EndpointUnnamed is a path that is never reported by name. Its label
	// is EndpointOther, or EndpointUnknown when the record names no path.
	EndpointUnnamed EndpointKind = iota
	// EndpointKnown is a route in knownEndpoints, always reported by name.
	EndpointKnown
	// EndpointModelRoute is a short, plain path that may be a model's own
	// route, such as /v1/science/predict. Whether it is reported by name
	// depends on the outcome of the requests to it; see
	// FileSource.endpointLabel.
	EndpointModelRoute
)

// NormalizeEndpoint maps a logged request path to the label it is reported
// under and says what kind of path it is.
//
// The ledger's endpoint is the request path, and the catch-all route logs
// any /v1/ path a client sends to a valid model. Kept as is, one user could
// create any number of distinct endpoints, each costing memory and a table
// row. So only a short, plain path outside knownEndpoints can be a model
// route, and the reader names it only after a request to it has succeeded,
// which means a model actually serves it. Every other path is EndpointOther.
// FileSource also caps how many model route names it keeps.
//
// Paths under /v1/tasks/ (one task's status or result) count as /v1/tasks,
// and a trailing slash is ignored, as it names the same route.
func NormalizeEndpoint(path string) (label string, kind EndpointKind) {
	if path == "" {
		return EndpointUnknown, EndpointUnnamed
	}
	path = strings.TrimSuffix(path, "/")
	if knownEndpoints[path] {
		return path, EndpointKnown
	}
	if strings.HasPrefix(path, "/v1/tasks/") {
		return "/v1/tasks", EndpointKnown
	}
	if plainEndpoint(path) {
		return path, EndpointModelRoute
	}
	return EndpointOther, EndpointUnnamed
}

// plainEndpoint reports whether path looks like a route a model card
// declares: /v1/ followed by a few lowercase segments of letters, digits,
// hyphens, and underscores.
func plainEndpoint(path string) bool {
	rest, ok := strings.CutPrefix(path, "/v1/")
	if !ok || len(path) > maxEndpointLength {
		return false
	}
	segments := strings.Split(rest, "/")
	if len(segments) > maxEndpointSegments {
		return false
	}
	for _, segment := range segments {
		if segment == "" {
			return false
		}
		for _, char := range segment {
			if !(char >= 'a' && char <= 'z' || char >= '0' && char <= '9' || char == '-' || char == '_') {
				return false
			}
		}
	}
	return true
}

// reasoningTokens reads the thinking-token count from the upstream usage
// detail. OpenAI chat-style runtimes such as vLLM report
// completion_tokens_details.reasoning_tokens; Responses-style ones report
// output_tokens_details.reasoning_tokens. Not every model reports it, so
// reported says whether a usable count was present: a model that never
// reports thinking is different from one that did no thinking. The count
// never exceeds the completion it is part of.
func reasoningTokens(detail json.RawMessage, completion int64) (count int64, reported bool) {
	detail = bytes.TrimSpace(detail)
	if len(detail) == 0 || detail[0] != '{' {
		return 0, false
	}
	type breakdown struct {
		ReasoningTokens json.RawMessage `json:"reasoning_tokens"`
	}
	var usage struct {
		CompletionDetails *breakdown `json:"completion_tokens_details"`
		OutputDetails     *breakdown `json:"output_tokens_details"`
	}
	// A type mismatch elsewhere in the object still fills the fields that do
	// match, so the error is deliberately ignored.
	_ = json.Unmarshal(detail, &usage)
	var raw json.RawMessage
	switch {
	case usage.CompletionDetails != nil && usage.CompletionDetails.ReasoningTokens != nil:
		raw = usage.CompletionDetails.ReasoningTokens
	case usage.OutputDetails != nil && usage.OutputDetails.ReasoningTokens != nil:
		raw = usage.OutputDetails.ReasoningTokens
	default:
		return 0, false
	}
	var reasoning int64
	if err := json.Unmarshal(raw, &reasoning); err != nil || bytes.Equal(bytes.TrimSpace(raw), []byte("null")) {
		return 0, false // present but not a count, such as null or a string
	}
	switch {
	case reasoning < 0:
		return 0, false
	case reasoning > completion:
		return completion, true
	}
	return reasoning, true
}

// TrackedStatuses are the HTTP error statuses counted individually. Other
// error statuses are counted as "other 4xx" or "other 5xx".
var TrackedStatuses = [...]int{400, 401, 403, 404, 408, 413, 422, 429, 499, 500, 502, 503, 504}

// Status bucket indexes after the tracked statuses.
const (
	StatusOther4xx = len(TrackedStatuses) + iota
	StatusOther5xx
	StatusBuckets // number of buckets in Agg.StatusCounts
)

// StatusBucket returns the index into Agg.StatusCounts for an error status,
// or -1 for a status below 400.
func StatusBucket(status int) int {
	if status < 400 {
		return -1
	}
	for i, tracked := range TrackedStatuses {
		if status == tracked {
			return i
		}
	}
	if status < 500 {
		return StatusOther4xx
	}
	return StatusOther5xx
}

// NearLimitFraction is the share of a model's context window at which a
// prompt counts as close to the limit.
const NearLimitFraction = 0.9

// Agg holds summed usage for one bucket. It holds only numbers and fixed-size
// arrays, so a copy is independent and Merge needs no allocation.
type Agg struct {
	Requests         int64 `json:"requests"`
	Errors           int64 `json:"errors"`
	ColdStarts       int64 `json:"cold_starts"`
	PromptTokens     int64 `json:"prompt_tokens"`
	CompletionTokens int64 `json:"completion_tokens"`
	ReasoningTokens  int64 `json:"reasoning_tokens"`
	// ReasoningReported counts requests whose runtime reported a thinking
	// count. Zero means "not reported", not "no thinking".
	ReasoningReported int64   `json:"reasoning_reported"`
	TotalTokens       int64   `json:"total_tokens"`
	GPUSeconds        float64 `json:"gpu_seconds"`
	LatencyMsSum      int64   `json:"-"`

	// StatusCounts counts errors by status, indexed by StatusBucket.
	StatusCounts [StatusBuckets]int64 `json:"-"`

	// Output-speed inputs: completion tokens and latency of successful
	// requests that produced output.
	SpeedCompletionTokens int64 `json:"-"`
	SpeedLatencyMs        int64 `json:"-"`

	// The prompt that used the largest share of its model's context window,
	// and how many prompts reached NearLimitFraction of the window. Records
	// without a known window are not counted.
	MaxPromptTokens  int64 `json:"-"`
	MaxPromptWindow  int64 `json:"-"`
	NearLimitPrompts int64 `json:"-"`
}

// Add folds one record into the bucket.
//
// The gateway sets cold_start only on scale-from-zero guard responses (status
// 503, zero latency and tokens). Those are attempts, not served requests
// (docs/LOGGING.md), so they count only as cold starts.
func (a *Agg) Add(rec Record) {
	if rec.ColdStart {
		a.ColdStarts++
		return
	}
	a.Requests++
	if bucket := StatusBucket(rec.Status); bucket >= 0 {
		a.Errors++
		a.StatusCounts[bucket]++
	}
	a.PromptTokens += rec.Tokens.Prompt
	a.CompletionTokens += rec.Tokens.Completion
	a.ReasoningTokens += rec.ReasoningTokens
	if rec.ReasoningReported {
		a.ReasoningReported++
	}
	total := rec.Tokens.Total
	if total == 0 {
		total = rec.Tokens.Prompt + rec.Tokens.Completion
	}
	a.TotalTokens += total
	a.GPUSeconds += rec.Derived.GPUSeconds
	a.LatencyMsSum += rec.LatencyMs
	if rec.Status < 400 && rec.Tokens.Completion > 0 && rec.LatencyMs > 0 {
		a.SpeedCompletionTokens += rec.Tokens.Completion
		a.SpeedLatencyMs += rec.LatencyMs
	}
	if rec.ContextWindow > 0 && rec.Tokens.Prompt > 0 {
		var nearLimit int64
		if float64(rec.Tokens.Prompt) >= NearLimitFraction*float64(rec.ContextWindow) {
			nearLimit = 1
		}
		a.notePrompt(rec.Tokens.Prompt, rec.ContextWindow, nearLimit)
	}
}

// notePrompt adds near-limit prompts and keeps the prompt with the larger
// share of its window. Shares are compared by cross-multiplying, so no
// rounding is involved.
func (a *Agg) notePrompt(prompt, window, nearLimit int64) {
	a.NearLimitPrompts += nearLimit
	if window <= 0 {
		return
	}
	if a.MaxPromptWindow == 0 || prompt*a.MaxPromptWindow > a.MaxPromptTokens*window {
		a.MaxPromptTokens, a.MaxPromptWindow = prompt, window
	}
}

// Merge adds another bucket into this one.
func (a *Agg) Merge(other *Agg) {
	a.Requests += other.Requests
	a.Errors += other.Errors
	a.ColdStarts += other.ColdStarts
	a.PromptTokens += other.PromptTokens
	a.CompletionTokens += other.CompletionTokens
	a.ReasoningTokens += other.ReasoningTokens
	a.ReasoningReported += other.ReasoningReported
	a.TotalTokens += other.TotalTokens
	a.GPUSeconds += other.GPUSeconds
	a.LatencyMsSum += other.LatencyMsSum
	for i := range a.StatusCounts {
		a.StatusCounts[i] += other.StatusCounts[i]
	}
	a.SpeedCompletionTokens += other.SpeedCompletionTokens
	a.SpeedLatencyMs += other.SpeedLatencyMs
	a.notePrompt(other.MaxPromptTokens, other.MaxPromptWindow, other.NearLimitPrompts)
}

// AvgLatencyMs is the mean latency of counted requests.
func (a *Agg) AvgLatencyMs() int64 {
	if a.Requests == 0 {
		return 0
	}
	return a.LatencyMsSum / a.Requests
}

// GPUHours is the GPU-time estimate in hours.
func (a *Agg) GPUHours() float64 { return a.GPUSeconds / 3600 }

// OutputTokensPerSecond is the observed output speed of successful requests
// that produced output, or 0 when there were none. Latency includes queueing
// and wake-up time, so this is not a benchmark of the model.
func (a *Agg) OutputTokensPerSecond() float64 {
	if a.SpeedLatencyMs <= 0 {
		return 0
	}
	return float64(a.SpeedCompletionTokens) * 1000 / float64(a.SpeedLatencyMs)
}

// MaxPromptPercent is the largest prompt's share of its context window in
// whole percent, or 0 when no request had a known window.
func (a *Agg) MaxPromptPercent() int64 {
	if a.MaxPromptWindow <= 0 {
		return 0
	}
	return a.MaxPromptTokens * 100 / a.MaxPromptWindow
}

// NearLimit reports whether the largest prompt reached NearLimitFraction of
// its context window.
func (a *Agg) NearLimit() bool {
	return a.MaxPromptWindow > 0 && float64(a.MaxPromptTokens) >= NearLimitFraction*float64(a.MaxPromptWindow)
}
