# tinyllama-1-1b — Test Report

Cluster 230, gateway ClusterIP `http://10.43.79.101:80`. Type: chat (CPU, llama.cpp GGUF). id `tinyllama-1-1b`.

## Verified this pass (2026-06-05)

### POST /v1/chat/completions (OpenAI) — PASS
```bash
curl -s -X POST $GW/v1/chat/completions -H 'Content-Type: application/json' \
  -d '{"model":"tinyllama-1-1b","messages":[{"role":"user","content":"Say hello in one sentence."}],"max_tokens":40}'
```
→ `object=chat.completion`, valid `choices[0].message.content`, usage reported. PASS.

### POST /v1/messages (Anthropic) — PASS
```bash
curl -s -X POST $GW/v1/messages -H 'Content-Type: application/json' \
  -d '{"model":"tinyllama-1-1b","max_tokens":40,"messages":[{"role":"user","content":"Name one color."}]}'
```
→ `type=message`, `content[0].type=text`, `stop_reason`, `usage.input/output_tokens`. PASS.

## Streaming — KNOWN LIMITATION (gateway-level, cross-cutting)
- `stream:true` returns 500. Card marks `no_stream:true` / `supports_streaming:false`.
- Backend is the official `llama_cpp.server` (supports SSE natively); failure is at the
  gateway↔Knative/Istio SSE proxy path (`httpx.RemoteProtocolError: incomplete chunked read`).
- Affects ALL chat models, not just tinyllama → tracked as a single gateway fix to be done
  during the chat-model wave, not per model.

## Card parity
id=tinyllama-1-1b, type=chat, gpu=false, scale-to-zero. OpenAI + Anthropic verified.
Streaming flagged false (accurate until gateway SSE path is fixed).
