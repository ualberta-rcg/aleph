# multilingual-e5-small Notes

## Purpose
Multilingual (100+) text embedding service (384-dim, mean-pooled + L2-normalized) for retrieval.
Template-C (`type: embedding`) — custom-transformers-server variant.

## Runtime
- Image: `python:3.11-slim` running `/data/venv/bin/python /app/server.py` (CPU torch 2.5.1 +
  transformers 4.44.2 + sentencepiece)
- server.py: embedded as the `multilingual-e5-small-server` ConfigMap (mounted at `/app`)
- API path(s): `POST /v1/embeddings` (OpenAI-shaped), `GET /health`, `GET /v1/models`
- NOTE: transformers pinned 4.44.2 (needs `sentencepiece`; init rebuilds the venv if the version
  drifts). This is a **custom transformers server, NOT TEI** (older docs incorrectly said TEI / `/embed`).

## Resources
- CPU request/limit: init 2/4, server 2/4
- Memory request/limit: init 4Gi/8Gi, server 2Gi/4Gi
- GPU request: **none** (CPU-only)

## Storage
- PVC name: `multilingual-e5-small` (**ReadWriteMany**, nfs-models, 5Gi; bare fleet naming, was `multilingual-e5-small-data`/`model-data`)
- Mount path: `/data` (init writes venv + model; server reads readOnly). App at `/app` (ConfigMap).
- Warm-cache condition: `/data/venv/bin/python` imports sentencepiece + transformers==4.44.2 AND `/data/model/config.json` present

## Known quirks
- **Custom transformers server** (not TEI/`/embed`): `/v1/embeddings` only, OpenAI-shaped output.
  Earlier README/CLAUDE described a TEI deployment that was never what got deployed — corrected 2026-06-19.
- **usage quirk:** `prompt_tokens` is the whitespace-split **word count** (not tokenizer tokens);
  `total_tokens` is hardcoded `0`. Cosmetic.
- **L2-normalized** server-side; mean pooling over attention-masked tokens.
- **No prefix enforcement:** `query:`/`passage:` is the caller's responsibility for retrieval.
- **Truncation safe:** tokenizer `max_length=512` pre-truncates → no OOM (small CPU model).
- **Always-on** (`minReplicas: 1`, max 5, scaleTarget 8): warm multilingual tier.

## Deploy / update steps
1. `kubectl apply -f pvc.yaml` (RWX; caches venv + model).
2. `kubectl apply -f inferenceservice.yaml` (ConfigMap server.py + ISVC; init builds venv + downloads).
3. `kubectl apply -f details.yaml` (Template-C card; hot-reloads via ConfigMap watch).
> Apply method: to sync the card/PVC only, apply `details.yaml`/`pvc.yaml` alone — don't re-apply the
> ISVC with plain client-side `kubectl apply` (churns a Knative revision).

## Validation checks
- [x] basic request — dim == 384
- [x] batch (3 texts → 3 vectors, same dim)
- [x] usage + model echo
- [x] distinctness (cos 0.86)
- [x] multilingual (EN/ES/ZH same sentence → cos 0.92)
- [x] encoding_format=float
- [x] truncation (>512 tokens → 384-dim, no 500)
- [x] guardrails (chat→embed 404, unknown model 404)
- [x] catalog entry (type=embedding, ctx 512)
- [x] no secret values in manifest (HF_TOKEN via hf-token Secret)
