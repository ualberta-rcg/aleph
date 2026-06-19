# ESM-1b (facebook/esm1b_t33_650M_UR50S)

Meta's **ESM-1b** 650M protein language model — 1280-dim mean-pooled per-protein embeddings of
amino-acid sequences (up to 1024 residues). Predecessor to ESM-2, trained on UniRef50, still widely
used. Custom FastAPI/transformers server on a HAMi GPU slice (fp16), scale-to-zero.

> **PVC:** `esm1b-data` is `ReadWriteMany` (migrated from RWO on 2026-06-19 so `scaleTarget: 5` can scale out).

## Deployment

```bash
kubectl apply -f pvc.yaml              # RWX venv + HF cache (nfs-client)
kubectl apply -f inferenceservice.yaml # custom transformers server (ConfigMap server.py) + ISVC, GPU
kubectl apply -f details.yaml          # Template-C card (type: embedding)
```

The init container builds a cu126 venv (torch>=2.6) and pre-downloads the model into the PVC HF cache.
`server.py` is embedded as the `esm1b-server` ConfigMap.

## Testing

The 10-check protein-embedding battery runs inside the gateway pod (first call wakes a
scaled-to-zero GPU model — cold start ~1–2 min):

```bash
cat models/esm1b/test.py | kubectl exec -i -n models deploy/model-gateway -c gateway -- python3 -
```

Last run (2026-06-19): **8 PASS / 2 EXP / 0 FAIL** — dim 1280, batch, model-echo, usage,
distinctness (cos 0.95), encoding_format, truncation (>1024 residues), guardrails (chat→embed 404,
unknown-model 404), catalog (type=embedding, ctx 1024).

## Key Configuration

| Setting | Value |
|---------|-------|
| Backend | custom FastAPI + `transformers` EsmModel (GPU) |
| Endpoint | `POST /v1/embeddings` (OpenAI-shaped; `input`/`sequences`), health `/health` |
| Embedding dim | 1280 (mean-pooled over residues) |
| Max input | 1024 residues (tokenizer truncates longer) |
| Precision | fp16 (GPU) |
| Parameters | 650M |
| GPU | HAMi slice 10 GiB (`nvidia.com/gpumem: 10240`) |
| Scale | scale-to-zero (`minReplicas: 0`, `scaleTarget: 5`, 15m retention) |
| Weights | PVC `esm1b-data` (⚠ RWO; caches venv + HF cache) |

## Model Highlights

- 1280-dim per-protein embeddings via mean pooling — structure/function/variant tasks.
- Predecessor to ESM-2; strong transfer despite age.
- Loads from the HF hub (cached on PVC); served fp16 on a GPU slice.
