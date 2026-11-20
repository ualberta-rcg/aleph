// Package fake writes synthetic usage-ledger files in the exact JSONL format
// and directory layout produced by gateway/app/usage.py for local development
// and automated tests. No real identities or keys are used.
package fake

import (
	"encoding/json"
	"fmt"
	"math/rand"
	"os"
	"path/filepath"
	"sort"
	"time"

	"github.com/ualberta-rcg/aleph/portal/internal/source"
)

// Options controls synthetic ledger generation.
type Options struct {
	Out          string
	Users        []string
	Days         int
	End          time.Time
	PerDay       int
	LivePods     int
	Retired      int
	Seed         int64
	MaxFileBytes int
	Backups      int
}

type kind int

const (
	chat kind = iota
	embed
	image
	audio
)

type simModel struct {
	id            string
	kind          kind
	gpus          int
	vramMiB       int
	latency       int
	contextWindow int
	reasoning     bool
	weight        int
}

var simModels = []simModel{
	{id: "sim-chat-large", kind: chat, gpus: 4, latency: 2800, contextWindow: 131072, reasoning: true, weight: 28},
	{id: "sim-chat-medium", kind: chat, gpus: 2, latency: 2100, contextWindow: 524288, reasoning: true, weight: 24},
	{id: "sim-chat-fast", kind: chat, gpus: 1, latency: 900, contextWindow: 131072, weight: 16},
	{id: "sim-embed-dense", kind: embed, gpus: 1, vramMiB: 8192, latency: 130, contextWindow: 8192, weight: 6},
	{id: "sim-image-gen", kind: image, gpus: 1, latency: 3800, weight: 2},
	{id: "sim-audio-asr", kind: audio, gpus: 1, vramMiB: 8192, latency: 600, weight: 2},
}

func pick(rng *rand.Rand, from []simModel) simModel {
	total := 0
	for _, candidate := range from {
		total += candidate.weight
	}
	roll := rng.Intn(total)
	for _, candidate := range from {
		if roll < candidate.weight {
			return candidate
		}
		roll -= candidate.weight
	}
	return from[len(from)-1]
}

type line struct {
	ts  time.Time
	rec map[string]any
}

var errorStatuses = []int{400, 400, 429, 429, 503, 504, 500, 499}

func apiFor(endpoint string) string {
	switch endpoint {
	case "/v1/messages":
		return "anthropic"
	case "/v1/images/generations":
		return "custom"
	default:
		return "openai"
	}
}

func buildRecord(rng *rand.Rand, ts time.Time, identity, identityType string, fp source.KeyFP, mdl simModel) map[string]any {
	status := 200
	cold := false
	latency := mdl.latency/2 + rng.Intn(mdl.latency+1)
	var prompt, completion int
	detail := map[string]any{}
	endpoint := "/v1/chat/completions"
	switch mdl.kind {
	case embed:
		endpoint = "/v1/embeddings"
		prompt = 8 + rng.Intn(400)
		if rng.Intn(50) == 0 {
			prompt = mdl.contextWindow * (90 + rng.Intn(8)) / 100
		}
		detail = map[string]any{"prompt_tokens": prompt, "total_tokens": prompt}
	case image:
		endpoint = "/v1/images/generations"
		detail = map[string]any{"images": 1 + rng.Intn(4)}
	case audio:
		endpoint = "/v1/audio/transcriptions"
		detail = map[string]any{"audio_input_bytes": 200000 + rng.Intn(2000000), "audio_output_bytes": 50, "text_chars": 10 + rng.Intn(1000)}
	default:
		if rng.Intn(15) == 0 {
			endpoint = "/v1/messages"
		}
		prompt = 300 + int(rng.ExpFloat64()*5000)
		if rng.Intn(120) == 0 {
			prompt = mdl.contextWindow * (90 + rng.Intn(8)) / 100
		}
		completion = 20 + int(rng.ExpFloat64()*400)
		latency += completion * 8
		detail = map[string]any{
			"prompt_tokens":     prompt,
			"completion_tokens": completion,
			"total_tokens":      prompt + completion,
		}
		if mdl.reasoning {
			thinking := 0
			if rng.Intn(3) == 0 {
				thinking = completion * (40 + rng.Intn(50)) / 100
			}
			detail["completion_tokens_details"] = map[string]any{"reasoning_tokens": thinking}
		}
	}
	switch roll := rng.Float64(); {
	case roll < 0.008 && mdl.weight < 8:
		status, cold, latency, prompt, completion = 503, true, 0, 0, 0
		detail = map[string]any{}
	case roll < 0.014:
		status, prompt, completion = errorStatuses[rng.Intn(len(errorStatuses))], 0, 0
		latency = 10 + rng.Intn(200)
		if status == 504 || status == 499 {
			latency = 30000 + rng.Intn(30000)
		}
		detail = map[string]any{}
	}
	gpuSeconds := 0.0
	resources := map[string]any{"model": mdl.id, "cpu_cores": 4.0, "system_ram_mib": 16384, "latency_ms": latency}
	if !cold {
		resources["gpus"] = mdl.gpus
		resources["node"] = fmt.Sprintf("gpu-worker-%d", 1+rng.Intn(6))
		resources["gpu_product"] = "L40S"
		if mdl.vramMiB > 0 {
			resources["vram_mib"] = mdl.vramMiB
		}
		gpuSeconds = float64(int(float64(mdl.gpus)*float64(latency)/1000*10000)) / 10000
	}
	return map[string]any{
		"ts":                    ts.UTC().Format(source.TimeLayout),
		"site":                  "aleph",
		"identity":              identity,
		"identity_type":         identityType,
		"account":               "def-" + identity,
		"key_fp":                fp,
		"endpoint":              endpoint,
		"api":                   apiFor(endpoint),
		"model":                 mdl.id,
		"status":                status,
		"stream":                mdl.kind == chat && rng.Intn(2) == 0,
		"cold_start":            cold,
		"latency_ms":            latency,
		"tokens":                map[string]any{"prompt": prompt, "completion": completion, "total": prompt + completion, "detail": detail},
		"context_window":        mdl.contextWindow,
		"max_completion_tokens": 0,
		"resources":             resources,
		"derived":               map[string]any{"gpu_seconds": gpuSeconds},
	}
}

