package catalog

import (
	"context"
	"net/http"
	"net/http/httptest"
	"testing"
	"time"
)

func TestCatalogClientDynamicSelectionAndFallback(t *testing.T) {
	srv := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, _ *http.Request) {
		w.Header().Set("Content-Type", "application/json")
		_, _ = w.Write([]byte(`{
			"object": "list",
			"data": [
				{
					"id": "alpha-embed-v1",
					"type": "embeddings",
					"mode": "api",
					"ready": true,
					"scaled_up": true,
					"scaling": {"scale_to_zero": false}
				},
				{
					"id": "beta-chat-warm",
					"type": "chat",
					"mode": "api",
					"ready": true,
					"scaled_up": true,
					"capabilities": {"tools": true, "reasoning": true},
					"scaling": {"scale_to_zero": false}
				},
				{
					"id": "gamma-ocr-task",
					"type": "vision",
					"mode": "task",
					"ready": true,
					"scaled_up": false,
					"scaling": {"scale_to_zero": true}
				}
			]
		}`))
	}))
	defer srv.Close()

	client := NewClient(srv.URL+"/v1/models?all=true", time.Minute)
	snap := client.Get(context.Background())
	if !snap.Available || snap.TotalModels != 3 || snap.AlwaysOnModels != 2 {
		t.Fatalf("unexpected snapshot counts: %+v", snap)
	}
	if snap.ChatModel != "beta-chat-warm" || snap.AnthropicModel != "beta-chat-warm" {
		t.Fatalf("unexpected chat/anthropic selection: %+v", snap)
	}
	if snap.EmbedModel != "alpha-embed-v1" || snap.TaskModel != "gamma-ocr-task" {
		t.Fatalf("unexpected embed/task selection: %+v", snap)
	}

	// Unconfigured client cleanly returns placeholders without panicking.
	offline := NewClient("", time.Minute).Get(context.Background())
	if offline.Available || offline.ChatModel != "<chat-model-id>" {
		t.Fatalf("unexpected offline fallback: %+v", offline)
	}
}
