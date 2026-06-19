# Changelog — model gateway + models

Verified on the HAMi test cluster (control-plane + GPU workers). Newest first.
Cluster-specific values (the 230 test cluster, 232 legacy POC) are in the local working dir.

## 2026-06-18 — Retest campaign: harden chat-LLM test.py + README Testing sections

Re-running the 29 chat LLMs through the gateway and tightening each per-model `test.py` from
status-only checks to correctness assertions. Shared hardening (folded into existing checks,
+1 new `truncation` probe, 33→34 checks for reasoning models): `temp0` asserts the answer contains
"Paris"; `stop_seq` asserts `finish_reason=="stop"`; `tools` asserts the called function name;
`stream` requires non-zero chunks; `usage` asserts the `model` field echoes the requested id;
`truncation` (`max_tokens=5` → `finish_reason=="length"`). Each README gets a Testing section
(run command + last result).
- **gpt-oss-120b / gpt-oss-20b**: hardened to 34-check battery; both **31/3/0** (3 EXP = vision /
  embed / bad-model guards). Managed thinking ON exposes `reasoning`, OFF strips + caps; tools,
  Anthropic parity, streaming reasoning, meta-tasks all green. README Testing sections added.
- **qwen3-32b**: hardened to 34-check battery; **31/3/0**. Effort + binary `enable_thinking` (real
  off); hermes tools, thinking on/off/budget/stream green.
- **qwen36-27b**: hardened to 31-check vision+tools battery; **29/2/0**. Image vision + tools +
  managed thinking all green. (Campaign-wide: capped thinking-check `max_tokens` at 4096 for verbose
  reasoners — assertions only need a non-empty reasoning trace, so ~4× faster, no loss of coverage.)
- **qwen36-35b-a3b**: hardened to 31-check vision+tools battery; **29/2/0**. README Testing section
  refreshed (was stale `tee`-method + 21-pass).

## 2026-06-18 — Managed thinking: expose reasoning ON, strip+cap OFF (gpt-oss)

- **gateway**: managed-thinking models (`param_translation.thinking.mode` in budget/effort/toggle)
  now expose reasoning when thinking is ON and strip+cap when OFF — replacing the old global
  `strips_thinking` strip. OpenAI ships the `reasoning` field; Anthropic emits a `thinking` content
  block (non-stream + SSE). OFF caps `max_tokens` to the card's `off_max_tokens` (default 2048) so
  the model can't burn tokens on about-to-be-stripped reasoning.
- **gateway**: effort/toggle models fake a token budget — a caller-supplied
  `thinking_token_budget` caps `max_tokens` (budget + answer reserve); consumed and not forwarded.
- **gateway**: `prepare_chat` returns `(body, thinking_on)`; added `_manages_thinking` /
  `_expose_reasoning` / `_off_token_cap`; `thinking_token_budget` counts as explicit thinking.
- **Root cause**: vLLM v0.20.2 emits gpt-oss reasoning in the `reasoning` field (NOT
  `reasoning_content`), so "thinking wasn't working" was a false negative — the parser splits fine.
- **gpt-oss-20b / gpt-oss-120b**: cards → `strips_thinking: false` + `off_max_tokens: 2048`;
  test.py rebuilt as a 33-check comprehensive battery (both pass 30/3/0): wake-through-503,
  full OpenAI + Anthropic feature suite (stream/system/temp/top_k/stop/tools/max_tokens/usage),
  thinking ON/OFF/fake-budget/stream assertions on the `reasoning` field, OpenWebUI meta-tasks
  (title/tags/followups), vision guard, and catalog/guardrails.
- **qwen3-32b** re-verified on the managed-thinking gateway — 33-check battery 30/3/0 (wake +
  OpenAI/Anthropic + thinking on/off/budget/stream + meta-tasks + guardrails). Card: add
  `off_max_tokens` + `input_map`/`output_map`/`custom_params` (v2 completeness) + managed-thinking
  note; README/CLAUDE updated.
- **gemma-4-26b-a4b** re-verified — fixed thinking: card was `effort` mode (reasoning_effort yields
  no trace on gemma-4); changed to **toggle** mode via `chat_template_kwargs.enable_thinking`
  (confirmed direct-to-predictor). 32-check vision-variant battery 30/2/0 (vision works, thinking
  on/off/budget/stream, meta, both protocols). README added; CLAUDE gateway/test section.
