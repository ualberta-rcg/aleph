# BioBERT (dmis-lab/biobert-base-cased-v1.1)

DMIS Lab **BioBERT v1.1** — BERT pre-trained on PubMed abstracts + PMC full-text. 768-dim
mean-pooled biomedical text embeddings for NER, relation extraction, and search. Custom
FastAPI/transformers server on a HAMi GPU slice, always-on (minReplicas: 1).

## Deployment

```bash
kubectl apply -f pvc.yaml              # RWX weights + venv (nfs-models)
kubectl apply -f inferenceservice.yaml # custom transformers server (ConfigMap server.py) + ISVC, GPU
kubectl apply -f details.yaml          # Template-C card (type: embedding)
```

The init container builds a cu121 venv (transformers 4.46.3) and downloads the model to the PVC
on first deploy (idempotent). `server.py` is embedded as the `biobert-server` ConfigMap.

## Testing

The 10-check biomedical-embedding battery runs inside the gateway pod (first call wakes a
scaled-to-zero GPU model — cold start ~1–2 min):

```bash
# External via gateway VIP + Tyk auth (preferred)
GW_URL=http://<GATEWAY_VIP> TYK_KEY=<key> python3 models/biobert/test.py

# Or inside the gateway pod (no auth)
cat models/biobert/test.py | kubectl exec -i -n models deploy/model-gateway -c gateway -- python3 -
```

Last run (2026-06-19): **8 PASS / 2 EXP / 0 FAIL** — dim 768, batch, model-echo, usage,
distinctness (cos 0.81), encoding_format, truncation (>512 tokens), guardrails (chat→embed 404,
unknown-model 404), catalog (type=embedding, ctx 512).

## Key Configuration

| Setting | Value |
|---------|-------|
| Backend | custom FastAPI + `transformers` BertModel (GPU) |
| Endpoint | `POST /v1/embeddings` (OpenAI-shaped), health `/health` |
| Embedding dim | 768 (mean-pooled, attention-masked) |
| Max input | 512 tokens (tokenizer truncates longer) |
| Precision | fp16 (GPU) |
| Parameters | 110M (BERT-base) |
| GPU | HAMi slice 3 GiB (`nvidia.com/gpumem: 3072`) |
| Scale | scale-to-zero (`minReplicas: 0`, 15m retention) |
| Weights | PVC `biobert-data` (RWX, nfs-models, 15Gi) |

## Model Highlights

- Pre-trained on PubMed + PMC → strong for biomedical NER/relation extraction/search.
- 768-dim mean-pooled embeddings.
- Served fp16 on a small GPU slice with scale-to-zero.
