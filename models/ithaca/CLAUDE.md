# Ithaca — Model Context

## What This Model Does

Ithaca by DeepMind x UCL x Venice. JAX/Flax model published in Nature 2022. Restores damaged ancient Greek inscriptions, attributes chronological dating (BCE), and predicts geographic origin. Takes ancient Greek text with gaps marked [---], returns restored text, date range, and location attribution. GPU required for full inference.

## Source Repo

**GitHub**: [google-deepmind/predictingthepast](https://github.com/google-deepmind/predictingthepast)
**Paper**: [Restoring and attributing ancient texts using deep neural networks](https://www.nature.com/articles/s41586-022-04448-z) (Nature 2022)

Key info from source:
- **Input format**: Ancient Greek text with gaps marked [---]
- **Text length**: 50-750 characters
- **License**: Apache-2.0
- **Framework**: JAX/Flax (not PyTorch)
- **Weights**: Downloaded from Google Cloud Storage (public bucket)

## How The Server Works

- **Pattern**: Custom FastAPI prediction server with JAX/haiku
- **Container**: `python:3.11` (full image, not slim) — installs JAX deps at startup
- **Init container**: Downloads weights + data from GCS, clones predictingthepast repo
- **PVC**: `ithaca-data` — stores weights + source code + retrieval data
- **Health**: Custom `/health` endpoint + startupProbe
- **GPU**: 1x full L40S (46GB, not shared) — JAX uses GPU for inference
- **Memory**: 8Gi request / 16Gi limit
- **Output**: Custom `/v1/science/predict` with restoration + date + location
- **Fallback**: Falls back to demo mode if model loading fails
- **Sentinel**: Uses `/data/.ithaca-ready-v3` to skip re-downloads

## Gateway Integration

- **k8s ISVC name**: `ithaca`
- **API model ID**: `ithaca` (no mapping in ISVC_NAME_MAP)
- **MODEL_TYPE**: defaults to "chat" — needs update to "predict"
- **KSERVE_CUSTOM_MODELS**: not listed — needs addition
- **Scale-to-zero**: minReplicas=0, scaleTarget=5, 900s retention

## Deploy / Update / Test

```bash
# Deploy
kubectl apply -k models/ithaca/

# Check status
kubectl get pods -n models -l serving.kserve.io/inferenceservice=ithaca

# Logs
kubectl logs -n models -l serving.kserve.io/inferenceservice=ithaca -c kserve-container -f

# Test (public) — demo mode
curl -X POST https://inference.kubeflow.vulcan.alliancecan.ca/serving/api/v1/science/predict \
  -H "Content-Type: application/json" \
  -d '{"model":"ithaca","demo":true}'

# Test — real inference
curl -X POST https://inference.kubeflow.vulcan.alliancecan.ca/serving/api/v1/science/predict \
  -H "Content-Type: application/json" \
  -d '{"model":"ithaca","text":"ΕΜΟΙΔΕΤΙΣ[---]ΑΓΑΘΟΣΣΤΡΑΤΗΓΟΣ"}'
```

## Known Issues / Optimization Opportunities

1. **Full python:3.11 image**: Uses full Python image (not slim). Larger attack surface.

2. **No venv-on-PVC pattern**: Installs JAX and deps in container every restart (~5 min cold start). Should use venv-on-PVC.

3. **Git clone in init**: Clones predictingthepast repo from GitHub during init. Fragile.

4. **Demo fallback hides errors**: If model loading fails, silently falls back to demo mode. Hard to debug.

5. **pickle deserialization**: Loads weights via `pickle.load()` — potential security risk with untrusted checkpoints.

6. **High resource usage**: 16Gi memory limit, 1 full GPU. JAX has high overhead.

7. **No PVC storageClassName**: PVC not defined in manifest (referenced as external).

8. **Gateway registration incomplete**: Model not in MODEL_TYPES, MODEL_METADATA, KSERVE_CUSTOM_MODELS in gateway.py.

## Files

| File | Purpose |
|------|---------|
| `details.yaml` | ConfigMap with model metadata |
| `inferenceservice.yaml` | ConfigMap + ISVC spec (PVC external) |

**IMPORTANT: When changing this model's deployment config (inferenceservice.yaml), update details.yaml to match.**
