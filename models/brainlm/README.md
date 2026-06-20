# BrainLM (vandijklab/BrainLM)

BrainLM (650M, vandijklab, ICLR 2024) — a ViT-MAE foundation model for fMRI, trained on 6,700h of
recordings (UK Biobank + Human Connectome Project). Accepts 424-ROI time-series and returns a
**1280-dim latent embedding** per window. Downstream: disease classification, brain-state prediction,
connectivity analysis.

Custom FastAPI/transformers server on a HAMi GPU slice, scale-to-zero, venv-on-PVC.

**Non-text domain model**: fMRI-array input — does **not** expose OpenAI `/v1/embeddings` as primary.
Serves `POST /v1/science/embed` (with `/v1/embeddings` as a secondary alias).

## Deployment

```bash
kubectl apply -f pvc.yaml              # RWX venv + weights (nfs-client, already RWX)
kubectl apply -f inferenceservice.yaml # ConfigMap (server.py) + ISVC, GPU
kubectl apply -f details.yaml          # Template-C card (type: embedding)
```

## Testing

```bash
cat models/brainlm/test.py | kubectl exec -i -n models deploy/model-gateway -c gateway -- python3 -
```

Last run (2026-06-20): **6 PASS / 0 FAIL** — dim 1280, non-zero, distinctness, deterministic,
model-echo, malformed.

## Key Configuration

| Setting | Value |
|---------|-------|
| Backend | custom FastAPI + transformers `ViTMAEForPreTraining` (GPU) |
| Endpoint | `POST /v1/science/embed` (domain; fMRI array; `/v1/embeddings` secondary) |
| Embedding dim | 1280 (ViT-MAE latent) |
| Input | `fmri` [424 ROIs × timepoints] (padded to 3×434×434 internally) |
| Parameters | 650M |
| GPU | HAMi L40S slice |
| Scale | scale-to-zero (`minReplicas: 0`, 15m retention) |
| PVC | `brainlm-data` (RWX, nfs-client) — venv + weights |
