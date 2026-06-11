# Qwen2.5-VL-3B Model Card

## Identity
- **Model**: Qwen/Qwen2.5-VL-3B-Instruct (3B dense + ViT, vision-language)
- **Type**: Chat (vision + text, no tools, no thinking)
- **Framework**: vLLM v0.20.2, tensor-parallel 1
- **Source**: https://huggingface.co/Qwen/Qwen2.5-VL-3B-Instruct

## Capabilities
- **Vision**: ✅ Dynamic resolution images, video, OCR, chart/document parsing, object grounding
- **Tool Calling**: ❌ No tool/function calling
- **Thinking/Reasoning**: ❌ No — not a reasoning model
- **Context**: 32K native, deployed at 4096 (conservative for small model on shared GPU)
- **Architecture**: Qwen2.5-based, 3B dense (36 layers, GQA 16Q/2KV) + ViT (32 layers)
- **Video**: Up to 1+ hour, temporal grounding, dynamic FPS

## vLLM Args
```
--model=/data
--served-model-name=qwen25-vl-3b
--port=8080
--max-model-len=4096
--dtype=bfloat16
--gpu-memory-utilization=0.90
--trust-remote-code
--limit-mm-per-prompt={"image": 4}
```

Env: `HF_HUB_CACHE=/tmp/hf-cache`

## Recommended Sampling
- Deterministic: near-greedy, `repetition_penalty=1.05`
- General chat: `temperature=0.2`, `top_p=0.9`

## Resources
- **GPU**: 1× GPU (HAMi vGPU slice, 24 GB gpumem)
- **CPU**: 2 req / 4 limit
- **Memory**: 12Gi req / 16Gi limit
- **SHM**: 4Gi (emptyDir Memory)
- **Cold start**: ~2 minutes (6 GB BF16 + ViT over NFS + vLLM init)
- **Fits on any GPU node** — single GPU, can coexist with other workloads

## Special Notes
- **Vision model** — images, video, OCR, chart/document parsing, visual localization
- **No tool calling** — visual grounding only, not structured function calling
- **Non-reasoning** — no thinking/reasoning mode
- **max-model-len=4096** — conservative 4K context (32K native but 4K conserves VRAM for vision)
- **limit-mm-per-prompt** allows 4 images per request
- **gpumem=24576** — 24 GB HAMi VRAM slice (model ~6 GB + ViT + KV cache)
- **init container** downloads weights from HF on first deploy
- **Apache-2.0** license

## Test Results (2026-06-11)
**18/18 passed, 2 expected failures, 0 failed**

All OpenAI and Anthropic endpoints working:
- ✅ Basic chat, streaming, temp/top_p, stop sequences, system prompt
- ✅ Vision (OAI image_url) — correctly describes images and colors
- ✅ Vision (ANT image block) — correctly identifies logo
- ✅ No reasoning content (correct)
- ✅ Resources block with vram_mib
- ✅ Catalog: vision=True, tools=False, reasoning=False, ctx=4096, max_out=2048
- Cold start: ~120s

## Files
- `details.yaml` — ConfigMap (v2 card, supports_vision=true, supports_tools=false)
- `inferenceservice.yaml` — KServe ISVC (vLLM v0.20.2, TP1, gpumem 24GB, init container)
- `test.py` — 20-check gateway test with vision