// SyntheticKey returns the deterministic synthetic key string for a fake user.
func SyntheticKey(user string) string {
	return "fake-aleph-key-" + user + "-0001"
}

// Generate writes synthetic rotated pod directories under opts.Out.
func Generate(opts Options) (int, error) {
	if opts.Days <= 0 || opts.LivePods <= 0 || len(opts.Users) == 0 {
		return 0, fmt.Errorf("need days > 0, live pods > 0, and at least one user")
	}
	rng := rand.New(rand.NewSource(opts.Seed))
	end := opts.End.UTC()
	start := end.Add(-time.Duration(opts.Days) * 24 * time.Hour)

	prefs := map[string][]simModel{}
	userFP := map[string]source.KeyFP{}
	for _, user := range opts.Users {
		userFP[user] = source.ComputeKeyFP(SyntheticKey(user))
		want := 3 + rng.Intn(3)
		chosen := map[string]bool{}
		for len(prefs[user]) < want {
			candidate := pick(rng, simModels)
			if !chosen[candidate.id] {
				chosen[candidate.id] = true
				prefs[user] = append(prefs[user], candidate)
			}
		}
	}

	var lines []line
	for dayIndex := 0; dayIndex < opts.Days; dayIndex++ {
		day := start.Add(time.Duration(dayIndex) * 24 * time.Hour)
		for _, user := range opts.Users {
			requests := rng.Intn(2*opts.PerDay + 1)
			if rng.Intn(6) == 0 {
				requests = 0
			}
			for i := 0; i < requests; i++ {
				ts := day.Add(time.Duration(rng.Int63n(int64(24 * time.Hour))))
				if ts.After(end) {
					continue
				}
				mdl := pick(rng, prefs[user])
				lines = append(lines, line{ts, buildRecord(rng, ts, user, "user", userFP[user], mdl)})
			}
		}
		for _, svc := range []string{"openwebui", "task-worker"} {
			fp := source.ComputeKeyFP("svc-key-" + svc)
			for i := 0; i < opts.PerDay*2; i++ {
				ts := day.Add(time.Duration(rng.Int63n(int64(24 * time.Hour))))
				if ts.After(end) {
					continue
				}
				lines = append(lines, line{ts, buildRecord(rng, ts, svc, "service", fp, pick(rng, simModels[:3]))})
			}
		}
	}
	sort.Slice(lines, func(i, j int) bool { return lines[i].ts.Before(lines[j].ts) })

	rollout := start
	if opts.Retired > 0 {
		rollout = start.Add(end.Sub(start) / 3)
	}
	pods := map[string]*podLog{}
	for _, entry := range lines {
		var dir string
		if opts.Retired > 0 && entry.ts.Before(rollout) {
			dir = fmt.Sprintf("model-gateway-7f9c8d6b5-old%02d", rng.Intn(opts.Retired))
		} else {
			dir = fmt.Sprintf("model-gateway-5c4b7d9f8-live%02d", rng.Intn(opts.LivePods))
		}
		encoded, err := json.Marshal(entry.rec)
		if err != nil {
			return 0, err
		}
		pod := pods[dir]
		if pod == nil {
			pod = &podLog{}
			pods[dir] = pod
		}
		pod.write(append(encoded, '\n'), opts.MaxFileBytes, opts.Backups)
	}

	kept := 0
	for dir, pod := range pods {
		if err := os.MkdirAll(filepath.Join(opts.Out, dir), 0o755); err != nil {
			return 0, err
		}
		for number, file := range pod.files {
			name := "usage.log"
			if number > 0 {
				name = fmt.Sprintf("usage.log.%d", number)
			}
			if err := os.WriteFile(filepath.Join(opts.Out, dir, name), file.content, 0o644); err != nil {
				return 0, err
			}
			kept += file.records
		}
	}
	return kept, nil
}

type podLog struct {
	files []logFile
}

type logFile struct {
	content []byte
	records int
}

func (pod *podLog) write(record []byte, maxBytes, backups int) {
	if len(pod.files) == 0 {
		pod.files = []logFile{{}}
	}
	current := &pod.files[0]
	rotates := maxBytes > 0 && backups > 0
	if rotates && len(current.content) > 0 && len(current.content)+len(record) >= maxBytes {
		pod.files = append([]logFile{{}}, pod.files...)
		if len(pod.files) > backups+1 {
			pod.files = pod.files[:backups+1]
		}
		current = &pod.files[0]
	}
	current.content = append(current.content, record...)
	current.records++
}
