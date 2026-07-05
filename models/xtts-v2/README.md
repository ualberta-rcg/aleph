# XTTS-v2 (coqui/XTTS-v2)

Coqui **XTTS-v2** — multilingual text-to-speech with voice cloning from a ~6 s sample. 17 languages,
24 kHz WAV output. Custom FastAPI server (`server-configmap.yaml`, ConfigMap `xtts-v2-server`) wrapping
`coqui-tts`, on a HAMi GPU slice, always-on (minReplicas: 1). OpenAI-style
`POST /v1/audio/speech {model,input,language,voice}` → `audio/wav`. ~1.8B params, fp32.

## Deployment

```bash
kubectl apply -f pvc.yaml               # RWX venv + XTTS cache + voices (nfs-models)
kubectl apply -f server-configmap.yaml  # the FastAPI TTS server (ConfigMap xtts-v2-server)
kubectl apply -f inferenceservice.yaml  # ISVC (init builds venv on PVC) + mounts the server
kubectl apply -f details.yaml           # Template card (type: tts)
```

## Testing

```bash
# Inside the gateway pod (no auth)
cat models/xtts-v2/test.py | kubectl exec -i -n models deploy/model-gateway -c gateway -- python3 -

# External via gateway VIP + Tyk auth
GW_URL=http://<GATEWAY_VIP> TYK_KEY=<key> python3 models/xtts-v2/test.py
```

## Key configuration

| Setting | Value |
|---------|-------|
| Backend | coqui-tts (custom FastAPI server, ConfigMap `xtts-v2-server`) |
| Endpoint | `POST /v1/audio/speech` (OpenAI-style; `{model,input,language,voice}`), `GET /health` |
| Output | `audio/wav` (24 kHz, RIFF/WAVE) |
| Languages | 17 (en, es, fr, de, it, pt, pl, tr, ru, nl, cs, ar, zh-cn, ja, hu, ko, hi) |
| Parameters | ~1.8B, fp32 |
| GPU | HAMi slice 8 GiB (`nvidia.com/gpumem: 8192`) |
| Scale | always-on (`minReplicas: 1`, max 2, 15m retention) |
| Weights | PVC `xtts-v2` (RWX, nfs-models, 25Gi; bare fleet naming) |
