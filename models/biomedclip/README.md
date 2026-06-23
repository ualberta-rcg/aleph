# BiomedCLIP (microsoft/BiomedCLIP-PubMedBERT_256-vit_base_patch16_224)

Microsoft BiomedCLIP — a CLIP variant pretrained on 15M PubMed figure-caption pairs. Encodes
biomedical images (radiology, pathology) and text into a shared **512-dim space** for cross-modal
retrieval and zero-shot image classification.

Custom FastAPI/open_clip server on a HAMi GPU slice, scale-to-zero, venv-on-PVC.

**Domain model** (biomedical image+text): serves `POST /v1/science/embed` (also `/v1/embeddings`)
for embeddings and `POST /v1/classify` for zero-shot.

## Deployment

```bash
kubectl apply -f pvc.yaml              # RWX venv + weights (nfs-models, already RWX)
kubectl apply -f inferenceservice.yaml # ConfigMap (server.py) + ISVC, GPU
kubectl apply -f details.yaml          # Template-C card (type: embedding)
```

## Testing

```bash
cat models/biomedclip/test.py | kubectl exec -i -n models deploy/model-gateway -c gateway -- python3 -
```

Last run (2026-06-19): **7 PASS / 0 FAIL** — image+text 512-dim, text distinctness, deterministic,
shared-space sanity, model-echo, malformed.

## Key Configuration

| Setting | Value |
|---------|-------|
| Backend | custom FastAPI + open_clip `BiomedCLIP` (GPU) |
| Endpoints | `POST /v1/science/embed` (+`/v1/embeddings`), `POST /v1/classify` |
| Embedding dim | 512 (shared image+text space) |
| Input | `images` [base64] and/or `texts` [str]; classify: `labels` [str] |
| Parameters | ~400M |
| GPU | HAMi L40S slice |
| Scale | scale-to-zero (`minReplicas: 0`, 15m retention) |
| PVC | `biomedclip-data` (RWX, nfs-models) — venv + weights |
