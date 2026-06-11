# Qwen2.5-VL-72B Model Card

## Identity
- **Model**: Qwen/Qwen2.5-VL-72B-Instruct (72.2B dense, vision-language)
- **Type**: Chat (vision + text, no thinking/reasoning mode)
- **Framework**: vLLM v0.20.2, tensor-parallel 4
- **Source**: https://huggingface.co/Qwen/Qwen2.5-VL-72B-Instruct

## Capabilities
- **Vision**: ✅ Dynamic resolution images, video up to 1+ hour, up to 5 images per prompt
- **Tool Calling**: ❌ No structured tool/function calling (visual grounding for GUI agents only)
- **Thinking/Reasoning**: ❌ No — not a reasoning model
- **Context**: 32,768 native (131K with YaRN, not recommended for VL tasks)
- **Architecture**: Qwen2.5-based, 72.2B dense, 80 layers, GQA (64Q/8KV heads)
- **Visual Grounding**: Supports bounding box / GUI agent use cases

## vLLM Args
```
--model=/mnt/models
--served-model-name=qwen25-vl-72b
--tensor-parallel-size=4
--max-model-len=32768
--dtype=auto
--gpu-memory-utilization=0.92
--max-num-seqs=8
--limit-mm-per-prompt={"image": 5}
--disable-custom-all-reduce
--port=8080
```

Env: `HF_HUB_OFFLINE=1`, `VLLM_ATTENTION_BACKEND=TRITON_ATTN_VLLM_V1`, `VLLM_WORKER_MULTIPROC_METHOD=spawn`, `OMP_NUM_THREADS=1`

## Recommended Sampling
- Deterministic (vision analysis): `temperature=0.1`, `top_p=0.001`, `repetition_penalty=1.05`
- General chat: `temperature=0.7`, `top_p=0.8`, `top_k=20`

## Resources
- **GPU**: 4× L40S (48 GB each), whole-device allocation (`nvidia.com/gpu: "4"`)
- **CPU**: 8 req / 16 limit
- **Memory**: 32Gi req / 128Gi limit
- **SHM**: 16Gi (emptyDir Memory)
- **Cold start**: ~4 minutes (144 GB BF16 over NFS + vLLM init)
- **Requires full node** — all 4 GPUs on one node for TP4

## Special Notes
- **Vision model** — supports images, video, multiple images (up to 5 per prompt)
- **No tool calling** — visual grounding for GUI agents only, not structured function calling
- **Non-reasoning** — no thinking/reasoning mode
- **TRITON_ATTN_VLLM_V1 required** on L40S (SM89)
- **disable-custom-all-reduce required** for TP>=2 on HAMi
- **limit-mm-per-prompt** set to 5 images max per request
- **TP4 requires all 4 GPUs on one node** — cannot coexist with other GPU workloads on same node
- **131K YaRN available but not recommended for VL tasks** per Qwen docs
- **Qwen License** — permissive except 100M+ MAU commercial threshold

## Test Results (2026-06-11)
**22/22 passed, 2 expected failures, 0 failed**

All OpenAI and Anthropic endpoints working:
- ✅ Basic chat, streaming (20 chunks), temp/top_p/top_k, stop sequences, system prompt
- ✅ Vision (OAI image_url) — correctly describes Google logo colors
- ✅ Vision (ANT image block) — correctly describes image content
- ✅ max_tokens=32k accepted
- ✅ No reasoning content (correct for non-reasoning model)
- ✅ Resources block present
- ✅ Anthropic /v1/messages (basic, streaming, system, vision, max_tokens truncation)
- ✅ Catalog: vision=True, tools=False, reasoning=False, ctx=32768, max_out=32768
- Cold start: ~285s (~4.75 min) for 144 GB BF16 on 4x L40S

## Files
- `details.yaml` — ConfigMap (v2 card, supports_vision=true, supports_tools=false)
- `inferenceservice.yaml` — KServe ISVC (vLLM v0.20.2, TP4, scale-to-zero 15m)
- `test.py` — Gateway test suite with vision checks
