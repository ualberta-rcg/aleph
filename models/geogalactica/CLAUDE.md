# GeoGalactica — Geoscience Large Language Model

## Source
- HuggingFace: https://huggingface.co/geobrain-ai/geogalactica
- License: Apache 2.0

## Deployment Summary
- **Model**: GeoGalactica 30B (OPT-style, 48 layers, 56 heads)
- **GPU**: 2x L40S (full, tensor parallel)
- **PVC**: geogalactica-data (~60GB weights)
- **Scale-to-zero**: Yes (minReplicas: 0)
- **Image**: vllm/vllm-openai:v0.8.4
- **Max model length**: 2048 tokens
- **VRAM guard**: Yes (needs 25GB free per GPU)

## API
- `POST /v1/chat/completions` — OpenAI-compatible chat (via vLLM)
- Input: messages, max_tokens, stream
- Output: standard OpenAI chat completion format

## Key Files
- `inferenceservice.yaml` — ISVC with vLLM container + HF download init
- `pvc.yaml` — geogalactica-data PVC
- `details.yaml` — model metadata ConfigMap
- `kustomization.yaml` — kustomize resources

## Dependencies
- vLLM v0.8.4 (handles inference)
- HuggingFace snapshot_download for weight fetch

## Gateway Integration
- ISVC name: `geogalactica`
- MODEL_TYPE: chat
- KSERVE_CUSTOM_MODELS: yes
- GPU_MODELS: not listed (should be added)
- CONTEXT_WINDOWS: not listed (should add 2048)
- MODEL_MAX_TOKENS: not listed (should add 2048)

## Audit Notes
- Uses VRAM guard to wait for sufficient GPU memory before starting
- Trust-remote-code enabled for OPT-style model
- Very large model (~60GB weights) — long cold start
- Only 2048 context window (architectural limit)
- vLLM provides proper OpenAI API compatibility with streaming

## Update Reminder
- Check for GeoGalactica v2 with longer context
- Consider FP8 quantization to reduce to 1 GPU
- Monitor vLLM compatibility with OPT architecture
