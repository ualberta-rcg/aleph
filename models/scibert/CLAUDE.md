# scibert (scibert-110m) Notes

## Purpose
Scientific-text embedding service (768-dim mean-pooled) for scientific NLP — NER, classification,
similarity. Template-C (`type: embedding`), custom-transformers-server variant.

## Runtime
- Image: `python:3.11-slim` running `/data/venv/bin/python /app/server.py` (CPU torch + transformers)
- server.py: embedded as the `scibert-server` ConfigMap (mounted at `/app`)
- API path(s): `POST /v1/embeddings` (OpenAI-shaped), `GET /health`, `GET /v1/models`

## Resources
- CPU request/limit: init 2/4, server 2/4
- Memory request/limit: init 4Gi/8Gi, server 2Gi/4Gi
- GPU request: **none** (CPU-only)

## Storage
- PVC name: `scibert-data` (**ReadWriteMany**, nfs-client, 5Gi)
- Mount path: `/data` (init writes venv + model; server reads readOnly). App at `/app` (ConfigMap).
- Warm-cache condition: `/data/venv/bin/python` + `/data/model/config.json` present

## Known quirks
- **SciVocab tokenizer** (custom SentencePiece) — standard `AutoTokenizer` loads it fine.
- **Mean-pooling over attention-masked tokens** (standard BERT pooling).
- **usage quirk:** `prompt_tokens` is the whitespace-split **word count** (not tokenizer tokens), and
  `total_tokens` is hardcoded `0`. Cosmetic only.
- **Truncation safe:** tokenizer uses `truncation=True, max_length=512`, so >512-token inputs are
  pre-truncated → no OOM (tiny 110M model, CPU).
- **v2 card conversion (2026-06-19):** the card was old-schema (top-level fields, `compatibility`/
  `deployment`/`server_config` blocks) → rewritten to v2 Template C (`behavior`/`scaling`/`limits`/
  `catalog`). The gateway reads `behavior.*` (NOT the old `compatibility.*`).

## Deploy / update steps
1. `kubectl apply -f pvc.yaml` (RWX; caches venv + model).
2. `kubectl apply -f inferenceservice.yaml` (ConfigMap server.py + ISVC).
3. `kubectl apply -f details.yaml` (Template-C card; hot-reloads via ConfigMap watch).
> Apply method: to sync the card/PVC only, apply `details.yaml`/`pvc.yaml` alone — do NOT re-apply the
> ISVC with plain client-side `kubectl apply` (churns a Knative revision). If the ISVC must change,
> use `kubectl apply --server-side --force-conflicts`.

## Validation checks
- [x] basic request — dim == 768
- [x] batch (3 texts → 3 vectors, same dim)
- [x] usage + model echo (scibert-110m)
- [x] distinctness (cos 0.71 between two texts)
- [x] encoding_format=float
- [x] truncation (>512 tokens → 768-dim, no 500)
- [x] guardrails (chat→embed 404, unknown model 404)
- [x] catalog entry (type=embedding, ctx 512)
- [x] no secret values in manifest (HF_TOKEN via hf-token Secret)
