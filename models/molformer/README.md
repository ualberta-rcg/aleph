# MoLFormer-XL (ibm-research/MoLFormer-XL-both-10pct)

IBM Research MoLFormer-XL (110M) — linear-attention transformer pre-trained on 1.1B molecules
(PubChem + ZINC). Turns a **SMILES string into a 768-dim molecular embedding** for property
prediction / similarity (outperforms GROVER/ChemBERTa on MoleculeNet). Custom FastAPI/transformers
server on a HAMi GPU slice, scale-to-zero. Serves the standard OpenAI `/v1/embeddings`
(`/v1/science/embed` kept as secondary).

## Deployment

```bash
kubectl apply -f pvc.yaml              # RWX venv + model (nfs-models)
kubectl apply -f inferenceservice.yaml # custom transformers server (ConfigMap server.py) + ISVC, GPU
kubectl apply -f details.yaml          # Template-C card (type: embedding)
```

## Testing

```bash
cat models/molformer/test.py | kubectl exec -i -n models deploy/model-gateway -c gateway -- python3 -
```

Last run (2026-06-19): **7 PASS / 2 EXP / 0 FAIL** — dim 768, batch, model-echo, usage,
distinctness, truncation, guardrails, catalog.

## Key Configuration

| Setting | Value |
|---------|-------|
| Backend | custom FastAPI + `transformers` AutoModel (GPU, trust_remote_code, deterministic_eval) |
| Endpoint | `POST /v1/embeddings` (OpenAI; + `/v1/science/embed` secondary) |
| Embedding dim | 768 (pooler/mean) |
| Max input | 202 tokens (SMILES) |
| Parameters | 110M |
| GPU | HAMi slice 3 GiB (`nvidia.com/gpumem: 3072`) |
| Scale | scale-to-zero (`minReplicas: 0`, 15m retention) |
| Weights | PVC `molformer-data` (RWX, nfs-models; migrated from RWO) |
