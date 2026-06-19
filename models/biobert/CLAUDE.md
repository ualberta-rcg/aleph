# biobert Notes

## Purpose
Biomedical text embedding service (768-dim mean-pooled) for biomedical NLP — NER, relation
extraction, search. Template-C (`type: embedding`) — custom-transformers-on-GPU variant.

## Runtime
- Image: `python:3.11-slim` running `/data/venv/bin/python /app/server.py` (cu121 torch +
  transformers 4.46.3)
- server.py: embedded as the `biobert-server` ConfigMap (mounted at `/app`); BertTokenizer + BertModel
- API path(s): `POST /v1/embeddings` (OpenAI-shaped; accepts `input`/`texts`), `GET /health`
- NOTE: transformers pinned 4.46.3 for the cu121 torch wheel (>=4.48 imports an absent float8 type).

## Resources
- CPU request/limit: init 2/4, server 2/4
- Memory request/limit: init 4Gi/8Gi, server 4Gi/8Gi
- GPU request: `nvidia.com/gpu: 1` · HAMi `nvidia.com/gpumem: 3072` (3 GiB slice; fp16)

## Storage
- PVC name: `biobert-data` (**ReadWriteMany**, **nfs-models** SC, 15Gi) — split out of inferenceservice.yaml
  2026-06-19. NOTE: live PVC is on `nfs-models` (the dedicated model-weights share), not `nfs-client`.
- Mount path: `/data` (venv + model; `HF_HOME=/data/hf_cache`). App at `/app` (ConfigMap).

## Known quirks
- `ignore_mismatched_sizes=True` on load (BioBERT checkpoint vs config head size).
- **usage quirk:** `prompt_tokens`/`total_tokens` = the **number of input strings** (not token counts).
- **Truncation safe:** tokenizer `max_length=512` pre-truncates → no OOM (small model, 3 GiB slice).
- **Scale-to-zero** (`minReplicas: 0`): first request scales 0→1 (cold start ~1–2 min).

## Deploy / update steps
1. `kubectl apply -f pvc.yaml` (RWX; caches venv + model).
2. `kubectl apply -f inferenceservice.yaml` (ConfigMap server.py + ISVC; init builds venv + downloads).
3. `kubectl apply -f details.yaml` (Template-C card; hot-reloads via ConfigMap watch).
> Apply method: to sync the card/PVC only, apply `details.yaml`/`pvc.yaml` alone — don't re-apply the
> ISVC with plain client-side `kubectl apply` (churns a Knative revision).

## Validation checks
- [x] basic request — dim == 768
- [x] batch (3 texts → 3 vectors, same dim)
- [x] usage + model echo (biobert)
- [x] distinctness (cos 0.81)
- [x] encoding_format=float
- [x] truncation (>512 tokens → 768-dim, no 500)
- [x] guardrails (chat→embed 404, unknown model 404)
- [x] catalog entry (type=embedding, ctx 512)
- [x] no secret values in manifest
