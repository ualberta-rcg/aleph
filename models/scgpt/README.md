# scGPT (bowang-lab/scGPT)

scGPT — a foundation model for single-cell gene-expression data, trained on 33M cells. Takes gene
names + expression values per cell (tokenized via GeneVocab; unknown genes → `<pad>`) and returns
a **512-dim cell embedding** (mean-pooled). Use cases: cell-type annotation, batch correction,
perturbation prediction, multi-omic integration.

Custom FastAPI/scgpt server on a HAMi GPU slice, scale-to-zero, venv-on-PVC.

**Non-text domain model**: gene-expression input — does **not** expose OpenAI `/v1/embeddings` as
primary. Serves `POST /v1/science/embed` (OpenAI-style `/v1/embeddings` kept as secondary).

## Deployment

```bash
kubectl apply -f pvc.yaml              # RWX venv + weights + vocab (nfs-models, already RWX)
kubectl apply -f inferenceservice.yaml # ConfigMap (server.py) + ISVC, GPU
kubectl apply -f details.yaml          # Template-C card (type: embedding)
```

## Testing

```bash
# External via gateway VIP + Tyk auth (preferred)
GW_URL=http://<GATEWAY_VIP> TYK_KEY=<key> python3 models/scgpt/test.py

# Or inside the gateway pod (no auth)
cat models/scgpt/test.py | kubectl exec -i -n models deploy/model-gateway -c gateway -- python3 -
```

Last run (2026-06-19): **7 PASS / 0 FAIL** — dim 512, non-zero, distinctness, deterministic,
batch x2, model-echo, malformed.

## Key Configuration

| Setting | Value |
|---------|-------|
| Backend | custom FastAPI + scgpt `TransformerModel._encode` (GPU) |
| Endpoint | `POST /v1/science/embed` (domain; OpenAI-style cell input; `/v1/embeddings` secondary) |
| Embedding dim | 512 (mean-pooled) |
| Input | `input` = `{genes:[names], values:[floats]}` (a cell) or list of cells |
| Parameters | ~51M (12-layer, 8-head, 512 hidden) |
| GPU | HAMi L40S slice 10 GiB (`nvidia.com/gpumem: 10240`) |
| Scale | scale-to-zero (`minReplicas: 0`, 15m retention) |
| PVC | `scgpt-data` (RWX, nfs-models, 15Gi) — venv + weights + vocab |
