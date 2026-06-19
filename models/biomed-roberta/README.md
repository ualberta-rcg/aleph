# BioMed-RoBERTa-base (allenai/biomed_roberta_base)

AllenAI BioMed-RoBERTa — RoBERTa pre-trained from scratch on PubMed + PMC + MIMIC-III biomedical
text. 768-dim mean-pooled embeddings for biomedical NLP. Custom FastAPI/transformers server on a
HAMi GPU slice, scale-to-zero. OpenAI-compliant `/v1/embeddings` (batch + usage).

## Deployment

```bash
kubectl apply -f pvc.yaml              # RWX venv + HF cache (nfs-models)
kubectl apply -f inferenceservice.yaml # custom transformers server (ConfigMap server.py) + ISVC, GPU
kubectl apply -f details.yaml          # Template-C card (type: embedding)
```

## Testing

```bash
cat models/biomed-roberta/test.py | kubectl exec -i -n models deploy/model-gateway -c gateway -- python3 -
```

Last run (2026-06-19): **8 PASS / 2 EXP / 0 FAIL** — dim 768, batch, model-echo, usage,
distinctness, encoding_format, truncation, guardrails, catalog.

## Key Configuration

| Setting | Value |
|---------|-------|
| Backend | custom FastAPI + `transformers` AutoModel (GPU) |
| Endpoint | `POST /v1/embeddings` (OpenAI-shaped; `input`/`texts`), health `/health` |
| Embedding dim | 768 (mean-pooled) |
| Max input | 512 tokens |
| Parameters | 125M (RoBERTa) |
| GPU | HAMi slice 8 GiB (`nvidia.com/gpumem: 8192`) |
| Scale | scale-to-zero (`minReplicas: 0`, 15m retention) |
| Weights | PVC `biomed-roberta-data` (RWX, nfs-models; migrated from RWO) |
