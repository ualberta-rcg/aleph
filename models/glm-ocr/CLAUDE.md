# GLM-OCR (`glm-ocr`) — Deployment & Operational Notes

## Architecture & Engine
- **HuggingFace Repo**: `zai-org/GLM-OCR` (0.9B parameters: CogViT vision encoder + GLM-0.5B language decoder, `GlmOcrForConditionalGeneration`).
- **vLLM Image**: `vllm/vllm-openai:v0.32.0` (standard 2026 cluster vLLM image).
- **HAMi Slice**: 1× L40S slice with `nvidia.com/gpu: "1"` and `nvidia.com/gpumem: "12288"` (12 GiB). The bf16 checkpoint is ~2.3 GB, leaving ~8 GB for vision encoder activations and KV cache at `--gpu-memory-utilization=0.85` and `--max-model-len=16384`.
- **Scale-to-zero**: `minReplicas: 0`, `maxReplicas: 2`, `scaleTarget: 8`, 15m idle retention.

## Task Mode (`mode: "task"`)
- `glm-ocr` is a task-only model (`mode: "task"` in `details.yaml`):
  - Excluded from default `GET /v1/models` so OpenWebUI chat dropdowns are never polluted with a non-conversational OCR model.
  - Included in `GET /v1/models?all=true`, `GET /v1/models?tasks=true`, `GET /v1/models/glm-ocr`, `GET /v1/tasks/models`, and `GET /v1/tasks/models/glm-ocr`.
  - Displayed on `GET /` with `.card.task-card` styling and the `async task` badge.
  - Synchronous calls to `POST /v1/chat/completions` with `model="glm-ocr"` return `400 task_only_model` directing the caller to `POST /v1/tasks`.

## Multimodal Message Ordering
- Per `zai-org/GLM-OCR` upstream specification, the `image_url` content block is placed **before** the `text` prompt block in `messages[0]["content"]`:
  - `"Text Recognition:"` (default)
  - `"Table Recognition:"`
  - `"Formula Recognition:"`
  - Or a custom JSON schema prompt.
- All card defaults (`temperature: 0.0`, `max_tokens: 4096`) and any caller-supplied vLLM parameters (`repetition_penalty`, `top_p`, `seed`, `guided_json`, etc.) pass through `prepare_chat_payload` directly to vLLM.

## Verification
```bash
GW_URL=https://inference.vulcan.alliancecan.ca TYK_KEY=$KEY python3 models/glm-ocr/test.py
```
