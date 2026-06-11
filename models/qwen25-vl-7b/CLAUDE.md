# Qwen2.5-VL-7B Model Card

## Identity
- **Model**: Qwen/Qwen2.5-VL-7B-Instruct (7B dense + ViT, vision-language)
- **Type**: Chat (vision + text + tools, no thinking/reasoning mode)
- **Framework**: vLLM v0.20.2, tensor-parallel 1
- **Source**: https://huggingface.co/Qwen/Qwen2.5-VL-7B-Instruct

## Capabilities
- **Vision**: ✅ Dynamic resolution images, video, up to 20 images per prompt, object grounding
- **Tool Calling**: ✅ Hermes parser (forced via ISVC — model has no native tool_call_parser)
- **Thinking/Reasoning**: ❌ No — not a reasoning model
- **Context**: 32K native, 128K with YaRN (not recommended for VL tasks). Deployed at 65K.
- **Architecture**: Qwen2.5-based, 7B dense (28 layers, GQA 28Q/4KV) + ViT (32 layers)
- **Video**: Up to 1+ hour, temporal grounding, dynamic FPS

## vLLM Args
```
vllm serve /data
--served-model-name=qwen25-vl-7b
--port=8080
--tensor-parallel-size=1
--max-model-len=65536
--dtype=bfloat16
--gpu-memory-utilization=0.90
--trust-remote-code
--limit-mm-per-prompt={"image":20,"video":1}
--enable-auto-tool-choice
--tool-call-parser=hermes
```

Env: `HF_HUB_CACHE=/tmp/hf-cache`, `VLLM_WORKER_MULTIPROC_METHOD=spawn`

## Recommended Sampling
- Deterministic (vision analysis): near-greedy, `repetition_penalty=1.05`
- General chat: `temperature=0.2`, `top_p=0.9`

## Resources
- **GPU**: 1× GPU (HAMi vGPU slice, 32 GB gpumem)
- **CPU**: 4 req / 8 limit
- **Memory**: 24Gi req / 32Gi limit
- **SHM**: 8Gi (emptyDir Memory)
- **Cold start**: ~2 minutes (15 GB BF16 + ViT over NFS + vLLM init)
- **Fits on any GPU node** — single GPU, can coexist with other workloads

## Special Notes
- **Vision model** — images, video, OCR, chart/document parsing, visual localization
- **Tool calling forced** via hermes parser — model has no native tool_call_parser, may be conservative on tool_choice='auto'
- **Non-reasoning** — no thinking/reasoning mode
- **max-model-len=65536** — 65K context (exceeds 32K native, uses model's MRoPE position encoding)
- **limit-mm-per-prompt** allows 20 images + 1 video per request
- **gpumem=32768** — 32 GB HAMi VRAM slice (model ~15 GB + ViT + KV cache)
- **init container** downloads weights from HF on first deploy
- **Apache-2.0** license

## Test Results (2026-06-11)
**22/22 passed, 2 expected failures, 0 failed**

All OpenAI and Anthropic endpoints working:
- ✅ Basic chat, streaming, temp/top_p, stop sequences, system prompt
- ✅ Vision (OAI image_url) — correctly describes images and colors
- ✅ Vision (ANT image block) — correctly describes image content
- ✅ Tool calling: hermes parser active (model answered directly — conservative on auto)
- ✅ max_tokens=16k accepted
- ✅ No reasoning content (correct)
- ✅ Resources block with vram_mib
- ✅ Catalog: vision=True, tools=True, reasoning=False, ctx=65536, max_out=16384
- Cold start: ~120s

## Files
- `details.yaml` — ConfigMap (v2 card, supports_vision=true, supports_tools=true)
- `inferenceservice.yaml` — KServe ISVC (vLLM v0.20.2, TP1, gpumem 32GB, init container)
- `test.py` — 24-check gateway test with vision + tools
