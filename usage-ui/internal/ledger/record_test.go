package ledger

import (
	"context"
	"fmt"
	"path/filepath"
	"reflect"
	"strings"
	"testing"
)

func parse(t *testing.T, line string) Record {
	t.Helper()
	rec, _, err := ParseRecord([]byte(line))
	if err != nil {
		t.Fatalf("parse %s: %v", line, err)
	}
	return rec
}

// detailed builds a ledger line with a chosen endpoint, status, latency,
// context window, and raw tokens.detail value.
func detailed(identity, model, endpoint string, status, latencyMs, prompt, completion, contextWindow int, detail string) string {
	return fmt.Sprintf(`{"ts":"2026-11-03T10:00:00Z","identity":%q,"identity_type":"user","endpoint":%q,"model":%q,"status":%d,"cold_start":false,"latency_ms":%d,"tokens":{"prompt":%d,"completion":%d,"total":%d,"detail":%s},"context_window":%d,"derived":{"gpu_seconds":1}}`,
		identity, endpoint, model, status, latencyMs, prompt, completion, prompt+completion, detail, contextWindow)
}

// Thinking tokens come from the usage detail the runtime sent. Each case
// has 100 completion tokens.
func TestReasoningTokensAreReadFromTheUsageDetail(t *testing.T) {
	cases := []struct {
		name     string
		detail   string
		want     int64
		reported bool
	}{
		{"chat completions style", `{"completion_tokens":100,"completion_tokens_details":{"reasoning_tokens":40}}`, 40, true},
		{"responses style", `{"output_tokens_details":{"reasoning_tokens":25}}`, 25, true},
		{"no breakdown is not reported", `{"prompt_tokens":5,"completion_tokens_details":null}`, 0, false},
		{"null detail is not reported", `null`, 0, false},
		{"empty detail is not reported", `{}`, 0, false},
		{"a count of the wrong type is not reported", `{"completion_tokens_details":{"reasoning_tokens":"many"}}`, 0, false},
		{"a wrong type elsewhere is ignored", `{"prompt_tokens_details":"odd","completion_tokens_details":{"reasoning_tokens":7}}`, 7, true},
		{"detail that is not an object is not reported", `[1,2]`, 0, false},
		{"a count above the completion tokens is capped at them", `{"completion_tokens_details":{"reasoning_tokens":500}}`, 100, true},
		{"a negative count is not reported", `{"completion_tokens_details":{"reasoning_tokens":-3}}`, 0, false},
		{"a reported zero is reported", `{"completion_tokens_details":{"reasoning_tokens":0}}`, 0, true},
		{"a null count is not reported", `{"completion_tokens_details":{"reasoning_tokens":null}}`, 0, false},
		{"details without the field (gpt-oss) are not reported", `{"completion_tokens_details":{"accepted_prediction_tokens":0}}`, 0, false},
	}
	for _, tc := range cases {
		t.Run(tc.name, func(t *testing.T) {
			rec := parse(t, detailed("alice", "m", "/v1/chat/completions", 200, 1000, 10, 100, 0, tc.detail))
			if rec.ReasoningTokens != tc.want || rec.ReasoningReported != tc.reported {
				t.Errorf("reasoning = %d reported %v, want %d reported %v", rec.ReasoningTokens, rec.ReasoningReported, tc.want, tc.reported)
			}
		})
	}
}

// The raw detail is decoded once and not kept in every record.
func TestRawUsageDetailIsDroppedAfterDecoding(t *testing.T) {
	rec := parse(t, detailed("alice", "m", "/v1/chat/completions", 200, 1000, 10, 100, 0, `{"completion_tokens_details":{"reasoning_tokens":40}}`))
	if rec.Tokens.Detail != nil {
		t.Errorf("raw detail kept: %s", rec.Tokens.Detail)
	}
}

func TestRecordWithoutUsageDetailOrEndpointParses(t *testing.T) {
	rec := parse(t, `{"ts":"2026-11-03T10:00:00Z","identity":"alice","identity_type":"user","model":"m","status":200,"tokens":{"prompt":1,"completion":2,"total":3}}`)
	if rec.ReasoningTokens != 0 || rec.ReasoningReported || rec.Endpoint != EndpointUnknown {
		t.Errorf("reasoning %d reported %v endpoint %q, want 0, false, %q", rec.ReasoningTokens, rec.ReasoningReported, rec.Endpoint, EndpointUnknown)
	}
}

