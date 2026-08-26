# Qwen3.8-27B-FP8 — Model Context

## What This Model Does

Qwen3.8-27B-FP8 — dense 27B with **hybrid attention**: 16×(Gated DeltaNet → FFN) then 1×
(Gated Attention → FFN) per block, 64 layers, hidden 5120. GDN: 48 V-heads / 16 QK-heads
(head dim 128); full-attn layer: 24 Q-heads / 4 KV-heads (head dim 256). Fine-grained FP8
(block 128). Native VLM: images + video (fps / `do_sample_frames` configurable). Thinking
on by default; **real effort levels** (xhigh default / medium / low) + `preserve_thinking`
(retains reasoning across turns, default on). MTP-trained (multi-step multi-token
prediction). 262K native context (1M via YaRN).

## Source

- HuggingFace: https://huggingface.co/Qwen/Qwen3.8-27B-FP8 (Apache-2.0)
- vLLM recipe: https://recipes.vllm.ai/Qwen/Qwen3.8-27B

## Chat-template kwargs (verified from chat_template.jinja)

| Kwarg | Values | Default |
|---|---|---|
| `enable_thinking` | bool | `true` |
| `reasoning_effort` | `xhigh`/`medium`/`low` | **`xhigh`** (too slow on L40S → card defaults medium) |
| `preserve_thinking` | bool | `true` |

**vLLM 0.20.2 effort plumbing (verified live):** body-level `reasoning_effort` reaches the
chat template; `chat_template_kwargs.reasoning_effort` is **ignored**. The OpenAI protocol
enum only admits `none/low/medium/high`, while the model side only accepts
`low/medium/xhigh` — so through the API only **low/medium** are real efforts. `high` and
`xhigh`/`max` alias down to `medium` on the card (callers never get a 400); true xhigh
requires a newer vLLM. `enable_thinking` via `chat_template_kwargs` DOES work (think-OFF
path uses it).

Sampling recs: thinking `temp=1.0 top_p=0.95 top_k=20`; non-thinking `temp=0.7 top_p=0.8
top_k=20 presence_penalty=1.5`.

## Our config vs the recipe

| Setting | Ours | Recipe / note |
|---|---|---|
| image | fleet digest = vLLM **0.20.2** (transformers 5.8.0) | model declares arch `Qwen3_5ForConditionalGeneration` — in 0.20.2's registry; card floor is transformers ≥5.4. Fallback ladder if init fails: v0.28.0 → nightly |
| TP | 2 (whole GPUs, no gpumem) | recipe FP8 reference is TP4 on GB300; TP2 fits L40S pair (2 replicas per 4-GPU node) |
| `--max-model-len` | 262144 | full native |
| `--kv-cache-dtype fp8` | ✓ | recipe |
| `--gpu-memory-utilization` | **0.88** | 0.92 (recipe) OOM-killed the engine — see postmortem below |
| `--max-num-seqs` | 64 | recipe; ~9-10 concurrent 128k sessions per replica at 0.88 KV |
| `--enable-prefix-caching` | ✓ | recipe; pairs with preserve_thinking |
| MTP | `{"method":"mtp","num_speculative_tokens":3}` | drop first if the build rejects it or it conflicts |
| `--limit-mm-per-prompt` | image 16, video 2 | video eats KV; kept modest |
| `--reasoning-parser qwen3` / `--tool-call-parser qwen3_coder` | ✓ | without the reasoning parser, `<think>` blocks land in `content` |
| `--disable-custom-all-reduce` | ✓ | L40S NODE topology (PCIe, no NVLink P2P) |
| `VLLM_ATTENTION_BACKEND=TRITON_ATTN_VLLM_V1` | ✓ | SM89; FA3 unavailable |

## Gateway integration

- ISVC/PVC/card id: `qwen38-27b` (clean `<model>` naming).
- Card thinking: `mode: effort`, `default_effort: medium`, `on = {"reasoning_effort":
  "medium"}` (gateway setdefaults only when client didn't choose), `off =
  {"chat_template_kwargs": {"enable_thinking": false}}` (real off), `off_max_tokens: 2048`.
- Aliases: none/minimal/disabled → off; low/medium/high/xhigh real levels (max → xhigh).
- `strips_thinking: false`; usage logs keep reasoning lengths.
- Sampling defaults on the card follow thinking-mode recs (1.0/0.95/20); non-thinking recs
  (0.7/0.8/1.5 presence) documented in input_map + note.

## Measured on first deploy (2026-08-26, cluster 43)

- **GPU KV cache: 1,268,249 tokens per TP group at util 0.88** (fp8 KV; was 1,361,977 at 0.92) → ~9-10 concurrent 128k sessions/replica.
- Weights 14.66 GiB/GPU; engine cold init ~8 min (weights+venv cached on PVC; compile cache is NOT persisted).
- MTP drafter loads (66 shards); cudagraph mode auto-drops FULL_AND_PIECEWISE→PIECEWISE under spec-decode; min_p/logit_bias are inert with spec decode.
- Prefix caching forces mamba cache 'align' mode — upstream experimental; first suspect if outputs repeat/blank.
- L40S has no tuned W8A8 block-FP8 kernel config for N=7168,K=5120 (default kernel used; perf note).

## Postmortem — 2026-08-26 engine death (why util is 0.88 + liveness is tight)

At `gpu-memory-utilization 0.92` the card sat at ~1.3 GiB free (weights 14.7 + KV pool fill
92%). The first large chunked-prefill batch OOM'd inside `w8a8_triton_block_scaled_mm`
(532 MiB GEMM output alloc, 1.0-1.5 GiB more lost to allocator fragmentation) →
`EngineDeadError` → every later request hung or 500'd while the pod kept 2 whole L40S for
hours (liveness took ~5+ min to kill, and the restart path was muddy). Requests that hang
never reach usage.log, so the log showed a healthy battery then a 4-hour gap.

Fix (all in the ISVC): util **0.88** (~3.4 GiB headroom), `PYTORCH_CUDA_ALLOC_CONF=
expandable_segments:True` (fragmentation), liveness `periodSeconds 15 / failureThreshold 2`
(dead engine recycles in ~1-2 min; restart ≈ 8 min engine init, no re-download).

Proof: `stress.py` — 24.5k-token prefill (bigger than the crash batch), prefix-cache
repeat, 8×8k concurrent burst, 12k+image, 12k+video, 20-mix sustained — **9/9 PASS, zero
OutOfMemoryError/EngineDead in logs**. No dial-downs (batched-tokens stayed 16384, mm
limits 16/2, seqs 64) were needed at 0.88.

## Gotchas

- **Model default effort is xhigh** — 262k-token reasoning budget is far too slow on L40S;
  the card exists mainly to default callers down to medium.
- MXFP4 quantization does not load on Nvidia (recipe known issue) — we use FP8, unaffected.
- Never request `nvidia.com/gpumem` on this model: HAMi vGPU mode breaks multi-GPU P2P.
- Whole GPUs: one replica = 2 L40S; maxReplicas 2 = 4 L40S at peak.

## Deploy / test

```bash
# apply separately: pvc -> inferenceservice -> details (aleph1)
GW_URL=https://inference.vulcan.alliancecan.ca TYK_KEY=<key> MODEL=qwen38-27b \
    python3 models/qwen38-27b/test.py
# video check: VIDEO_URL=<small mp4> … or VIDEO_B64=<base64>
```

**IMPORTANT: When changing inferenceservice.yaml, update details.yaml to match**
(context window, max tokens, vision flags).
