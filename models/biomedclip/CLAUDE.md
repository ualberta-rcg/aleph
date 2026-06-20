# BiomedCLIP — biomedical vision-language model

Microsoft BiomedCLIP — CLIP variant pretrained on 15M PubMed figure-caption pairs. Encodes
biomedical images and text into a shared **512-dim space** (cross-modal retrieval + zero-shot
classification).

## Source
- HuggingFace: https://huggingface.co/microsoft/BiomedCLIP-PubMedBERT_256-vit_base_patch16_224
- License: Apache-2.0

## API — `POST /v1/science/embed` (domain endpoint, primary)
Also `/v1/embeddings` (alias) + `POST /v1/classify` (zero-shot). Body needs `"model": "biomedclip"`:
- `{"model":"biomedclip", "images":["<base64 PNG/JPEG>"], "texts":["..."]}` → `image_embeddings` and/or `text_embeddings`
- `{"model":"biomedclip", "images":[...], "labels":["pneumonia","normal"]}` → zero-shot classify

## Deployment
- **GPU**: 1× L40S (shared HAMi slice).
- **PVC**: `biomedclip-data` — **ReadWriteMany**, nfs-client (already RWX, `pvc.yaml`).
- **Venv-on-PVC**: `/data/venv` (open_clip + torch, guarded).
- **Scale-to-zero**: minReplicas 0, 15m retention.

## Key files
- `inferenceservice.yaml` — ConfigMap (server.py) + ISVC
- `details.yaml` — v2 card (Template C)
- `pvc.yaml` — RWX PVC
- `test.py` — 7-case gateway battery (image + text / distinctness / deterministic / shared-space / echo / malformed); pure-stdlib PNG generator (no PIL in gateway pod)

## Notes
- Server returns `image_embeddings`/`text_embeddings` (per modality), dim 512.
- Text tokenizer: `open_clip.get_tokenizer("hf-hub:microsoft/BiomedCLIP-PubMedBERT_256-vit_base_patch16_224")`.

## Update reminder
- Watch microsoft for BiomedCLIP v2 / larger variants.