func TestEachErrorStatusHasItsBucket(t *testing.T) {
	for status, want := range map[int]int{
		200: -1, 399: -1, 400: 0, 429: 7, 499: 8, 500: 9, 503: 11, 504: 12,
		418: StatusOther4xx, 498: StatusOther4xx, 501: StatusOther5xx, 599: StatusOther5xx,
	} {
		if got := StatusBucket(status); got != want {
			t.Errorf("StatusBucket(%d) = %d, want %d", status, got, want)
		}
	}
}

func statusAgg(t *testing.T, statuses ...int) Agg {
	t.Helper()
	var agg Agg
	for _, status := range statuses {
		agg.Add(parse(t, detailed("alice", "m", "/v1/chat/completions", status, 100, 1, 1, 0, `{}`)))
	}
	return agg
}

func TestFailedRequestsAreCountedByStatus(t *testing.T) {
	agg := statusAgg(t, 200, 429, 429, 500, 418)
	var want [StatusBuckets]int64
	want[StatusBucket(429)] = 2
	want[StatusBucket(500)] = 1
	want[StatusOther4xx] = 1
	if agg.Requests != 5 || agg.Errors != 4 || agg.StatusCounts != want {
		t.Errorf("requests %d, errors %d, by status %v; want 5, 4, %v", agg.Requests, agg.Errors, agg.StatusCounts, want)
	}
}

// Merge adds every status bucket, and a copy of an Agg is independent of
// the original.
func TestMergeAddsStatusCountsWithoutChangingTheOriginal(t *testing.T) {
	agg := statusAgg(t, 429, 429)
	copied := agg
	copied.Merge(&agg)
	if got := copied.StatusCounts[StatusBucket(429)]; got != 4 {
		t.Errorf("merged 429 count = %d, want 4", got)
	}
	if got := agg.StatusCounts[StatusBucket(429)]; got != 2 {
		t.Errorf("original 429 count = %d after merging into a copy, want 2", got)
	}
}

// 500 tokens in 5 seconds of successful requests that produced output; the
// failed request and the one without output are left out.
func TestOutputSpeedUsesOnlySuccessfulRequestsWithOutput(t *testing.T) {
	var agg Agg
	agg.Add(parse(t, detailed("alice", "m", "/v1/chat/completions", 200, 2000, 10, 100, 0, `{}`)))
	agg.Add(parse(t, detailed("alice", "m", "/v1/chat/completions", 200, 3000, 10, 400, 0, `{}`)))
	agg.Add(parse(t, detailed("alice", "m", "/v1/chat/completions", 500, 9000, 10, 900, 0, `{}`)))
	agg.Add(parse(t, detailed("alice", "m", "/v1/embeddings", 200, 9000, 10, 0, 0, `{}`)))
	if agg.SpeedCompletionTokens != 500 || agg.SpeedLatencyMs != 5000 {
		t.Errorf("speed sums %d tokens / %d ms, want 500 / 5000", agg.SpeedCompletionTokens, agg.SpeedLatencyMs)
	}
	if got := agg.OutputTokensPerSecond(); got != 100 {
		t.Errorf("speed = %v tokens/s, want 100", got)
	}
}

func TestOutputSpeedWithoutRequestsIsZero(t *testing.T) {
	var empty Agg
	if got := empty.OutputTokensPerSecond(); got != 0 {
		t.Errorf("speed = %v, want 0", got)
	}
}

// smallWindow has a prompt at 91.8% of a 512-token window and one at 19%.
// largeWindow has one at 76% of 131,072 and one with no window.
func contextAggs(t *testing.T) (smallWindow, largeWindow Agg) {
	t.Helper()
	smallWindow.Add(parse(t, detailed("alice", "m", "/v1/chat/completions", 200, 100, 470, 1, 512, `{}`)))
	smallWindow.Add(parse(t, detailed("alice", "m", "/v1/chat/completions", 200, 100, 100, 1, 512, `{}`)))
	largeWindow.Add(parse(t, detailed("alice", "m", "/v1/chat/completions", 200, 100, 100000, 1, 131072, `{}`)))
	largeWindow.Add(parse(t, detailed("alice", "m", "/v1/chat/completions", 200, 100, 5000, 1, 0, `{}`)))
	return smallWindow, largeWindow
}

func TestPromptAtNinetyPercentOfItsWindowIsNearTheLimit(t *testing.T) {
	small, _ := contextAggs(t)
	if small.MaxPromptTokens != 470 || small.MaxPromptWindow != 512 || small.NearLimitPrompts != 1 || !small.NearLimit() {
		t.Errorf("largest prompt %d of %d, %d near the limit, near %v; want 470 of 512, 1, true",
			small.MaxPromptTokens, small.MaxPromptWindow, small.NearLimitPrompts, small.NearLimit())
	}
}

