# SatMAE (MVRL/satmae-vitlarge-fmow-pretrain-800)

SatMAE — a Masked Autoencoder ViT-Large pretrained on functional Map of the World (fMoW)
satellite imagery. Zero-mask-ratio `forward_encoder` extracts a **1024-dim [CLS] embedding**
of an RGB satellite image patch (auto-resized to 224×224, normalized with fMoW mean/std).
Use cases: satellite-image classification, retrieval, change detection.

Custom FastAPI/torch server on CPU, scale-to-zero, venv-on-PVC.

**Non-text domain model**: image input only — does **not** expose OpenAI `/v1/embeddings`.
Serves its domain endpoint `POST /v1/science/embed`.

## Deployment

```bash
kubectl apply -f pvc.yaml              # RWX venv + HF snapshot (nfs-models) — cp-migrated from old RWO
kubectl apply -f inferenceservice.yaml # ConfigMap (server.py) + ISVC, CPU
kubectl apply -f details.yaml          # Template-C card (type: embedding)
```

## Testing

```bash
# External via gateway VIP + Tyk auth (preferred)
GW_URL=http://<GATEWAY_VIP> TYK_KEY=<key> python3 models/satmae/test.py

# Or inside the gateway pod (no auth)
cat models/satmae/test.py | kubectl exec -i -n models deploy/model-gateway -c gateway -- python3 -
```

Last run (2026-06-19): **6 PASS / 0 FAIL** — dim 1024, non-zero real, distinctness,
deterministic, model-echo, malformed.

## Key Configuration

| Setting | Value |
|---------|-------|
| Backend | custom FastAPI + `MaskedAutoencoderViT.from_pretrained` (CPU) |
| Endpoint | `POST /v1/science/embed` (domain; RGB image, not OpenAI text) |
| Embedding dim | **1024** (ViT-Large [CLS], zero-mask forward_encoder) |
| Input | `image` HxW RGB (0-255; auto-resize 224×224, fMoW-normalized) |
| Parameters | ~300M (ViT-Large) |
| GPU | none (CPU) |
| Scale | scale-to-zero (`minReplicas: 0`, 15m retention) |
| PVC | `satmae-data-rwx` (RWX, nfs-models, 5Gi) — venv + weights |

## Cold start
~2-4 min on first boot (venv + deps install once; HF snapshot pre-downloaded by init).
Subsequent boots skip the venv (guarded). Loads fully offline (`HF_HUB_OFFLINE=1`).
