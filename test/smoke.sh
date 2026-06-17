#!/usr/bin/env bash
# Demo curls for the cluster-230 inference gateway (via Tyk).
# Run from the Vulcan login node. Usage:
#   bash demo.sh         # run all demos in order
#   bash demo.sh 4       # run only demo #4
#
# Endpoint = Tyk NodePort on the control-plane node. Auth = Tyk API key.
BASE="${BASE:-http://172.26.92.230:30808}"
KEY="${KEY:-eyJvcmciOiIiLCJpZCI6ImM3NmM3ZDliM2RiYTQ4MzdhYTY5NjFlYWY2ODM0OWY0IiwiaCI6Im11cm11cjEyOCJ9}"
AUTH=(-H "Authorization: Bearer $KEY" -H "Content-Type: application/json")

# A small 64x64 PNG (blue field with a red diagonal) for the vision demo.
IMG="iVBORw0KGgoAAAANSUhEUgAAAEAAAABACAIAAAAlC+aJAAABNElEQVR42tXXiwnDMAxF0TtOZurYHaJztFAopU381ecJHBLbkuAQEts8juO0Hbd7icYVoIqhBShh6AD0DX2AuGEIoGwYBcgaJgCaBl5XaQPvW10Dn6eiBr47FQ389MsZ+B+qZeB0tJCBq4kqBhpzJQy0p/UNdCPEDYwEKRsYjJM1MB6qaWAqWtDAbIKagYUcKQNraToGljNFDOwkKxjYzE83sF8i14BJlUQDVoWyDBjWSjFg+0LjDZh/VcEGPH5tkQac1pcwA36LfIwB151WgAHv7a63gYAzh6uBmIOfn4Gw07eTIQ7gZAgFeBiiAeaGBICtIQdgaEgDWBkyASaGZMC+IR+waZAA7BhUAMsGIcCaQQuwYJADzBoUAVMGUcC4QRcwaJAGjBjUAV1DAUDbUAPQMDwBPvzXPWTxKEYAAAAASUVORK5CYII="

run() {
case "$1" in
1)
  echo "# 1. Full catalogue (card-driven: capabilities, source, scaling, live resources)"
  curl -s "$BASE/v1/models?all=true" "${AUTH[@]}" \
    | jq '.data[] | {id, type, ready, gpu, context_window, caps: [.capabilities|to_entries[]|select(.value)|.key]}'
  ;;
2)
  echo "# 2. Chat-only models (what a chat UI sees)"
  curl -s "$BASE/v1/models" "${AUTH[@]}" | jq '.data[].id'
  ;;
3)
  echo "# 3. OpenAI chat — command-r-7b (always-warm)"
  curl -s "$BASE/v1/chat/completions" "${AUTH[@]}" -d '{
    "model":"command-r-7b",
    "messages":[{"role":"user","content":"In two sentences, what is retrieval-augmented generation?"}],
    "max_tokens":150}' | jq '.choices[0].message.content, .resources'
  ;;
4)
  echo "# 4. OpenAI chat — gpt-oss-20b reasoning model, effort=high (shows reasoning)"
  curl -s "$BASE/v1/chat/completions" "${AUTH[@]}" -d '{
    "model":"gpt-oss-20b","reasoning_effort":"high",
    "messages":[{"role":"user","content":"A bat and ball cost $1.10. The bat costs $1 more than the ball. How much is the ball?"}],
    "max_tokens":3000}' | jq 'if .error then .error else {answer: .choices[0].message.content, reasoning: .choices[0].message.reasoning, tokens: .usage.completion_tokens, resources} end'
  ;;
5)
  echo "# 5. OpenAI streaming (SSE) — gpt-oss-20b"
  curl -sN "$BASE/v1/chat/completions" "${AUTH[@]}" -d '{
    "model":"gpt-oss-20b","stream":true,
    "messages":[{"role":"user","content":"Count from 1 to 5."}],"max_tokens":200}'
  echo
  ;;
6)
  echo "# 6. Anthropic Messages API — gpt-oss-20b (/v1/messages)"
  curl -s "$BASE/v1/messages" "${AUTH[@]}" -d '{
    "model":"gpt-oss-20b","max_tokens":1000,
    "messages":[{"role":"user","content":"Name the planets in order from the sun."}]}' \
    | jq 'if .error then .error else {role, stop_reason, text: .content[0].text, resources} end'
  ;;
7)
  echo "# 7. Vision (multimodal) — qwen2.5-vl-7b describes an inline image"
  curl -s "$BASE/v1/chat/completions" "${AUTH[@]}" -d "{
    \"model\":\"qwen25-vl-7b\",
    \"messages\":[{\"role\":\"user\",\"content\":[
      {\"type\":\"text\",\"text\":\"Describe this image: colors and any shapes/patterns.\"},
      {\"type\":\"image_url\",\"image_url\":{\"url\":\"data:image/png;base64,$IMG\"}}]}],
    \"max_tokens\":150}" | jq '.choices[0].message.content, .resources'
  ;;
8)
  echo "# 8. Embeddings — bge-small (384-dim vectors)"
  curl -s "$BASE/v1/embeddings" "${AUTH[@]}" -d '{
    "model":"bge-small","input":["GPU scheduling with HAMi","Kubernetes model serving"]}' \
    | jq '{model, dims: (.data[0].embedding|length), count: (.data|length), resources}'
  ;;
9)
  echo "# 9. Resource telemetry — every response carries the allocated footprint"
  curl -s "$BASE/v1/chat/completions" "${AUTH[@]}" -d '{
    "model":"command-r-7b","messages":[{"role":"user","content":"hi"}],"max_tokens":10}' \
    | jq '.resources'
  ;;
10)
  echo "# 10. Scale-to-zero cold start — if a model is asleep you get a fast, friendly 503"
  echo "#     (gpt-oss-20b / qwen25-vl-7b scale to zero after 15m idle; retry as told)"
  curl -s -o /tmp/demo10.json -w 'HTTP %{http_code} in %{time_total}s\n' "$BASE/v1/chat/completions" "${AUTH[@]}" -d '{
    "model":"qwen25-vl-7b","messages":[{"role":"user","content":"hi"}],"max_tokens":10}'
  jq -c '.error // .choices[0].message.content' /tmp/demo10.json
  ;;
*) echo "unknown demo: $1" ;;
esac
echo
}

if [ -n "$1" ]; then run "$1"; else for i in 1 2 3 4 5 6 7 8 9 10; do run "$i"; done; fi
