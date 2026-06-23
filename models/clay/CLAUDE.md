# Clay Foundation Model — Geospatial Satellite Embeddings

Clay v1.5 (large, ~330M) — Masked Autoencoder for multi-band satellite imagery. Encoder produces
a CLS-token embedding from an any-band image cube + wavelength/GSD/geo metadata.

## Source
- HuggingFace: https://huggingface.co/made-with-clay/Clay
- GitHub: https://github.com/Clay-foundation/model
- License: Apache-2.0

## API — `POST /v1/science/embed` (NON-OpenAI domain endpoint)
Image+metadata input → does NOT expose OpenAI `/v1/embeddings`. Body needs `"model": "clay"`:
- `{"model":"clay", "pixels":[[band,H,W]], "waves":[µm...], "gsd":10.0, "lat":?, "lon":?, "time":?}`
- Returns `{"embeddings":..., "cls_embedding":..., "embedding_dim":N, "model":"clay", "n_bands":B}`.
  (`embeddings` aliases `cls_embedding`, added 2026-06-19 for cross-embedder consistency.)

## Deployment
- **CPU-only** (~330M encoder; runs on CPU).
- **PVC**: `clay-data-rwx` — **ReadWriteMany**, nfs-models, 8 Gi (`pvc.yaml`). Migrated RWO→RWX
  2026-06-19 via **cp-from-RWO** (venv + checkpoint + cloned repo preserved; old `clay-data`
  deleted). Split out of the ISVC (was inline + RWO).
- **Venv-on-PVC**: `/data/venv` (torch + lightning + einops + timm + vit-pytorch + claymodel
  repo clone, guarded). Main container runs `/data/venv/bin/python /app/server.py`.
- **Scale-to-zero**: minReplicas 0, 15m retention.

## Key files
- `inferenceservice.yaml` — ConfigMap (server.py) + ISVC (PVC split to `pvc.yaml`)
- `details.yaml` — v2 card (Template C)
- `pvc.yaml` — RWX PVC
- `test.py` — 6-case gateway battery (dim / non-zero / distinctness / deterministic / echo / malformed)

## Notes
- Only encoder weights loaded (decoder + projection head skipped). State-dict keys remapped
  `model.encoder.X → X`. Clay repo cloned for `claymodel.module`; cwd changed to repo dir for
  relative config paths. Embedding dim read from the response `embedding_dim`.

## Update reminder
- Monitor made-with-clay/Clay for newer checkpoints (dim may change).
