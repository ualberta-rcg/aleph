package fake

import (
	"context"
	"encoding/json"
	"os"
	"path/filepath"
	"strings"
	"testing"
	"time"

	"github.com/ualberta-rcg/aleph/usage-ui/internal/ledger"
)

// Every generated record is one the reader accepts, so the demo shows every
// generated request.
func TestGeneratedLedgerIsReadWithoutSkippingALine(t *testing.T) {
	root := t.TempDir()
	end := time.Date(2026, 11, 16, 0, 0, 0, 0, time.UTC)
	written, err := Generate(Options{Out: root, Users: []string{"alice", "bob"}, Days: 7, End: end, PerDay: 10, LivePods: 2, Retired: 1, Seed: 7})
	if err != nil {
		t.Fatal(err)
	}
	src := ledger.NewFileSource(root, 0)
	read, err := src.Refresh()
	if err != nil {
		t.Fatal(err)
	}
	if written == 0 || read != written || src.Skipped() != 0 {
		t.Errorf("wrote %d records, read %d, skipped %d; want a non-zero count read in full", written, read, src.Skipped())
	}
}

// generatedByModel generates two weeks for eight users and totals every
// user's usage by model and endpoint.
func generatedByModel(t *testing.T) (byModel map[string]*ledger.Agg, endpoints map[string]bool) {
	t.Helper()
	root := t.TempDir()
	end := time.Date(2026, 11, 16, 0, 0, 0, 0, time.UTC)
	users := []string{"u1", "u2", "u3", "u4", "u5", "u6", "u7", "u8"}
	if _, err := Generate(Options{Out: root, Users: users, Days: 14, End: end, PerDay: 60, LivePods: 2, Retired: 1, Seed: 3}); err != nil {
		t.Fatal(err)
	}
	src := ledger.NewFileSource(root, 0)
	if _, err := src.Refresh(); err != nil {
		t.Fatal(err)
	}
	byModel = map[string]*ledger.Agg{}
	endpoints = map[string]bool{}
	for _, user := range users {
		report, err := src.Usage(context.Background(), user, end.AddDate(0, 0, -13), end)
		if err != nil {
			t.Fatal(err)
		}
		for _, row := range report.Rows {
			if byModel[row.Model] == nil {
				byModel[row.Model] = &ledger.Agg{}
			}
			byModel[row.Model].Merge(&row.Agg)
			endpoints[row.Endpoint] = true
		}
	}
	return byModel, endpoints
}

// As checked on the live platform, gpt-oss-120b sends no thinking count.
func TestGeneratedGPTOSSNeverReportsThinking(t *testing.T) {
	byModel, _ := generatedByModel(t)
	if gptOSS := byModel["gpt-oss-120b"]; gptOSS == nil || gptOSS.Requests == 0 || gptOSS.ReasoningReported != 0 {
		t.Errorf("gpt-oss-120b should have requests and never report thinking: %+v", gptOSS)
	}
}

func TestGeneratedQwenReportsThinking(t *testing.T) {
	byModel, _ := generatedByModel(t)
	if qwen := byModel["qwen38-27b"]; qwen == nil || qwen.ReasoningReported == 0 || qwen.ReasoningTokens == 0 {
		t.Errorf("qwen38-27b should report thinking: %+v", qwen)
	}
}

func TestGeneratedChatUseIsInputHeavy(t *testing.T) {
	byModel, _ := generatedByModel(t)
	qwen := byModel["qwen38-27b"]
	if qwen == nil || qwen.PromptTokens < 5*qwen.CompletionTokens {
		t.Errorf("chat use should have at least 5 input tokens per output token: %+v", qwen)
	}
}

func TestGeneratedUsageCoversChatMessagesAndEmbeddings(t *testing.T) {
	_, endpoints := generatedByModel(t)
	for _, endpoint := range []string{"/v1/chat/completions", "/v1/messages", "/v1/embeddings"} {
		if !endpoints[endpoint] {
			t.Errorf("no %s records generated", endpoint)
		}
	}
}

func TestGeneratedPromptsFitTheirContextWindow(t *testing.T) {
	byModel, _ := generatedByModel(t)
	for model, agg := range byModel {
		if agg.MaxPromptWindow > 0 && agg.MaxPromptTokens > agg.MaxPromptWindow {
			t.Errorf("%s: a %d-token prompt exceeds its %d-token window", model, agg.MaxPromptTokens, agg.MaxPromptWindow)
		}
	}
}

func TestGeneratedUsageIncludesSomeErrors(t *testing.T) {
	byModel, _ := generatedByModel(t)
	var errors int64
	for _, agg := range byModel {
		errors += agg.Errors
	}
	if errors == 0 {
		t.Error("expected a few failed requests for the Errors page")
	}
}

