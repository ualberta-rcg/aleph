# qwen38-27b — Qwen3.8-27B-FP8

Dense 27B hybrid-attention VLM (16× Gated DeltaNet + 1× Gated Attention per block, 64
layers). FP8 weights (~28 GB). Native vision-language (images **and video**). Thinking with
real effort levels (low / medium / xhigh) + `preserve_thinking`. MTP-trained; served with
MTP speculative decoding. 262K native context.

Served by vLLM **0.20.2** (the fleet-pinned digest, same as every other vLLM model — the
model declares arch `Qwen3_5ForConditionalGeneration`, already in 0.20.2) across 2× L40S (TP2) per the
official recipe: `--kv-cache-dtype fp8 --max-num-seqs 64 --max-model-len 262144
--gpu-memory-utilization 0.88 --enable-prefix-caching`. Always-on (`minReplicas: 1`,
max 2).

Single-request 256K boundary validation passed on 2026-09-09: 261888 input tokens plus a 256-token output allowance, 33 generated tokens, all three markers recalled, 120.15 seconds, and no observed engine errors. See [measured scope and limitations](CONTEXT-256K-RESULT.md). Memory utilization stays at the OOM-hardened 0.88.

## Files
| File | Purpose |
|------|---------|
| `pvc.yaml` | PVC `qwen38-27b`, 60Gi RWX NFS (weights + helper venv) |
| `inferenceservice.yaml` | KServe ISVC: initContainer staging + pinned vLLM 0.20.2 + TP2 |
| `details.yaml` | v2 card ConfigMap (`qwen38-27b-details`) — catalog entry |
| `test.py` | Gateway battery: features, output limits, long inputs, concurrency and recovery |
| `CLAUDE.md` | Model context + research findings + OOM postmortem |

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

Running `models/qwen38-27b/test.py` runs all API, output-limit and pressure checks.
The pressure checks include long prefills, an eight-request concurrent burst,
long text with images/video, twenty mixed requests and a final health check.
Video checks report SKIP unless `VIDEO_URL` or `VIDEO_B64` supplies a fixture.
Inspect scoped runtime logs separately for OOM/engine errors; the API test does
not perform SSH or claim to validate pod logs. The dated 256K boundary result
above remains separate evidence; this battery does not retest that full boundary.
