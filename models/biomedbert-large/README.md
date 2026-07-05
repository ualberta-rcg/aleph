# BiomedBERT-large (microsoft/BiomedNLP-BiomedBERT-large-uncased-abstract)

Microsoft **BiomedBERT-large** (340M, BERT-large) — pre-trained from scratch on PubMed abstracts
(domain-specific vocabulary); state-of-the-art on BioASQ/PubMedQA/BLURB. **1024-dim [CLS]-pooled
embeddings** of biomedical text. Custom FastAPI/transformers server on a HAMi GPU slice,
always-on (minReplicas: 1). Serves the standard OpenAI `/v1/embeddings` (legacy `/v1/science/embed` kept).

## Deployment

```bash
kubectl apply -f pvc.yaml              # RWX venv + model (nfs-models)
kubectl apply -f inferenceservice.yaml # custom transformers server (ConfigMap server.py) + ISVC, GPU
kubectl apply -f details.yaml          # Template-C card (type: embedding)
```

## Testing

```bash
# External via gateway VIP + Tyk auth (preferred)
GW_URL=http://<GATEWAY_VIP> TYK_KEY=<key> python3 models/biomedbert-large/test.py

# Or inside the gateway pod (no auth)
cat models/biomedbert-large/test.py | kubectl exec -i -n models deploy/model-gateway -c gateway -- python3 -
```

Last run (2026-06-19): **8 PASS / 2 EXP / 0 FAIL** — dim 1024, batch, model-echo, usage,
distinctness, encoding_format, truncation, guardrails, catalog.

## Key Configuration

| Setting | Value |
|---------|-------|
| Backend | custom FastAPI + `transformers` AutoModel (GPU) |
| Endpoint | `POST /v1/embeddings` (OpenAI; + `/v1/science/embed` secondary) |
| Embedding dim | 1024 ([CLS]-pooled) |
| Max input | 512 tokens |
| Parameters | 340M (BERT-large) |
| GPU | HAMi slice 10 GiB (`nvidia.com/gpumem: 10240`) |
| Scale | always-on (`minReplicas: 1`, max 3, 15m retention) |
| Weights | PVC `biomedbert-large` (RWX, nfs-models; bare fleet naming) |
