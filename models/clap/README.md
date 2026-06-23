# CLAP (laion/larger_clap_general)

CLAP — Contrastive Language-Audio Pretraining. Embeds **audio and text into a shared 512-dim
space** (in-modal + cross-modal retrieval) and does zero-shot audio classification. Use cases:
bioacoustics, environmental monitoring, audio scene analysis.

Custom FastAPI/transformers server (CPU), scale-to-zero, venv-on-PVC.

**Domain model** (audio+text): serves `POST /v1/science/embed` (also `/v1/embeddings`) for
embeddings and `POST /v1/classify` for zero-shot classification.

## Deployment

```bash
kubectl apply -f pvc.yaml              # RWX venv + weights (nfs-models, already RWX)
kubectl apply -f inferenceservice.yaml # ConfigMap (server.py) + ISVC, CPU
kubectl apply -f details.yaml          # Template-C card (type: embedding)
```

## Testing

```bash
cat models/clap/test.py | kubectl exec -i -n models deploy/model-gateway -c gateway -- python3 -
```

Last run (2026-06-19): **7 PASS / 0 FAIL** — text dim 512, audio dim 512, text distinctness,
deterministic, shared-space sanity, model-echo, malformed.

## Key Configuration

| Setting | Value |
|---------|-------|
| Backend | custom FastAPI + transformers `ClapModel` (CPU) |
| Endpoints | `POST /v1/science/embed` (+`/v1/embeddings`), `POST /v1/classify` |
| Embedding dim | 512 (shared audio+text space) |
| Input | `audio` [[samples]] @48kHz and/or `texts` [str]; classify: `labels` [str] |
| Parameters | larger_clap_general |
| GPU | none (CPU, pinned torch 2.5.1) |
| Scale | scale-to-zero (`minReplicas: 0`, 15m retention) |
| PVC | `clap-data` (RWX, nfs-models) — venv + weights |

## Notes
- Pinned `torch==2.5.1` (CPU) + `transformers==4.46.3` + librosa/soundfile.
- `/v1/classify` patched for the `logit_scale` → `logit_scale_a` rename in newer transformers.
