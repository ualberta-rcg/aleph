# kev-9b — research + quirks

## Research (2026-10-28, pre-deploy)

- **What**: "decision model" family by Jared Palmer (Apache-2.0), Jev/TypeSafe
  System One API. Prefill-only calibrated classification: state + typed
  questions → probabilities. No generation. Sizes 0.5b/0.8b/4b/9b/27b.
- **kev-9b** (chosen): Qwen3.5-9B-Base frozen + LoRA r16 (173 MB) + pointer head
  (head.pt, T=2.19). ~21.9 GB resident bf16, **validated on L40S** by the author:
  66.4 ms/decision (235 ms new state), ~32.7 req/s @64 clients. Trails kev-27b by
  11 pts on breadth-v1.
- **kev-27b rejected**: 51.3 GB bf16, ~65.5 GB resident, 87 GB peak at 64K states
  → needs >80 GB single GPU. **The Kev server has NO tensor parallelism** (single
  process = single GPU; options are only --run/--device/--host/--port/--dtype).
  TP is an engine feature (vLLM has it; kev.serve does not). GGUF conversions
  exist but serve the backbone as a chat model — NOT the decision API. No
  alternative serving path exists for the System One API.
- **Package**: `kev` 0.1.0 (pyproject: python >=3.12,<3.14; torch >=2.6,<2.9;
  transformers >=5.17,<6; peft/accelerate/pydantic/sklearn; serve extra =
  fastapi/uvicorn/typesafe-sdk). No entry points — `python -m kev.serve`.
  **flash-linear-attention is NOT a dependency** — must install explicitly for
  CUDA+Qwen3.5 (author's deploy scripts do the same).
- **Checkpoint layout**: jaredpalmer/kev-9b repo is just ~202 MB (adapter +
  head.pt + tokenizer + chat_template). **Base Qwen/Qwen3.5-9B-Base (~18 GB) is
  a separate download** at first run — both staged to the PVC HF cache
  (HF_HOME=/data/hf), then `--run jaredpalmer/kev-9b` cache-hits.
- **Endpoints**: POST /v1/systemone (+/permute, /separate), GET /v1/models
  (health). No /healthz. `x-typesafe-request-id` header on responses.
  States >65,536 tokens (+8,192/question) → 422 (KEV_TRUNCATE_STATES to change).
  Validated context only 8,192 (training ≤7,552); 32k/64k degrade 5+ pts.
- **Gateway fit**: `/v1/{path}` catch-all (forward_custom) routes any POST/GET
  /v1/* via body.model with cold-start guard — verified in gateway source.
  Card type `decision` (free-form like tts/dock/structure).
- Env: KEV_API_KEY (unused — Tyk front), KEV_DTYPE=bf16, --device cuda skips
  the child-process probe (probe can misbehave in k8s).

## Quirks / watch-items

- **Main container MUST be full `python:3.12`, not -slim**: Triton JIT-compiles
  the FLA kernels at runtime and needs a C compiler ("Failed to find C compiler"
  crashloop verified 2026-10-28). Slim is fine for the init container (wheels only).

- pip install from the GitHub main tarball — pin a tag later if the author cuts
  releases (`@v1.0`-style revisions exist for --run).
- FLA kernels JIT-compile on first decisions — first request after cold start
  is slow-ish; warm decisions ~40-70 ms.
- max-completion-tokens is meaningless (no generation) — card sets 0.
- 422 over-length states return token counts — informative, not an error to fix.

## Measured on first deploy (2026-10-28, rack09-04, slice gpumem 26624)

- Staging (one-time): venv ~10 GB wheels + Qwen3.5-9B-Base 18 GB + adapter —
  ~15 min. Warm cold start: ~2-4 min (venv/weights cached; Triton re-JITs each
  boot — TRITON_CACHE_DIR on the PVC is a future cold-start optimization).
- Decision latency observed: single noul 33-320 ms (warm ~35-70 ms typical);
  fixture 3-question pass 168 ms; sustained 20-mix median 131 ms, max 377 ms;
  8-way burst all 200.
- Fixture parity with the author's card: returns 0.464 (their 0.47), frustration
  score 1.32 (their 1.44) — bf16-vs-M5 wiggle, semantics identical.
- 422 over-length verified at 120k tokens with informative token counts.
- Battery: 13 PASS / 2 EXP / 0 FAIL after fixes (permute request-wrapper schema;
  so() timeout arg). Proof redeploy battery: see /tmp/kev-9b-proof.log.
