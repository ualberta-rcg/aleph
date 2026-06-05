# Multilingual E5 Small

Multilingual embedding model for generating dense vector representations of text in 100+ languages.

## Model Information

| Property | Value |
|----------|-------|
| Source | [intfloat/multilingual-e5-small](https://huggingface.co/intfloat/multilingual-e5-small) |
| Type | Text Embedding |
| Parameters | 118M |
| Runtime | Text Embeddings Inference (TEI) |

## API Endpoint

- **Endpoint:** `/embed`
- **Method:** POST
- **Format:** TEI (Text Embeddings Inference)

### Example Usage

```bash
curl -X POST "http://multilingual-e5-small.models.svc.cluster.local/embed" \
  -H "Content-Type: application/json" \
  -d '{
    "inputs": "query: What is machine learning?"
  }'
```

**Batch request:**

```bash
curl -X POST "http://multilingual-e5-small.models.svc.cluster.local/embed" \
  -H "Content-Type: application/json" \
  -d '{
    "inputs": ["query: First text", "query: Second text"]
  }'
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
| Min Replicas | 1 |
| Scale-to-Zero | No |

## Notes

- CPU-only deployment using TEI runtime
- Prefix queries with `query:` and documents with `passage:` for optimal results
- Supports 100+ languages including English, Chinese, Spanish, French, German, etc.
