# ESM-C 300M (EvolutionaryScale/esmc-300m-2024-12)

**ESM-C (Cambrian) 300M** — EvolutionaryScale's next-gen protein language model, a drop-in
replacement for ESM-2 with improved performance. Uses the **esm SDK**. 960-dim mean-pooled
per-protein embeddings of amino-acid sequences (up to 2048 residues). Custom FastAPI server on a
HAMi GPU slice, always-on (minReplicas: 1).

## Deployment

```bash
kubectl apply -f pvc.yaml              # RWX venv + model (nfs-models)
kubectl apply -f inferenceservice.yaml # custom FastAPI server (esm SDK, ConfigMap server.py) + ISVC, GPU
kubectl apply -f details.yaml          # Template-C card (type: embedding)
```

## Testing

The 10-check protein-embedding battery runs inside the gateway pod (first call wakes a
scaled-to-zero GPU model — ESM-C's cold rebuild is **slow, >6 min** after a PVC recreate):

```bash
# External via gateway VIP + Tyk auth (preferred)
GW_URL=http://<GATEWAY_VIP> TYK_KEY=<key> python3 models/esmc-300m/test.py

# Or inside the gateway pod (no auth)
cat models/esmc-300m/test.py | kubectl exec -i -n models deploy/model-gateway -c gateway -- python3 -
```

Last run (2026-06-19): **8 PASS / 2 EXP / 0 FAIL** — dim 960, batch, model-echo, usage,
distinctness (cos 0.82), encoding_format, truncation (>2048 residues), guardrails (chat→embed 404,
unknown-model 404), catalog (type=embedding, ctx 2048).

## Key Configuration

| Setting | Value |
|---------|-------|
| Backend | custom FastAPI + **esm SDK** (`ESMC.from_pretrained` → `encode` w/ `return_embeddings`) |
| Endpoint | `POST /v1/embeddings` (OpenAI-shaped; `input`/`sequences`), health `/health` |
| Embedding dim | 960 (mean-pooled over residues) |
| Max input | 2048 residues (tokenizer truncates longer) |
| Parameters | 300M |
| GPU | HAMi sub-GPU slice |
| Scale | always-on (`minReplicas: 1`, max 3, 15m retention) |
| Weights | PVC `esmc-300m` (RWX, nfs-models, 5Gi; bare fleet naming) |

## Model Highlights

- Next-gen ESM (Cambrian) — improved over ESM-2; uses the esm SDK.
- 960-dim per-protein embeddings via mean pooling.
- Long context (2048 residues); GPU slice, always-on.
