# matscibert Notes

## Purpose
Materials-science text embedding service (768-dim [CLS]-pooled) + masked-token prediction.
Template-C (`type: embedding`), custom-transformers-on-GPU.

## Runtime
- Image: `python:3.11-slim` running `/data/venv/bin/python /app/server.py` (cu121 torch + transformers 4.46.3)
- server.py: embedded as the `matscibert-server` ConfigMap (mounted at `/app`)
- Endpoints: **`POST /v1/embeddings`** (OpenAI-style, added 2026-06-19) + `POST /v1/science/embed`
  (legacy `{text}`→`{embeddings}`) + `POST /v1/science/predict` (fill-mask). `GET /health`, `/v1/models`.

## Resources
- CPU request/limit: init 1/2, server 1/2
- Memory request/limit: init 2Gi/4Gi, server 2Gi/4Gi
- GPU: HAMi `nvidia.com/gpumem: 3072` (3 GiB slice)

## Storage
- PVC `matscibert` (**ReadWriteMany**, nfs-models, 15Gi) — bare fleet naming (was `matscibert-data`/`model-data`).
- Mount `/data` (venv + model + HF cache); server code at `/app` (ConfigMap).

## Known quirks
- **[CLS] pooling** (`last_hidden_state[:, 0, :]`) — not mean. Card reflects this.
- **/v1/embeddings added 2026-06-19**: the legacy server only exposed `/v1/science/embed` (non-OpenAI
  shape `{text}`→`{embeddings}`), so it 404'd on the standard `/v1/embeddings` (the gateway forwards
  to backend `/v1/embeddings`). Added an OpenAI-contract `/v1/embeddings` route (keeps the legacy route).
  Apply = update the `matscibert-server` ConfigMap + restart the pod (delete it; wake-on-demand recreates).
- usage: `prompt_tokens` = whitespace word count.
- Always-on (`minReplicas: 1`, max 3, scaleTarget 8).

## Deploy / update steps
1. `kubectl apply -f pvc.yaml` (RWX; caches venv + model).
2. `kubectl apply -f inferenceservice.yaml` (ConfigMap server.py + ISVC).
3. `kubectl apply -f details.yaml` (Template-C card; hot-reloads via ConfigMap watch).
> After changing server.py: the ConfigMap updates, but the running pod keeps the old code in memory —
> delete the predictor pod (or toggle stop) so the next pod loads the new server.py.

## Validation checks
- [x] basic request — dim == 768 (via /v1/embeddings)
- [x] batch, model-echo, usage, distinctness, encoding_format, truncation
- [x] guardrails (chat→embed 4xx, unknown model 404), catalog (type=embedding, ctx 512)
- [x] no secret values in manifest (HF_TOKEN via hf-token Secret)
