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
curl -X POST "http://<GATEWAY_VIP>/v1/vision/embed" \
  -H "Authorization: Bearer <TYK_KEY>" \
  -H "Content-Type: application/json" \
  -d '{"model":"zoobot-15m","image":"<base64_png>"}'
```

Run the full test battery externally:

```bash
GW_URL=http://<GATEWAY_VIP> TYK_KEY=<key> python3 models/zoobot/test.py
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

