package source

import (
	"context"
	"crypto/sha256"
	"encoding/hex"
	"encoding/json"
	"errors"
	"os"
	"path/filepath"
	"sync"
	"testing"
	"time"
)

func TestComputeKeyFPParity(t *testing.T) {
	raw := "eyJvcmciOiJvcmdpZCIsImlkIjoiYWJjZGVmMTIzNDU2Nzg5MCJ9"
	sum := sha256.Sum256([]byte(raw))
	hexDigest := hex.EncodeToString(sum[:])
	want := KeyFP{
		SHA256_8: hexDigest[len(hexDigest)-8:],
		Last4:    raw[len(raw)-4:],
	}
	got := ComputeKeyFP(raw)
	if got != want {
		t.Fatalf("ComputeKeyFP(%q) = %+v, want %+v", raw, got, want)
	}
	if !got.Valid() {
		t.Fatalf("expected valid KeyFP: %+v", got)
	}

	short := ComputeKeyFP("xyz")
	if short.Last4 != "xyz" || !short.Valid() {
		t.Fatalf("short key ComputeKeyFP = %+v", short)
	}

	// Null or legacy string key_fp must never break record parsing.
	for _, rawJSON := range []string{`null`, `"legacy123456"`, `{}`} {
		var fp KeyFP
		if err := json.Unmarshal([]byte(rawJSON), &fp); err != nil {
			t.Fatalf("Unmarshal(%s) unexpected error: %v", rawJSON, err)
		}
		if fp.Valid() {
			t.Fatalf("Unmarshal(%s) expected empty/invalid KeyFP, got %+v", rawJSON, fp)
		}
	}
}

func TestIdentityValidators(t *testing.T) {
	validLedger := []string{"alice", "Kevin", "holland-college-pei", "user.name@ualberta.ca", "a", "user_01"}
	for _, id := range validLedger {
		if !ValidLedgerIdentity(id) {
			t.Errorf("ValidLedgerIdentity(%q) = false, want true", id)
		}
	}
	invalidLedger := []string{"", "-flag", ".dot", "../etc", "has space", "bad/slash", "unicode-é", string(make([]byte, 65))}
	for _, id := range invalidLedger {
		if ValidLedgerIdentity(id) {
			t.Errorf("ValidLedgerIdentity(%q) = true, want false", id)
		}
	}
	if !ValidPOSIXUsername("alice_01") || ValidPOSIXUsername("Kevin") || ValidPOSIXUsername("alice@ualberta.ca") {
		t.Errorf("ValidPOSIXUsername rules mismatch")
	}
}

func TestParseRecordReasoningAndColdStart(t *testing.T) {
	line := `{"ts":"2026-11-18T14:22:09Z","site":"aleph","identity":"alice","identity_type":"user","account":"def-pi","key_fp":{"sha256_8":"a1b2c3d4","last4":"9f8e"},"endpoint":"/v1/chat/completions","api":"openai","model":"qwen38-27b","status":200,"stream":true,"cold_start":false,"latency_ms":2000,"tokens":{"prompt":100,"completion":300,"total":400,"detail":{"completion_tokens_details":{"reasoning_tokens":220}}},"context_window":524288,"derived":{"gpu_seconds":4.0}}`
	rec, ts, err := ParseRecord([]byte(line))
	if err != nil {
		t.Fatalf("ParseRecord failed: %v", err)
	}
	if ts.Format(TimeLayout) != "2026-11-18T14:22:09Z" {
		t.Fatalf("ts = %s", ts)
	}
	if rec.KeyFP.SHA256_8 != "a1b2c3d4" || rec.KeyFP.Last4 != "9f8e" {
		t.Fatalf("KeyFP = %+v", rec.KeyFP)
	}
	var agg Agg
	agg.Add(rec)
	// Reasoning tokens are a breakdown of completion_tokens, never added to TotalTokens.
	if agg.TotalTokens != 400 || agg.CompletionTokens != 300 || agg.ReasoningTokens != 220 || agg.ReasoningReported != 1 {
		t.Fatalf("unexpected token aggregation: %+v", agg)
	}

	coldLine := `{"ts":"2026-11-18T14:23:00Z","identity":"alice","identity_type":"user","endpoint":"/v1/tasks/task-123/result","model":"glm-ocr","status":503,"cold_start":true,"latency_ms":0,"tokens":{"prompt":0,"completion":0,"total":0},"derived":{"gpu_seconds":0}}`
	coldRec, _, err := ParseRecord([]byte(coldLine))
	if err != nil {
		t.Fatalf("ParseRecord cold failed: %v", err)
	}
	if coldRec.Endpoint != "/v1/tasks" {
		t.Fatalf("expected /v1/tasks normalization, got %q", coldRec.Endpoint)
	}
	agg.Add(coldRec)
	if agg.ColdStarts != 1 || agg.Requests != 1 || agg.Errors != 0 {
		t.Fatalf("cold start should increment ColdStarts only: %+v", agg)
	}
}

