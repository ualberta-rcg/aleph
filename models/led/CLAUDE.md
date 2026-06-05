# led (Longformer Encoder-Decoder)

## Status: DEFERRED

The 232 source is a stub-only directory (card + kustomization, no `inferenceservice.yaml` or `server.py`).

**Model**: allenai/led-base-16384 (~162M params, 16K-token encoder-decoder)
**Use case**: Long-document summarization, QA over very long contexts (up to 16K tokens).
**License**: Apache-2.0

## To implement (future)

Build a summarization server:
- `AutoTokenizer` + `LEDForConditionalGeneration` (16384 max input tokens)
- `/v1/science/summarize` endpoint: `{"text": "...", "max_new_tokens": 256}`
- CPU (large input context, but small model); PVC nfs-client; init container

## Why deferred
No server.py existed on 232 to port. Building from scratch is straightforward but
outside the copy+modernise scope for this wave.
