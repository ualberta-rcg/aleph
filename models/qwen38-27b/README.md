# qwen38-27b — Qwen3.8-27B-FP8

Dense 27B hybrid-attention VLM (16× Gated DeltaNet + 1× Gated Attention per block, 64
layers). FP8 weights (~28 GB). Native vision-language (images **and video**). Thinking with
real effort levels (low / medium / xhigh) + `preserve_thinking`. MTP-trained; served with
MTP speculative decoding. 262K native context.

Served by vLLM **0.20.2** (the fleet-pinned digest, same as every other vLLM model — the
model declares arch `Qwen3_5ForConditionalGeneration`, already in 0.20.2) across 2× L40S (TP2) per the
official recipe: `--kv-cache-dtype fp8 --max-num-seqs 64 --max-model-len 262144
--gpu-memory-utilization 0.92 --enable-prefix-caching`. Always-on (`minReplicas: 1`,
max 2).

## Files
| File | Purpose |
|------|---------|
| `pvc.yaml` | PVC `qwen38-27b`, 60Gi RWX NFS (weights + helper venv) |
| `inferenceservice.yaml` | KServe ISVC: initContainer staging + vLLM v0.28.0 + TP2 |
| `details.yaml` | v2 card ConfigMap (`qwen38-27b-details`) — catalog entry |
| `test.py` | 36-check gateway battery (image+video+tools+effort levels) |
| `CLAUDE.md` | Model context + research findings |

## Deploy
```bash
# via aleph1 (172.26.92.43), each file in its own apply:
kubectl apply -f models/qwen38-27b/pvc.yaml
kubectl apply -f models/qwen38-27b/inferenceservice.yaml
kubectl apply -f models/qwen38-27b/details.yaml

# test through the public edge:
GW_URL=https://inference.vulcan.alliancecan.ca TYK_KEY=<key> MODEL=qwen38-27b \
    python3 models/qwen38-27b/test.py
```

## Verify at startup (pod logs)
- `GPU KV cache size` — expect ~1.3–1.5M tokens per TP group (fp8 KV)
- mamba/GDN state allocation line
- MTP acceptance metrics (`spec_decode_num_accepted/draft_tokens`)
