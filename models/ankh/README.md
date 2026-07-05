# Ankh-base (ElnaggarLab/ankh-base)

Protein language model based on a **T5 encoder** (trained on ~30M unlabeled protein sequences) —
**768-dim mean-pooled protein embeddings**. Input is space-separated amino acids; fp32 (T5 encoders
overflow to NaN in fp16, sanitized). Custom FastAPI/transformers server on a HAMi GPU slice,
always-on (minReplicas: 1). OpenAI-compliant `/v1/embeddings` (batch + usage).

## Deployment

```bash
kubectl apply -f pvc.yaml              # RWX venv + HF cache (nfs-models)
kubectl apply -f inferenceservice.yaml # custom transformers server (ConfigMap server.py) + ISVC, GPU
kubectl apply -f details.yaml          # Template-C card (type: embedding)
```

## Testing

```bash
# External via gateway VIP + Tyk auth (preferred)
GW_URL=http://<GATEWAY_VIP> TYK_KEY=<key> python3 models/ankh/test.py

# Or inside the gateway pod (no auth)
cat models/ankh/test.py | kubectl exec -i -n models deploy/model-gateway -c gateway -- python3 -
```

Last run (2026-06-19): **8 PASS / 2 EXP / 0 FAIL** — dim 768, batch, model-echo, usage,
distinctness, encoding_format, truncation, guardrails, catalog.

## Key Configuration

| Setting | Value |
|---------|-------|
| Backend | custom FastAPI + `transformers` T5EncoderModel (GPU, fp32) |
| Endpoint | `POST /v1/embeddings` (OpenAI-shaped; `input`/`sequences`), health `/health` |
| Embedding dim | 768 (mean-pooled, NaN→0) |
| Max input | 1024 residues |
| Precision | fp32 (T5 encoder NaN in fp16) |
| GPU | HAMi slice 8 GiB (`nvidia.com/gpumem: 8192`) |
| Scale | always-on (`minReplicas: 1`, max 3, 15m retention) |
| Weights | PVC `ankh` (RWX, nfs-models; bare fleet naming) |
