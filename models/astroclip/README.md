# AstroCLIP (polymathic-ai/astroclip)

Cross-modal contrastive foundation model for astronomy — embeds galaxy images (DESI Legacy
Survey g,r,z cutouts) and optical spectra (DESI) into a shared embedding space. DINOv2 image
encoder + masked-modeling spectrum transformer, aligned by cross-attention CLIP projection
heads; trained on ~90K cross-matched galaxies. Enables in-modal/cross-modal similarity search
and downstream redshift / property / morphology tasks.

Custom FastAPI/Lightning server on a HAMi GPU slice, scale-to-zero, venv-on-PVC.

**Non-text domain model**: image/spectrum input only — does **not** expose OpenAI
`/v1/embeddings`. Serves its domain endpoint `POST /v1/science/embed`.

## Deployment

```bash
kubectl apply -f pvc.yaml              # RWX checkpoint + venv + cloned repo (nfs-models)
kubectl apply -f inferenceservice.yaml # ConfigMap (server.py) + ISVC + venv-on-PVC init, GPU
kubectl apply -f details.yaml          # Template-C card (type: embedding)
```

## Testing

```bash
cat models/astroclip/test.py | kubectl exec -i -n models deploy/model-gateway -c gateway -- python3 -
```

Last run (2026-06-19): **9 PASS / 0 FAIL** — image dim 1024, spectrum dim 1024, shape field,
in-modal distinctness (cos 0.85), cross-modal cos 0.28, deterministic (cos 1.0), modality echo,
demo path, malformed-input handling.

## Key Configuration

| Setting | Value |
|---------|-------|
| Backend | custom FastAPI + Lightning (`AstroClipModel.load_from_checkpoint`, GPU) |
| Endpoint | `POST /v1/science/embed` (domain; image/spectrum, not OpenAI text) |
| Embedding dim | **1024** (not 512 — README is wrong; verified empirically) |
| Modalities | `image` (144×144×3 g,r,z), `spectrum` (wavelength bins) |
| Parameters | 370M |
| GPU | HAMi slice 10 GiB (`nvidia.com/gpumem: 10240`) |
| Scale | scale-to-zero (`minReplicas: 0`, 15m retention) |
| PVC | `astroclip-data` (RWX, nfs-models, 10Gi) — checkpoint + venv + repo |

## Cold start

~2-4 min on first boot (venv + deps install once; cu126 torch, DINOv2 `--no-deps`, AstroCLIP
`--no-deps`, runtime deps). Subsequent boots skip the venv (sentinel-gated). The init is fully
self-contained — deleting the PVC and re-applying rebuilds checkpoint + repo + venv.
