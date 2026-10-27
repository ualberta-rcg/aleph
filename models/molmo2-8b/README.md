# Molmo2-8B

Ai2's **Molmo2-8B** — the largest Molmo 2 model (~9B params: Qwen3-8B LLM backbone +
SigLIP 2 `so400m` vision encoder). Image + **video** understanding, **pointing**,
tracking, multi-image. Native 36,864-token context. Released Dec 2025; no thinking mode,
no tool calling. Beats much larger models on video grounding (32.9% video-pointing vs
17% for Gemini 2.5 Pro per Ai2). Apache-2.0 weights, but training data includes
third-party datasets restricted to academic/non-commercial use.

## Serving config

- **Engine**: vLLM, image `vllm/vllm-openai:v0.28.0` (operator order 2026-10-27 —
  first model on 0.28.0; fleet pin remains 0.20.2 for older models). Native support
  since v0.15.0 (`Molmo2ForConditionalGeneration`).
- **GPU layout**: TP1 **whole device** — `nvidia.com/gpu: "1"`, NO gpumem (operator
  rule: at ~44 GB asks, request a card). Checkpoint is fp32 ~36 GB; forced
  `--dtype bfloat16` → 16.1 GiB weights. No `--disable-custom-all-reduce` (TP1).
- **Flags**: `--max-model-len 36864` (native), `--gpu-memory-utilization 0.93`,
  `--max-num-seqs 8`, `--max-num-batched-tokens 36864` (**mandatory**: vLLM 0.28 MM
  budget requires ≥ max_tokens_per_mm_item 31872), `--enable-prefix-caching`,
  `--limit-mm-per-prompt {"image":32,"video":8}` (64 images starved KV — encoder
  reservation), `--trust-remote-code` (auto_map processor code).
  Measured: KV 3.77 GiB = 54,928 tokens (1.49× full-ctx concurrency); engine init 60 s.
- **Scaling**: scale-to-zero, min 0 / max 2, scaleTarget 8 (== max-num-seqs).
- KV bf16; fallback if concurrency ever bites: `--kv-cache-dtype=fp8` (qwen38 pattern).

## Files

| File | Purpose |
|---|---|
| `pvc.yaml` | 60Gi RWX `nfs-models` PVC `molmo2-8b` (fp32 weights ~36 GB + venv) |
| `inferenceservice.yaml` | ISVC: gemma-4 init pattern (venv+weights on PVC) + qwen38 hardening |
| `details.yaml` | v2 card — vision true, tools false, reasoning false, ctx 36864 |
| `test.py` | Non-reasoning auto-detecting battery (from qwen25-vl-72b-awq) |
| `README.md` | This file — deploy record |
| `CLAUDE.md` | Research notes + quirks |

## Deploy

```bash
K='export PATH=$PATH:/var/lib/rancher/rke2/bin; export KUBECONFIG=/etc/rancher/rke2/rke2.yaml; kubectl apply -f -'
cat models/molmo2-8b/pvc.yaml              | sudo ssh root@172.26.92.43 "$K"
cat models/molmo2-8b/inferenceservice.yaml | sudo ssh root@172.26.92.43 "$K"
cat models/molmo2-8b/details.yaml          | sudo ssh root@172.26.92.43 "$K"
```

Test through the public edge (first run stages ~36 GB to the PVC, 5–20 min):

```bash
source ~/.aleph_tyk.env
GW_URL=https://inference.vulcan.alliancecan.ca TYK_KEY=$TYK_KEY MODEL=molmo2-8b \
  python3 models/molmo2-8b/test.py > /tmp/molmo2-8b-test.log 2>&1 &
```

## Verify at startup (pod logs)

- `GPU KV cache size: 54,928 tokens` / `Available KV cache memory: 3.77 GiB` (util 0.93, whole card)
- `Model loading took 16.14 GiB` / engine init ~60 s (first v0.28.0 image pull on a node adds minutes)

## Quirks

- **fp32 checkpoint** — never drop `--dtype bfloat16` (36 GB fp32 would blow the slice).
- Images must be **base64 data URIs** (`data:image/png;base64,…`) — no external URLs.
- **No system role**: Molmo2's template requires strict user/assistant alternation —
  system messages are a clean 400 (card `supports_system_prompt: false`).
- Video goes through `video_url` data-URI content blocks (server accepts up to 8);
  gateway video passthrough still needs a real-video manual test (battery uses images).
- Multi-image verified to the full 32 limit; 33+ → clean 400.
- No reasoning parser needed; empty thought blocks are not emitted (not a thinking model).

## Status

- **2026-10-27: DEPLOYED + PROVEN** (first model on vLLM v0.28.0). Battery
  24 PASS / 5 EXP / 0 FAIL (1 SKIP = known fleet embed-guard artifact); workload
  section green (32-image limit, 9k-token prefill, 8-way burst, sustained 20-mix);
  clean delete + repo-file redeploy + battery re-run passed. Scale-to-zero,
  wakes on request. Settings journey + measured numbers in CLAUDE.md.
