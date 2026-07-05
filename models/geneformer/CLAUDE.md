# Geneformer — single-cell transcriptomics embeddings

Geneformer V2 (NIH NCI / ctheodoris, 104M) — context-aware foundation model pretrained on 30M
single-cell transcriptomes. Takes ranked gene tokens (gene names + expression) and produces a
**cell-level embedding** (mean-pooled hidden states).

## Source
- HuggingFace: https://huggingface.co/ctheodoris/Geneformer (V2-104M)
- License: BSD-2-Clause

## API — `POST /v1/science/embed` (NON-OpenAI domain endpoint, primary)
Gene-expression input → does NOT expose OpenAI `/v1/embeddings`. `/v1/embed` kept as secondary.
Body needs `"model": "geneformer"`:
- `{"model":"geneformer", "genes":["TP53","BRCA1",...], "expression":[1.2,0.5,...]}` → cell embedding
- Returns `{"embeddings":[[...]], "embedding_dim":N, "model":"geneformer"}`.

## Deployment
- **GPU** (HAMi 8 GiB slice; 104M transformer).
- **PVC**: `geneformer` — **ReadWriteMany**, nfs-models, 8 Gi (`pvc.yaml`; bare fleet naming, was
  `geneformer-data-rwx`/`model-data`). Migrated RWO→RWX 2026-06-19 via cp-from-RWO (venv + weights +
  tokenizer preserved). Split out of the ISVC (was inline + RWO).
- **Venv-on-PVC**: `/data/venv` (transformers + torch, guarded). Loads via `AutoModel(trust_remote_code)`.
- **Scale-to-zero**: minReplicas 0, 15m retention.

## Key files
- `inferenceservice.yaml` — ConfigMap (server.py) + ISVC (PVC split to `pvc.yaml`)
- `details.yaml` — v2 card (Template C)
- `pvc.yaml` — RWX PVC
- `test.py` — 6-case gateway battery (dim / non-zero / distinctness / deterministic / echo / malformed)

## Notes
- The server tokenizes gene names (via the gene token dictionary) + ranks by expression, then runs
  the transformer; embedding = mean-pool over token hidden states. Dim 768 (v2-104M; V1-10M was 256).
- Downloads the Geneformer-V2-104M subdirectory only.

## Update reminder
- Watch ctheodoris/Geneformer for larger variants (dim may change from 768).
