// Package catalog fetches live model metadata from model-gateway's internal
// /v1/models?all=true endpoint so the Connect tab renders current, non-hardcoded
// model IDs and counts.
package catalog

import (
	"context"
	"encoding/json"
	"io"
	"net/http"
	"strings"
	"sync"
	"time"
)

const defaultTTL = 5 * time.Minute

// Entry describes the subset of a live Aleph model entry used by /connect.
type Entry struct {
	ID            string `json:"id"`
	Type          string `json:"type"`
	Mode          string `json:"mode"`
	ContextWindow int64  `json:"context_window"`
	Ready         bool   `json:"ready"`
	ScaledUp      bool   `json:"scaled_up"`
	Capabilities  struct {
		Vision    bool `json:"vision"`
		Tools     bool `json:"tools"`
		Reasoning bool `json:"reasoning"`
	} `json:"capabilities"`
	Scaling struct {
		ScaleToZero bool `json:"scale_to_zero"`
	} `json:"scaling"`
}

// Snapshot is the summarized live model catalog used to render /connect.
type Snapshot struct {
	Available       bool
	FetchedAt       time.Time
	TotalModels     int
	AlwaysOnModels  int
	ChatModels      int
	TaskModels      int
	ChatModel       string
	AnthropicModel  string
	EmbedModel      string
	TaskModel       string
	AlwaysOnChatIDs []string
}

func placeholderSnapshot() Snapshot {
	return Snapshot{
		ChatModel:      "<chat-model-id>",
		AnthropicModel: "<always-on-chat-model-id>",
		EmbedModel:     "<embedding-model-id>",
		TaskModel:      "<task-model-id>",
	}
}

// Client caches live model snapshots from model-gateway.
type Client struct {
	url    string
	ttl    time.Duration
	http   *http.Client
	Now    func() time.Time
	mu     sync.Mutex
	cached Snapshot
}

// NewClient constructs a catalog Client. An empty url disables live fetches and
// cleanly serves placeholder model tokens.
func NewClient(url string, ttl time.Duration) *Client {
	if ttl <= 0 {
		ttl = defaultTTL
	}
	return &Client{
		url: strings.TrimSpace(url),
		ttl: ttl,
		http: &http.Client{
			Timeout: 4 * time.Second,
		},
		Now:    time.Now,
		cached: placeholderSnapshot(),
	}
}

// Get returns a cached Snapshot or refreshes from model-gateway when stale.
func (c *Client) Get(ctx context.Context) Snapshot {
	if c == nil || c.url == "" {
		return placeholderSnapshot()
	}
	now := c.Now().UTC()
	c.mu.Lock()
	if c.cached.Available && now.Sub(c.cached.FetchedAt) < c.ttl {
		snap := c.cached
		c.mu.Unlock()
		return snap
	}
	stale := c.cached
	c.mu.Unlock()

	fresh, ok := c.fetch(ctx, now)
	if !ok {
		return stale
	}
	c.mu.Lock()
	c.cached = fresh
	c.mu.Unlock()
	return fresh
}

func (c *Client) fetch(ctx context.Context, now time.Time) (Snapshot, bool) {
	req, err := http.NewRequestWithContext(ctx, http.MethodGet, c.url, nil)
	if err != nil {
		return Snapshot{}, false
	}
	req.Header.Set("Accept", "application/json")
	resp, err := c.http.Do(req)
	if err != nil {
		return Snapshot{}, false
	}
	defer resp.Body.Close()
	if resp.StatusCode < 200 || resp.StatusCode >= 300 {
		return Snapshot{}, false
	}
	var payload struct {
		Data []Entry `json:"data"`
	}
	if err := json.NewDecoder(io.LimitReader(resp.Body, 4<<20)).Decode(&payload); err != nil {
		return Snapshot{}, false
	}
	return Summarize(payload.Data, now), true
}

// Summarize computes representative model IDs and fleet counts without any
// hardcoded model names.
func Summarize(entries []Entry, now time.Time) Snapshot {
	snap := placeholderSnapshot()
	snap.Available = true
	snap.FetchedAt = now
	snap.TotalModels = len(entries)

	var bestChatScore, bestAnthScore, bestEmbedScore, bestTaskScore int
	for _, e := range entries {
		if e.ID == "" {
			continue
		}
		mode := e.Mode
		if mode == "" {
			mode = "api"
		}
		alwaysOn := !e.Scaling.ScaleToZero
		if alwaysOn {
			snap.AlwaysOnModels++
		}
		if mode == "task" || mode == "both" {
			snap.TaskModels++
			score := 1
			if e.Ready {
				score += 2
			}
			if e.ScaledUp {
				score++
			}
			if score > bestTaskScore {
				bestTaskScore = score
				snap.TaskModel = e.ID
			}
		}
		if e.Type == "chat" && mode != "task" {
			snap.ChatModels++
			if alwaysOn {
				snap.AlwaysOnChatIDs = append(snap.AlwaysOnChatIDs, e.ID)
			}
			chatScore := 1
			if alwaysOn {
				chatScore += 4
			}
			if e.ScaledUp {
				chatScore += 2
			}
			if e.Capabilities.Tools {
				chatScore++
			}
			if chatScore > bestChatScore {
				bestChatScore = chatScore
				snap.ChatModel = e.ID
			}
			if alwaysOn {
				anthScore := 1
				if e.ScaledUp {
					anthScore += 4
				}
				if e.Capabilities.Tools {
					anthScore += 2
				}
				if e.Capabilities.Reasoning {
					anthScore++
				}
				if anthScore > bestAnthScore {
					bestAnthScore = anthScore
					snap.AnthropicModel = e.ID
				}
			}
		}
		if strings.HasPrefix(e.Type, "embed") && mode != "task" {
			embedScore := 1
			if alwaysOn {
				embedScore += 4
			}
			if e.ScaledUp {
				embedScore += 2
			}
			if embedScore > bestEmbedScore {
				bestEmbedScore = embedScore
				snap.EmbedModel = e.ID
			}
		}
	}
	return snap
}
