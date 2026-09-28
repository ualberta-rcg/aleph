# deepseek-v4-flash (HF checkpoint) — DeepSeek-V4-Flash-0731

> **STATUS: BLOCKED + REMOVED FROM CLUSTER (2026-09-28) — DeepSeek-V4-Flash is not
> really L40S-compatible.** Stock vLLM (v0.30.0, the newest release) hard-wires the
> DeepSeek-V4 *hyperconnection* op to DeepGEMM, which asserts
> `Unsupported architecture` on SM89 — twice verified, including with
> `--linear-backend=triton` (the op ignores the backend setting). The MoE (Marlin MXFP4),
> KV (fp8_ds_mla) and indexer paths all select SM89-safe kernels fine; this one op is the
> blocker. Serving it on L40S requires a patched build (the unmerged upstream
> portability PRs, or a fork). Files kept as the record; nothing deployed.

## Purpose and supported API

DeepSeek-V4-Flash-0731: 284B total / 13B active MoE (MXFP4 routed experts + FP8 attention,
~155.5 GiB, 48 shards, MIT, ungated) served from
`deepseek-ai/DeepSeek-V4-Flash-0731` on **4× L40S whole devices (TP4)** with **stock
`vllm/vllm-openai:v0.30.0`** — the same pattern as the rest of the vLLM fleet. Text-only
chat + reasoning (always-on; effort `low`/`high`/`max`, card aliases `none`→low,
`medium`→high, `xhigh`→max) + tool calling via the `deepseek_v4` parsers. Public model id:
`deepseek-v4-flash` (k8s objects carry the `-hf` suffix; the card routes via
`routing.k8s_name`). Context 131072, output cap 32768, max-num-seqs 4 (weights leave
~25-30 GiB for KV — low concurrency by design; expect queueing beyond 4 concurrent
requests, not scale-out). Recommended sampling: temperature 1.0, top_p 0.95.

Predecessor: `models/deepseek-v4-flash/` — the NGC NIM attempt, removed from the cluster
2026-09-27 (NGC support matrix is H100+ only).

## Deploy and use

```bash
# via aleph1 (172.26.92.43), each file in its own apply:
kubectl apply -f models/deepseek-v4-flash-hf/pvc.yaml
kubectl apply -f models/deepseek-v4-flash-hf/inferenceservice.yaml
kubectl apply -f models/deepseek-v4-flash-hf/details.yaml

# test through the public edge (background it; the full battery is long):
GW_URL=https://inference.vulcan.alliancecan.ca TYK_KEY=<key> MODEL=deepseek-v4-flash \
    python3 models/deepseek-v4-flash-hf/test.py
```

The first-ever boot builds the helper venv and downloads the 155.5 GiB of weights inside
the ISVC's initContainer (one-time; the 3600s progress deadline covers it). Every later
wake is engine-init only, ~5-10 min like the other big TP4 models.

Example request:

```bash
curl -s https://inference.vulcan.alliancecan.ca/v1/chat/completions \
  -H "Authorization: Bearer <TYK_KEY>" -H "Content-Type: application/json" \
  -d '{"model": "deepseek-v4-flash", "messages": [{"role": "user", "content": "Hello"}],
       "max_tokens": 128}'
```

## Tested configuration

- Runtime: `vllm/vllm-openai:v0.30.0` (digest-pin at commit time), TP4 + whole devices
  (`nvidia.com/gpu: "4"`, no gpumem), `--kv-cache-dtype fp8`, `--max-model-len 131072`,
  `--gpu-memory-utilization 0.95`, `--max-num-seqs 4`, `--disable-custom-all-reduce`
  (L40S PCIe topology), `VLLM_ATTENTION_BACKEND=TRITON_ATTN_VLLM_V1`.
- Storage: PVC `deepseek-v4-flash-hf`, 200Gi RWX `nfs-models` (weights + helper venv).
- Scaling: scale-to-zero, min 0 / max 1, scaleTarget 4, idle 15m.
- First boot marker recording (attention/MoE backend selection, KV pool size) — see
  CLAUDE.md open items.

## Validation and limitations

- 2026-09-28 (first deploy attempt, removed): two full boots on 4× L40S (rack09-01),
  stock `vllm/vllm-openai:v0.30.0`. Weight staging verified (155.5 GiB in ~6 min via the
  initContainer), architecture resolves, MARLIN MXFP4 MoE + fp8_ds_mla KV + FP8 indexer
  all selected — then engine init dies on
  `Assertion error (deepgemm-src/csrc/apis/hyperconnection.hpp:56): Unsupported
  architecture`. Same assert with and without `--linear-backend=triton`. No inference
  performed; the battery never ran. ISVC, card and PVC removed from the cluster.
- Known design limits (had it served): concurrency cap 4 per pod (single replica);
  vision unsupported (rejected 400 by the gateway).
