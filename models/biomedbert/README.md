# BiomedBERT (microsoft/BiomedNLP-BiomedBERT-base-uncased-abstract)

Microsoft **BiomedBERT** — BERT-base pre-trained from scratch on biomedical text (PubMed
abstracts + PMC full text). 768-dim mean-pooled embeddings for biomedical literature mining,
clinical NLP, NER, and relation extraction. Custom FastAPI/transformers server, CPU-only,
scale-to-zero.

> Requests use `model: "biomedbert-110m"` (the card id / served name).

## Deployment

```bash
kubectl apply -f pvc.yaml              # RWX weights + venv (nfs-client)
kubectl apply -f inferenceservice.yaml # custom transformers server (ConfigMap server.py) + ISVC
kubectl apply -f details.yaml          # Template-C card (type: embedding)
```

## Testing

The 10-check biomedical-embedding battery runs inside the gateway pod (first call wakes a
scaled-to-zero model — cold start ~1–2 min):

```bash
cat models/biomedbert/test.py | kubectl exec -i -n models deploy/model-gateway -c gateway -- python3 -
```

Last run (2026-06-19): **8 PASS / 2 EXP / 0 FAIL** — dim 768, batch, model-echo, usage,
distinctness, encoding_format, truncation (>512 tokens), guardrails (chat→embed 404, unknown-model
404), catalog (type=embedding, ctx 512).

## Key Configuration

| Setting | Value |
|---------|-------|
| Backend | custom FastAPI + `transformers` BertModel (CPU) |
| Endpoint | `POST /v1/embeddings` (OpenAI-shaped), health `/health` |
| Embedding dim | 768 (mean-pooled, attention-masked) |
| Max input | 512 tokens (tokenizer truncates longer) |
| Precision | fp32 |
| Parameters | 110M (BERT-base) |
| Scale | scale-to-zero (`minReplicas: 0`, 15m retention) |
| Weights | PVC `biomedbert-data` (RWX, nfs-client) |

## Model Highlights

- Pre-trained from scratch on PubMed + PMC → strong for biomedical NER/relation extraction/literature mining.
- 768-dim mean-pooled embeddings; CPU-only with scale-to-zero.
