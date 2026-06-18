# protgpt2 — Model Context

ProtGPT2 (~1.5B, GPT-2 architecture) generates **novel protein sequences** (amino-acid strings) from a seed. A custom (non-OpenAI) generation server — **not** a chat model.

## Serving
- Custom FastAPI server (image `python:3.11-slim`, venv at `/data/venv`) on a HAMi vGPU slice (1× L40S, ~2 GB VRAM). Server code ships as a ConfigMap.
- Weights on PVC `protgpt2-data`; `transformers.GPT2LMHeadModel` + `AutoTokenizer`, float16.
- **NOT vLLM.** No streaming (`routing.no_stream: true`). `minReplicas: 0` + 15m idle retention; cold start ~1-2 min.

## Gateway integration
- Card `details.yaml`: **Template B (custom science)**, `schema_version: 2`. Primary endpoint `POST /v1/completions`.
- Behavior gates: no vision, no tools, no system prompt, no streaming, no reasoning. `type: chat` with a custom pass-through endpoint (gateway routes `/v1/completions` straight to the server).
- Input `{prompt, max_tokens, temperature, num_sequences}` → output `{sequences: [amino-acid strings]}`.

## Deploy / test
```bash
kubectl apply -f models/protgpt2/         # details.yaml + inferenceservice.yaml + pvc.yaml
cat models/protgpt2/test.py | kubectl exec -i -n models deploy/model-gateway -c gateway -- env MODEL=protgpt2 python3 -
```
Last result: **6 pass / 1 expected / 0 fail** (custom generation battery: wake + protein gen + continue-from-prompt + num_sequences + temperature + health + catalog).

## Notes
- **Requires a non-empty seed prompt** (e.g. `"prompt":"M"`, a start methionine). An empty prompt crashes the server with a 500 (`reshape tensor of 0 elements`).
- Non-OpenAI generation only — chat/tools/vision/Anthropic batteries don't apply.
- Validate generated sequences downstream (folding/stability) before experimental use.
