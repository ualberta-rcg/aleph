# dino-vit-b8 — Test Report

Cluster 230, gateway `http://10.43.79.101:80`. Type: vision embedding (CPU). id `dino-vit-b8`.

## Scale-up
- Cold start: venv + model download. `3/3 Running`. ~3-4 min cold.

## Endpoint tests (PASS)

### POST /v1/vision/embed
```bash
IMG="iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg=="
curl -s -X POST $GW/v1/vision/embed -H 'Content-Type: application/json' \
  -d "{\"model\":\"dino-vit-b8\",\"image\":\"$IMG\"}"
```
→ float array embedding. PASS.

### Catalog
- `GET /v1/models?all=true` → `dino-vit-b8` discovered, type=embed. PASS.

## Card parity
id=dino-vit-b8, k8s_name=dino-vit-b8, type=embed, gpu=false, endpoint /v1/vision/embed.
