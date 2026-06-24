# Zoobot (`zoobot`/`zoobot-15m`)

Galaxy morphology embedding model using ConvNeXt Nano from the Zoobot project.

## Model Information

| Property | Value |
|----------|-------|
| Source | [mwalmsley/zoobot-encoder-convnext_nano](https://huggingface.co/mwalmsley/zoobot-encoder-convnext_nano) |
| Type | Vision Embedding |
| Parameters | ~15M |
| Runtime | Custom FastAPI + timm |

## API Endpoint

- Gateway (`/serving/api`): `POST /v1/vision/embed`
- Direct service route: `/v1/vision/embed`
- Method: `POST`

## Example Usage

```bash
curl -X POST "https://inference.kubeflow.vulcan.alliancecan.ca/serving/api/v1/vision/embed" \
  -H "Content-Type: application/json" \
  -d '{"model":"zoobot-15m","image":"<base64_png>"}'
```

```bash
curl -X POST "https://kubeflow.vulcan.alliancecan.ca/serving/models/zoobot/v1/vision/embed" \
  -H "Content-Type: application/json" \
  -d '{"image":"<base64_png>"}'
```

## Resource Requirements

| Resource | Request | Limit |
|----------|---------|-------|
| CPU | 2 | 4 |
| Memory | 2Gi | 4Gi |
| GPU | None | None |
| Storage | 5Gi | - |

## Scaling Configuration

| Setting | Value |
|---------|-------|
| minReplicas | 1 |
| scale-to-zero | No |
| timeout | 600s |

## Files

| File | Purpose |
|------|---------|
| `pvc.yaml` | `zoobot-data` dedicated PVC |
| `configmap.yaml` | Vision server config (`server.py`) |
| `inferenceservice.yaml` | KServe predictor spec |
| `server.py` | Local copy of server logic used to build config |

## HF / upstream I/O reference

- Source: <https://huggingface.co/mwalmsley/zoobot-encoder-convnext_nano>
- Task family: galaxy morphology image embedding (ConvNeXt encoder).
- Input: base64 RGB image.
- Output: single 640-dim embedding vector (`embedding` + `dim`).

