# bge-reranker-v2-m3 — Test Report

Cluster 230, gateway ClusterIP `http://10.43.79.101:80`. Type: reranker (CPU). id `bge-reranker-v2-m3`.

## Verified this pass (2026-06-05)

### POST /v1/rerank (Cohere-style) — PASS
```bash
curl -s -X POST $GW/v1/rerank -H 'Content-Type: application/json' \
  -d '{"model":"bge-reranker-v2-m3","query":"What is a panda?","documents":["The giant panda is a bear native to China.","Paris is the capital of France.","Pandas eat bamboo."]}'
```
→ `results` sorted by `relevance_score`: index 0 (panda/bear) 0.328 > index 2 (bamboo) 3e-4 >
index 1 (Paris) 1.6e-5. Semantically correct ranking. PASS.

### Catalog
- `GET /v1/models?all=true` → present (type=reranker). PASS.

## Not applicable
- OpenAI chat / Anthropic / embeddings: N/A (reranker; documents->scores).

## Card parity
id=bge-reranker-v2-m3, type=reranker, gpu=false, scale-to-zero. `/v1/rerank` verified
(server translates Cohere `documents`->`texts`).
