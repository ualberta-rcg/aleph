# Gemma 4 31B (dense)

Google **Gemma 4 31B** (`google/gemma-4-31B-it`) — dense 30.7B multimodal (text +
image + video frames), native system role, configurable thinking, native tool
calling. Deployed at **full native 256K context** — its differentiator vs the
fleet's gemma-4-26b-a4b MoE (131K). Dense ⇒ slower per token than the MoE; value =
giant context + tools + system role. Released 2026-04-02.

## Serving config

- **Engine**: vLLM `vllm/vllm-openai:v0.32.0` (operator order 2026-10-27; CUDA 13
  image — node drivers verified 595.71.05/CUDA 13.2). Arch
  `Gemma4ForConditionalGeneration` = same class as the prod 26B.
- **GPU layout**: **TP2 whole devices** — `nvidia.com/gpu: "2"`, no gpumem;
  `--disable-custom-all-reduce` (L40S PCIe recipe). On-the-fly `--quantization fp8`
  (62 GB bf16 ckpt → ~31 GB) + `--kv-cache-dtype fp8` (qwen38 pattern).
- **Flags**: `--max-model-len 262144` (FULL native), util 0.93, `--max-num-seqs 8`,
  `--max-num-batched-tokens 8192`, prefix caching, `--limit-mm-per-prompt
  {"image":32,"video":8}` (matched to molmo2-8b; Gemma4 images ~70–1120 tokens each),
  `gemma4` tool + reasoning parsers.
- **Scaling**: scale-to-zero, min 0 / **max 1** (operator scaling rule — a pending
  TP2 replica HAMi-reserves whole cards; see qwen35-122b incident 2026-10-27),
  scaleTarget 8.

## Files

| File | Purpose |
|---|---|
| `pvc.yaml` | 80Gi RWX `nfs-models` PVC `gemma-4-31b` (bf16 ckpt ~62 GB + venv) |
| `inferenceservice.yaml` | ISVC: gemma-4 init pattern + qwen38 TP2/hardening |
| `details.yaml` | v2 card — vision/tools/system/thinking true, ctx 262144 |
| `test.py` | Full vision+thinking+tools battery (from 26b) + workload block incl. ~60k-token context test |
| `README.md` / `CLAUDE.md` | This record / research + quirks |

## Deploy

```bash
K='export PATH=$PATH:/var/lib/rancher/rke2/bin; export KUBECONFIG=/etc/rancher/rke2/rke2.yaml; kubectl apply -f -'
cat models/gemma-4-31b/pvc.yaml              | sudo ssh root@172.26.92.43 "$K"
cat models/gemma-4-31b/inferenceservice.yaml | sudo ssh root@172.26.92.43 "$K"
cat models/gemma-4-31b/details.yaml          | sudo ssh root@172.26.92.43 "$K"
```

Test (first staging: ~62 GB download + v0.32.0 image pull; engine init incl. fp8
quantization — expect 15–30 min cold start):

```bash
source ~/.aleph_tyk.env
GW_URL=https://inference.vulcan.alliancecan.ca TYK_KEY=$TYK_KEY MODEL=gemma-4-31b \
  python3 models/gemma-4-31b/test.py > /tmp/gemma-4-31b-test.log 2>&1 &
```

## Verify at startup (pod logs)

- `GPU KV cache size` — must be LARGE (≈hundreds of K tokens; v0.30.x had a Gemma-4
  KV-layout bug shrinking it ~1/6 — if it looks tiny, that bug is still live)
- `Model loading took ~31 GiB` total across TP ranks (fp8); engine init incl. quant

## Quirks

- Thinking-off still emits an EMPTY thought block on non-E2B/E4B — `gemma4`
  reasoning parser must strip it (battery's think_off verifies).
- Video = frame sequences (`video_url` data URIs; ≤8/prompt). Images base64 only.
- Dense ⇒ ~15 tok/s-class generation (community reports) — do not expect MoE speed.
- max_completion_tokens 8192; managed thinking via `enable_thinking` (26b card pattern).

## Status

- **2026-10-27: DEPLOYED + PROVEN** (first on vLLM v0.32.0). Proof battery 37 PASS / 3 EXP / 0 FAIL incl. workload block (32-image accept, 33-image clean 400, 9k prefill, ~60k-token context probe, 8-way burst, sustained 20-mix, zero OOM/EngineDead); clean delete + repo-file redeploy + re-run passed. KV 747,909 tokens = 2.85x at full 262K. Deployed ON rack09-01 — the live proof the WW reprovision fixed the istio exit-126 bug.
