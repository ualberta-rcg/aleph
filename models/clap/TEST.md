# clap — Test Report

Cluster 230, gateway `http://10.43.79.101:80`. Type: embedding/audio (CPU). id `clap`.

## Scale-up
- Cold start: venv (CPU torch) + HF snapshot_download (laion/larger_clap_general), then
  load. `3/3 Running`. ~3-4 min (warm restart ~80s).

## Endpoint tests (PASS)

### POST /v1/embeddings (text)
```bash
curl -s -X POST $GW/v1/embeddings -d '{"model":"clap","texts":["a dog barking","rain falling"]}'
```
→ `text_count=2, dim=512`. PASS. (Audio embeddings via `audio` field, same 512-dim space.)

### POST /v1/classify (zero-shot audio)
Synthetic 440 Hz sine (48 kHz, 1s) with labels [bird song, rain, pure tone, speech]:
→ top = **pure tone** (score 0.99999). PASS — correctly identifies the tone.

### Catalog
- `GET /v1/models?all=true` → `clap` discovered. PASS.

## Migration fix
- `/v1/classify` failed on newer transformers: `ClapModel` has `logit_scale_a`/`logit_scale_t`,
  not `logit_scale`. Server patched to use `logit_scale_a` (fallback to `logit_scale`).
- Also switched the venv from GPU torch (cu126, unused) to CPU torch.

## Not applicable
- OpenAI chat / Anthropic / reasoning: N/A (audio-language model).

## Card parity
id=clap, k8s_name=clap, type=embedding, dim=512 (verified), gpu=false,
endpoints /v1/embeddings + /v1/classify.