func TestLargePromptInALargeWindowIsNotNearTheLimit(t *testing.T) {
	_, large := contextAggs(t)
	if large.MaxPromptPercent() != 76 || large.NearLimit() || large.NearLimitPrompts != 0 {
		t.Errorf("%d%%, near %v, %d near; want 76%%, false, 0", large.MaxPromptPercent(), large.NearLimit(), large.NearLimitPrompts)
	}
}

// The merged largest prompt is the largest share of its window, not the
// most tokens, in either merge order.
func TestMergeKeepsTheLargestShareOfWindowInEitherOrder(t *testing.T) {
	small, large := contextAggs(t)
	for _, order := range [][2]*Agg{{&small, &large}, {&large, &small}} {
		var merged Agg
		merged.Merge(order[0])
		merged.Merge(order[1])
		if merged.MaxPromptTokens != 470 || merged.MaxPromptPercent() != 91 || merged.NearLimitPrompts != 1 {
			t.Errorf("merged: %d tokens, %d%%, %d near; want 470, 91%%, 1", merged.MaxPromptTokens, merged.MaxPromptPercent(), merged.NearLimitPrompts)
		}
	}
}

func TestNoContextWindowReportsNoContextPressure(t *testing.T) {
	var none Agg
	if none.MaxPromptPercent() != 0 || none.NearLimit() {
		t.Errorf("%d%%, near %v; want 0%%, false", none.MaxPromptPercent(), none.NearLimit())
	}
}

// endpointRow is the part of a report row the endpoint tests check.
type endpointRow struct {
	Model, Endpoint                    string
	Requests, Errors                   int64
	ReasoningTokens, ReasoningReported int64
}

func endpointRows(t *testing.T, lines []string, user string) []endpointRow {
	t.Helper()
	root := t.TempDir()
	write(t, filepath.Join(root, "pod", "usage.log"), strings.Join(lines, "\n")+"\n")
	src := NewFileSource(root, 0)
	mustRefresh(t, src)
	report, err := src.Usage(context.Background(), user, day1, day9)
	if err != nil {
		t.Fatal(err)
	}
	out := []endpointRow{}
	for _, row := range report.Rows {
		out = append(out, endpointRow{row.Model, row.Endpoint, row.Requests, row.Errors, row.ReasoningTokens, row.ReasoningReported})
	}
	return out
}

func TestRowsAreSplitByEndpointWithTheirOwnThinkingTotals(t *testing.T) {
	got := endpointRows(t, []string{
		detailed("alice", "qwen", "/v1/chat/completions", 200, 1000, 10, 100, 0, `{"completion_tokens_details":{"reasoning_tokens":30}}`),
		detailed("alice", "qwen", "/v1/messages", 200, 1000, 10, 50, 0, `{"completion_tokens_details":{"reasoning_tokens":20}}`),
		detailed("alice", "qwen", "/v1/chat/completions", 200, 1000, 10, 10, 0, `{}`),
		detailed("bob", "qwen", "/v1/messages", 200, 1000, 10, 10, 0, `{}`),
	}, "alice")
	want := []endpointRow{
		{"qwen", "/v1/chat/completions", 2, 0, 30, 1},
		{"qwen", "/v1/messages", 1, 0, 20, 1},
	}
	if !reflect.DeepEqual(got, want) {
		t.Errorf("rows:\n got %+v\nwant %+v", got, want)
	}
}

// Endpoints come from the request path, which a client controls through the
// gateway's catch-all route. Known endpoints keep their name; a short, plain
// path is a candidate model route; anything else is "other".
func TestNormalizeEndpointNamesOnlyKnownAndPlainPaths(t *testing.T) {
	type outcome struct {
		label string
		kind  EndpointKind
	}
	for _, test := range []struct {
		path string
		want outcome
	}{
		{"/v1/chat/completions", outcome{"/v1/chat/completions", EndpointKnown}},
		{"/v1/messages/count_tokens", outcome{"/v1/messages/count_tokens", EndpointKnown}},
		{"/v1/embeddings/", outcome{"/v1/embeddings", EndpointKnown}},
		{"/v1/tasks/3f2a9c01/result", outcome{"/v1/tasks", EndpointKnown}},
		{"/v1/science/predict", outcome{"/v1/science/predict", EndpointModelRoute}},
		{"/v1/biology/ipd/rfdiffusion/generate", outcome{"/v1/biology/ipd/rfdiffusion/generate", EndpointModelRoute}},
		{"/V1/CHAT/COMPLETIONS", outcome{EndpointOther, EndpointUnnamed}},
		{"/v1/a/b/c/d/e/f", outcome{EndpointOther, EndpointUnnamed}},
		{"/v1/" + strings.Repeat("a", 5000), outcome{EndpointOther, EndpointUnnamed}},
		{"/v1/science/predict?x=1", outcome{EndpointOther, EndpointUnnamed}},
		{"", outcome{EndpointUnknown, EndpointUnnamed}},
	} {
		label, kind := NormalizeEndpoint(test.path)
		if got := (outcome{label, kind}); got != test.want {
			t.Errorf("NormalizeEndpoint(%.40q) = %+v, want %+v", test.path, got, test.want)
		}
	}
}