func writeJSONL(t *testing.T, path string, lines []map[string]any) {
	t.Helper()
	if err := os.MkdirAll(filepath.Dir(path), 0o755); err != nil {
		t.Fatal(err)
	}
	f, err := os.Create(path)
	if err != nil {
		t.Fatal(err)
	}
	defer f.Close()
	enc := json.NewEncoder(f)
	for _, rec := range lines {
		if err := enc.Encode(rec); err != nil {
			t.Fatal(err)
		}
	}
}

func TestDualScopeAndDeniedIdentities(t *testing.T) {
	dir := t.TempDir()
	fpAliceOld := ComputeKeyFP("alice-old-key-1111")
	fpAliceNew := ComputeKeyFP("alice-new-key-2222")
	fpTrialA := ComputeKeyFP("trial-service-key-aaaa")
	fpTrialB := ComputeKeyFP("trial-service-key-bbbb")
	fpWebUI := ComputeKeyFP("shared-openwebui-9999")

	lines := []map[string]any{
		{
			"ts": "2026-11-18T10:00:00Z", "identity": "alice", "identity_type": "user", "account": "def-alice",
			"key_fp": fpAliceOld, "endpoint": "/v1/chat/completions", "model": "qwen38-27b", "status": 200,
			"latency_ms": 1000, "tokens": map[string]any{"prompt": 10, "completion": 20, "total": 30},
			"derived": map[string]any{"gpu_seconds": 2.0},
		},
		{
			// Historical poc record for alice should still be included in ScopeIdentity.
			"ts": "2026-11-18T11:00:00Z", "identity": "alice", "identity_type": "poc", "account": "def-alice",
			"key_fp": fpAliceNew, "endpoint": "/v1/chat/completions", "model": "qwen38-27b", "status": 200,
			"latency_ms": 1000, "tokens": map[string]any{"prompt": 40, "completion": 60, "total": 100},
			"derived": map[string]any{"gpu_seconds": 2.0},
		},
		{
			// Service record that happens to have identity "alice" must NOT leak into ScopeIdentity.
			"ts": "2026-11-18T11:30:00Z", "identity": "alice", "identity_type": "service", "account": "svc",
			"key_fp": fpTrialA, "endpoint": "/v1/chat/completions", "model": "gpt-oss-120b", "status": 200,
			"latency_ms": 1000, "tokens": map[string]any{"prompt": 500, "completion": 500, "total": 1000},
			"derived": map[string]any{"gpu_seconds": 2.0},
		},
		{
			"ts": "2026-11-18T12:00:00Z", "identity": "Kevin", "identity_type": "service", "account": "poc",
			"key_fp": fpTrialB, "endpoint": "/v1/chat/completions", "model": "gemma-4-31b", "status": 200,
			"latency_ms": 1500, "tokens": map[string]any{"prompt": 70, "completion": 30, "total": 100},
			"derived": map[string]any{"gpu_seconds": 3.0},
		},
		{
			// Denied shared platform identity must never be returned under any scope.
			"ts": "2026-11-18T12:30:00Z", "identity": "openwebui", "identity_type": "service", "account": "platform",
			"key_fp": fpWebUI, "endpoint": "/v1/chat/completions", "model": "qwen38-27b", "status": 200,
			"latency_ms": 1000, "tokens": map[string]any{"prompt": 999, "completion": 1, "total": 1000},
			"derived": map[string]any{"gpu_seconds": 2.0},
		},
	}
	writeJSONL(t, filepath.Join(dir, "model-gateway-live01", "usage.log"), lines)

	src := NewLedgerSource(LedgerConfig{Root: dir, Backups: 5})
	if _, err := src.Refresh(); err != nil {
		t.Fatalf("Refresh: %v", err)
	}
	day := time.Date(2026, 11, 18, 0, 0, 0, 0, time.UTC)

	// 1. ScopeIdentity for alice includes "user" + "poc" (30 + 100 = 130 tokens), excludes "service".
	repAlice, err := src.Usage(context.Background(), Subject{
		Scope: ScopeIdentity, AuthMethod: AuthMethodMockOIDC, Identity: "alice",
	}, day, day)
	if err != nil {
		t.Fatalf("Usage alice: %v", err)
	}
	if len(repAlice.Rows) != 1 || repAlice.Rows[0].TotalTokens != 130 || repAlice.Rows[0].Requests != 2 {
		t.Fatalf("ScopeIdentity alice mismatch: %+v", repAlice.Rows)
	}

	// 2. ScopeKeyFP for trial key B ("Kevin", type:service) sees strictly its 100 tokens.
	metaB, ok := src.LookupKeyFP(fpTrialB)
	if !ok || metaB.Identity != "Kevin" || metaB.IdentityType != "service" {
		t.Fatalf("LookupKeyFP(fpTrialB) = %+v, %v", metaB, ok)
	}
	repTrialB, err := src.Usage(context.Background(), Subject{
		Scope: ScopeKeyFP, AuthMethod: AuthMethodAPIKey, Identity: metaB.Identity, KeyFP: fpTrialB,
	}, day, day)
	if err != nil {
		t.Fatalf("Usage trialB: %v", err)
	}
	if len(repTrialB.Rows) != 1 || repTrialB.Rows[0].TotalTokens != 100 {
		t.Fatalf("ScopeKeyFP trialB mismatch: %+v", repTrialB.Rows)
	}

	// 3. Denied identities fail closed in both ScopeIdentity and ScopeKeyFP.
	if _, err := src.Usage(context.Background(), Subject{
		Scope: ScopeIdentity, AuthMethod: AuthMethodMockOIDC, Identity: "openwebui",
	}, day, day); !errors.Is(err, ErrDeniedSubject) {
		t.Fatalf("expected ErrDeniedSubject for openwebui ScopeIdentity, got %v", err)
	}
	repDeniedFP, err := src.Usage(context.Background(), Subject{
		Scope: ScopeKeyFP, AuthMethod: AuthMethodAPIKey, KeyFP: fpWebUI,
	}, day, day)
	if err != nil {
		t.Fatalf("Usage anonymous KeyFP: %v", err)
	}
	if len(repDeniedFP.Rows) != 0 {
		t.Fatalf("expected 0 rows for denied openwebui key_fp, got %+v", repDeniedFP.Rows)
	}
}

