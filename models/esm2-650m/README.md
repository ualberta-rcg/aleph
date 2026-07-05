# ESM-2 650M (facebook/esm2_t33_650M_UR50D)

Meta AI's ESM-2 650M protein language model — produces **1280-dim mean-pooled per-protein
embeddings** of amino-acid sequences for downstream structure/function prediction, variant
effect, and similarity search. Custom FastAPI/transformers server on a HAMi sub-GPU slice,
always-on (minReplicas: 1).

## Deployment

```bash
kubectl apply -f pvc.yaml              # RWX weights + venv (nfs-models) — downloaded once
kubectl apply -f inferenceservice.yaml # custom transformers server (ConfigMap server.py) + ISVC, GPU slice
kubectl apply -f details.yaml          # Template-C card (type: embedding)
```

The init container builds a cu121 venv and downloads the model to the PVC on first deploy
(idempotent). The server itself (`server.py`) is embedded as the `esm2-650m-server` ConfigMap.

## Testing

The 10-check protein-embedding battery runs inside the gateway pod (first call wakes a
scaled-to-zero model — cold start ~1–2 min):

```bash
# External via gateway VIP + Tyk auth (preferred)
GW_URL=http://<GATEWAY_VIP> TYK_KEY=<key> python3 models/esm2-650m/test.py

# Or inside the gateway pod (no auth)
cat models/esm2-650m/test.py | kubectl exec -i -n models deploy/model-gateway -c gateway -- python3 -
```

Last run (2026-06-19): **8 PASS / 2 EXP / 0 FAIL** — dim 1280, batch, model-echo, usage,
distinctness (cos 0.89 between two peptides), encoding_format, truncation (>1022 residues),
guardrails (chat→embed 404, unknown-model 404), catalog (type=embedding, ctx 1022).

## Key Configuration

| Setting | Value |
|---------|-------|
| Backend | custom FastAPI + `transformers` EsmModel (not vLLM/TEI) |
| Endpoint | `POST /v1/embeddings` (OpenAI-shaped), health `/health` |
| Embedding dim | 1280 (mean-pooled over residues) |
| Max input | 1022 residues (tokenizer truncates longer sequences) |
| Precision | fp16 (GPU) |
| Parameters | 650M (33-layer MLM transformer) |
| GPU | HAMi slice 4 GiB (`nvidia.com/gpumem: 4096`) |
| Scale | always-on (`minReplicas: 1`, max 5, 15m retention) |
| Weights | PVC `esm2-650m` (RWX, nfs-models, 15Gi; bare fleet naming) |

## Model Highlights

- The most widely used protein language model; strong transfer to structure/function/variant tasks.
- 1280-dim per-protein embeddings via mean pooling over residue tokens.
- Input is a 1-letter amino-acid sequence (or list); sequences >1022 residues are truncated.
- Served on a sub-GPU HAMi slice (<1/11 of an L40S), always-on.