- **phi-4-reasoning** re-verified (budget mode) — 31-check 26/5/0. Thinking ON exposes
  reasoning. Documented quirk: phi-4 always emits a CoT trace, so requests need adequate
  max_tokens (≥~4000) or reasoning eats the budget → empty content; OFF (budget 0) is
  unreliable on vLLM V1 (redacted_thinking not always extracted, vllm#18141). Card: strips_thinking
  off + off_max_tokens + quirk note.
- **qwen36-27b** re-verified — 30-check vision+tools battery 28/2/0 (managed thinking effort +
  enable_thinking toggle, vision, qwen3_coder tools). Card: add off_max_tokens + input_map/
  output_map/custom_params. README + CLAUDE created.
- **qwen36-35b-a3b** re-verified — 30-check vision+tools battery 28/2/0 (managed thinking effort
  + enable_thinking, vision, qwen3_coder tools). Card: off_max_tokens + input_map/output_map.
- **gateway**: always-on reasoning models (`mode: always_on`) are now managed too — ON exposes
  reasoning, OFF strips + caps max_tokens (reduce what fits, since they can't stop reasoning).
  `_manages_thinking` now includes `always_on`. For qwq/r1-distill meta-tasks (OpenWebUI).
- **qwen35-122b**: NO-ISVC on 230 (TP4 122B not deployed) — skip-and-note.
- **r1-distill-qwen-32b / r1-distill-llama-70b**: managed always_on — ON exposes reasoning,
  OFF strips+caps; 20/5/0 each. Cards rewritten to full v2; README+CLAUDE created; pre-set stop
  annotation removed so wake-on-demand works.
- **glm-z1-32b / glm-z1-rumination-32b**: skip-and-note — glm45 parser keeps reasoning in-template
  (not surfaced as a `reasoning` field, so managed expose/strip doesn't apply); glm-z1-32b tool
  parser broken; rumination ignores tools/system by design.
- **qwen35-122b**: DEPLOYED on 230 (was NO-ISVC) — TP4 122B FP8, weights pre-staged on PVC;
  28-check 25/3/0 (managed toggle thinking, qwen3_coder tools, vision off via --language-model-only).
  Card: off_max_tokens + input_map/output_map.
- **phi-4-reasoning**: FIXED the OFF path — budget mode with REDUCE-off (effort_map none →
  thinking_token_budget 512, NOT 0). budget 0 was mishandled (vLLM#18141: burns tokens, empty
  content). OFF now = reduce reasoning (512) + strip + cap → content returns. Meta caps bumped
  (phi-4 reasons a lot). 31-check 26/5/0. (Research: vLLM#18141 phi-4+deepseek_r1 finicky.)
- **glm-z1-32b / glm-z1-rumination-32b**: RETIRED + deleted (repo + cluster: ISVC, ConfigMap,
  PVC, crashloop zombies). Redundant reasoning models whose chat template has no enable_thinking
  + glm45 parser crashes — reasoning not surfaceable as a field. Superseded by the working
  reasoning fleet (qwq/r1-distill/gpt-oss/qwen3/phi-4). glm-4-32b remains for GLM-family coverage.

## 2026-06-15 — GLM-4 tool calling working; Anthropic streaming tool_use fix

- **glm-4-32b — working tool calling** via a custom vLLM parser. GLM-4-32B-0414 emits tool calls as
  plain text (`function_name\n{json}`), not `<tool_call>` tokens, so vLLM's built-in `glm45` parser
  returned empty `tool_calls`. Built `models/glm-4-32b/glm4_0414_tool_parser.py` (mirrors the model
  card's regex + name-validation), mounted via `--tool-parser-plugin` + `--tool-call-parser=glm4_0414`.
- **gateway**: emit `tool_use` content blocks in Anthropic `/v1/messages` **streaming** responses —
  tool calls were being dropped in SSE (only the non-stream path produced them).
- MODEL-STATUS: fixed a blank line that broke GitHub table rendering.

## 2026-06-12 — GLM family modernized (v2 cards, parsers, test suites)

- **glm-4-32b / glm-z1-32b / glm-z1-rumination-32b** → v2 cards, `vllm serve` format, `glm45` tool
  parsers, per-model test suites. Documented the **GLM reasoning-parser incompatibility**:
  `--reasoning-parser=glm45` crashes (maps to a DeepSeek parser expecting `<think>` tokens GLM's
  tokenizer lacks), so GLM-Z1 thinking stays in-template and is never surfaced as `reasoning_content`.
  Rumination's chat template ignores tools/system-prompt by design (`supports_tools: false`).

## 2026-06-11 — Qwen + vision fleet: full v2 card campaign (11 models)

Migrated the Qwen line to v2 cards with full gateway test suites:
- **qwen3-32b** (effort, 23/25), **qwen35-122b** (toggle, 23/23), **qwen3-235b** (non-thinking, 21/21),
  **qwq-32b** (always-on, 21/21), **qwen25-coder-32b** (22/22), **qwen25-vl-3b/7b/72b** (18/22/22),
  **qwen36-35b-a3b** (reasoning+tools+vision, 21/21), **qwen25-vl-72b-awq** (16/18).
- **Vision standardization**: `--limit-mm-per-prompt=20` across VLMs; context raised to 64K
  (32K on qwen25-vl-3b). qwen25-vl-72b-awq switched TP4→TP2 (model `max_position_embeddings`=128K).
- **Removed k2-v2** — FP32-only (~290 GB), impractical cold start over NFS.
- Refreshed `models.md` + `MODEL-STATUS.md` for all 9 Qwen models + vision limits.

## 2026-06-10 — Science/chat v2 cards + gateway vision gating

- **v2 cards**: command-r-7b (scale-to-zero + 15m, 16/16), deepseek-v2-lite-16b (14/14),
  openbiollm-70b, oceangpt-30b (64K + tools), geogalactica (v0.20.2 + chat template), tinyllama
  (llama.cpp crash fix), astrosage (`no_stream` custom server), progen2 (protein gen + input/output maps).
- **gateway**: vision gating — reject image input for non-vision models; force `stream=false` upstream
  for `no_stream` card models.
- astrosage: rewrote CLAUDE.md + added README.

## 2026-06-09 — qwen36-27b flagship + single-file gateway + CI

- **qwen36-27b**: enabled reasoning + tools + vision, 131K context; switched thinking to **effort
  mode** for native `reasoning_effort` support (became the effort-mode template for the fleet).
- **gateway**: merged `anthropic_xlate.py` into `gateway.py` — single-file gateway.
- **CI/deploy**: post-build image verification + Docker cache-bust fixes; deployment pinned to a CI
  tag with `imagePullPolicy: Always`, then moved to `latest` + always-pull.

## 2026-06-08 — Science wake-up batch, NIM containers, card templates

- **Wake-up tested 10 stalled models** → 6 FIXED (presto pass-mask fix, aeneas JAX warmup,
  geogalactica gate accepted, others), 2 need code fixes, 1 vLLM fail.
- **NIM containers**: renamed boltz→boltz-2 and added openfold-3 (both `nvcr.io/nim/...`); patched
  boltz NIM v1.7.0 `confidence_score` KeyError at startup; standardized 16 GiB `/dev/shm` for NIMs.
- **Batch-fixed 7 failed models**; bumped Knative `progress-deadline` for caduceus / prithvi-eo.
- Merged the 2026-06 LLM batch into the MODEL-STATUS main table + added NIM notes.
- **Templates**: expanded the details.yaml template with real input_map/output_map patterns from
  science models; added an audit prompt for systematic model audit.
- **gateway**: moved the Anthropic type-gate ahead of readiness/cold-start checks; added API mapping docs.

## 2026-06-07 — Tier 2 science models: 2 PASS, 3 blocked by Knative timeout

### Verified PASS
- **progen2** — added sentinel + progress-deadline 600s annotation; 6.4B protein generation works
  (`MRENAQKALEIKRTRVIAEDL` from seed `M`).
- **timesfm** — pinned `transformers>=4.51,<4.53` + `torch>=2.5 cu126`; `TimesFmModelForPrediction`
  (v2.0 500M) loads and forecasts; 128 quantile levels, sensible trend continuation.

### Blocked (Knative progress-deadline 600s cap)
- **caduceus** — torch 2.2.0 + mamba-ssm 1.2.0 pinned, AutoModel for RCPS embeddings, new venv path.
  Init compiles mamba CUDA kernels (~20 min) → exceeds Knative 600s deadline.
  Fix: bump Knative `progress-deadline` max in `config-deployment` ConfigMap.
- **prithvi-eo** — rewrote to BACKBONE_REGISTRY API, added GDAL system deps, forward_features.
  Init installs terratorch + deps (~12 min) → exceeds 600s deadline. Same Knative fix needed.
- **boltz-1** — PVC venv, YAML input, `--checkpoint` path fix, `--no_kernels`. SIGSEGV (rc=-11)
  during `boltz predict` after MSA step. Likely cuEquivariance/CUDA kernel crash on L40S.
  Deferred — needs deeper CUDA debugging or different boltz version.

## 2026-06-07 — Tier 1 science models: 5 deep-fixes to PASS

Systematic fix of 5 GPU science models that were FAIL/PENDING. All now verified with
real payloads on cluster 230.

### timer-s1 (replaces timer-xl-1b)
- **Model swap**: Timer-XL-1B was gated (weights 403), replaced with Timer-S1 (open, Saleen2023/Timer-S1).
- **dtype fix**: Cast all float inputs to `torch.bfloat16` — Timer-S1 weights are bf16, mismatch caused NaN.
- **Init RAM**: Raised to 32Gi to avoid OOM during model load.
- **Test**: 200, 9 quantile forecasts (q0.1–q0.9), sensible trend continuation.

### moirai-moe-1-0-r-base (replaces moirai-moe)
- **Full rewrite**: Original handler used non-functional `Moirai` class. Rewrote to official
  `uni2ts` API: `create_predictor()` + `GluonTS` dataset + `Prediction` object extraction.
- **Quantile extraction**: Reads 19 quantile levels from prediction output.
- **Test**: 200, quantile forecasts with correct shape and values.

### enformer
- **Python 3.12 + GPU torch**: Base image `python:3.12-slim`, pip install `torch` (CUDA) not CPU-only.
- **transformers pin**: `transformers<4.52` — newer versions break Enformer model class.
- **Dict output fix**: `model(x)` returns `{'human': tensor, 'mouse': tensor}`, not an object
  with `.human` attribute. Changed `hasattr(out, 'human')` → `isinstance(out, dict) and 'human' in out`.
- **Payload**: Summarized output (mean + sample) to avoid 896×5313 = ~4.7M value JSON.
- **Test**: 200, human_shape [896, 5313], correct gene expression predictions.

### ernierna
- **GPU torch (cu126)**: Force-reinstall `torch` from cu126 index (base image had CPU-only torch).
- **nodeSelector**: Added `gpu: "on"` to schedule on GPU node.
- **progress-deadline**: Raised to 600s for cold-start model download.
- **storageClassName**: Set to `nfs-client` for PVC.
- **Test**: 200, 768-dim RNA embeddings.

### totalsegmentator
- **torch reinstall**: TotalSegmentator pulls in CPU-only torch as a dep; force-reinstall
  `torch` + `torchvision` from cu126 index after TotalSegmentator install.
- **Test**: 200, segmentation runs on synthetic 16³ volume (0 structures expected on zeros).

### Also
- Deleted `models/timer-xl-1b/` (gated, replaced by `models/timer-s1/`).
- Deleted `models/moirai-moe/` (non-functional, replaced by `models/moirai-moe-1-0-r-base/`).

## 2026-06-06 — phi-4-reasoning card refresh (no gateway remap)

- Rewrote `models/phi-4-reasoning/details.yaml` to schema v2 (whole L40S, v0.20.2,
  `always_on` thinking, verified PASS status, known quirks documented).
- Reverted `fill_empty_content_from_reasoning()` — empty `content` is a vLLM parser or
  `max_tokens` budget issue, not something the gateway should paper over.

## 2026-06-06 — gateway: switch cluster 230 to Docker Hub pull

- Deployment now uses `rkhoja/aleph:latest` with `imagePullPolicy: IfNotPresent`
  (replaces local `model-gateway:<tag>` + `Never` + containerd import).
- `deploy-aleph/deploy.sh` / `gateway/remote-deploy.sh` no longer build on the control plane; `GATEWAY_IMAGE`
  env var selects the tag (default `rkhoja/aleph:latest`).
- RUNBOOK/README/gateway CLAUDE updated: Docker Hub is primary; local build is appendix only.
- Rolled out on cluster 230; gateway deployment healthy.

## 2026-06-06 — science model batch (gateway body-limit + init fixes)

Continued the verification loop on remaining PENDING science models. Key pattern:
several models returned 30–286 MB JSON grids/point clouds that exceed the ingress/gateway
body limit (connection reset even when the pod returned 200). Fix: summarize outputs
(shape/stats/downsampled preview) with opt-in `full_grid` / `full_cloud` flags.

### Verified FIXED
- earthpt — CPU checkpoint load + 24Gi RAM (was GPU+host OOM on startup)
- fengwu — summarize 286 MB forecast grid; demo + real ONNX OK
- dust3r — downsample point cloud to ≤2000 pts + bbox + alignment loss
- diffdock — pass SMILES string directly to `--ligand` (not `.smi` path); fix confidence
  regex; 11 ranked poses on crambin (1CRN) + aspirin
- mast3r — `/v1/science/match` (not reconstruct for 2 images); numpy not tensor fix
- granite-geospatial-biomass/ocean — add gcc/g++ to init (terratorch→stringzilla compile)
- pangu-weather — demo + real ONNX; summarized stats (already had stats in handler)

### Verified DEMO (blocked on deps/access)
- fourcastnet3 — demo OK; real FCN3 needs purpose-built image (makani+torch-harmonics
  CUDA matrix unresolvable via runtime pip)
- naturecode-earth — demo OK; weights gated (`naturecodeproject/earth` 403)

### Still PENDING from this batch
- mattergen (CLI loads; diffusion timeout raised 300→1500s, verify pending)
- prithvi-eo/wxc, surya, terramind-flood, totalsegmentator (in progress)

Tracker: `models/MODEL-STATUS.md` updated for all of the above.

## 2026-06-05 — per-model verification loop (complete) — 138 models migrated 232→230

Systematic one-by-one verification of every migrated model on 230: bring up via gateway,
test the real endpoint(s) with task-realistic payloads, deep-fix until correct, scale-cycle,
document (`TEST.md`/`CLAUDE.md`), and mark an honest `status` on each card.

### Tooling
- `test/test-model.sh` — apply-from-repo, Knative-aware activation (pre-warm via gateway
  request, not manual scale), `recreate` (delete+clear+reapply, keep PVC), curl with
  cold-start retry, scale-cycle.
- `models/MODEL-STATUS.md` — master matrix (PASS / FIXED / FAIL) for all ~157 models.

### Key finding
- KServe "READY" was misleading: several servers returned `/health` 200 while the model
  silently failed to load (no egress, wrong package, fake inputs). These were deployed but
  never actually exercised. The loop now hits real endpoints with real payloads.

### Verified PASS (CPU)
- Embeddings: bge-m3 (1024-dim, multilingual), biomedbert, chemberta, clinicalbert,
  pubmedbert, dnabert-2, dnabert-s, hyenadna (256), splicebert, scibert, specter2.
- Rerank: bge-reranker-v2-m3 (correct ranking).
- Chat: tinyllama (OpenAI + Anthropic). Streaming is a cross-cutting gateway/Knative SSE
  issue (tracked, to fix once for all chat models).

### Deep-fixed (were broken/garbage; now correct, status=production)
- ablang2: `/v1/restore` (AbLang2 needs `[heavy,light]` pairs; handler normalizes input).
- aion: rewrote to the real `polymathic-aion` API (AION + CodecManager + typed modalities);
  init pre-downloads model+codec weights so the offline runtime can load. legacy_image +
  photometry → 768-dim.
- biot5: use task-specific checkpoints (mol2text/text2mol) + SELFIES + official prompts.
- chem-t5: replace invented task prompts with the exact GT4SD training templates.

## 2026-06-04 — migrate climatebert (classification, CPU)

### climatebert (Wave 1)
- Ported ClimateBERT (DistilRoBERTa, 3 models: base + detector + netzero-reduction) from 232.
  CPU; scale-to-zero; PVC nfs-client; HF_HOME=/data/hf-home; HF_HUB_OFFLINE=1 at runtime.
- /v1/science/classify (tasks: detect, netzero) + /v1/embeddings (768-dim). All PASS.
- Inline HF_TOKEN → secretKeyRef; v2 card with routing.k8s_name=climatebert.

## 2026-06-04 — migrate birdnet-analyzer (audio-classification, CPU)

### birdnet-analyzer (Wave 1)
- Ported BirdNET-Analyzer (Cornell Lab, birdnetlib + tensorflow-cpu) from 232.
  CPU; scale-to-zero; PVC nfs-client; no HF token needed (bundled model weights).
- /v1/science/identify: 48kHz float samples → species detections. PASS (synthetic tone → empty
  detections as expected; pipeline end-to-end verified in ~16s).
- v2 card with routing.k8s_name=birdnet-analyzer.

## 2026-06-04 — migrate chem-t5 (chemistry T5, CPU)

### chem-t5 (Wave 1)
- Ported Chem-T5 (GT4SD/multitask-text-and-chemistry-t5-base-standard) from 232. CPU; T5
  seq2seq; scale-to-zero; PVC nfs-client; HF_TOKEN → secretKeyRef; v2 card.
- /v1/science/generate (tasks: forward_synthesis, retrosynthesis, mol2text, text2mol, etc).
  Demo forward_synthesis PASS. ~10s beam search on CPU.

## 2026-06-05 — migrate tinyllama (chat LLM, CPU llama.cpp)

### tinyllama (Wave 1)
- Ported TinyLlama-1.1B-Chat (GGUF Q4_K_M) from 232 via llama-cpp-python server.
- Removed `nvidia.com/gpu.product: NVIDIA-L40S-SHARED` nodeSelector; minReplicas:1→0;
  added Knative scale-to-zero; HF_TOKEN→secretKeyRef; `--n_gpu_layers=0` for CPU.
- POST /v1/chat/completions PASS (~270ms). OpenAI-compatible. Context 4096.

## 2026-06-05 — migrate yolov8n + yolov8s (object detection, ONNX, CPU)

### yolov8n + yolov8s (Wave 1)
- Ported YOLOv8n/s (Ultralytics COCO 80-class, ONNX) from 232. Already Knative.
- Added `routing.k8s_name` to both cards. POST /v1/vision/detect PASS.
- Init exports `.pt` → `.onnx` on first cold start (cached on PVC).

## 2026-06-05 — migrate dino-vit-b8 + efficientnet-b0 (vision, CPU)

### dino-vit-b8 + efficientnet-b0 (Wave 1)
- Ported DINO ViT-B/8 and EfficientNet-B0 (ONNX) from 232. Already Knative.
- Added `routing.k8s_name` to both cards.
- /v1/vision/embed (dino-vit-b8) and /v1/vision/classify (efficientnet-b0) PASS.

## 2026-06-05 — migrate rita (protein generation, CPU)

### rita (Wave 1)
- Ported RITA-XL (LightOn, 1.2B, protein autoregressive LM) from 232. CPU.
- Already Knative; added `routing.k8s_name`, fixed `endpoints` dict, added /v1/science/generate alias.
- Fix: `transformers==4.36.2` required (4.37+ adds `can_generate()` check that breaks RITA custom model).
- /v1/science/generate PASS.

## 2026-06-05 — migrate multilingual-e5-small (multilingual embedding, CPU)

### multilingual-e5-small (Wave 1)
- Ported intfloat/multilingual-e5-small (117M, 512-dim, 100+ languages) from 232.
- Rewrote from TEI (ghcr.io/huggingface/text-embeddings-inference) to standard Python FastAPI
  embedding server (same pattern as biomedbert), enabling standard /v1/embeddings routing.
- Fix: added `sentencepiece` to venv; `transformers==4.44.2` (4.46.3 has lazy-import bug for XLM-R).
- HF_TOKEN→secretKeyRef; minReplicas:1→0; Knative scale-to-zero.
- /v1/embeddings (3-language batch) PASS. 512-dim, L2-normalized.

## 2026-06-05 — migrate scibert + specter2 (scientific embeddings, CPU)

### scibert + specter2 (Wave 1)
- Ported from 232. Already Knative + nfs-client. Only change: HF_TOKEN→secretKeyRef,
  added `routing.k8s_name`.
- /v1/embeddings (768-dim) PASS for both.

## 2026-06-05 — migrate dnabert-2 + dnabert-s (DNA embeddings, CPU)

### dnabert-2 (Wave 1)
- Ported from 232 (already Knative). HF_TOKEN→secretKeyRef, k8s_name added.
- Fix: model returns tuple not ModelOutput — patched to use `raw[0]` as hidden states.
- /v1/embeddings PASS.

### dnabert-s (Wave 1)
- RawDeployment → Knative; removed GPU nodeSelector; added PVC + init container.
- MODEL_ID env var → local path `/data/model`; HF_HUB_OFFLINE=1 at runtime.
- Fixed `endpoints` list→dict in card. /v1/embeddings PASS.

## 2026-06-05 — migrate pubmedbert (biomedical embedding, CPU)

### pubmedbert (Wave 1)
- 232 source was a stub-only card. Built fresh (biomedbert pattern).
  microsoft/BiomedNLP-PubMedBERT-base-uncased-abstract (110M, 768-dim).
- /v1/embeddings PASS. Use model id `pubmedbert` (response shows `pubmedbert-110m`).

## 2026-06-05 — defer longformer + led (stub-only on 232)

### longformer + led (Wave 1, deferred)
- Both were stub-only directories on 232 (card + kustomization, no server.py/ISVC).
- Deferred. Implementation notes in CLAUDE.md for each.

## 2026-06-04 — migrate biot5 (bio T5, CPU)

### biot5 (Wave 1)
- Ported BioT5 (QizhiPei/biot5-base) from 232. CPU; T5 seq2seq; scale-to-zero;
  PVC nfs-client; HF_TOKEN → secretKeyRef; v2 card.
- /v1/science/generate (tasks: mol2text, forward_synthesis, etc). Demo mol2text PASS (~25s
  greedy on CPU — not a hang, use --max-time ≥60).

## 2026-06-04 — migrate clap (audio-language, CPU)

### clap (Wave 1)
- Ported CLAP (laion/larger_clap_general) from 232: `/v1/embeddings` (audio+text, 512-dim)
  and `/v1/classify` (zero-shot audio). CPU.
- Fixes: switched unused GPU torch → CPU torch; patched `/v1/classify` for transformers
  `ClapModel.logit_scale_a` (was `logit_scale`). Inline token → secretKeyRef; v2 card.
- Verified text dim=512 and 440Hz sine classified as "pure tone" (0.99999).

## 2026-06-04 — migrate chronos-bolt (time-series forecast, CPU)

### chronos-bolt (Wave 1)
- Ported Chronos-Bolt (amazon/chronos-bolt-base) from 232: `/v1/forecast`, CPU,
  scale-to-zero (kustomize configMapGenerator for server.py). Inline token → secretKeyRef;
  v2 card (param count corrected to ~205M). Verified horizon=6 forecast.

## 2026-06-04 — migrate alphafold2 (structure prediction, GPU)

### alphafold2 (Wave 1, GPU/HAMi)
- Ported AlphaFold2-via-ColabFold from 232. RawDeployment+GPU-Operator → Knative
  scale-to-zero + HAMi `gpumem 24576`; PVC `nfs-client`; moved jax[cuda12]/fastapi install
  into guarded init so warm restarts are fast.
- Verified end-to-end: demo fold returned a valid PDB + pLDDT (mean 51.0) in ~163s; MSA
  fetched from public api.colabfold.com (egress OK). See models/alphafold2/TEST.md.

## 2026-06-04 — migrate chemberta + clinicalbert (embeddings, CPU)

### chemberta (Wave 1)
- ChemBERTa (seyonec/ChemBERTa-zinc-base-v1) SMILES embeddings, /v1/embeddings 768-dim,
  CPU. Inline token → secretKeyRef; pinned torch/transformers; v2 card. Verified dim=768.

### clinicalbert (Wave 1)
- Bio_ClinicalBERT clinical-text embeddings, /v1/embeddings 768-dim, CPU. Inline token →
  secretKeyRef; pinned torch/transformers; v2 card. Verified dim=768.

## 2026-06-04 — aion deferred (BLOCKED)

### aion (Wave 1) — blocked
- AION-base (Polymathic AI) astro multimodal FM: the 232 server is a non-functional stub
  (uses `transformers`/bogus import; real model needs the `aion` package `CodecManager` +
  modality dataclasses and structured astro inputs). Load fails both paths.
- Converted manifests to HAMi but removed the broken deployment from the cluster.
  Documented the correct integration path in models/aion/CLAUDE.md; marked `[s]` in
  MIGRATION.md for a later proper rewrite.

## 2026-06-04 — migrate agront (plant DNA LM, GPU)

### agront (Wave 1, gpu→HAMi slice)
- Ported AgroNT 1B (InstaDeepAI) from 232. Converted from `RawDeployment` + GPU-Operator
  nodeSelector + ephemeral `/tmp` download to standard 230 pattern: Knative scale-to-zero,
  PVC venv+weights, HAMi `gpu: "on"` + `nvidia.com/gpumem: 8192`, HF token via secretKeyRef.
- Corrected embedding dim **1280 → 1500** (verified live). `/v1/embeddings` +
  `/v1/science/predict` both return 1500-dim. See models/agront/TEST.md.

## 2026-06-04 — migrate arcface (face recognition, CPU/ONNX)

### arcface (Wave 1, gpu=0)
- Ported ArcFace ResNet-100 from 232: `/v1/vision/face`, 512-dim L2-normalized, CPU
  onnxruntime, scale-to-zero. Pinned `onnxruntime==1.19.2`; v2 card
  (`routing.k8s_name: arcface`). Verified dim=512, normalized. See models/arcface/TEST.md.

## 2026-06-04 — migrate biomedbert (biomedical embeddings, CPU)

### biomedbert (Wave 1, gpu=0)
- Ported Microsoft BiomedBERT (110M) from 232: `/v1/embeddings`, 768-dim, CPU,
  scale-to-zero, `nfs-client` PVC.
- Inline HF token → `secretKeyRef`; pinned `torch==2.5.1`/`transformers==4.46.3`.
- v2 card with `routing.k8s_name: biomedbert` (id `biomedbert-110m`). Verified dim=768
  via gateway. See models/biomedbert/TEST.md.

## 2026-06-04 — migrate ablang2 (antibody embeddings, CPU)

### ablang2 (Wave 1, gpu=0)
- Ported AbLang-2 (OxPIG) from 232: antibody PLM, `/v1/embeddings` (mean-pooled) +
  `/v1/restore`. CPU-only (48M), scale-to-zero, `nfs-client` PVC.
- **Fix**: ablang2 0.2.1 dropped the old arbitrary-local-path loading the 232 server
  relied on (`AssertionError: ... does not exist`). Switched to the supported id
  `model_to_use='ablang2-paired'`, pre-downloading weights in the init container into
  the package dir on the PVC so the read-only runtime can load them. Pinned
  `ablang2==0.2.1`, `torch==2.5.1+cpu`. Removed unused inline HF token.
- Converted card to v2 schema; verified dim=480, ctx=512. Tested embeddings single +
  batch via gateway; catalog discovery via `?all=true`. See models/ablang2/TEST.md.

## 2026-06-04 (latest) — begin 232→230 ≤2GPU model migration

### Migration scaffolding
- Created `hf-token` Secret in `models` namespace (manifests now use `secretKeyRef`).
- Added `models/MIGRATION.md` tracker: 138 models to migrate (54 gpu=0, 80 gpu=1,
  4 gpu=2), smallest-first, skipping the 18 already on 230 + the 4-GPU models.
- Confirmed capacity: 2 GPU workers (`rack05-16`, `rack15-03`), 8× L40S, gpu=on.

## 2026-06-04 (latest) — docs/process + gateway image CI workflow

### README/template alignment and operator notes
- Replaced the temporary SoftMig-oriented README text with Aleph stack content while
  preserving the same section/template shape.
- Added explicit reference to the external node-image repo we use:
  `ualberta-rcg/warewulf-rke2-hami`.

### CLAUDE guidance expansion
- Added `models/CLAUDE.md` with a standard model deployment process and validation
  checklist.
- Added `models/CLAUDE-TEMPLATE.md` for per-model operational notes.
- Added `models/gpt-oss-20b/CLAUDE.md` as a concrete per-model example.
- Added `gateway/CLAUDE.md` for gateway rollout/compatibility guardrails.
- Updated root `CLAUDE.md` with a required changelog-first commit process.

### GitHub Actions (DockerHub) for gateway image
- Added `.github/workflows/deploy-gateway.yml` modeled after the publish pattern in
  `ualberta-rcg/warewulf-rke2-hami`:
  - build on `main` pushes touching `gateway/**`,
  - push immutable `gateway-<shortsha>` and stable `latest` tags,
  - default image `rkhoja/aleph` (override via `DOCKER_HUB_REPO` secret/Variable),
  - DockerHub auth via `DOCKER_HUB_USER`, `DOCKER_HUB_TOKEN`.

## 2026-06-04 (later) — 3 more sub-GPU science models + cold-start fix

### Added esm2-650m, molformer, finbert (all sub-GPU, scale-to-zero)
- **esm2-650m** — Meta ESM-2 protein language model (650M), `POST /v1/embeddings`,
  1280-dim embeddings, fp16, 4 GiB HAMi slice. domain: proteomics.
- **molformer** — IBM MoLFormer-XL molecular embeddings from SMILES (110M),
  `POST /v1/science/embed`, 768-dim, 3 GiB slice. domain: chemistry.
- **finbert** — ProsusAI FinBERT financial sentiment **classification** (110M),
  `POST /v1/science/classify` → positive/negative/neutral, 3 GiB slice. domain: finance.
- All ported like proteinmpnn (HF transformers server in a ConfigMap): `nodeSelector
  gpu:on` + `nvidia.com/gpumem`, `nfs-models` PVC (venv on NFS), `minReplicas 0`, 15m idle.
  Cards rewritten to our schema (type embedding/classify, catalog, input/output_format).
- **Switched molformer + finbert torch from CPU → cu121** so they actually use the GPU
  slice they request (POC installed CPU torch, wasting the allocation).
- **transformers version pin (`==4.46.3`)**: the unpinned latest transformers imports
  `torch.float8_e8m0fnu`, which the cu121 torch wheel lacks → `EsmModel`/`BertForSeq...`
  failed to import. Pinned esm2 + finbert; molformer already pins `<4.36` (onnx).
- Verified: esm2 1280-dim, molformer 768-dim (aspirin), finbert sentiment
  (surged→positive .92, bankruptcy→negative .68).

### Gateway 0.8 — cold-start guard now handles never-started models
- Bug: a brand-new scale-to-zero ISVC has no `latestReadyRevision`, so
  `_ready_replicas` returned -1 (fail-open) and the request hit Knative → **empty 404**.
- Fix: `_ready_replicas_sync` now also falls back to `latestCreatedRevision` (whose
  Deployment exists at 0 replicas), so the guard sees "0", returns the friendly 503, and
  the wake-up primes the very first scale-up. Verified: fresh models now 503 (not 404) and
  self-prime on first request. (gateway image 0.7 → 0.8)

### HAMi multi-tenancy confirmed
- With these up, packing across the 4 L40S (binpack):
  GPU A = command-r-7b (24G) + finbert (3G); GPU B = esm2-650m (4G) + molformer (3G);
  2 GPUs free for qwen/gpt-oss/gemma/proteinmpnn cold starts. Multiple models per
  physical GPU, as intended.

## 2026-06-04 (later) — proteinmpnn (science model), public catalogue, gemma, qwen

### proteinmpnn — first "science" model on 230 (sub-GPU)
- Moved ProteinMPNN (Dauparas et al., Science 2022, Baker Lab) from POC 232:
  `models/proteinmpnn/` (custom PyTorch FastAPI server in a ConfigMap, `POST /v1/design`).
  Routes through the gateway's existing `/v1/{path}` catch-all (no gateway change).
- 230 adaptations: `nodeSelector gpu:on` + **HAMi sub-GPU slice `nvidia.com/gpumem: 6144`**
  (6 GiB of an L40S — ~1.7M-param model, mostly CUDA/cuDNN context), `nfs-models` PVC,
  scale-to-zero (15m). First cold start builds the ~5 GB torch venv **onto NFS** — verified
  the `nfs-models` SC handles it (no EIO). Later starts reuse the cached venv/weights.
- **Fixed broken server.py**: the POC's `model.sample(..., chain_idx=...)` call no longer
  matches upstream ProteinMPNN `main` (sig is now `sample(X, randn, S_true, chain_mask,
  chain_encoding_all, residue_idx, mask=, ...)` returning a dict). Rewrote `_design` to use
  the repo's own helpers (`parse_PDB`, `StructureDatasetPDB`, `tied_featurize`, `_scores`,
  `_S_to_seq`) exactly like `protein_mpnn_run.py`. Now returns sequences + score +
  global_score + seq_recovery + native sequence.
- **Card corrected from the source** (`models/proteinmpnn/details.yaml`): `context_window`
  1022 → **200000** (upstream `--max_length` default), added architecture (k=48 GNN, 3+3
  layers), weights `v_48_020` (48 nbrs / 0.20A noise), Science 2022 citation + paper URL,
  available weights, accurate input/output schema.
- Verified end-to-end on crambin (1CRN, 46 aa): native parsed correctly, 3 designs at T=0.2
  with ~52–57% sequence recovery (expected for ProteinMPNN), disulfide cysteines preserved.

## 2026-06-04 (later) — public catalogue endpoint, gemma cleanup, qwen images=20

### Public catalogue endpoint (keyless), like POC 232's `/serving/api/v1/models`
- New **keyless** Tyk API `model-catalogue` (`gateway/tyk/model-catalogue-api.json`),
  `listen_path: /serving/api/v1/models` → proxies to the gateway's `/v1/models`.
  Scoped to the catalogue path only, so chat/embeddings still require a key
  (verified `/v1/chat/completions` with no key → 401; `/serving/api/v1/models?all=true`
  with no key → 200). Added as a 2nd key in the `tyk-api-definitions` ConfigMap.
- Gotcha: `kubectl rollout restart deploy -l <wrong-label>` returns success (no-op) when
  the selector matches nothing — restart by deploy name (`deploy/gateway-tyk-oss-tyk-gateway`).
- Output is the same rich card-driven schema as `/v1/models?all=true` (richer than 232:
  adds `capabilities`, `scaling`, live `resources`, `ready`, `embedding_dimensions`).

### gemma cleanup + move to 230
- POC called it `gemma-4b` but the repo is **`google/gemma-3-4b-it`** (Gemma *3*). Renamed
  the model id + served name to **`gemma-3-4b-it`** to match the repo.
- `models/gemma-3-4b-it/` (isvc + card + pvc): vLLM `v0.20.2` (vs POC's 0.8.4), bf16 (dropped
  POC's fp8 + nvidia-smi VRAM-guard — HAMi enforces VRAM), HAMi 16 GiB slice, `nodeSelector
  gpu: on`, NFS PVC, scale-to-zero (15 m), no `--enforce-eager`, `--max-model-len 8192`.
  Verified chat incl. a system prompt (vLLM merges it into the Gemma chat template).

### qwen25-vl-7b — images per prompt 5 → 20
- `--limit-mm-per-prompt '{"image":20,"video":1}'`. **No KV penalty** in vLLM 0.20.x: still
  8.56 GiB KV / 160,272 tokens / 4.89x concurrency on the 32 GiB slice (it doesn't reserve
  worst-case multimodal memory from the limit).

## 2026-06-04 — NFS persistence, scaling/cold-start, model catalog, multimodal

### Storage — NFS large-write EIO fixed
- **Root cause:** the OneFS/Isilon backend (`manage.storage.data.vulcan.local:/kubeflow`)
  returns `Errno 5 (EIO)` on COMMIT for write RPCs > 128 KiB over **NFSv4.1/4.2**. The
  default `nfs-client` SC mounts v4.2 @ `wsize/rsize=1Mi`, so multi-GB safetensors failed
  at `close()` (small files were fine). NFSv3 and v4.0 work even at 1 MiB.
- **Fix:** new StorageClass **`nfs-models`** (`deploy-aleph/storage/nfs-models-storageclass.yaml`) with
  `mountOptions: nfsvers=4.2,wsize=131072,rsize=131072,hard`. Verified ~700 MB/s, 2 GB write OK.
- **Impact:** model weights now persist on NFS PVCs (`models/*/pvc.yaml`, SC `nfs-models`).
  Scale-from-zero cold starts **skip the re-download** (~90 s vs ~3 min before). Replaces the
  earlier `emptyDir` workaround.

### Scaling — scale-to-zero, scale-up-on-use, friendly cold-start
- Cards gained a **`scaling`** block: `scale_to_zero`, `min_replicas`, `idle_retention`,
  `cold_start_estimate`.
- Convention: most models `minReplicas: 0` (scale-to-zero, **15 m** idle retention via
  `autoscaling.knative.dev/scale-to-zero-pod-retention-period: "15m"`); a few stay
  `minReplicas: 1` (always-warm). Examples: gpt-oss-20b & qwen25-vl-7b = 0; command-r-7b = 1.
- **Gateway cold-start handling** (mirrors POC 232, but card-driven): on each request the
  gateway checks the active predictor revision's `readyReplicas`. At **0** it fires an async
  Knative wake-up (`GET /v1/models` with the model's `Host` header) and returns a fast
  `503 {code: model_scaled_to_zero}` "starting up… retry in <cold_start_estimate>" instead of
  hanging into Tyk's 30 s `504`. Verified: 503 in ~0.06 s, wake triggers a 0→1 scale-up.
  (Replica count is read live with a 3 s TTL cache; RBAC already grants `apps/deployments`.)

### gpt-oss-20b — HAMi slice tightened
- KV math showed the 32 GB slice was ~2× oversized for `max_num_seqs=8`. Reduced to a **24 GB
  slice** (`nvidia.com/gpumem: 24576`) at `--gpu-memory-utilization 0.90`:
  KV 12.15 GiB → **6.55 GiB** (268k tokens, 8.18× @ 32k, matches `max_num_seqs=8`). Frees ~8 GB/GPU.

### Gateway — card param-translation fix (reasoning models)
- `thinking.mode: effort` previously **overwrote** a client-supplied `reasoning_effort`. Now it
  uses `setdefault` when thinking is enabled (respects the caller; only fills the card default
  when absent) and still forces "off" for meta-tasks. Verified: low=171 vs high=445 tokens.

### Gateway — `/v1/models` is now fully card-driven (richer than 232)
- The endpoint emits the **232-compatible schema** (`id, object, owned_by, type,
  context_window, max_completion_tokens, description, endpoint, input_format, source,
  source_url, tags, parameters, gpu`) **plus extras**: `ready`, `license`, `precision`,
  `framework`, `domain`, `subdomain`, `capabilities{vision,video,tools,reasoning,system_prompt}`,
  `scaling{...}`, and live `resources{gpus,vram_mib,cpu_cores,system_ram_mib}`.
- All of it comes from the **details ConfigMap (card)** + live ISVC state — 232 hardcodes this
  metadata in the gateway; here it is auto-detected. `source_url` auto-derives from a HF `source`.
- Cards gained `limits.context_window`; `catalog.input_format` / `catalog.gpu` optional.
- `?all=true` returns every model; default returns chat-class only.

### Token budgets (researched, were too tight)
- gpt-oss natively supports 131k context **and** 131k output; reasoning burns many tokens.
  Bumped gpt-oss-20b `defaults.chat.max_tokens` 4096→**8192** and `limits.max_completion_tokens`
  16000→**24000** so reasoning + answer don't truncate (verified: bat-and-ball at effort=high
  used 473 tokens, full `reasoning` + correct $0.05 answer).
- qwen25-vl-7b default `max_tokens` 2048→**4096** (vision/OCR outputs).

### bge-small embedding — values verified + actually deployed
- Researched specs: **384 dims, 512 max tokens, cls pooling** (so `context_window: 512` was
  correct). Card now carries `embedding_dimensions: 384`, `max_input_tokens`, `pooling`; the
  endpoint surfaces `embedding_dimensions`.
- The card existed without a backing ISVC (404 on `/v1/embeddings`). Deployed the real TEI
  service (`models/bge-small/inferenceservice.yaml`, CPU, always-warm). Verified 384-dim vectors.

### Models
- **Added qwen2.5-vl-7b** (`models/qwen25-vl-7b/`) — multimodal: text + images + video, OCR,
  charts, document parsing. Card declares `supports_vision`/`supports_video`; NFS PVC; scale-to-zero.
  - vLLM **v0.20.2** (was 0.8.4) — newer, consistent with gpt-oss, cached on node. NB:
    `--limit-mm-per-prompt` format differs by version: **JSON** `{"image":5,"video":1}` on 0.20.x,
    `image=5,video=1` on 0.8.x.
  - **No `--enforce-eager`** (CUDA graphs kept on). With graphs+ViT resident a 28 GB slice left
    only ~5 GB KV (2.8×), so bumped to a **32 GB slice** → 8.56 GB KV (4.89× @ 32k).
  - Verified vision end-to-end via gateway+Tyk (correctly described a red/blue test image).
- command-r-7b, gpt-oss-20b: moved to NFS PVCs; cards gained `scaling` + `context_window`.

### Scale-up-on-use — confirmed working (matches 232 mechanism)
- Verified the full cycle: idle model scales to 0 → request returns fast 503 → async wake-up
  (Knative activator) spins a pod 0→1 → retry serves 200. Same approach as POC 232's
  `_wake_up_model`, but the retry estimate is card-driven.

### Demo
- `test/smoke.sh` — 10 copy-pasteable curls (catalogue, OpenAI chat, reasoning, streaming,
  Anthropic, vision, embeddings, telemetry, cold-start) runnable from a login node with a key.

### Gateway image
- `model-gateway` `0.3 → 0.6`. Built with podman on the head node, imported into RKE2
  containerd (`ctr -n k8s.io`), retagged `docker.io/library/model-gateway:<v>`.
  - 0.4: effort param-translation fix
  - 0.5: scale-to-zero cold-start guard + wake-up
  - 0.6: card-driven `/v1/models` enrichment
