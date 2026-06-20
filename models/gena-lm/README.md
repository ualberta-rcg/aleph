# GENA-LM bert-base-t2t (AIRI-Institute/gena-lm-bert-base-t2t)

BERT-style DNA language model pre-trained on the T2T human genome — **768-dim mean-pooled DNA
embeddings** (last hidden state). Custom FastAPI/transformers server on a HAMi GPU slice,
scale-to-zero. OpenAI-compliant `/v1/embeddings` (batch + usage).

## Deployment

```bash
kubectl apply -f pvc.yaml              # RWX venv + HF cache (nfs-models)
kubectl apply -f inferenceservice.yaml # custom transformers server (ConfigMap server.py) + ISVC, GPU
kubectl apply -f details.yaml          # Template-C card (type: embedding)
```

## Testing

```bash
cat models/gena-lm/test.py | kubectl exec -i -n models deploy/model-gateway -c gateway -- python3 -
```

Last run (2026-06-19): **7 PASS / 2 EXP / 0 FAIL** — dim 768, batch, model-echo, usage,
distinctness, truncation, guardrails, catalog.

## Key Configuration

| Setting | Value |
|---------|-------|
| Backend | custom FastAPI + `transformers` AutoModel (GPU, trust_remote_code) |
| Endpoint | `POST /v1/embeddings`, health `/health` |
| Embedding dim | 768 (mean-pooled, last hidden state) |
| Max input | 512 tokens |
| GPU | HAMi slice 8 GiB (`nvidia.com/gpumem: 8192`) |
| Scale | scale-to-zero (`minReplicas: 0`, 15m retention) |
| Weights | PVC `gena-lm-data` (RWX, nfs-models; migrated from RWO) |
