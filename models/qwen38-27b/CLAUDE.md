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

**vLLM 0.29.0 effort plumbing (verified live 2026-09-15):** body-level `reasoning_effort`
AND `chat_template_kwargs.reasoning_effort` both reach the chat template now (0.20.2
ignored the kwargs form). Real efforts are **low/medium/xhigh** — the model rejects
`high` with its own 400 ("Supported types are xhigh (default), medium, and low"), so the
card aliases high/max UP to xhigh. `reasoning_effort: none` also works as an off switch;
`enable_thinking:false` via `chat_template_kwargs` remains the off path. Measured on the
sqrt-2 probe: rc_len 148/150/289 for low/medium/xhigh.

Sampling recs: thinking `temp=1.0 top_p=0.95 top_k=20`; non-thinking `temp=0.7 top_p=0.8
top_k=20 presence_penalty=1.5`.

## Our config vs the recipe

| Setting | Ours | Recipe / note |
|---|---|---|
| image | vLLM **0.29.0** digest `sha256:c291476…` (upgraded from fleet 0.20.2 on 2026-09-15 for real xhigh + 131k outputs) | 0.20.2 worked (arch in registry) but capped efforts at medium and its env-var attention override was inert |
| TP | 2 (whole GPUs, no gpumem) | recipe FP8 reference is TP4 on GB300; TP2 fits L40S pair (2 replicas per 4-GPU node) |
| `--max-model-len` | **524288** + YaRN 2× hf-override | 262144 native; HF card documents YaRN (factor 2 for ~512K). 512K boundary probe passed (markers recalled at 522,240 tok). Short-text sanity unchanged. Needs `VLLM_ALLOW_LONG_MAX_MODEL_LEN=1` |
| `--kv-cache-dtype fp8` | ✓ (FlashInfer backend) | **fallback: `int4_per_token_head` = 1.78× pool (2.44M tok, TRITON_ATTN) but giant one-shot prefills 1.6-4× slower; nvfp4 has NO backend on SM89 (tested — worker ValueError, crashloop)** |
| `--gpu-memory-utilization` | **0.90** | 0.92 (recipe) OOM-killed the engine on 0.20.2; since v0.21 CUDA-graph memory is accounted inside the util budget, 0.90-on-0.29 ≈ 0.893 effective — pressure-verified 2026-09-15 |
| `--max-num-seqs` | 64 | recipe; pool serves ~2.6 concurrent 512K / ~13 × 100K / ~85 × 16K sessions |
| `--enable-prefix-caching` | ✓ | recipe; pairs with preserve_thinking; follow-up turns skip the big prefill (91.8% hit rate observed live) |
| MTP | `{"method":"mtp","num_speculative_tokens":3}` | acceptance ~2.8-3.1; decode ~67 tok/s prose, ~110 tok/s counting |
| `--limit-mm-per-prompt` | image 64, video 4 | generous-but-safe in a 512K window (vLLM canon is 16/2); per-request video frame sampling via mm_processor_kwargs fps/do_sample_frames |
| `--reasoning-parser qwen3` / `--tool-call-parser qwen3_coder` | ✓ | without the reasoning parser, `<think>` blocks land in `content` |
| `--disable-custom-all-reduce` | ✓ | L40S NODE topology (PCIe, no NVLink P2P) |
| attention backend | auto → FlashInfer (logged) | the old `VLLM_ATTENTION_BACKEND=TRITON…` env is dropped — 0.20.2 ignored it; 0.29 has a real `--attention-backend` flag if pinning is ever needed |

## Gateway integration

