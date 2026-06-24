# ablang2 Notes

## Purpose
AbLang-2 (OxPIG) antibody-specific protein language model. Mean-pooled sequence
embeddings (`/v1/embeddings`) + CDR/masked-position restoration (`/v1/restore`).

## Runtime
- Custom FastAPI server (ConfigMap `ablang2-server`), venv-on-PVC pattern.
- CPU-only (48M params) — no GPU slice, correct for this size.
- `image: python:3.11-slim`; `ablang2==0.2.1`, `torch==2.5.1+cpu`.

## Key quirk (migration fix)
- ablang2 0.2.1 **removed** the old "arbitrary local path as model_to_use" behavior.
  Passing `/data/ablang2-weights` now raises `AssertionError: ... does not exist`.
- Fix: use the supported id `model_to_use='ablang2-paired'`. Weights are **pre-downloaded
  in the init container** into the package dir on the PVC (Zenodo), so the read-only
  runtime mount can load them without writing. Pin `ablang2==0.2.1` for reproducibility.
- Embedding API (`ablang.tokenizer` + `ablang.AbRep(...).last_hidden_states`) is unchanged.

## Resources
- CPU req/limit 1/2; mem 2Gi/4Gi. PVC `ablang2-data-rwx` 2Gi RWX (weights ~158MB + venv).
- No HF token needed (weights from Zenodo, not HuggingFace).
- PVC migrated RWO→RWX (2026-06-19) by copying from old `ablang2-data` (avoid slow Zenodo re-download).

## Validation
See [test.py](test.py). Embeddings single+batch verified, dim=480, ctx=512.
Run externally: `GW_URL=http://<GATEWAY_VIP> TYK_KEY=<key> python3 models/ablang2/test.py`.

## Notes
- Paired model expects `VH|VL`; single chains still embed (mean-pooled).
- Zenodo cold-start download is slow; warm restarts reuse PVC cache.

## /v1/restore fix (2026-06-05 verification pass)
- AbLang2's `__call__(..., mode="restore")` runs `heavy, light = seq` per item, so each
  sequence MUST be a `[heavy, light]` pair — the old handler passed raw strings and always
  500'd with `not enough values to unpack (expected 2, got 1)`.
- Handler now normalizes input: accepts a single chain (light=""), a `"heavy|light"` string,
  or a `[heavy, light]` list. Verified: masked `*` positions get restored. Both endpoints PASS.
