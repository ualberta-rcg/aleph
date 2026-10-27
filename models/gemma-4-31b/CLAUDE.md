# gemma-4-31b — research + quirks

## Research (2026-10-27, pre-deploy)

- **HF**: `google/gemma-4-31B-it` (Apr 2, 2026). Dense 30.7B bf16 (~62 GB),
  60 layers, hybrid sliding-window(1024)/global attention, p-RoPE, vocab 262K.
  Text+image+video (frames); NO audio at 31B. **Native 256K context.** Native
  system role (new in Gemma 4). Configurable thinking (`<|think|>`; empty thought
  block still emitted when OFF on non-E2B/E4B). Native function calling (Tau2 76.9).
  Sampling recs: temp 1.0 / top_p 0.95 / top_k 64 (same as 26b card).
  `architectures: Gemma4ForConditionalGeneration` — identical class to the prod
  gemma-4-26b-a4b (fleet pin 0.20.2 runs it with `gemma4` parsers).
- **vLLM version**: deployed on **v0.32.0** per operator order (latest; CUDA 13.0
  default — drivers verified 595.71.05 = CUDA 13.2 on rack09-07/rack01-11).
  WATCH: v0.30.x had a Gemma-4 KV-layout bug (pool ~1/6) — check the startup
  "GPU KV cache size" line; if suspicious, try v0.28.0.
- Community: dense 31B is slow (~15 tok/s reports); EAGLE3 drafter exists (future
  speedup option); 12B MoE positioned as the fast alternative.

## Sizing (2x whole L40S, fp8 w + fp8 KV, util 0.93)

- fp8 weights ~31 GB (~16/card); ~42.8 GiB budget/card → ~50 GiB KV pool (fp8)
  across TP group → full 262144-token requests + several concurrent long sessions.
- Alternative rejected: TP1 fp8 (1 card) caps ctx ~128K (11 GiB KV) — operator
  chose FULL context (option A).

## Quirks / watch-items

- Empty thought block on thinking-off (parser strips — battery verifies).
- maxReplicas 1 by operator rule (TP2 pending replicas blockade the fleet).
- Media limits matched to molmo2-8b (image 32 / video 8) per operator request —
  Gemma4 images are cheap (~70–1120 tok), no encoder-reservation risk.
- Cold start: ~62 GB download (first), fp8 quantization at load, TP2 NCCL init —
  expect 15–30 min first wake; ~5-8 min from warm PVC.

## Measured on first deploy (2026-10-27, rack09-01 TP2 — also the live proof the
WW reprovision fixed the rack09-01 istio exit-126 bug; pod inits+serves there)

- Cold start 21 min total (62 GB download + v0.32.0 pull + quant + init)
- Per-rank fp8 weights **16.45 GiB** (70 s load); KV **23.75 GiB/rank**
- **KV pool 747,909 tokens = 2.85× concurrency at FULL 262,144 ctx** — the v0.30.x
  Gemma-4 KV-layout bug is NOT present on v0.32.0 (startup line verified)
- Engine init 137.8 s (92 s compile); v0.32 logs a benign CUDA-graph-profiling note
