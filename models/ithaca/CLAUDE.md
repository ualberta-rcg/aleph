# ithaca — Ancient Greek Inscription Restoration (JAX)

## Source
- GitHub: https://github.com/google-deepmind/predictingthepast (weights from GCS `ithaca-resources`)
- License: Apache-2.0
- Architecture: JAX/Flax transformer (dm-haiku/optax); Nature 2022; fp32

## Serving contract (research 2026-06-27)
- **Install:** `jax[cuda12]` (**GPU jaxlib** — plain `jax`/jaxlib is CPU-only → ~3 min/inference) +
  `dm-haiku` + `optax` + `numpy` + `absl-py` + `fastapi`/`uvicorn`, in a **persisted venv on the PVC**.
  Plus `pip install -e predictingthepast` (cloned from GitHub).
- **Weights:** `ithaca_153143996_2.pkl` + `iphi.json` + `iphi_emb_xid153143996.pkl` from GCS
  (`storage.googleapis.com/ithaca-resources/models`) → `/data`.
- **API:** `POST /v1/science/predict` {text, contextualize?} → {restoration, attribution}.
  - **Gap char is `?`** (the predictingthepast `GreekAlphabet` has no `[`, `]`, `-` → KeyError; the
    docstring/demo `[---]` is WRONG for the real API). Text 50-750 chars, **uppercase Greek**.
  - `restoration` = {input_text, predictions, top_prediction, prediction_saliency};
    `attribution` = date (BCE) + region/subregion.
  - `contextualize: true` adds a corpus retrieval search (~2 min, CPU/IO) — opt-in.
  - **Cyrillic homoglyphs** (Α/А, В/В, etc.) are rejected — build Greek text from codepoints, don't
    type it (see `test.py`'s ASCII→Greek `_BETA` transliteration).
- Fallback: if jax load fails, the server returns canned **demo** output (`demo: true`) — a test must
  assert `demo != true` to confirm real inference.

## Deployment (standardized)
- **Pattern:** caduceus — ConfigMap `ithaca-server` (server.py embedded) mounted read-only at `/app`;
  initContainer builds `/data/venv` (jax[cuda12] + deps), clones predictingthepast, downloads weights
  — all gated by sentinel `.ithaca-ready-v4` → cold starts skip the ~1 GB install; main container
  (`python:3.11-slim`) runs `/data/venv/bin/python /app/server.py`. `/health` probes.
- **Refactor (2026-06-27):** moved the per-cold-start `pip install jax[cuda12] …` OUT of the container
  args (and the in-server `subprocess.run(["pip",…])` calls) INTO the init venv. Cold start was
  reinstalling ~1 GB every wake.
- **PVC:** standalone `pvc.yaml`, name `ithaca` (was `ithaca-data`), RWX `nfs-models`.
- **GPU:** 1× L40S HAMi slice (`gpumem 16384`); nodeSelector `gpu=on`.
- **Scale-to-zero:** `minReplicas: 0`, 15m idle retention. Cold start ~3-6 min; first restore/attribute
  JIT-compiles (~90s), then ~8s warm.

## Files
- `details.yaml` (v2, `ithaca-details`) · `inferenceservice.yaml` (ConfigMap `ithaca-server` + ISVC) ·
  `pvc.yaml` (`ithaca`) · `test.py` (ASCII→Greek transliteration, `?` gap) · `README.md`.
