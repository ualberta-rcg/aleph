# tinyllama — Test Report

Cluster 230, gateway `http://10.43.79.101:80`. Type: chat LLM (CPU llama.cpp). id `tinyllama-1.1b`.

## Scale-up
- Cold start: downloads GGUF (TheBloke/TinyLlama-1.1B-Chat-v1.0-GGUF, Q4_K_M) to PVC,
  starts llama-cpp-python server. `3/3 Running`. ~3-4 min cold start.

## Endpoint tests (PASS)

### POST /v1/chat/completions
```bash
curl -s -X POST $GW/v1/chat/completions -H 'Content-Type: application/json' \
  -d '{"model":"tinyllama-1.1b","messages":[{"role":"user","content":"Say hi in 3 words:"}],"max_tokens":10}'
```
→ HTTP 200, `choices[0].message.content="Hi!"`. Latency ~270ms. PASS.

### Catalog
- `GET /v1/models?all=true` → `tinyllama-1.1b` discovered, type=chat. PASS.

## Migration fix
- Removed GPU nodeSelector (`nvidia.com/gpu.product: NVIDIA-L40S-SHARED`).
- Added `--n_gpu_layers=0` to ensure CPU-only inference.
- Set `minReplicas: 0` for scale-to-zero.

## Card parity
id=tinyllama-1.1b, k8s_name=tinyllama, type=chat, gpu=false,
endpoint /v1/chat/completions (OpenAI-compatible), context=4096.
