# tinyllama-1-1b

**Type**: Chat LLM (1.1B, llama.cpp GGUF, CPU)
**Model**: TheBloke/TinyLlama-1.1B-Chat-v1.0-GGUF (Q4_K_M quantization)
**Endpoint**: POST /v1/chat/completions (OpenAI-compatible)
**Runtime**: CPU, llama-cpp-python server

## Naming
- Card id: `tinyllama-1-1b`
- ISVC name: `tinyllama-1-1b`
- PVC: `tinyllama-1-1b-models`
- Model alias: `tinyllama-1-1b`
- All names match — no `upstream_model_id` mapping needed.

## Key quirks
- Uses llama-cpp-python server (not vLLM). Serves OpenAI `/v1/chat/completions` and `/v1/models`.
- Q4_K_M quantization (~640MB). Very fast response on CPU (~270ms for short replies).
- Context: 4096 tokens.
- `--n_gpu_layers=0` essential — without it llama-cpp-python tries to use CUDA and fails.
- Card has `no_stream: true` — gateway forces stream=false upstream.
- CPU-only, no GPU needed.
- Card says `scale_to_zero: false` but ISVC has `minReplicas: 0` — effectively scale-to-zero. Card needs update.

## Migration notes (from POC 232)
- Ported from 232. Changes:
  - `nvidia.com/gpu.product: NVIDIA-L40S-SHARED` nodeSelector removed (CPU model).
  - `minReplicas: 1` → `0` + Knative scale-to-zero annotation added.
  - Inline `HF_TOKEN` → `secretKeyRef: hf-token`.
  - Added `--n_gpu_layers=0` arg to force CPU inference.
  - PVC: renamed from `tinyllama-models` to `tinyllama-1-1b-models`.
- Card updated to v2 schema with input_map/output_map.

## Validation (2026-06-10)
- 14/14 tests passed through gateway (OpenAI + Anthropic endpoints)
- Basic chat, system prompt, temperature, streaming (no_stream), tools rejected, vision rejected, reasoning effort ignored, Anthropic basic/system/tools/vision
