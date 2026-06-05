# Clay Foundation Model — Geospatial Satellite Embeddings

## Source
- HuggingFace: https://huggingface.co/made-with-clay/Clay
- GitHub: https://github.com/Clay-foundation/model
- License: Apache 2.0

## Deployment Summary
- **Model**: Clay v1.5 (~330M, ViT-Large encoder)
- **GPU**: CPU-only (no GPU request)
- **PVC**: clay-data (15Gi, ReadWriteOnce)
- **Scale-to-zero**: Yes (minReplicas: 0)
- **Venv**: Yes (/data/venv on PVC)

## API
- `POST /v1/science/embed` — satellite image to CLS embedding
- Input: pixels [bands, H, W], wavelengths, GSD, lat/lon, time
- Output: CLS token embedding vector
- Supports any number of spectral bands

## Key Files
- `inferenceservice.yaml` — ConfigMap (server.py) + ISVC + init container
- `pvc.yaml` — clay-data PVC (15Gi RWO)
- `details.yaml` — model metadata ConfigMap

## Dependencies
- torch + torchvision (CPU)
- lightning, einops, timm, vit-pytorch
- claymodel repo cloned from GitHub
- python-box, jsonargparse, fastapi, uvicorn

## Audit Notes
- Only encoder weights loaded (decoder and projection head skipped)
- State dict keys remapped: model.encoder.X -> X
- Clay repo cloned for module code (claymodel.module)
- Working directory changed to repo dir for relative config paths
- CPU-only deployment (no GPU requested)

## Update Reminder
- Monitor made-with-clay/Clay for newer checkpoints
- Consider GPU deployment for faster inference on large batches
- Could add fine-tuning endpoints for specific EO tasks
