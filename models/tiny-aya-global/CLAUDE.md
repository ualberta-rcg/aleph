# tiny-aya-global Notes

## Purpose
Multilingual chat LLM (23+ languages) from Cohere's Aya family. Requested by Montaser (Amii).

## Runtime
- Image: `vllm/vllm-openai:v0.20.2`
- Args: `serve /data/model --served-model-name tiny-aya-global --port 8080 --tensor-parallel-size 1 --max-model-len 8192 --dtype bfloat16 --gpu-memory-utilization 0.90 --trust-remote-code`
- API: `POST /v1/chat/completions`, `GET /v1/models`
- HF: `CohereLabs/tiny-aya-global` (3.35B, cohere2, bf16, gated)
- GPU: HAMi slice — `nvidia.com/gpu: "1"` + `nvidia.com/gpumem: "16384"` (~7GB weights + KV cache)

## Resources
- CPU: 4/8, Memory: 16Gi/32Gi
- GPU: 1× L40S slice (16 GiB gpumem)
- Storage: 25Gi RWX PVC (`nfs-models`)

## Config (from HF config.json)
- hidden_size: 2048, layers: 36, vocab: 262144
- max_position_embeddings: 8192
- rope_theta: 50000
- arch: Cohere2ForCausalLM (cohere2)

## Quirks
- Gated repo — needs HF token with access granted
- cohere2 arch in vLLM v0.20.2 — verify support (command-r-7b uses cohere, proven)