// A candidate model route is named after a request to it succeeds; a
// failure to a route never seen to succeed is "other". Known routes keep
// their name whatever the status.
func TestModelRouteIsNamedOnlyOnceARequestToItSucceeds(t *testing.T) {
	got := endpointRows(t, []string{
		detailed("alice", "m", "/v1/chat/completions", 500, 100, 1, 1, 0, `{}`),
		detailed("alice", "m", "/v1/made-up-path-0001", 404, 100, 1, 1, 0, `{}`),
		detailed("alice", "m", "/v1/science/predict", 200, 100, 1, 1, 0, `{}`),
	}, "alice")
	want := []endpointRow{
		{"m", "/v1/chat/completions", 1, 1, 0, 0},
		{"m", "/v1/science/predict", 1, 0, 0, 0},
		{"m", EndpointOther, 1, 1, 0, 0},
	}
	if !reflect.DeepEqual(got, want) {
		t.Errorf("rows:\n got %+v\nwant %+v", got, want)
	}
}

// A failed request to a model route that has already succeeded is counted
// under that route, so the route's error count is right.
func TestFailedRequestToAKnownModelRouteCountsUnderThatRoute(t *testing.T) {
	got := endpointRows(t, []string{
		detailed("alice", "m", "/v1/science/predict", 200, 100, 1, 1, 0, `{}`),
		detailed("alice", "m", "/v1/science/predict", 500, 100, 1, 1, 0, `{}`),
		detailed("alice", "m", "/v1/science/predict/", 422, 100, 1, 1, 0, `{}`),
	}, "alice")
	if want := []endpointRow{{"m", "/v1/science/predict", 3, 2, 0, 0}}; !reflect.DeepEqual(got, want) {
		t.Errorf("rows:\n got %+v\nwant %+v", got, want)
	}
}

// However many distinct failing paths a user sends, they make one bucket.
func TestInventedFailingPathsShareOneBucket(t *testing.T) {
	var lines []string
	for index := 0; index < 50; index++ {
		lines = append(lines, detailed("alice", "m", fmt.Sprintf("/v1/invented-%d", index), 404, 100, 1, 1, 0, `{}`))
	}
	if got, want := endpointRows(t, lines, "alice"), []endpointRow{{"m", EndpointOther, 50, 50, 0, 0}}; !reflect.DeepEqual(got, want) {
		t.Errorf("rows:\n got %+v\nwant %+v", got, want)
	}
}

// Even if a backend answered arbitrary paths with success, only the first
// maxModelEndpoints distinct model routes are named; the rest are "other".
func TestModelEndpointsAreCapped(t *testing.T) {
	const extra = 10
	var lines []string
	named := map[string]bool{}
	for index := 0; index < maxModelEndpoints+extra; index++ {
		route := fmt.Sprintf("/v1/route-%d", index)
		lines = append(lines, detailed("alice", "m", route, 200, 100, 1, 1, 0, `{}`))
		if index < maxModelEndpoints {
			named[route] = true
		}
	}
	got := endpointRows(t, lines, "alice")
	gotNamed := map[string]bool{}
	var other *endpointRow
	for index, row := range got {
		if row.Endpoint == EndpointOther {
			other = &got[index]
			continue
		}
		if row.Requests != 1 {
			t.Errorf("%s has %d requests, want 1", row.Endpoint, row.Requests)
		}
		gotNamed[row.Endpoint] = true
	}
	if !reflect.DeepEqual(gotNamed, named) {
		t.Errorf("named %d routes, want the first %d (route-0 to route-%d)", len(gotNamed), maxModelEndpoints, maxModelEndpoints-1)
	}
	if other == nil || other.Requests != extra {
		t.Errorf("%q row = %+v, want %d requests past the cap", EndpointOther, other, extra)
	}
}