- ISVC/PVC/card id: `qwen38-27b` (clean `<model>` naming).
- Card thinking: `mode: effort`, `default_effort: medium`, `on = {"reasoning_effort":
  "medium"}` (gateway setdefaults only when client didn't choose), `off =
  {"chat_template_kwargs": {"enable_thinking": false}}` (real off), `off_max_tokens: 2048`.
- Aliases: none/minimal/disabled → off; low/medium/xhigh real levels; high/max alias UP to
  **xhigh** (real on 0.29.0; callers never get a 400 — the model itself rejects literal
  "high").
- `strips_thinking: false`; usage logs keep reasoning lengths.
- Sampling defaults on the card follow thinking-mode recs (1.0/0.95/20); non-thinking recs
  (0.7/0.8/1.5 presence) documented in input_map + note.

## Verified boundaries

**256K (2026-09-09, live gateway):** 261888 rendered input tokens + 256 reserved; 33
generated, all three markers recalled, 120.15 s, zero restarts. **512K YaRN (2026-09-15,
lab):** 522240 input tokens, 3/3 markers, exact prompt accounting, finish=stop; first
token 1031.8 s on the int4/Triton path (expect roughly a third of that on fp8/FlashInfer).
Both are single synthetic text requests with thinking disabled — not concurrency or
arbitrary-document guarantees. The probe lives on as the env-gated boundary check in
`test.py` (needs `CONTEXT_GATEWAY_URL` + `CONTEXT_ENGINE_URL`, sends exactly one
full-boundary request, no retries).

## Measured (0.20.2 @ 0.88 on 2026-08-26; 0.29.0 @ 0.90 on 2026-09-15 lab)

- GPU KV cache per TP group: 1,268,249 tok (0.20.2/fp8/0.88) → 1,265,320 (0.29/fp8/0.90,
  262K len) → 2,254,438 (0.29/int4/0.90, 262K) → 2,439,078 (0.29/int4/0.90, 512K).
  fp8@512K expected ~1.3-1.4M (read the startup line after deploy).
- Weights 14.66→14.84 GiB/GPU; engine init ~200 s both versions (weights+venv cached on
  PVC; compile cache NOT persisted).
- MTP drafter loads; cudagraph mode auto-drops FULL_AND_PIECEWISE→PIECEWISE under
  spec-decode; min_p/logit_bias are inert with spec decode.
- Prefix caching forces mamba cache 'align' mode — upstream experimental; first suspect
  if outputs repeat/blank. Engine-args docs warn align + spec-decode is unsupported
  territory; it runs and passed pressure — keep an eye on it.
- 0.29 warns the checkpoint ships no FP8 KV/q scales (k_scale=1.0 defaults). Quality
  gates all green with them (temp0 answers, markers, tools). `--calculate-kv-scales`
  CRASHED the 0.29 worker (tested 2026-09-15 — do not re-add); the proper fix is an
  offline llm-compressor calibrated checkpoint (future work).
- 0.29's CUDA-graph memory profiling reserves ~0.8% effective util; disabling
  (`VLLM_MEMORY_PROFILER_ESTIMATE_CUDAGRAPHS=0`) is NOT recommended (removes graph
  accounting — the old OOM class).

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

Historical proof from `stress.py` (API checks now in `test.py`) — 24.5k-token prefill (bigger than the crash batch), prefix-cache
repeat, 8×8k concurrent burst, 12k+image, 12k+video, 20-mix sustained — **9/9 PASS, zero
OutOfMemoryError/EngineDead in logs**. No dial-downs (batched-tokens stayed 16384, mm
limits 16/2, seqs 64) were needed at 0.88.

## Gotchas

- **Model default effort is xhigh** — the card still defaults callers to medium (xhigh
  burns large reasoning budgets); users can now explicitly request xhigh and get it.
- MXFP4 quantization does not load on Nvidia (recipe known issue) — we use FP8, unaffected.
- **nvfp4 KV has no attention backend on SM89** (tested 2026-09-15: worker ValueError →
  crashloop). int4_per_token_head DOES work (TRITON_ATTN) but slows giant one-shot
  prefills ~1.6-4× — that's why fp8/FlashInfer is the deployed choice.
- Never request `nvidia.com/gpumem` on this model: HAMi vGPU mode breaks multi-GPU P2P.
- Whole GPUs: one replica = 2 L40S; maxReplicas 6 = 12 L40S at absolute peak, taken only
  under real concurrency (Knative scaleTarget 16).
- A 512K one-shot first paste costs minutes of prefill ONCE; follow-up turns hit the
  prefix cache (seconds). The usage pattern that hurts is many users each pasting huge
  NEW contexts simultaneously.

## Deploy / test

```bash
# apply separately: pvc -> inferenceservice -> details (aleph1)
GW_URL=https://inference.vulcan.alliancecan.ca TYK_KEY=<key> MODEL=qwen38-27b \
    python3 models/qwen38-27b/test.py
# video check: VIDEO_URL=<small mp4> … or VIDEO_B64=<base64>
```

**IMPORTANT: When changing inferenceservice.yaml, update details.yaml to match**
(context window, max tokens, vision flags).