func TestMidScanRotationRecovery(t *testing.T) {
	dir := t.TempDir()
	podDir := filepath.Join(dir, "model-gateway-live01")
	logPath := filepath.Join(podDir, "usage.log")
	rotatedPath := filepath.Join(podDir, "usage.log.1")

	writeJSONL(t, logPath, []map[string]any{
		{
			"ts": "2026-11-18T09:00:00Z", "identity": "alice", "identity_type": "user",
			"endpoint": "/v1/chat/completions", "model": "qwen38-27b", "status": 200,
			"latency_ms": 500, "tokens": map[string]any{"prompt": 25, "completion": 75, "total": 100},
			"derived": map[string]any{"gpu_seconds": 1.0},
		},
	})

	src := NewLedgerSource(LedgerConfig{Root: dir, Backups: 5})
	if _, err := src.Refresh(); err != nil {
		t.Fatalf("initial Refresh: %v", err)
	}

	// Simulate RotatingFileHandler rotating usage.log -> usage.log.1 and creating
	// a brand-new usage.log right before the first on-demand scan opens usage.log.
	var rotatedOnce sync.Once
	src.openFile = func(name string) (*os.File, error) {
		if name == logPath {
			rotatedOnce.Do(func() {
				_ = os.Rename(logPath, rotatedPath)
				writeJSONL(t, logPath, []map[string]any{
					{
						"ts": "2026-11-18T10:00:00Z", "identity": "alice", "identity_type": "user",
						"endpoint": "/v1/chat/completions", "model": "qwen38-27b", "status": 200,
						"latency_ms": 500, "tokens": map[string]any{"prompt": 50, "completion": 150, "total": 200},
						"derived": map[string]any{"gpu_seconds": 1.0},
					},
				})
			})
		}
		return os.Open(name)
	}

	day := time.Date(2026, 11, 18, 0, 0, 0, 0, time.UTC)
	rep, err := src.Usage(context.Background(), Subject{
		Scope: ScopeIdentity, AuthMethod: AuthMethodMockOIDC, Identity: "alice",
	}, day, day)
	if err != nil {
		t.Fatalf("Usage across rotation failed: %v", err)
	}
	if rep.ReadErrors {
		t.Fatalf("expected clean rotation retry with ReadErrors=false")
	}
	if len(rep.Rows) != 1 || rep.Rows[0].TotalTokens != 300 || rep.Rows[0].Requests != 2 {
		t.Fatalf("expected both rotated (100) and new (200) tokens = 300, got %+v", rep.Rows)
	}
}

