# Geneformer (ctheodoris/Geneformer, V2-104M)

Geneformer (NIH NCI / ctheodoris, 104M) — a context-aware foundation model pretrained on 30M
single-cell transcriptomes. Takes ranked gene tokens (gene names + expression values) and produces
a **cell-level embedding** (mean-pooled hidden states). Use cases: cell-type classification, gene
network analysis, in silico perturbation.

Custom FastAPI/transformers server on CPU, scale-to-zero, venv-on-PVC.

**Non-text domain model**: gene-expression input — does **not** expose OpenAI `/v1/embeddings`.
Serves `POST /v1/science/embed` (with `/v1/embed` as a secondary alias).

## Deployment

```bash
kubectl apply -f pvc.yaml              # RWX venv + weights + tokenizer (nfs-client) — cp-migrated from old RWO
kubectl apply -f inferenceservice.yaml # ConfigMap (server.py) + ISVC, CPU
kubectl apply -f details.yaml          # Template-C card (type: embedding)
```

## Testing

```bash
cat models/geneformer/test.py | kubectl exec -i -n models deploy/model-gateway -c gateway -- python3 -
```

Last run (2026-06-19): **6 PASS / 0 FAIL** — dim (read from response), non-zero, distinctness,
deterministic, model-echo, malformed.

## Key Configuration

| Setting | Value |
|---------|-------|
| Backend | custom FastAPI + transformers `AutoModel` (CPU) |
| Endpoint | `POST /v1/science/embed` (domain; genes+expression; `/v1/embed` secondary) |
| Embedding dim | 256 (v2-104M mean-pooled hidden states) |
| Input | `genes` [names] + `expression` [floats] (tokenized + ranked; max 4096) |
| Parameters | 104M (V2) |
| GPU | none (CPU) |
| Scale | scale-to-zero (`minReplicas: 0`, 15m retention) |
| PVC | `geneformer-data-rwx` (RWX, nfs-client, 8Gi) — venv + weights + tokenizer |
