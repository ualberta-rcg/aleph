# longformer

## Status: DEFERRED

The 232 source is a stub-only directory (card + kustomization, no `inferenceservice.yaml` or `server.py`).

**Model**: allenai/longformer-base-4096 (~148M params, 4096-token sliding-window attention)
**Use case**: Long-document classification, NER, QA on documents up to 4096 tokens.
**License**: Apache-2.0

## To implement (future)

Build a standard embedding/classification server similar to scibert/biomedbert but with:
- `AutoTokenizer` + `LongformerModel` (4096 max tokens, sliding-window)
- `/v1/embeddings` endpoint (global attention on `[CLS]`, mean pool otherwise)
- Optional `/v1/science/classify` if fine-tuning for specific tasks
- CPU; PVC nfs-client; init container for venv + HF download

## Why deferred
No server.py existed on 232 to port. Building from scratch is straightforward but
outside the copy+modernise scope for this wave.
