# ESM-2 150M (facebook/esm2_t30_150M_UR50D)

Meta's **ESM-2 150M** protein language model (30 layers) — 640-dim mean-pooled per-protein
embeddings of amino-acid sequences (up to 1024 residues). Good speed/accuracy balance.
Custom FastAPI/transformers server on a HAMi GPU slice (fp16), scale-to-zero.

## Deployment

```bash
kubectl apply -f pvc.yaml              # RWX venv + model (nfs-models)
kubectl apply -f inferenceservice.yaml # custom transformers server (ConfigMap server.py) + ISVC, GPU
kubectl apply -f details.yaml          # Template-C card (type: embedding)
```

## Testing

The 10-check protein-embedding battery runs inside the gateway pod (first call wakes a
scaled-to-zero GPU model — cold start ~1–2 min):

```bash
cat models/esm2-150m/test.py | kubectl exec -i -n models deploy/model-gateway -c gateway -- python3 -
```

Last run (2026-06-19): **8 PASS / 2 EXP / 0 FAIL** — dim 640, batch, model-echo, usage,
distinctness (cos 0.81), encoding_format, truncation (>1024 residues), guardrails (chat→embed 404,
unknown-model 404), catalog (type=embedding, ctx 1024).

## Key Configuration

| Setting | Value |
|---------|-------|
| Backend | custom FastAPI + `transformers` EsmModel (GPU) |
| Endpoint | `POST /v1/embeddings` (OpenAI-shaped; `input`/`sequences`), health `/health` |
| Embedding dim | 640 (mean-pooled over residues) |
| Max input | 1024 residues (tokenizer truncates longer) |
| Precision | fp16 (GPU) |
| Parameters | 150M (30 layers) |
| GPU | HAMi sub-GPU slice |
| Scale | scale-to-zero (`minReplicas: 0`, 15m retention) |
| Weights | PVC `esm2-150m-data` (RWX, nfs-models, 5Gi; migrated from RWO) |

## Model Highlights

- 640-dim per-protein embeddings — mid-size ESM-2 (faster than the 650M/1280-dim variant).
- Strong transfer to structure/function/variant tasks.
- Served fp16 on a GPU slice with scale-to-zero.
