# AgroNT-1B (InstaDeepAI/agro-nucleotide-transformer-1b)

1B-param **plant-genome DNA language model** — trained on 48 edible plant species (472.5B tokens),
6-mer tokenizer, ~6 kbp context. Produces **1500-dim mean-pooled plant DNA embeddings**.
Custom FastAPI/transformers server on a HAMi GPU slice, scale-to-zero. OpenAI-compliant
`/v1/embeddings` (batch + usage + truncate).

## Deployment

```bash
kubectl apply -f pvc.yaml              # RWX venv + model (nfs-models)
kubectl apply -f inferenceservice.yaml # custom transformers server (ConfigMap server.py) + ISVC, GPU
kubectl apply -f details.yaml          # Template-C card (type: embedding)
```

## Testing

```bash
# External via gateway VIP + Tyk auth (preferred)
GW_URL=http://<GATEWAY_VIP> TYK_KEY=<key> python3 models/agront/test.py

# Or inside the gateway pod (no auth)
cat models/agront/test.py | kubectl exec -i -n models deploy/model-gateway -c gateway -- python3 -
```

Last run (2026-06-19): **7 PASS / 2 EXP / 0 FAIL** — dim 1500, batch, model-echo, usage,
distinctness, truncation, guardrails, catalog.

## Key Configuration

| Setting | Value |
|---------|-------|
| Backend | custom FastAPI + `transformers` AutoModelForMaskedLM (GPU, hidden_states) |
| Endpoint | `POST /v1/embeddings` (OpenAI; + `/v1/science/predict` secondary) |
| Embedding dim | 1500 (mean-pooled) |
| Max input | 1024 tokens (~6 kbp) |
| Parameters | 1B |
| GPU | HAMi slice 8 GiB (`nvidia.com/gpumem: 8192`) |
| Scale | scale-to-zero (`minReplicas: 0`, 15m retention) |
| Weights | PVC `agront-data` (RWX, nfs-models, 20Gi) |
