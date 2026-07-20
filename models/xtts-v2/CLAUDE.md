# xtts-v2 Notes

## Purpose
Coqui XTTS-v2 multilingual TTS **+ voice cloning**. Three public paths:
- `POST /v1/audio/speech` — OpenAI-style TTS → `audio/wav`. `voice` is a built-in preset name
  **or** a saved clone name (recalled from the PVC).
- `POST /v1/audio/clone` — clone a voice from a ~6 s reference WAV (multipart `file=` upload,
  or JSON base64 `voice_sample`). Optional `save_as=<name>` persists the clip on the PVC.
- `GET /v1/audio/voices` — `{voices:[built-in presets], saved:[cloned names], default}`.
Card type `tts`.

## Voice cloning
Coqui clones via the `speaker_wav` argument. `_synthesize(..., speaker_wav=<path>)` calls
`tts.tts_to_file(text=, speaker_wav=, language=, speed=)`. Saved clones live at
`/data/voices/<sanitized-name>.wav` (PVC); `/v1/audio/speech` resolves `voice` against saved
clones first, then built-in speakers, then the default — fully additive over the old preset-only
behaviour.

## Runtime
- Custom FastAPI server in `server-configmap.yaml` (ConfigMap `xtts-v2-server`, mounted at `/app`).
- `python:3.11-slim` running `/data/venv/bin/python /app/server.py`.
- Init builds the venv on the PVC (`TTS`, `transformers==4.40.2`, `torch`, `python-multipart`,
  `fastapi`, `uvicorn`) — gated by `import TTS, torch, fastapi` so cold starts skip the rebuild.
- Env: `COQUI_TOS_AGREED=1`, `HF_HOME=/data/xtts-cache`.
- GPU HAMi slice 8 GiB; fp32 (~1.8B).

## Gotchas (bring-up, 2026-07-19)
- **torchaudio 2.11 backend:** defaults to `torchcodec` (not installed) — Coqui's
  `xtts.load_audio` → `torchaudio.load` would 500 on clone. The server monkeypatches
  `torchaudio.load` to decode via `soundfile` (already in the venv; `librosa` fallback). Preset
  TTS was unaffected (it never loads a file).
- **Synth output → `/dev/shm`** tmpfs (fallback default temp dir) to skip overlay/NFS round-trip.
- **Saved-voice name sanitization:** lowercase alnum + dash only.

## Storage
- PVC `xtts-v2` (RWX, nfs-models, 25Gi; bare fleet naming, was `xtts-v2-data`/`model-data`):
  venv + XTTS cache + `/data/voices/*.wav` (saved clones).

## Gateway integration
- ISVC / PVC / card id: `xtts-v2`; `routing.k8s_name: xtts-v2`; type `tts`.
- Gateway has dedicated handlers for `/v1/audio/clone` (POST, multipart + JSON) and
  `/v1/audio/voices` (GET) — both resolve the card by `model` (default `xtts-v2`) and are
  registered before the JSON-only catch-all. `/v1/audio/speech` and the catch-all are unchanged.
- Always-on: minReplicas 1 (max 2). Cold start ~1–2 min (venv cached on PVC after first build).

## Deploy / update steps
1. `kubectl apply -f pvc.yaml`
2. `kubectl apply -f server-configmap.yaml`
3. `kubectl apply -f inferenceservice.yaml`
4. `kubectl apply -f details.yaml`

> Apply each file in its own `kubectl apply -f -` (plain apply, not `--server-side`). After a
> server change, restart the pod: `kubectl delete pod -l serving.knative.dev/service=xtts-v2-predictor`.

## Validation
- POST `/v1/audio/speech {model,input,language,voice}` → 200, `audio/wav` (preset or saved voice).
- POST `/v1/audio/clone` (multipart `file` or base64 `voice_sample`) → 200, `audio/wav`.
- GET `/v1/audio/voices` → JSON with `voices`, `saved`, `default`.
- Run inside the gateway pod:
  `cat models/xtts-v2/test.py | kubectl exec -i -n models deploy/model-gateway -c gateway -- python3 -`

