# xtts-v2 Notes

## Purpose
Coqui XTTS-v2 multilingual TTS + voice cloning. OpenAI-style `POST /v1/audio/speech` → `audio/wav`.
Card type `tts`.

## Runtime
- Custom FastAPI server in `server-configmap.yaml` (ConfigMap `xtts-v2-server`, mounted at `/app`).
- `python:3.11-slim` running `/data/venv/bin/python /app/server.py`.
- Init builds the venv on the PVC (`TTS`, `transformers==4.40.2`, torch) — gated by
  `import TTS, torch, fastapi` so cold starts skip the rebuild.
- Env: `COQUI_TOS_AGREED=1`, `HF_HOME=/data/xtts-cache`.
- GPU HAMi slice 8 GiB; fp32 (~1.8B).

## Storage
- PVC `xtts-v2` (RWX, nfs-models, 25Gi; bare fleet naming, was `xtts-v2-data`/`model-data`):
  venv + XTTS cache + saved voices.

## Gateway integration
- ISVC / PVC / card id: `xtts-v2`; `routing.k8s_name: xtts-v2`; type `tts`.
- Always-on: minReplicas 1 (max 2). Cold start ~1–2 min (venv cached on PVC after first build).

## Deploy / update steps
1. `kubectl apply -f pvc.yaml`
2. `kubectl apply -f server-configmap.yaml`
3. `kubectl apply -f inferenceservice.yaml`
4. `kubectl apply -f details.yaml`

> Apply each file in its own `kubectl apply -f -` (plain apply, not `--server-side`).

## Validation
- POST `/v1/audio/speech {model,input,language}` → 200, `audio/wav` (RIFF/WAVE header, >1 KB).
- Run inside the gateway pod:
  `cat models/xtts-v2/test.py | kubectl exec -i -n models deploy/model-gateway -c gateway -- python3 -`
