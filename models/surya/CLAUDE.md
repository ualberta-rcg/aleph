# Surya 1.0 — Model Context

## What This Model Does

Surya 1.0 by NASA-IBM AI4Science. 366M params. Spatiotemporal transformer pretrained on 9 years of NASA SDO data (AIA 8 channels + HMI 5 channels) at 4096x4096 resolution. Fine-tuned for solar flare forecasting, active region segmentation, and solar wind prediction. Full 4096x4096 input uses ~6GB VRAM; 256x256 patches for testing. Apache 2.0 license.

## Source Repo

**HuggingFace**: [nasa-ibm-ai4science/Surya-1.0](https://huggingface.co/nasa-ibm-ai4science/Surya-1.0)
**GitHub**: [NASA-IMPACT/Surya](https://github.com/NASA-IMPACT/Surya)

Key info from source:
- **Input format**: 13-channel SDO image arrays (8 AIA + 5 HMI), normalized
- **Native resolution**: 4096x4096
- **License**: Apache-2.0
- **Architecture**: Spatiotemporal transformer with spectral gating (366M params)
- **GPU required**: ~6GB VRAM for full resolution

## How The Server Works

- **Pattern**: Custom FastAPI forecast server with PyTorch
- **Container**: `python:3.11` (full image, not slim) — installs torch+Surya at startup
- **Init container**: Downloads weights + config from GCS/HF, clones Surya repo
- **PVC**: `surya-data` — stores weights + source code
- **Health**: Custom `/health` endpoint + startupProbe
- **GPU**: 1x full L40S (46GB VRAM, not shared)
- **Output**: Custom `/v1/science/forecast` with next-step prediction + flare risk
- **Fallback**: Falls back to demo mode if Surya library import fails
- **Sentinel**: Uses `/data/.surya-ready-v1` to skip re-downloads

## Gateway Integration

- **k8s ISVC name**: `surya`
- **API model ID**: `surya-366m` (no mapping in ISVC_NAME_MAP)
- **MODEL_TYPE**: defaults to "chat" — needs update to "forecast"
- **KSERVE_CUSTOM_MODELS**: not listed — needs addition
- **Scale-to-zero**: minReplicas=0, scaleTarget=5, 900s retention

## Deploy / Update / Test

```bash
# Deploy
kubectl apply -k models/surya/

# Check status
kubectl get pods -n models -l serving.kserve.io/inferenceservice=surya

# Logs
kubectl logs -n models -l serving.kserve.io/inferenceservice=surya -c kserve-container -f

# Test (public) — demo mode
curl -X POST https://inference.kubeflow.vulcan.alliancecan.ca/serving/api/v1/science/forecast \
  -H "Content-Type: application/json" \
  -d '{"model":"surya-366m","demo":true}'
```

## Known Issues / Optimization Opportunities

1. **Full python:3.11 image**: Uses full Python image (not slim). Larger attack surface and slower startup.

2. **No venv-on-PVC pattern**: Installs deps in container every restart. Should use venv-on-PVC.

3. **Git clone in init**: Clones Surya repo from GitHub during init. Fragile — repo could move or change.

4. **Fallback to raw weights**: If Surya library import fails, loads raw weights dict as model. Only demo mode works in this case.

5. **High resource requests**: 16Gi RAM / 32Gi limit / 8 CPU. Required for 4096x4096 input.

6. **No PVC storageClassName**: PVC not defined in manifest (referenced as external).

7. **Gateway registration incomplete**: Model not in MODEL_TYPES, MODEL_METADATA, KSERVE_CUSTOM_MODELS in gateway.py.

## Files

| File | Purpose |
|------|---------|
| `details.yaml` | ConfigMap with model metadata |
| `inferenceservice.yaml` | ConfigMap + ISVC spec (PVC external) |

**IMPORTANT: When changing this model's deployment config (inferenceservice.yaml), update details.yaml to match.**
