package source

import (
	"bytes"
	"encoding/json"
	"fmt"
	"strings"
	"time"
)

// Record is the subset of one gateway usage-ledger JSONL line used by the portal.
type Record struct {
	TS           string `json:"ts"`
	Identity     string `json:"identity"`
	IdentityType string `json:"identity_type"`
	Account      string `json:"account"`
	KeyFP        KeyFP  `json:"key_fp"`
	Endpoint     string `json:"endpoint"`
	API          string `json:"api"`
	Model        string `json:"model"`
	Status       int    `json:"status"`
	Stream       bool   `json:"stream"`
	ColdStart    bool   `json:"cold_start"`
	LatencyMs    int64  `json:"latency_ms"`
	Tokens       struct {
		Prompt     int64           `json:"prompt"`
		Completion int64           `json:"completion"`
		Total      int64           `json:"total"`
		Detail     json.RawMessage `json:"detail"`
	} `json:"tokens"`
	ContextWindow int64 `json:"context_window"`
	Derived       struct {
		GPUSeconds float64 `json:"gpu_seconds"`
	} `json:"derived"`

	ReasoningTokens   int64        `json:"-"`
	ReasoningReported bool         `json:"-"`
	EndpointKind      EndpointKind `json:"-"`
}

// Succeeded reports whether the request returned a 2xx HTTP status.
func (rec Record) Succeeded() bool { return rec.Status >= 200 && rec.Status < 300 }

// ParseRecord decodes one ledger JSONL line and its UTC timestamp.
func ParseRecord(line []byte) (Record, time.Time, error) {
	var rec Record
	if err := json.Unmarshal(line, &rec); err != nil {
		return rec, time.Time{}, err
	}
	ts, err := parseTimestamp(rec.TS)
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
	rec.Tokens.Detail = nil
	return rec, ts.UTC(), nil
}

func parseTimestamp(raw string) (time.Time, error) {
	if ts, err := time.Parse(TimeLayout, raw); err == nil {
		return ts, nil
	}
	if ts, err := time.Parse(time.RFC3339, raw); err == nil {
		return ts, nil
	}
	return time.Parse(time.RFC3339Nano, raw)
}

const (
	EndpointUnknown = "unknown"
	EndpointOther   = "other"
)

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

const (
	maxEndpointLength   = 64
	maxEndpointSegments = 5
)

// EndpointKind classifies a logged request path.
type EndpointKind int

const (
	EndpointUnnamed EndpointKind = iota
	EndpointKnown
	EndpointModelRoute
)

// NormalizeEndpoint maps a logged request path to its bounded reporting label.
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
			if !((char >= 'a' && char <= 'z') || (char >= '0' && char <= '9') || char == '-' || char == '_') {
				return false
			}
		}
	}
	return true
}

// reasoningTokens extracts thinking tokens from tokens.detail. Reasoning tokens
// are a subset of completion_tokens (never added to total_tokens).
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
		return 0, false
	}
	switch {
	case reasoning < 0:
		return 0, false
	case reasoning > completion:
		return completion, true
	}
	return reasoning, true
}

// TrackedStatuses are the HTTP error statuses counted individually.
var TrackedStatuses = [...]int{400, 401, 403, 404, 408, 413, 422, 429, 499, 500, 502, 503, 504}

const (
	StatusOther4xx = len(TrackedStatuses) + iota
	StatusOther5xx
	StatusBuckets
)

// StatusBucket returns the index into Agg.StatusCounts for an error status, or -1.
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

// NearLimitFraction is the context-window share at which a prompt is flagged.
const NearLimitFraction = 0.9

// Agg holds summed usage for one bucket.
type Agg struct {
	Requests          int64   `json:"requests"`
	Errors            int64   `json:"errors"`
	ColdStarts        int64   `json:"cold_starts"`
	PromptTokens      int64   `json:"prompt_tokens"`
	CompletionTokens  int64   `json:"completion_tokens"`
	ReasoningTokens   int64   `json:"reasoning_tokens"`
	ReasoningReported int64   `json:"reasoning_reported"`
	TotalTokens       int64   `json:"total_tokens"`
	GPUSeconds        float64 `json:"gpu_seconds"`
	LatencyMsSum      int64   `json:"-"`

	StatusCounts [StatusBuckets]int64 `json:"-"`

	SpeedCompletionTokens int64 `json:"-"`
	SpeedLatencyMs        int64 `json:"-"`

	MaxPromptTokens  int64 `json:"-"`
	MaxPromptWindow  int64 `json:"-"`
	NearLimitPrompts int64 `json:"-"`
}

// Add folds one record into the bucket. Scale-from-zero guard responses
// (status=503, cold_start=true, latency_ms=0 — emitted on both pod wake-up and
// insufficient_capacity refusal in gateway.py) are counted separately under
// ColdStarts rather than served Requests.
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

func (a *Agg) notePrompt(prompt, window, nearLimit int64) {
	a.NearLimitPrompts += nearLimit
	if window <= 0 {
		return
	}
	if a.MaxPromptWindow == 0 || prompt*a.MaxPromptWindow > a.MaxPromptTokens*window {
		a.MaxPromptTokens, a.MaxPromptWindow = prompt, window
	}
}

// Merge folds another Agg into this one.
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

// GPUHours returns estimated GPU-hours (allocated GPUs × request duration).
func (a *Agg) GPUHours() float64 { return a.GPUSeconds / 3600 }

// OutputTokensPerSecond returns observed output tokens/s for successful answers.
func (a *Agg) OutputTokensPerSecond() float64 {
	if a.SpeedLatencyMs <= 0 {
		return 0
	}
	return float64(a.SpeedCompletionTokens) * 1000 / float64(a.SpeedLatencyMs)
}

// MaxPromptPercent returns the largest prompt's context-window percentage.
func (a *Agg) MaxPromptPercent() int64 {
	if a.MaxPromptWindow <= 0 {
		return 0
	}
	return a.MaxPromptTokens * 100 / a.MaxPromptWindow
}

// NearLimit reports whether the largest prompt reached NearLimitFraction.
func (a *Agg) NearLimit() bool {
	return a.MaxPromptWindow > 0 && float64(a.MaxPromptTokens) >= NearLimitFraction*float64(a.MaxPromptWindow)
}
