# esm2-650m Notes

## Purpose
Protein-sequence embedding service (1280-dim mean-pooled) for proteomics downstream tasks.
Template-C (`type: embedding`) — custom-transformers-server variant.

## Runtime
- Image: `python:3.11-slim` running `/data/venv/bin/python /app/server.py` (cu121 torch + transformers 4.46.3)
- server.py: embedded as the `esm2-650m-server` ConfigMap (mounted at `/app`)
- API path(s): `POST /v1/embeddings` (OpenAI-shaped), `GET /health`, `GET /v1/models`
- NOTE: transformers must be pinned `==4.46.3` for the cu121 torch wheel (>=4.48 imports
  `torch.float8_e8m0fnu`, absent in cu121). Idempotent pip in the init container.

## Resources
- CPU request/limit: init 2/4, server 2/4
- Memory request/limit: init 4Gi/8Gi, server 4Gi/8Gi
- GPU request: `nvidia.com/gpu: 1` · HAMi `nvidia.com/gpumem: 4096` (4 GiB slice; model fp16 ~1.3 GiB)

## Storage
- PVC name: `esm2-650m-data` (**ReadWriteMany**, nfs-client, 15Gi) — split out of inferenceservice.yaml 2026-06-19
- Mount path: `/data` (init writes venv + model; server reads readOnly). App at `/app` (ConfigMap).
- Warm-cache condition: `/data/venv/bin/python` imports torch AND `/data/model/config.json` exists

## Known quirks
- **Custom transformers server** (not vLLM/TEI): no streaming, no `encoding_format=base64` (float only;
  the param is accepted but ignored). `/v1/embeddings` returns OpenAI-shaped `{object:list, data:[...]}`.
- **Truncation is safe here:** the tokenizer uses `truncation=True, max_length=1022`, so >1022-residue
  inputs are pre-truncated before the model — no OOM (unlike TEI bge-m3). The test exercises this.
- **usage.prompt_tokens = raw residue count** (server sums `len(seq)`), not the truncated token count.
- **Scale-to-zero** (`minReplicas: 0`): first request scales 0→1 (cold start ~1–2 min). Leave at 0, no stop.

## Deploy / update steps
1. `kubectl apply -f pvc.yaml` (RWX; caches venv + model).
2. `kubectl apply -f inferenceservice.yaml` (ConfigMap server.py + ISVC; init builds venv + downloads).
3. `kubectl apply -f details.yaml` (Template-C card; hot-reloads via ConfigMap watch).
> Apply method: to sync only the card/PVC, apply `details.yaml`/`pvc.yaml` alone — do NOT re-apply
> the ISVC with plain client-side `kubectl apply`: it churns a new Knative revision (observed 2 pods
> transiently, drains in ~1 min). If the ISVC spec must change, use
> `kubectl apply --server-side --force-conflicts`.

## Validation checks
- [x] basic request — dim == 1280
- [x] batch (3 sequences → 3 vectors, same dim)
- [x] usage + model echo
- [x] distinctness (two peptides → cosine < 0.99)
- [x] encoding_format=float
- [x] truncation (>1022 residues → 1280-dim, no 500)
- [x] guardrails (chat→embed 404, unknown model 404)
- [x] catalog entry (type=embedding, ctx 1022)
- [x] no secret values in manifest (HF_TOKEN via hf-token Secret)
