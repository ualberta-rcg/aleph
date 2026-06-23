# DNABERT-2 (zhihan1996/DNABERT-2-117M)

~117M-param **multi-species DNA foundation model** — 768-dim mean-pooled embeddings of DNA
sequences for variant-effect prediction, genome annotation, regulatory-element analysis, and
epigenomic prediction. Uses BPE tokenization (not fixed k-mers). Custom FastAPI/transformers
server, CPU-only, scale-to-zero.

## Deployment

```bash
kubectl apply -f pvc.yaml              # RWX weights + venv (nfs-models)
kubectl apply -f inferenceservice.yaml # custom transformers server (ConfigMap server.py) + ISVC
kubectl apply -f details.yaml          # Template-C card (type: embedding)
```

The init container builds a CPU venv pinned to **torch 2.5.1 + transformers 4.40.2** (custom ops
break on newer torch) and downloads the model to the PVC on first deploy (idempotent via a
sentinel). `server.py` is embedded as the `dnabert-2-server` ConfigMap.

## Testing

The 10-check DNA-embedding battery runs inside the gateway pod (first call wakes a
scaled-to-zero model — cold start ~30–60s):

```bash
cat models/dnabert-2/test.py | kubectl exec -i -n models deploy/model-gateway -c gateway -- python3 -
```

Last run (2026-06-19): **8 PASS / 2 EXP / 0 FAIL** — dim 768, batch, model-echo, usage,
distinctness (cos 0.44), encoding_format, truncation (>512 tokens), guardrails (chat→embed 404,
unknown-model 404), catalog (type=embedding, ctx 512).

## Key Configuration

| Setting | Value |
|---------|-------|
| Backend | custom FastAPI + `transformers` AutoModel (trust_remote_code, CPU) |
| Endpoint | `POST /v1/embeddings` (OpenAI-shaped), health `/health` |
| Embedding dim | 768 (mean-pooled, attention-masked) |
| Max input | 512 tokens (tokenizer truncates longer) |
| Precision | fp32 |
| Parameters | ~117M |
| Pins | torch 2.5.1+cpu, transformers 4.40.2, TORCHDYNAMO_DISABLE=1 |
| Scale | scale-to-zero (`minReplicas: 0`, 15m retention) |
| Weights | PVC `dnabert-2-data` (RWX, nfs-models, 5Gi) |

## Model Highlights

- BPE tokenization (variable k-mer) trained on multi-species genomes — generalizes across organisms.
- 768-dim embeddings for downstream genomics tasks (classification, variant effect, annotation).
- Custom remote-code model; served with pinned torch for op compatibility.
