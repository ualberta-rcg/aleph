# ProkBERT-mini (neuralbioinfo/prokbert-mini)

Compact **prokaryotic (bacterial) DNA language model** — MegatronBERT (20.6M params), trained on
206B nucleotides from bacterial genomes, 6-mer Local-Context-Aware tokenizer. **384-dim mean-pooled
embeddings** of bacterial DNA for phage/promoter/genomics tasks. Custom FastAPI/transformers server
on a HAMi GPU slice, scale-to-zero. No PVC (loads from HF hub, ephemeral cache). OpenAI-compliant
`/v1/embeddings` (batch + usage).

## Deployment

```bash
kubectl apply -f inferenceservice.yaml # custom transformers server (ConfigMap server.py) + ISVC, GPU
kubectl apply -f details.yaml          # Template-C card (type: embedding)
```

No PVC — the model is small; the container installs deps + loads from the HF hub on each cold start
(`HF_HOME=/tmp/hf_cache`, ephemeral).

## Testing

```bash
# External via gateway VIP + Tyk auth (preferred)
GW_URL=http://<GATEWAY_VIP> TYK_KEY=<key> python3 models/prokbert/test.py

# Or inside the gateway pod (no auth)
cat models/prokbert/test.py | kubectl exec -i -n models deploy/model-gateway -c gateway -- python3 -
```

Last run (2026-06-19): **8 PASS / 2 EXP / 0 FAIL** — dim 384, batch, model-echo, usage,
distinctness, encoding_format, truncation, guardrails, catalog.

## Key Configuration

| Setting | Value |
|---------|-------|
| Backend | custom FastAPI + `transformers` AutoModel (GPU, trust_remote_code) |
| Endpoint | `POST /v1/embeddings` (OpenAI; + `/v1/science/predict` secondary) |
| Embedding dim | 384 (mean-pooled) |
| Max input | 1024 tokens |
| Parameters | 20.6M (MegatronBERT) |
| GPU | HAMi slice 3 GiB (`nvidia.com/gpumem: 3072`) |
| Scale | scale-to-zero (`minReplicas: 0`, 15m retention) |
| Weights | none (HF hub, ephemeral cache) |