// The default demo layout matches a long-running site: retired pods from an
// earlier rollout that never reached their deletion point, and live pods
// that rotated past it and so lost their oldest records. The ledger reader
// must then report complete coverage only from after the rollout.
func TestGeneratedLayoutHasRetiredPodsAndLivePodsThatRotatedPastDeletion(t *testing.T) {
	root := t.TempDir()
	end := time.Date(2026, 11, 16, 12, 0, 0, 0, time.UTC)
	start := end.AddDate(0, 0, -21)
	rollout := start.Add(end.Sub(start) / 3)
	const backups = 3
	written, err := Generate(Options{
		Out: root, Users: []string{"alice", "bob", "carol"}, Days: 21, End: end, PerDay: 30,
		LivePods: 3, Retired: 2, Seed: 1, MaxFileBytes: 256 << 10, Backups: backups,
	})
	if err != nil {
		t.Fatal(err)
	}

	entries, err := os.ReadDir(root)
	if err != nil {
		t.Fatal(err)
	}
	live, retired := 0, 0
	for _, entry := range entries {
		lastBackup := filepath.Join(root, entry.Name(), "usage.log.4")
		if _, err := os.Stat(lastBackup); err == nil {
			t.Errorf("%s: kept more than %d rotated files", entry.Name(), backups)
		}
		_, statErr := os.Stat(filepath.Join(root, entry.Name(), "usage.log.3"))
		switch {
		case strings.Contains(entry.Name(), "-live"):
			live++
			if statErr != nil {
				t.Errorf("%s: a busy live pod should have rotated to usage.log.3", entry.Name())
			}
		case strings.Contains(entry.Name(), "-old"):
			retired++
			if statErr == nil {
				t.Errorf("%s: the retired pods should not have reached the deletion point", entry.Name())
			}
		}
	}
	if live != 3 || retired != 2 {
		t.Fatalf("want 3 live and 2 retired pod directories, got %d and %d", live, retired)
	}

	src := ledger.NewFileSource(root, backups)
	read, err := src.Refresh()
	if err != nil {
		t.Fatal(err)
	}
	if read != written {
		t.Fatalf("Generate reported %d records on disk, the reader found %d", written, read)
	}
	report, _ := src.Usage(context.Background(), "alice", start, end)
	if report.Oldest.Before(start) || report.Oldest.After(start.Add(24*time.Hour)) {
		t.Errorf("oldest record %v should be on the first day, from %v", report.Oldest, start)
	}
	if !report.CompleteFrom.After(rollout) || !report.CompleteFrom.Before(end) {
		t.Errorf("complete from %v should fall after the rollout at %v and before %v", report.CompleteFrom, rollout, end)
	}

	// Without the backup count, the reader may understate coverage but
	// never overstate it.
	unknown := ledger.NewFileSource(root, 0)
	if _, err := unknown.Refresh(); err != nil {
		t.Fatal(err)
	}
	cautious, _ := unknown.Usage(context.Background(), "alice", start, end)
	if cautious.CompleteFrom.Before(report.CompleteFrom) {
		t.Errorf("with backups unknown, complete from %v is earlier than the exact %v", cautious.CompleteFrom, report.CompleteFrom)
	}
}

// The ledger's api field follows the client-facing API: Anthropic-style for
// /v1/messages, whose tokens.detail is still the OpenAI-shaped usage object
// the gateway receives from the upstream.
func TestGeneratedMessagesRecordsAreLoggedAsAnthropicWithOpenAIUsage(t *testing.T) {
	root := t.TempDir()
	end := time.Date(2026, 11, 16, 0, 0, 0, 0, time.UTC)
	if _, err := Generate(Options{Out: root, Users: []string{"u1", "u2", "u3"}, Days: 7, End: end, PerDay: 60, LivePods: 1, Seed: 5}); err != nil {
		t.Fatal(err)
	}
	content, err := os.ReadFile(filepath.Join(root, "model-gateway-5c4b7d9f8-live00", "usage.log"))
	if err != nil {
		t.Fatal(err)
	}
	messages := 0
	for _, text := range strings.Split(strings.TrimSpace(string(content)), "\n") {
		var entry struct {
			Endpoint string `json:"endpoint"`
			API      string `json:"api"`
			Status   int    `json:"status"`
			Tokens   struct {
				Detail map[string]any `json:"detail"`
			} `json:"tokens"`
		}
		if err := json.Unmarshal([]byte(text), &entry); err != nil {
			t.Fatal(err)
		}
		if entry.Endpoint != "/v1/messages" {
			continue
		}
		messages++
		if entry.API != "anthropic" {
			t.Errorf("/v1/messages logged with api %q, want anthropic", entry.API)
		}
		if _, ok := entry.Tokens.Detail["completion_tokens"]; entry.Status == 200 && !ok {
			t.Errorf("/v1/messages detail should be OpenAI-shaped: %v", entry.Tokens.Detail)
		}
	}
	if messages == 0 {
		t.Fatal("no /v1/messages records generated")
	}
}
