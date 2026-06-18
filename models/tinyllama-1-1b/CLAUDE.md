# tinyllama-1-1b — Model Context

TinyLlama 1.1B Chat (GGUF Q4_K_M) — a tiny, fast chat model served on **CPU** via llama-cpp-python (not vLLM). Good for quick tests and simple tasks; the cluster's only CPU model.

## Serving
- Image `ghcr.io/abetlen/llama-cpp-python`, GGUF Q4_K_M (~640 MB) on PVC `tinyllama-1-1b-models`. Zephyr prompt template.
- **CPU only** — `--n_gpu_layers=0` is mandatory (without it llama-cpp-python tries CUDA and fails). No GPU request.
- No streaming: `routing.no_stream: true` → the gateway forces `stream=false` upstream and returns a normal JSON response. `needs_json_fixing: true` (gateway repairs malformed JSON from the server).
- `serialize: true` (single in-flight request). `minReplicas: 0` + 15m idle retention; cold start ~30 s (model is tiny + already on PVC).

## Gateway integration
- Card `details.yaml`: **Template A (no_stream variant)**, `schema_version: 2`. Endpoints OpenAI `/v1/chat/completions` + `/v1/models`.
- Behavior gates: no vision, no tools, no streaming, no reasoning; system prompts supported.
- A client `stream:true` request is **not** an error — the gateway returns a single non-streaming JSON completion.

## Deploy / test
```bash
kubectl apply -f models/tinyllama-1-1b/     # details.yaml + inferenceservice.yaml + pvc.yaml
cat models/tinyllama-1-1b/test.py | kubectl exec -i -n models deploy/model-gateway -c gateway -- env MODEL=tinyllama-1-1b python3 -
```
Last result: **18 pass / 4 expected / 0 fail / 1 skip** (comprehensive battery; the 4 expected = tools + vision rejected on both endpoints).

## Notes
- Small model — fine for simple/deterministic tasks, weak on complex reasoning or long instructions.
- CPU-bound: latency scales with output length; keep `max_tokens` modest.
