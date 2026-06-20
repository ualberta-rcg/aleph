# AstroPT (Smith42/astroPT_v2.0)

AstroPT v2.0 (95M, UniverseTBD/Smith42) — an autoregressive GPT trained on 8.6M galaxy images
from SDSS/DESI. Patchifies a galaxy image and emits **patch-level latent embeddings `[N, 512]`**
via causal attention. Use cases: galaxy morphology, redshift estimation, similarity search.
(Output is patch-level 2D, not a single pooled vector.)

Custom FastAPI/astropt server on a HAMi GPU slice, scale-to-zero, venv-on-PVC.

**Non-text domain model**: galaxy image input — does **not** expose OpenAI `/v1/embeddings`.
Serves its domain endpoint `POST /v1/science/embed`.

## Deployment

```bash
kubectl apply -f pvc.yaml              # RWX weights + venv (nfs-client, already RWX)
kubectl apply -f inferenceservice.yaml # ConfigMap (server.py) + ISVC + venv-on-PVC init, GPU
kubectl apply -f details.yaml          # Template-C card (type: embedding)
```

## Testing

```bash
cat models/astropt/test.py | kubectl exec -i -n models deploy/model-gateway -c gateway -- python3 -
```

Last run (2026-06-19): **7 PASS / 0 FAIL** — shape [N,512], non-zero, distinctness, deterministic,
model-echo, demo, malformed.

## Key Configuration

| Setting | Value |
|---------|-------|
| Backend | custom FastAPI + `astropt` `load_astropt()` (GPU) |
| Endpoint | `POST /v1/science/embed` (domain; galaxy image, not OpenAI text) |
| Embedding | patch latents **[N, 512]** (2D; not pooled) |
| Input | `image` (H,W,3) float [0,1] (patchified); `demo:true` → [16,512] |
| Parameters | 95M |
| GPU | HAMi slice 8 GiB (`nvidia.com/gpumem: 8192`) |
| Scale | scale-to-zero (`minReplicas: 0`, 15m retention) |
| PVC | `astropt-data` (RWX, nfs-client) — venv + weights |
