// Package fake writes synthetic usage-ledger files in the same format and
// directory layout as the Aleph gateway, for development and tests. Record
// shapes follow the examples in docs/LOGGING.md. No real identities or keys.
package fake

import (
	"encoding/json"
	"fmt"
	"math/rand"
	"os"
	"path/filepath"
	"sort"
	"time"
)

// Options controls generation.
type Options struct {
	Out      string    // ledger root to write into
	Users    []string  // user identities (LDAP-style usernames)
	Days     int       // days of history, ending at End
	End      time.Time // last day of data (UTC)
	PerDay   int       // average user requests per user per day
	LivePods int       // pods running now, which wrote the newest records
	Retired  int       // pod directories left by an earlier rollout
	Seed     int64

	// MaxFileBytes and Backups mirror the gateway's
	// GATEWAY_USAGE_LOG_MAX_BYTES and GATEWAY_USAGE_LOG_BACKUPS. Each pod's
	// log rotates when the next record would reach MaxFileBytes, and only
	// usage.log plus Backups rotated files are kept, so the oldest records of
	// a busy pod are deleted, as on the real volume. If either is 0 nothing
	// rotates, as with Python's RotatingFileHandler.
	MaxFileBytes int
	Backups      int
}

// kind is what a model's endpoint returns, which decides its token shape.
type kind int

const (
	chat  kind = iota // prompt and completion tokens, sometimes thinking
	embed             // input tokens only
	image             // no tokens; the gateway logs counts only
	audio             // no tokens; byte and character counts in detail
)

// model mirrors a public Aleph model: IDs, GPU counts, and context windows
// come from models/<model>/details.yaml and inferenceservice.yaml.
type model struct {
	id            string
	kind          kind
	gpus          int
	vramMiB       int
	latency       int // typical ms
	contextWindow int // 0 when the card declares none
	// reasoning: the runtime always sends
	// completion_tokens_details.reasoning_tokens, 0 when thinking is off.
	// Checked against the live API on 2026-11-17 for qwen38-27b and
	// gemma-4-31b; gpt-oss-120b omits the object entirely. The other qwen and
	// gemma entries follow the same runtime and are assumed to match.
	reasoning bool
	weight    int // relative popularity
}

var models = []model{
	{id: "qwen38-27b", kind: chat, gpus: 2, latency: 2500, contextWindow: 524288, reasoning: true, weight: 30},
	{id: "qwen35-122b", kind: chat, gpus: 4, latency: 3000, contextWindow: 131072, reasoning: true, weight: 22},
	{id: "gpt-oss-120b", kind: chat, gpus: 2, latency: 1800, contextWindow: 131072, weight: 16},
	{id: "gemma-4-31b", kind: chat, gpus: 2, latency: 2000, contextWindow: 262144, reasoning: true, weight: 8},
	{id: "gemma-4-26b-a4b", kind: chat, gpus: 1, latency: 900, contextWindow: 131072, reasoning: true, weight: 8},
	{id: "bge-m3", kind: embed, gpus: 1, vramMiB: 8192, latency: 140, contextWindow: 8192, weight: 4},
	{id: "ancient-greek-bert", kind: embed, gpus: 1, vramMiB: 4096, latency: 90, contextWindow: 512, weight: 2},
	{id: "kandinsky-3-1-flash", kind: image, gpus: 1, latency: 4000, weight: 1},
	{id: "whisper-large-v3", kind: audio, gpus: 1, vramMiB: 8192, latency: 600, weight: 1},
}

