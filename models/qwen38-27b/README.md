# qwen38-27b — Qwen3.8-27B-FP8

Dense 27B hybrid-attention VLM (16× Gated DeltaNet + 1× Gated Attention per block, 64
layers). FP8 weights (~28 GB). Native vision-language (images **and video**). Thinking with
real effort levels (low / medium / **xhigh**; the card aliases `high`/`max` up to xhigh) +
`preserve_thinking`. MTP-trained; served with MTP speculative decoding. **512K context**
(262144 native, YaRN 2×) with a **131072-token output cap**.

Served by vLLM **0.29.0** (pinned digest) across 2× L40S (TP2) per the official recipe:
`--max-model-len 524288 --hf-overrides <yarn 2x> --gpu-memory-utilization 0.90
--max-num-seqs 64 --kv-cache-dtype fp8 --enable-prefix-caching
--limit-mm-per-prompt image:64/video:4` + MTP spec decode. Always-on (`minReplicas: 1`,
max 6 — extra pods only under real concurrency). fp8 KV keeps the FlashInfer backend
(fastest giant prefills); the int4_per_token_head fallback trades prefill speed for a
1.78× larger KV pool (see CLAUDE.md).

Single-request 256K boundary validation passed 2026-09-09 (261888 input tokens, all three
markers recalled, 120.15 s); the 512K YaRN boundary passed 2026-09-15 on the lab (522240
input tokens, 3/3 markers, exact accounting, ~17 min one-shot prefill on the int4 path —
expect roughly a third of that on fp8). Both probes live on as the env-gated
`256K/512K boundary probe` check in `test.py`.

## Files
| File | Purpose |
|------|---------|
| `pvc.yaml` | PVC `qwen38-27b`, 60Gi RWX NFS (weights + helper venv) |
| `inferenceservice.yaml` | KServe ISVC: initContainer staging + pinned vLLM 0.29.0 + TP2 + YaRN 512K |
| `details.yaml` | v2 card ConfigMap (`qwen38-27b-details`) — catalog entry |
| `test.py` | Gateway battery: features, output limits, >32k output, long inputs, concurrency, recovery, env-gated boundary probe |
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
- `GPU KV cache size` — expect ~1.3–1.4M tokens per TP group (fp8 KV at util 0.90)
- YaRN: `max_model_len: 524288` in the args echo
- mamba/GDN state allocation line
- MTP acceptance metrics (`spec_decode_num_accepted/draft_tokens`)

Running `models/qwen38-27b/test.py` runs all API, output-limit and pressure checks,
including a forced >32k-token completion (~6 min) and `max_tokens=131072` acceptance.
Video checks report SKIP unless `VIDEO_URL` or `VIDEO_B64` supplies a fixture;
the near-boundary context probe reports SKIP unless `CONTEXT_GATEWAY_URL` and
`CONTEXT_ENGINE_URL` supply the internal origins (allocated diagnostic
environment — it sends exactly one full-boundary request).
Inspect scoped runtime logs separately for OOM/engine errors; the API test does
not perform SSH or claim to validate pod logs.
