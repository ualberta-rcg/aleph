# tinyllama

**Type**: Chat LLM (1.1B, llama.cpp GGUF, CPU)
**Model**: TheBloke/TinyLlama-1.1B-Chat-v1.0-GGUF (Q4_K_M quantization)
**Endpoint**: POST /v1/chat/completions (OpenAI-compatible)
**Runtime**: CPU, llama-cpp-python server

## Migration notes
- Ported from 232. Changes:
  - `nvidia.com/gpu.product: NVIDIA-L40S-SHARED` nodeSelector removed (CPU model).
  - `minReplicas: 1` → `0` + Knative scale-to-zero annotation added.
  - Inline `HF_TOKEN` → `secretKeyRef: hf-token`.
  - Added `--n_gpu_layers=0` arg to force CPU inference.
  - PVC: `tinyllama-models` (already nfs-client).
- Card already had `routing.k8s_name: tinyllama`.

## Key quirks
- Uses llama-cpp-python server (not vLLM). Serves OpenAI `/v1/chat/completions` and `/v1/models`.
- Q4_K_M quantization (~640MB). Very fast response on CPU (~270ms for short replies).
- Context: 4096 tokens. Model alias: `tinyllama-1.1b`.
- `--n_gpu_layers=0` essential — without it llama-cpp-python tries to use CUDA and fails.

## Validation
- POST /v1/chat/completions → "Hi!" (chat response). PASS. ~270ms.
- Catalog: id=tinyllama-1.1b, type=chat. PASS.