// pick chooses a model by weight from a list.
func pick(rng *rand.Rand, from []model) model {
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

// errorStatuses is the spread of failed requests, about 0.3% of all.
var errorStatuses = []int{400, 400, 429, 429, 429, 503, 504, 500, 499}

// apiFor is the ledger's "api" value for an endpoint: the client-facing API
// style the gateway logs, not the upstream's. /v1/messages is Anthropic-style
// for the client, but the gateway translates it to an OpenAI chat request and
// logs the upstream's OpenAI-shaped usage object as tokens.detail, so its
// detail has the same shape as chat completions. Image generation goes
// through the gateway's catch-all route, which logs "custom".
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

func record(rng *rand.Rand, ts time.Time, identity, identityType string, mdl model) map[string]any {
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
		if rng.Intn(60) == 0 {
			prompt = mdl.contextWindow * (88 + rng.Intn(11)) / 100 // a long passage near the limit
		}
		detail = map[string]any{"prompt_tokens": prompt, "total_tokens": prompt}
	case image:
		endpoint = "/v1/images/generations"
		detail = map[string]any{"images": 1 + rng.Intn(4)}
	case audio:
		endpoint = "/v1/audio/transcriptions"
		detail = map[string]any{"audio_input_bytes": 200000 + rng.Intn(3000000), "audio_output_bytes": 50, "text_chars": 10 + rng.Intn(2000)}
	default:
		if rng.Intn(20) == 0 {
			endpoint = "/v1/messages" // Anthropic-style clients
		}
		// Input-heavy: long documents in, short answers out.
		prompt = 300 + int(rng.ExpFloat64()*6000)
		if rng.Intn(150) == 0 {
			prompt = mdl.contextWindow * (80 + rng.Intn(17)) / 100 // occasional near-limit prompt
		}
		completion = 20 + int(rng.ExpFloat64()*450)
		latency += completion * 8 // longer answers take longer
		detail = map[string]any{"prompt_tokens": prompt, "completion_tokens": completion, "total_tokens": prompt + completion, "prompt_tokens_details": nil}
		if mdl.reasoning {
			// These runtimes always send the field; it is 0 when thinking
			// is off, which is most requests.
			thinking := 0
			if rng.Intn(3) == 0 {
				thinking = completion * (40 + rng.Intn(55)) / 100
			}
			detail["completion_tokens_details"] = map[string]any{"reasoning_tokens": thinking}
		}
	}
	switch roll := rng.Float64(); {
	case roll < 0.004 && mdl.weight < 5: // wake-ups happen on low-traffic models
		status, cold, latency, prompt, completion = 503, true, 0, 0, 0
		detail = map[string]any{}
	case roll < 0.007:
		status, prompt, completion = errorStatuses[rng.Intn(len(errorStatuses))], 0, 0
		latency = 5 + rng.Intn(200)
		if status == 504 || status == 499 {
			latency = 30000 + rng.Intn(60000)
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
		"ts": ts.UTC().Format("2006-01-02T15:04:05Z"), "site": "aleph",
		"identity": identity, "identity_type": identityType, "account": identity,
		"endpoint": endpoint, "api": apiFor(endpoint), "model": mdl.id,
		"status": status, "stream": mdl.kind == chat && rng.Intn(2) == 0,
		"cold_start": cold, "latency_ms": latency,
		"tokens":         map[string]any{"prompt": prompt, "completion": completion, "total": prompt + completion, "detail": detail},
		"context_window": mdl.contextWindow, "max_completion_tokens": 0,
		"resources": resources, "derived": map[string]any{"gpu_seconds": gpuSeconds},
	}
}

// Generate writes the ledger tree and returns the number of records in it,
// which leaves out any that rotation deleted.
func Generate(opts Options) (int, error) {
	if opts.Days <= 0 || opts.LivePods <= 0 || len(opts.Users) == 0 {
		return 0, fmt.Errorf("need days > 0, live pods > 0, and at least one user")
	}
	rng := rand.New(rand.NewSource(opts.Seed))
	end := opts.End.UTC()
	start := end.Add(-time.Duration(opts.Days) * 24 * time.Hour)

	// Each user favours a few models so their pages look different.
	prefs := map[string][]model{}
	for _, user := range opts.Users {
		// Popular models are more likely to be among a user's favourites.
		want := 3 + rng.Intn(3)
		chosen := map[string]bool{}
		for len(prefs[user]) < want {
			candidate := pick(rng, models)
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
			if rng.Intn(5) == 0 {
				requests = 0 // quiet days
			}
			for i := 0; i < requests; i++ {
				ts := day.Add(time.Duration(rng.Int63n(int64(24 * time.Hour))))
				if ts.After(end) {
					continue
				}
				mdl := pick(rng, prefs[user])
				lines = append(lines, line{ts, record(rng, ts, user, "user", mdl)})
			}
		}
		// Shared service keys (browser chat, pipelines) are not per-person.
		for _, svc := range []string{"service-webui", "service-rag"} {
			for i := 0; i < opts.PerDay*3; i++ {
				ts := day.Add(time.Duration(rng.Int63n(int64(24 * time.Hour))))
				if ts.After(end) {
					continue
				}
				lines = append(lines, line{ts, record(rng, ts, svc, "service", pick(rng, models[:5]))})
			}
		}
	}
	sort.Slice(lines, func(i, j int) bool { return lines[i].ts.Before(lines[j].ts) })

	// An earlier rollout's pods served the first third of the history and
	// then stopped; their directories stay on the volume. The live pods
	// started at the rollout and wrote everything since. Each request goes to
	// one pod, and each pod rotates its own log.
	rollout := start
	if opts.Retired > 0 {
		rollout = start.Add(end.Sub(start) / 3)
	}
	pods := map[string]*podLog{}
	for _, entry := range lines {
		var dir string
		if entry.ts.Before(rollout) {
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

// podLog is one pod's ledger files while they are generated.
type podLog struct {
	files []logFile // files[0] is usage.log, files[n] is usage.log.n
}

type logFile struct {
	content []byte
	records int
}

// write appends one encoded record, rotating first the way the gateway's
// RotatingFileHandler does: when the record would take a non-empty
// usage.log to maxBytes, usage.log becomes usage.log.1, each older file
// moves up one number, and a file past usage.log.<backups> is deleted with
// the records in it.
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
