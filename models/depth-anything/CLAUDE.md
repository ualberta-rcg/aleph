# Depth Anything V2 Small — Model Context

## What This Model Does

Depth Anything V2 Small by TikTok/ByteDance. 24.8M params. Monocular depth estimation from a single RGB image. Produces normalized depth maps where darker values indicate closer objects. ONNX model from HuggingFace ONNX community. Trained on combined labeled (KITTI, NYUv2) and unlabeled datasets for robust zero-shot depth prediction. Returns raw normalized depth array plus original image dimensions.

## Source Repo

**HuggingFace**: [onnx-community/depth-anything-v2-small](https://huggingface.co/onnx-community/depth-anything-v2-small)
**Paper**: [Depth Anything V2](https://arxiv.org/abs/2406.09414)

Key info from source:
- **Input size**: 518x518 pixels
- **License**: Apache-2.0
- **Model variant**: Small (also available: Base, Large)
- **Output**: Single-channel depth map normalized to [0, 1]

## How The Server Works

- **Pattern**: Custom FastAPI with ONNX inference
- **Container**: `python:3.11-slim` running `/data/venv/bin/python /app/server.py`
- **Init container**: Creates venv, installs deps, downloads ONNX model from HuggingFace
- **ConfigMap**: `depth-anything-server` — server code embedded in inferenceservice.yaml
- **PVC**: `depth-anything-data` — stores venv + ONNX model (5Gi, NFS ReadWriteMany)
- **Health**: Custom `/health` endpoint
- **CPU only**: No GPU allocation. Uses `CPUExecutionProvider` in ONNX Runtime.
- **Env vars**: `MODEL_NAME=depth-anything-v2`, `MODEL_FILE=/data/model/model.onnx`
- **Preprocessing**: ImageNet mean/std normalization, resize to 518x518, CHW format
- **Output**: Depth map normalized to [0, 1] with min-max scaling

## Gateway Integration

- **k8s ISVC name**: `depth-anything`
- **API model ID**: `depth-anything-v2` (mapped via ISVC_NAME_MAP)
- **MODEL_TYPE**: depth
- **KSERVE_CUSTOM_MODELS**: yes — uses `/v1/` prefix
- **Scale-to-zero**: minReplicas=0, scaleTarget=2, 900s retention

## Deploy / Update / Test

```bash
kubectl apply -f models/depth-anything/pvc.yaml
kubectl apply -f models/depth-anything/inferenceservice.yaml
kubectl apply -f models/depth-anything/details.yaml

# Status / logs
kubectl get pods -n models -l serving.kserve.io/inferenceservice=depth-anything
kubectl logs -n models -l serving.kserve.io/inferenceservice=depth-anything -c kserve-container -f

# Test (external via gateway VIP + Tyk auth)
GW_URL=http://<GATEWAY_VIP> TYK_KEY=<key> python3 models/depth-anything/test.py
# Or inside the gateway pod (no auth):
cat models/depth-anything/test.py | kubectl exec -i -n models deploy/model-gateway -c gateway -- python3 -
```

## Known Issues / Optimization Opportunities

1. **CPU only**: Model runs on CPU with ONNX Runtime. Could use GPU for faster inference.

2. **Hardcoded INPUT_SIZE**: Server code has `INPUT_SIZE = 518` hardcoded rather than reading from env var.

3. **Large output**: Returns the full depth map as a JSON array of arrays, which can be very large for high-resolution inputs. Could return a base64-encoded grayscale PNG instead.

4. **Pip dependencies unpinned**: Init container installs deps without version pins.

5. **Model download path**: Downloads from `onnx-community/depth-anything-v2-small` and moves from `onnx/model.onnx` to `/data/model/model.onnx`.

6. **No depth unit**: Returns normalized [0,1] depth. Could add metric depth estimation with calibration.

## Files

| File | Purpose |
|------|---------|
| `details.yaml` | Model card (schema v2, type: depth) |
| `inferenceservice.yaml` | ConfigMap (server.py) + ISVC spec |
| `pvc.yaml` | PVC `depth-anything-data` (RWX, nfs-models) |
| `test.py` | Gateway test battery (~15 checks; 2026-06-24 deep pass, 0 FAIL) |
| `README.md` | Model overview |

**IMPORTANT: When changing this model's deployment config (inferenceservice.yaml), update details.yaml to match.**

## HF / upstream I/O reference
- Source: https://huggingface.co/onnx-community/depth-anything-v2-small
- Runtime mapping used here: base64 image -> `depth_png_base64` + `depth_grid_64` + `stats` on `/v1/vision/depth`.
