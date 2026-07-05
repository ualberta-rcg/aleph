# SciBERT (allenai/scibert_scivocab_uncased)

AllenAI **SciBERT** — 768-dim dense embeddings of scientific text. BERT-base pre-trained on 1.14M
papers from Semantic Scholar (82% biomedical / 18% CS) with the SciVocab tokenizer. 110M params.
Custom FastAPI/transformers server, CPU-only, scale-to-zero.

## Deployment

```bash
kubectl apply -f pvc.yaml              # RWX weights + venv (nfs-models)
kubectl apply -f inferenceservice.yaml # custom transformers server (ConfigMap server.py) + ISVC
kubectl apply -f details.yaml          # Template-C card (type: embedding)
```

The init container builds a CPU venv and downloads the model to the PVC on first deploy
(idempotent). The server (`server.py`) is embedded as the `scibert-server` ConfigMap.

## Testing

The 10-check scientific-embedding battery runs inside the gateway pod (first call wakes a
scaled-to-zero model — cold start ~30–60s):

```bash
# External via gateway VIP + Tyk auth (preferred)
GW_URL=http://<GATEWAY_VIP> TYK_KEY=<key> python3 models/scibert/test.py

# Or inside the gateway pod (no auth)
cat models/scibert/test.py | kubectl exec -i -n models deploy/model-gateway -c gateway -- python3 -
```

Last run (2026-06-19): **8 PASS / 2 EXP / 0 FAIL** — dim 768, batch, model-echo, usage,
distinctness (cos 0.71), encoding_format, truncation (>512 tokens), guardrails (chat→embed 404,
unknown-model 404), catalog (type=embedding, ctx 512).

## Key Configuration

| Setting | Value |
|---------|-------|
| Backend | custom FastAPI + `transformers` AutoModel (CPU) |
| Endpoint | `POST /v1/embeddings` (OpenAI-shaped), health `/health` |
| Embedding dim | 768 (mean-pooled, attention-masked) |
| Max input | 512 tokens (tokenizer truncates longer) |
| Precision | fp32 |
| Parameters | 110M (BERT-base) |
| Scale | always-on (`minReplicas: 1`, max 3, 15m retention) |
| Weights | PVC `scibert` (RWX, nfs-models, 5Gi; bare fleet naming) |

## Model Highlights

- Pre-trained on scientific text (biomedical + CS) → strong for scientific NER/classification.
- SciVocab SentencePiece tokenizer (uncased).
- 768-dim mean-pooled embeddings; good for retrieval and similarity over papers/abstracts.
- Served CPU-only on a sub-core footprint, always-on (minReplicas: 1).
