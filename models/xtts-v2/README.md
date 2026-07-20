# XTTS-v2 (coqui/XTTS-v2)

Coqui **XTTS-v2** — multilingual text-to-speech with voice cloning from a ~6 s reference clip. 17 languages,
24 kHz WAV output. Custom FastAPI server (`server-configmap.yaml`, ConfigMap `xtts-v2-server`) wrapping
`coqui-tts`, on a HAMi GPU slice, always-on (minReplicas: 1). ~1.8B params, fp32.

## Endpoints

| Endpoint | Purpose |
|----------|---------|
| `POST /v1/audio/speech` | OpenAI-style TTS (`{model,input,language,voice,speed?}`) → `audio/wav`. `voice` may be a built-in preset name **or** a saved clone name. |
| `POST /v1/audio/clone` | Clone a voice from a reference WAV. Multipart (`file=@ref.wav` + `input`, `language?`, `save_as?`, `model?`) or JSON (`{input, language?, save_as?, model?, voice_sample: <base64 wav>}`). `save_as=<name>` persists the clip on the PVC. |
| `GET /v1/audio/voices` | `{voices:[built-in presets], saved:[cloned names], default}` |
| `GET /health` | Liveness. |

**Voice cloning** uses Coqui's `speaker_wav` argument. A cloned clip is persisted to
`/data/voices/<name>.wav` on the PVC when `save_as` is given, then recalled by name in
`/v1/audio/speech {voice:"<name>"}` without re-uploading.

## Deployment

```bash
kubectl apply -f pvc.yaml               # RWX venv + XTTS cache + saved voices (nfs-models)
kubectl apply -f server-configmap.yaml  # the FastAPI TTS server (ConfigMap xtts-v2-server)
kubectl apply -f inferenceservice.yaml  # ISVC (init builds venv on PVC) + mounts the server
kubectl apply -f details.yaml           # Template card (type: tts)
```

> When changing the server, apply the ConfigMap then restart the pod
> (`kubectl delete pod -l serving.knative.dev/service=xtts-v2-predictor`).

## Testing

```bash
# Inside the gateway pod (no auth)
cat models/xtts-v2/test.py | kubectl exec -i -n models deploy/model-gateway -c gateway -- python3 -

# External via gateway VIP + Tyk auth
GW_URL=http://<GATEWAY_VIP> TYK_KEY=<key> python3 models/xtts-v2/test.py
```

The test covers preset TTS + voice cloning (base64 and multipart), saved-voice recall, the voices
listing, guardrails, and the catalog entry.

## Key configuration

| Setting | Value |
|---------|-------|
| Backend | coqui-tts (custom FastAPI server, ConfigMap `xtts-v2-server`) |
| Endpoints | `POST /v1/audio/speech`, `POST /v1/audio/clone`, `GET /v1/audio/voices`, `GET /health` |
| Output | `audio/wav` (24 kHz, RIFF/WAVE) |
| Languages | 17 (en, es, fr, de, it, pt, pl, tr, ru, nl, cs, ar, zh-cn, ja, hu, ko, hi) |
| Parameters | ~1.8B, fp32 |
| GPU | HAMi slice 8 GiB (`nvidia.com/gpumem: 8192`) |
| Scale | always-on (`minReplicas: 1`, max 2, 15m retention) |
| Storage | PVC `xtts-v2` (RWX, nfs-models, 25Gi): venv + XTTS cache + `/data/voices/*.wav` |

## Notes

- **torchaudio backend:** torchaudio 2.11 defaults to the `torchcodec` backend (not installed here);
  the server monkeypatches `torchaudio.load` to use `soundfile` so Coqui can read reference clips.
  `soundfile`/`librosa` are already in the venv (TTS deps).
- **Synth output** is written to `/dev/shm` tmpfs (falls back to the default temp dir) to avoid an
  overlay/NFS round-trip on the write + re-read.

