# molmo2-8b — research + quirks

## Model research (2026-10-27, pre-deploy)

- **HF**: `allenai/Molmo2-8B` (Dec 16, 2025). Largest of the public family: Molmo2-4B,
  Molmo2-8B, Molmo2-VideoPoint-4B, MolmoAct2 (robotics). No 72B-class Molmo2 exists.
  vLLM docs also list a `Molmo2-O` but its HF repo 401s (gated/unreleased) — ignore.
- **Architecture**: `Molmo2ForConditionalGeneration`, model_type `molmo2`.
  Qwen3-8B backbone + SigLIP 2 (so400m-patch14-384) vision encoder. ~9B total.
- **config.json**: dtype **float32** (the fp32 checkpoint is why we force bf16);
  `auto_map` → custom `configuration_molmo2` / `modeling_molmo2` code in the repo
  (vLLM has a native implementation since **v0.15.0** —
  vllm/model_executor/models/molmo2 — so `--trust-remote-code` is belt-and-braces
  for the processor side); `max_position_embeddings` 36864.
- **vLLM support**: native since v0.15.0 (fleet pin 0.20.2 ≥ that). Deployed on
  **v0.28.0** per operator order 2026-10-27 (user chose it; qwen38-27b actually runs
  a v0.29.0 sha-digest pin — if we ever align, resolve the v0.29.0 digest and pin by
  digest, not tag).
- **Guide flags** (overshoot.ai deploy article): `--trust-remote-code --dtype bfloat16
  --max-model-len 36864 --max-num-batched-tokens 36864 --gpu-memory-utilization 0.9`.
  We use `--max-num-batched-tokens 8192` instead (activation-spike safety on a
  40 GB slice; raise if pressure shows headroom).
- **License caveat**: Apache-2.0 weights, but training data includes third-party
  datasets limited to academic/non-commercial research — flagged in the card catalog.

## Sizing math (L40S 46 GB, slice gpumem 40960)

- bf16 weights ~19 GB; util 0.90 → ~36.9 GB budget → ~17.9 GB KV.
- Qwen3-8B backbone KV: 36 layers × 8 KV heads × 128 dim × 2 (K+V) × 2 B = ~147 KB/token
  bf16 → pool ≈ 115K tokens ≈ 3.1 concurrent full-36K sessions. Prefix caching on.
- No kv-cache fp8: pool is already 3× context; skip the extra failure mode.

## Quirks / watch-items

- fp32 checkpoint — `--dtype bfloat16` is mandatory.
- Battery base: qwen25-vl-72b-awq/test.py (non-reasoning auto-detecting, vision).
- Tools: unsupported (card `supports_tools: false`, battery expects 400 rejection).
- Thinking: none (`thinking.mode: "none"`).
- Video/pointing (`video_url` data URIs, `max_fps=8` for best tracking per Ai2):
  server accepts video via `--limit-mm-per-prompt {"video":4}`, but **gateway
  video passthrough is unverified** — manual curl during pressure before advertising.
- Multi-image limit 16/prompt (gemma-4-like; qwen38 allows 64 but has 512K ctx).

## Measured on first deploy (2026-10-27, whole card, util 0.93, image 32/video 8)

- Weights: **16.14 GiB** bf16 (8 shards, 39.8 s load); engine init 60.3 s (36 s torch.compile)
- Peak activation: **21.02 GiB** — the 36864 batched-tokens prefill + MM encoder budget;
  this is why slices starved: weights+activation ≈ 37 GiB before any KV
- KV cache: **3.77 GiB = 54,928 tokens**, max 1.49× concurrency at full 36864 ctx
- vLLM suggests `--kv-cache-memory=6735270912` (6.27 GiB) would fully utilize the card —
  a future util bump to ~0.96 buys ~+2.5 GiB KV if concurrency ever matters
- Settings journey: batched-tokens 8192 → **36864 mandatory** (MM budget check ≥31872);
  slice 40960 → 44032 gpumem → **whole card** (operator: at this size ask for a card);
  image 64 → **32** (encoder reservation starved KV: 3.77 < 5.06 GiB needed); video 4 → **8**
- Fallback if KV ever bites again: `--kv-cache-dtype=fp8` (qwen38 prod pattern, halves KV)
