package history

import (
	"fmt"
	"strconv"

	"github.com/ualberta-rcg/aleph/usage-ui/internal/ledger"
)

// formatVersion is written into every line, so a later change to the file
// format can still read older files.
const formatVersion = 1

// line is one row of a daily summary file: one user's totals for one model
// and endpoint on one day. Every field of ledger.Agg is written out by name,
// so the saved days show exactly what the pages showed while the ledger
// still held them. TestLineKeepsEveryAggField fails if a new Agg field is
// not added here.
type line struct {
	Version  int    `json:"v"`
	Day      string `json:"day"`
	User     string `json:"user"`
	Model    string `json:"model"`
	Endpoint string `json:"endpoint"`

	Requests          int64   `json:"requests"`
	Errors            int64   `json:"errors"`
	ColdStarts        int64   `json:"cold_starts"`
	PromptTokens      int64   `json:"prompt_tokens"`
	CompletionTokens  int64   `json:"completion_tokens"`
	ReasoningTokens   int64   `json:"reasoning_tokens"`
	ReasoningReported int64   `json:"reasoning_reported"`
	TotalTokens       int64   `json:"total_tokens"`
	GPUSeconds        float64 `json:"gpu_seconds"`
	LatencyMsSum      int64   `json:"latency_ms_sum"`

	// Errors by status. Keys are status codes ("429") or "other_4xx" and
	// "other_5xx", rather than bucket positions, so the file stays readable
	// if the list of tracked statuses changes.
	StatusCounts map[string]int64 `json:"status_counts,omitempty"`

	SpeedCompletionTokens int64 `json:"speed_completion_tokens"`
	SpeedLatencyMs        int64 `json:"speed_latency_ms"`
	MaxPromptTokens       int64 `json:"max_prompt_tokens"`
	MaxPromptWindow       int64 `json:"max_prompt_window"`
	NearLimitPrompts      int64 `json:"near_limit_prompts"`
}

// statusKey names a status bucket in the file.
func statusKey(bucket int) string {
	switch bucket {
	case ledger.StatusOther4xx:
		return "other_4xx"
	case ledger.StatusOther5xx:
		return "other_5xx"
	default:
		return strconv.Itoa(ledger.TrackedStatuses[bucket])
	}
}

// statusBucket is the inverse of statusKey. A status code that is no longer
// tracked falls into its "other" bucket; any other key is an error.
func statusBucket(key string) (int, error) {
	switch key {
	case "other_4xx":
		return ledger.StatusOther4xx, nil
	case "other_5xx":
		return ledger.StatusOther5xx, nil
	}
	status, err := strconv.Atoi(key)
	if err != nil {
		return 0, fmt.Errorf("unknown status key %q", key)
	}
	if bucket := ledger.StatusBucket(status); bucket >= 0 {
		return bucket, nil
	}
	return 0, fmt.Errorf("status %d is not an error status", status)
}

func lineFromRow(user string, row ledger.Row) line {
	saved := line{
		Version: formatVersion, Day: row.Day, User: user, Model: row.Model, Endpoint: row.Endpoint,
		Requests: row.Requests, Errors: row.Errors, ColdStarts: row.ColdStarts,
		PromptTokens: row.PromptTokens, CompletionTokens: row.CompletionTokens,
		ReasoningTokens: row.ReasoningTokens, ReasoningReported: row.ReasoningReported,
		TotalTokens: row.TotalTokens, GPUSeconds: row.GPUSeconds, LatencyMsSum: row.LatencyMsSum,
		SpeedCompletionTokens: row.SpeedCompletionTokens, SpeedLatencyMs: row.SpeedLatencyMs,
		MaxPromptTokens: row.MaxPromptTokens, MaxPromptWindow: row.MaxPromptWindow,
		NearLimitPrompts: row.NearLimitPrompts,
	}
	for bucket, count := range row.StatusCounts {
		if count == 0 {
			continue
		}
		if saved.StatusCounts == nil {
			saved.StatusCounts = make(map[string]int64)
		}
		saved.StatusCounts[statusKey(bucket)] = count
	}
	return saved
}

func (saved line) row() (ledger.Row, error) {
	if saved.Version != formatVersion {
		return ledger.Row{}, fmt.Errorf("unsupported format version %d", saved.Version)
	}
	row := ledger.Row{Day: saved.Day, Model: saved.Model, Endpoint: saved.Endpoint, Agg: ledger.Agg{
		Requests: saved.Requests, Errors: saved.Errors, ColdStarts: saved.ColdStarts,
		PromptTokens: saved.PromptTokens, CompletionTokens: saved.CompletionTokens,
		ReasoningTokens: saved.ReasoningTokens, ReasoningReported: saved.ReasoningReported,
		TotalTokens: saved.TotalTokens, GPUSeconds: saved.GPUSeconds, LatencyMsSum: saved.LatencyMsSum,
		SpeedCompletionTokens: saved.SpeedCompletionTokens, SpeedLatencyMs: saved.SpeedLatencyMs,
		MaxPromptTokens: saved.MaxPromptTokens, MaxPromptWindow: saved.MaxPromptWindow,
		NearLimitPrompts: saved.NearLimitPrompts,
	}}
	for key, count := range saved.StatusCounts {
		bucket, err := statusBucket(key)
		if err != nil {
			return ledger.Row{}, err
		}
		row.StatusCounts[bucket] += count
	}
	return row, nil
}
