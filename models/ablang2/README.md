# AbLang-2 (oxpig/ablang2-paired)

Antibody language model — **480-dim mean-pooled antibody/protein-sequence embeddings** (AbRep last
hidden states). Also serves `/v1/restore` (paratope/CDR restoration). CPU-only (48M params).
Custom FastAPI server, scale-to-zero. OpenAI-compliant `/v1/embeddings` (batch + usage).

> **Non-HF weights** — AbLang-2 downloads its weights from **Zenodo** (via the `ablang2` package),
> not HuggingFace. The PVC was migrated `RWO → RWX` (2026-06-19) by copying from the old RWO PVC
> (`ablang2-data`) into the RWX PVC (`ablang2-data-rwx`) to avoid a slow Zenodo re-download.

## Deployment

```bash
kubectl apply -f pvc.yaml              # venv + Zenodo weights (nfs-models, RWX: ablang2-data-rwx)
kubectl apply -f inferenceservice.yaml # custom FastAPI server (ConfigMap server.py) + ISVC, CPU
kubectl apply -f details.yaml          # Template-C card (type: embedding)
```

## Testing

```bash
# External via gateway VIP + Tyk auth (preferred)
GW_URL=http://<GATEWAY_VIP> TYK_KEY=<key> python3 models/ablang2/test.py

# Or inside the gateway pod (no auth)
cat models/ablang2/test.py | kubectl exec -i -n models deploy/model-gateway -c gateway -- python3 -
```

Last run (2026-06-19): **6 PASS / 2 EXP / 0 FAIL** — dim 480, batch, model-echo, usage,
distinctness, guardrails, catalog.

## Key Configuration

| Setting | Value |
|---------|-------|
| Backend | custom FastAPI + `ablang2` package (CPU) |
| Endpoint | `POST /v1/embeddings` (+ `/v1/restore`), health `/health` |
| Embedding dim | 480 (mean-pooled) |
| Parameters | 48M |
| Scale | scale-to-zero (`minReplicas: 0`, 15m retention) |
| Weights | PVC `ablang2-data-rwx` (RWX nfs-models; non-HF Zenodo, cp-migrated from RWO) |
