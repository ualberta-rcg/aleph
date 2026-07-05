# PubMedBERT (microsoft/BiomedNLP-PubMedBERT-base-uncased-abstract)

Microsoft **PubMedBERT** — BERT-base pre-trained **from scratch** on PubMed abstracts (no
general-domain pre-training, fully biomedical vocabulary). Outperforms BioBERT on domain-specific
tasks. 768-dim mean-pooled biomedical embeddings. Custom FastAPI/transformers server, CPU-only,
always-on (minReplicas: 1).

> Requests use `model: "pubmedbert"`; the server echoes `pubmedbert-110m` (its internal id).

## Deployment

```bash
kubectl apply -f pvc.yaml              # RWX weights + venv (nfs-models)
kubectl apply -f inferenceservice.yaml # custom transformers server (ConfigMap server.py) + ISVC
kubectl apply -f details.yaml          # Template-C card (type: embedding)
```

## Testing

The 10-check biomedical-embedding battery runs inside the gateway pod (first call wakes a
scaled-to-zero model — cold start ~30–60s):

```bash
# External via gateway VIP + Tyk auth (preferred)
GW_URL=http://<GATEWAY_VIP> TYK_KEY=<key> python3 models/pubmedbert/test.py

# Or inside the gateway pod (no auth)
cat models/pubmedbert/test.py | kubectl exec -i -n models deploy/model-gateway -c gateway -- python3 -
```

Last run (2026-06-19): **8 PASS / 2 EXP / 0 FAIL** — dim 768, batch, model-echo, usage,
distinctness (cos 0.93), encoding_format, truncation (>512 tokens), guardrails (chat→embed 404,
unknown-model 404), catalog (type=embedding, ctx 512).

## Key Configuration

| Setting | Value |
|---------|-------|
| Backend | custom FastAPI + `transformers` BertModel (CPU) |
| Endpoint | `POST /v1/embeddings` (OpenAI-shaped), health `/health` |
| Embedding dim | 768 (mean-pooled, attention-masked) |
| Max input | 512 tokens (tokenizer truncates longer) |
| Precision | fp32 |
| Parameters | 110M (BERT-base) |
| Scale | always-on (`minReplicas: 1`, max 3, 15m retention) |
| Weights | PVC `pubmedbert` (RWX, nfs-models, 5Gi; bare fleet naming) |

## Model Highlights

- Pre-trained from scratch on PubMed → domain-specific vocabulary; strong on biomedical NER/classification.
- 768-dim mean-pooled embeddings.
- CPU-only, always-on.
