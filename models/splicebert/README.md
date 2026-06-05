# SpliceBERT (`splicebert`/`splicebert-86m`)

RNA/DNA splice-site embedding model for sequence analysis.

## Model Information

| Property | Value |
|----------|-------|
| Source | [zhihan1996/DNA_bert_6](https://huggingface.co/zhihan1996/DNA_bert_6) |
| Type | Scientific embedding |
| Parameters | 86M |
| Runtime | FastAPI + Transformers + ONNX/PyTorch fallback |

## API Endpoint

- Gateway (`/serving/api`): `POST /v1/embeddings`
- Direct service route: `/v1/embeddings`
- Method: `POST`

## Example Usage

```bash
curl -X POST "https://inference.kubeflow.vulcan.alliancecan.ca/serving/api/v1/embeddings" \
  -H "Content-Type: application/json" \
  -d '{
    "model": "splicebert-86m",
    "input": ["A sample splice-site sequence"]
  }'
```

```bash
curl -X POST "https://kubeflow.vulcan.alliancecan.ca/serving/models/splicebert/v1/embeddings" \
  -H "Content-Type: application/json" \
  -d '{"input": ["Direct route embedding test"]}'
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
| `pvc.yaml` | `splicebert-data` dedicated PVC |
| `configmap.yaml` | Custom server code (`embed_server.py`) |
| `inferenceservice.yaml` | KServe predictor spec |
| `kustomization.yaml` | Kustomize bundle |
| `embed_server.py` | Local copy of server logic used to build config |