func TestConcurrentRefreshScanAndEvict(t *testing.T) {
	dir := t.TempDir()
	logPath := filepath.Join(dir, "model-gateway-live01", "usage.log")
	writeJSONL(t, logPath, []map[string]any{
		{
			"ts": "2026-11-18T08:00:00Z", "identity": "alice", "identity_type": "user",
			"endpoint": "/v1/chat/completions", "model": "qwen38-27b", "status": 200,
			"latency_ms": 400, "tokens": map[string]any{"prompt": 10, "completion": 10, "total": 20},
			"derived": map[string]any{"gpu_seconds": 0.8},
		},
	})
	src := NewLedgerSource(LedgerConfig{Root: dir, Backups: 5, MaxConcurrentScans: 1})
	if _, err := src.Refresh(); err != nil {
		t.Fatal(err)
	}
	subj := Subject{Scope: ScopeIdentity, AuthMethod: AuthMethodMockOIDC, Identity: "alice"}
	day := time.Date(2026, 11, 18, 0, 0, 0, 0, time.UTC)

	var wg sync.WaitGroup
	for i := 0; i < 6; i++ {
		wg.Add(1)
		go func(iter int) {
			defer wg.Done()
			for j := 0; j < 10; j++ {
				if iter == 0 {
					_, _ = src.Refresh()
				} else if iter == 1 {
					src.EvictSubject(subj)
				} else {
					if _, err := src.Usage(context.Background(), subj, day, day); err != nil {
						t.Errorf("concurrent Usage err: %v", err)
					}
				}
			}
		}(i)
	}
	wg.Wait()
}

func TestPrometheusSourceFailsClosed(t *testing.T) {
	if _, err := NewPrometheusSource(""); err == nil {
		t.Fatal("expected empty PROMETHEUS_URL error")
	}
	ps, err := NewPrometheusSource("http://prometheus.monitoring.svc:9090")
	if err != nil {
		t.Fatalf("NewPrometheusSource: %v", err)
	}
	if ps.Ready() {
		t.Fatal("PrometheusSource must report Ready()=false until subject series exist")
	}
	day := time.Date(2026, 11, 18, 0, 0, 0, 0, time.UTC)
	_, err = ps.Usage(context.Background(), Subject{Scope: ScopeIdentity, Identity: "alice"}, day, day)
	if !errors.Is(err, ErrPrometheusNotReady) {
		t.Fatalf("expected ErrPrometheusNotReady, got %v", err)
	}
}
