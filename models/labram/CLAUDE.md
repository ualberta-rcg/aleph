# LaBraM — Large Brain Model for EEG (ICLR 2024)

Real model (was serving an **untrained random model** until 2026-06-19 — see gotchas).
LaBraM is an EEG foundation model (Jiang/Zhao/Lu, SJTU, ICLR 2024 spotlight), pretrained on
~2500h of EEG from ~20 datasets. Segment-into-200-sample-patches → VQ neural spectrum tokenizer
(VQ-NSP) → BEiTv2-style 12-layer/200-dim/10-head windowed-attention transformer → 200-dim [CLS]
embedding per window. Shipped via **braindecode 1.5.2**.

## Source
- HF checkpoint (braindecode redistribution): https://huggingface.co/braindecode/labram-pretrained
  — ships `model.safetensors` + `config.json` (NOT a `.pt`).
- Original impl (SJTU): https://github.com/935963004/LaBraM
- Topic ref: https://www.emergentmind.com/topics/labram
- License: BSD-3-Clause. Authors: Wei-Bang Jiang, Li-Ming Zhao, Bao-Liang Lu (SJTU) — NOT Tsinghua.

## API — `POST /v1/science/embed` (NON-OpenAI domain endpoint)
EEG-array input, not text → does NOT expose OpenAI `/v1/embeddings`. Body needs `"model": "labram"`:

- `{"model":"labram", "eeg":[[ch1...],...], "ch_names":["Fp1",...]}` → 200-dim
- `eeg`: 2D `[n_channels][n_times]`; padded/truncated to the pretrained `n_times` (3000).
- `ch_names`: optional 10-20 names (any subset of the canonical 128-channel order; matched
  case-insensitively). Defaults to the canonical order truncated to the channel count.

## Deployment
- **CPU-only** (model is ~5.8M params; runs fine on CPU, ~seconds/window).
- **PVC**: `labram-data-rwx` — **ReadWriteMany**, nfs-client, 5 Gi (`pvc.yaml`). Migrated
  RWO→RWX 2026-06-19 by **cp-from-RWO** (preserved the slow torch+braindecode venv + the HF
  snapshot; NOT re-downloaded). Old `labram-data` (RWO) deleted after the copy + repoint.
- **Venv-on-PVC**: `/data/venv` (torch + braindecode 1.5.2 + safetensors), guarded in init.
  Main container runs `/data/venv/bin/python /app/server.py`. `HF_HUB_OFFLINE=1` + weights on PVC.
- **Scale-to-zero**: minReplicas 0, 15m idle retention. Cold start ~2-4 min (venv + weights on PVC).

## Key files
- `inferenceservice.yaml` — ConfigMap (server.py) + ISVC (PVC now split to `pvc.yaml`)
- `details.yaml` — v2 card (Template C)
- `pvc.yaml` — RWX PVC
- `test.py` — 8-case gateway battery (dim 200 / non-zero / distinctness / deterministic / channel
  subset / short-input padding / ch_names mismatch / malformed)

## Non-obvious gotchas (hard-won)
1. **No `.pt` exists.** The HF repo ships `model.safetensors` + `config.json`. The old server
   globbed for `*.pt`, found nothing, fell through to `from_pretrained("braindecode/labram-pretrained")`
   which FAILED under `HF_HUB_OFFLINE=1` (snapshot is in `/data/model`, not the HF cache), then to
   an **untrained random model** that reported READY. Fix: `Labram.from_pretrained(MODEL_DIR)` loads
   from the local directory ("Loading weights from local directory").
2. **Hardcoded `n_times=1600` was wrong.** The original 935963004 LaBraM-Base is
   `patch200_1600`, but the **braindecode** checkpoint's config specifies `n_times=3000`
   (15×200 patches). Padding/truncating to 1600 mismatched the learned temporal embeddings.
   Fix: read `model.n_times` dynamically after `from_pretrained` and pad/truncate to that.
3. **`LABRAM_CHANNEL_ORDER` import path.** It is defined in `braindecode.models.labram` but is
   NOT re-exported at the `braindecode.models` package level in 1.5.2 — `from braindecode.models
   import LABRAM_CHANNEL_ORDER` raises `ImportError` (this was the inference 500). Fix: import from
   the `braindecode.models.labram` submodule, once, at load time (stored as a global; not per-request).
4. **No untrained fallback.** The old server fell back to a random-init model "for API testing",
   silently serving garbage embeddings. Removed — load failure now leaves `model=None` (503).
5. **`ch_names` is the channel-subset mechanism.** The pretrained model has 128 canonical
   position embeddings; `forward(x, ch_names=[...], return_features=True)` matches names
   case-insensitively to select the right embeddings, so any subset works (graceful degradation
   to ~11 channels per the paper). `return_features=True` returns `{"features", "cls_token"}`.

## Update reminder
- braindecode is at 1.5.2; the Labram API (`from_pretrained`, `return_features`, `ch_names`,
  `LABRAM_CHANNEL_ORDER`) is stable since 0.9 but watch for submodule re-exports on bumps.
- The `@app.on_event("startup")` FastAPI handler is deprecated (harmless warning); modernize to a
  lifespan handler if touched.
