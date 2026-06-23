# dnabert-2 (dnabert-2-117m) Notes

## Purpose
DNA-sequence embedding service (768-dim mean-pooled) for genomics — variant-effect prediction,
genome annotation, regulatory/epigenomic tasks. Template-C (`type: embedding`), custom-transformers variant.

## Runtime
- Image: `python:3.11-slim` running `/data/venv/bin/python /app/server.py` (CPU torch 2.5.1 +
  transformers 4.40.2; **trust_remote_code** custom model)
- server.py: embedded as the `dnabert-2-server` ConfigMap (mounted at `/app`)
- API path(s): `POST /v1/embeddings` (OpenAI-shaped), `GET /health`, `GET /v1/models`
- Env: `TORCHDYNAMO_DISABLE=1`, `TORCH_COMPILE_DISABLE=1` (custom ops)

## Resources
- CPU request/limit: init 2/4, server 2/4
- Memory request/limit: init 4Gi/8Gi, server 2Gi/4Gi
- GPU request: **none** (CPU-only)

## Storage
- PVC name: `dnabert-2-data` (**ReadWriteMany**, nfs-models, 5Gi)
- Mount path: `/data` (init writes venv + model; server reads readOnly). App at `/app` (ConfigMap).
- Warm-cache condition: sentinel `/data/venv/.pin-torch251` + `/data/model/config.json`

## Known quirks
- **Pinned torch 2.5.1+cpu / transformers 4.40.2:** DNABERT-2's custom ops break on torch>=2.6
  (meta-device fake-dispatch). Init rebuilds the venv if the sentinel is missing.
- **Custom remote-code model:** `trust_remote_code=True`, custom BertConfig/BertModel.
  - Patches `pad_token_id=0` if unset in the config.
  - `low_cpu_mem_usage=False` (avoids meta-device init conflicting with custom-op fake registration).
  - **Tuple output:** the custom model returns a `tuple`, not a `ModelOutput` — server reads
    `raw.last_hidden_state if hasattr(...) else raw[0]`.
- **usage quirk:** `prompt_tokens` is the **sequence length** (char count), `total_tokens` hardcoded `0`.
- **Truncation safe:** tokenizer `max_length=512` pre-truncates → no OOM (small CPU model).
- **v2 card conversion (2026-06-19):** old-schema card rewritten to v2 Template C (`behavior`/`scaling`/`catalog`).

## Deploy / update steps
1. `kubectl apply -f pvc.yaml` (RWX; caches venv + model).
2. `kubectl apply -f inferenceservice.yaml` (ConfigMap server.py + ISVC; init pins venv + downloads).
3. `kubectl apply -f details.yaml` (Template-C card; hot-reloads via ConfigMap watch).
> Apply method: to sync the card/PVC only, apply `details.yaml`/`pvc.yaml` alone — don't re-apply the
> ISVC with plain client-side `kubectl apply` (churns a Knative revision).

## Validation checks
- [x] basic request — dim == 768
- [x] batch (3 DNA seqs → 3 vectors, same dim)
- [x] usage + model echo (dnabert-2-117m)
- [x] distinctness (cos 0.44)
- [x] encoding_format=float
- [x] truncation (>512 tokens → 768-dim, no 500)
- [x] guardrails (chat→embed 404, unknown model 404)
- [x] catalog entry (type=embedding, ctx 512)
- [x] no secret values in manifest (HF_TOKEN via hf-token Secret)
