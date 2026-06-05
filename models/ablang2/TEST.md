# ablang2 — Test Report

Cluster 230, via gateway ClusterIP `http://10.43.79.101:80`. Model type: embedding (CPU).

## Scale-up

- Cold start from zero: venv reused from PVC; init pre-downloads `ablang2-paired`
  weights (~158MB from Zenodo) into the package dir, then server loads read-only.
- Pod reached `3/3 Running`, `/health` 200. Cold start ~5 min (Zenodo download dominates;
  warm restarts skip it).

## Endpoint tests (PASS)

### POST /v1/embeddings (single)
```bash
curl -s -X POST $GW/v1/embeddings -H "Content-Type: application/json" \
  -d '{"model":"ablang2","input":"EVQLLESGGEVKKPGASVKVSCRASGYTFRNYGLTWVRQAPGQGLEWMGWISAYNGNTNYAQKFQGRVTLTTDTSTSTAYMELRSLRSDDTAVYFCARDVPGHGAAFMDVWGTGTTVTVSS"}'
```
→ `dim=480`, first3=`[-0.2932, 0.2015, 0.0657]`. PASS.

### POST /v1/embeddings (batch of 2)
```bash
curl -s -X POST $GW/v1/embeddings -H "Content-Type: application/json" \
  -d '{"model":"ablang2","input":["EVQLLESGG","DIQLTQSPL"]}'
```
→ `count=2, dim=480`. PASS.

### Catalog discovery
- `GET /v1/models?all=true` → `ablang2` present, type=embedding, ctx=512, dim reflected. PASS.
- (Default `/v1/models` is chat-only by design; embedding models need `?all=true`.)

## Not applicable / not tested

- OpenAI chat / Anthropic `/v1/messages` / reasoning: N/A (embedding model).
- `POST /v1/restore` (CDR restoration) is exposed by the server and reachable via the
  gateway `/v1/{path}` catch-all, but not exercised in this pass.

## Card parity

`details.yaml` matches deployed config: type=embedding, context_window=512,
embedding_dimensions=480 (verified), gpu=false, scale-to-zero.
