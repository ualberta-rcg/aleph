# Qwen3-32B Model Card

## Identity
- **Model**: Qwen/Qwen3-32B (32.8B dense, 64 layers, GQA 64Q/8KV)
- **Type**: Chat (reasoning + tool calling)
- **Framework**: vLLM v0.20.2, tensor-parallel 2
- **Source**: https://huggingface.co/Qwen/Qwen3-32B

## Capabilities
- **Thinking/Reasoning**: Binary `enable_thinking` via `chat_template_kwargs` (default: on). Uses `<think...</think` blocks.
- **Tool Calling**: Hermes parser (`--tool-call-parser=hermes` + `--enable-auto-tool-choice`)
- **Vision**: ❌ No (text only)
- **Languages**: 100+ languages and dialects
- **Context**: 32,768 native, 131,072 with YaRN. Deployed at 40,960 (32K output + 8K input, Qwen3 recommended default).

## vLLM Args
```
--model=/mnt/models
--served-model-name=qwen3-32b
--tensor-parallel-size=2
--max-model-len=40960
--dtype=auto
--gpu-memory-utilization=0.92
--max-num-seqs=8
--reasoning-parser=qwen3
--enable-auto-tool-choice
--tool-call-parser=hermes
--disable-custom-all-reduce
```

Env: `HF_HUB_OFFLINE=1`, `VLLM_ATTENTION_BACKEND=TRITON_ATTN_VLLM_V1`, `OMP_NUM_THREADS=1`

## Thinking Mode (effort)
Gateway maps `reasoning_effort` to `chat_template_kwargs.enable_thinking`:
- `none`/`low` → `enable_thinking: false`
- `medium`/`high`/`max` → `enable_thinking: true`

Best sampling:
- Thinking ON: `temperature=0.6`, `top_p=0.95`, `top_k=20`
- Thinking OFF: `temperature=0.7`, `top_p=0.8`, `top_k=20`
- **Never use greedy decoding (temp=0) with thinking ON** — causes repetition.

## Resources
- **GPU**: 2× L40S (48 GB each), whole-device allocation (`nvidia.com/gpu: "2"`)
- **CPU**: 8 req / 16 limit
- **Memory**: 24Gi req / 64Gi limit
- **SHM**: 12Gi (emptyDir Memory)
- **Cold start**: 3-4 minutes (NFS model load + vLLM init)

## Test Results (2026-06-11)
**23/25 passed, 2 expected failures, 0 failed**

All OpenAI and Anthropic endpoints working:
- ✅ Basic chat, streaming, system prompt
- ✅ Thinking on/off via chat_template_kwargs
- ✅ Tool calling (hermes parser)
- ✅ Temperature, top_p, top_k, stop sequences
- ✅ Anthropic /v1/messages (basic, streaming, system, thinking disabled, tools)
- ✅ Vision correctly rejected (400)
- ✅ Catalog: vision=False, tools=True, reasoning=True, ctx=40960, max_out=32768

## Files
- `details.yaml` — ConfigMap (v2 card with param_translation, effort mode)
- `inferenceservice.yaml` — KServe ISVC (vLLM v0.20.2, TP2, scale-to-zero 15m)
- `pvc.yaml` — NFS PVC (100Gi RWX)
- `test.py` — 25-check gateway test
