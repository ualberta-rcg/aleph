# Speaches -- Model Context

> **2026-07-05 — ISVC conversion (in progress, deferred).** Converted from the legacy standalone
> Deployment to a KServe **InferenceService** `speaches` (custom predictor, speaches image on :8000,
> HAMi 16 GiB slice, always-on). PVC renamed to bare `speaches` (RWX). HF-cache prefetch + chmod init
> preserved. Two v2 cards authored (`kokoro-82m` TTS, `whisper-large-v3` STT), both
> `routing.k8s_name: speaches`. **Two blockers, not yet PASSing:**
> 1. **STT multipart can't route** — the gateway catch-all (`forward_custom`) parses JSON + requires a
>    `model` field; `/v1/audio/transcriptions` is multipart → `400`. Needs a multipart-aware catch-all.
> 2. **TTS model id** — speaches 404s `kokoro-82m`/`kokoro` ("not installed locally"); needs the right
>    speaches model id (likely `upstream_model_id` rewrite + model-load config).
> State: ISVC + PVC live/Ready; the broken `kokoro-82m` card was removed from the cluster (kept in
> repo) so the catalog stays clean. Next: gateway multipart fix + speaches model-id follow-up.
> The Deployment/EXTRA_MODELS notes below are the **old** design (pre-conversion), kept for history.

## What This Model Does

Speaches is an OpenAI-compatible STT/TTS server providing two models behind a single Kubernetes Deployment:

1. **whisper-large-v3** (Systran/faster-whisper-large-v3): Speech-to-text in 99 languages via CTranslate2-based faster-whisper. GPU-accelerated with float16 compute.

2. **kokoro-82m** (speaches-ai/Kokoro-82M-v1.0-ONNX-fp16): Text-to-speech with multiple voice presets (af, af_bella, af_sky, am_adam, am_michael, bf_emma, bm_george). ONNX Runtime inference.

Both models share one time-sliced L40S GPU. The deployment is a standalone K8s Deployment + Service (NOT KServe). Registered in gateway as two separate models via `EXTRA_MODELS`.

## Source Repos

- **Speaches server**: [speaches-ai/speaches](https://github.com/speaches-ai/speaches)
- **Whisper model**: [Systran/faster-whisper-large-v3](https://huggingface.co/Systran/faster-whisper-large-v3) (faster-whisper/CTranslate2)
- **Kokoro model**: [speaches-ai/Kokoro-82M-v1.0-ONNX-fp16](https://huggingface.co/speaches-ai/Kokoro-82M-v1.0-ONNX-fp16)
- **License**: MIT

## How The Server Works

- **Pattern**: Standalone Deployment + Service (NOT KServe)
- **K8s resources**: `Deployment` + `Service` (not InferenceService)
- **Image**: `ghcr.io/speaches-ai/speaches@sha256:6ec12ebf...` (pinned by digest)
- **Init container**: `python:3.11-slim` prefetches HF model caches for both whisper and kokoro (idempotent via marker file `.speaches-hf-prefetch-ok`)
- **PVC**: `speaches-data` (30Gi, NFS) -- stores HF cache for both models
- **Health**: `/health` on port 8000
- **GPU**: 1x L40S-SHARED (time-sliced), fp16 inference for whisper
- **Startup**: ~2 minutes (model loading)
- **Environment config**:
  - `WHISPER__INFERENCE_DEVICE=cuda`
  - `WHISPER__COMPUTE_TYPE=float16`
  - `STT_MODEL_TTL=-1` (keep models loaded forever)
  - `TTS_MODEL_TTL=-1` (keep models loaded forever)
  - `SPEACHES__ENABLE_UI=false`

## Gateway Integration

- **NOT an InferenceService**: Standalone deployment
- **Registered in EXTRA_MODELS** as two separate models:
  - `whisper-large-v3`: `{"backend": "http://speaches.models.svc.cluster.local:8000", "health_path": "/health", "owned_by": "openai"}`
  - `kokoro-82m`: `{"backend": "http://speaches.models.svc.cluster.local:8000", "health_path": "/health", "owned_by": "hexgrad"}`
- **MODEL_TYPE**: whisper-large-v3=audio, kokoro-82m=tts
- **GPU_MODELS**: both listed
- **Always-on**: 1 replica, no autoscaling

## Deploy / Update / Test

```bash
# Deploy
kubectl apply -k models/speaches/

# Force update
kubectl apply --server-side --force-conflicts -k models/speaches/

# Check status
kubectl get pods -n models -l app=speaches

# Logs
kubectl logs -n models -l app=speaches -c speaches -f

# Test STT (public)
curl -X POST https://inference.kubeflow.vulcan.alliancecan.ca/serving/api/v1/audio/transcriptions \
  -F "model=whisper-large-v3" \
  -F "file=@recording.wav"

# Test TTS (public)
curl -X POST https://inference.kubeflow.vulcan.alliancecan.ca/serving/api/v1/audio/speech \
  -H "Content-Type: application/json" \
  -d '{"model":"kokoro-82m","input":"Hello, this is a test.","voice":"af_bella"}' \
  --output test.wav
```

## Known Issues / Optimization Opportunities

1. **Pinned by digest**: Image is pinned by SHA256 digest for reproducibility. This is good for stability but means updates require manual digest change.

2. **Two models, one deployment**: Cannot scale STT and TTS independently. Both share the same GPU and pod.

3. **Always-on**: Single replica, no autoscaling. Could be combined with scale-to-zero via Knative if needed, but the standalone Deployment pattern doesn't support it natively.

4. **30Gi PVC**: Large PVC needed for both HF caches. The prefetch marker prevents re-downloading.

5. **No readOnly mount**: PVC is mounted read-write (needed for HF cache at runtime). Could pre-cache everything in init container and use readOnly.

6. **Model TTL=-1**: Models are kept in memory forever, consuming GPU VRAM even when idle.

7. **Init container idempotent**: Yes -- uses marker file `/data/.speaches-hf-prefetch-ok` to skip prefetch.

## Files

| File | Purpose |
|------|---------|
| `details.yaml` | ConfigMap with model metadata (covers both whisper-large-v3 and kokoro-82m) |
| `deployment.yaml` | K8s Deployment spec (speaches pod with init container) |
| `service.yaml` | K8s ClusterIP Service (port 8000) |
| `kustomization.yaml` | Kustomize resources |
| `pvc.yaml` | Dedicated PVC (speaches-data, 30Gi NFS) |
| `README.md` | Original documentation |

**IMPORTANT: When changing this model's deployment config (deployment.yaml, service.yaml), update details.yaml to match.**
