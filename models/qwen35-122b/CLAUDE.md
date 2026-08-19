# Qwen3.5-122B Model Card

## Identity
- **Model**: Qwen/Qwen3.5-122B-A10B-FP8 (122B total / 10B active, sparse MoE, FP8)
- **Type**: Chat (reasoning + tool calling)
- **Framework**: vLLM v0.20.2, tensor-parallel 4
- **Source**: https://huggingface.co/Qwen/Qwen3.5-122B-A10B-FP8

## Capabilities
- **Thinking/Reasoning**: Toggle mode via `chat_template_kwargs.enable_thinking` (default: on). Uses `<think...</think` blocks.
- **Tool Calling**: Qwen3 coder parser (`--tool-call-parser=qwen3_coder` + `--enable-auto-tool-choice`)
- **Vision**: ❌ No (deployed with `--language-model-only` — vision encoder disabled to save VRAM)
- **Context**: 262K native, deployed at 131,072 on 4× L40S
- **Architecture**: Sparse MoE — 256 experts, 8 routed + 1 shared per token, 10B active params

## vLLM Args
```
--model=/mnt/models
--served-model-name=qwen35-122b
--tensor-parallel-size=4
--max-model-len=131072
--dtype=auto
--gpu-memory-utilization=0.95
--max-num-seqs=16
--reasoning-parser=qwen3
--enable-auto-tool-choice
--tool-call-parser=qwen3_coder
--language-model-only
--disable-custom-all-reduce
```

Env: `HF_HUB_OFFLINE=1`, `VLLM_ATTENTION_BACKEND=TRITON_ATTN_VLLM_V1`, `VLLM_WORKER_MULTIPROC_METHOD=spawn`, `OMP_NUM_THREADS=1`

## Thinking Mode (toggle)
Gateway injects `chat_template_kwargs: {enable_thinking: bool}`:
- Default: **on** (`enable_thinking: true`)
- Off: `{"chat_template_kwargs": {"enable_thinking": false}}`

Best sampling:
- Thinking ON: `temperature=0.6`, `top_p=0.95`, `top_k=20`
- Thinking OFF: `temperature=0.7`, `top_p=0.8`, `top_k=20`

## Resources
- **GPU**: 4× L40S (48 GB each), whole-device allocation (`nvidia.com/gpu: "4"`)
- **CPU**: 8 req / 16 limit
- **Memory**: 64Gi req / 128Gi limit
- **SHM**: 16Gi (emptyDir Memory)
- **Cold start**: ~5 minutes (122 GB FP8 over NFS + vLLM init)

## Special Notes
- **TRITON_ATTN_VLLM_V1 required** on L40S (SM89) — FlashAttention-3 unavailable
- **disable-custom-all-reduce required** — TP=4 on HAMi triggers P2P stall with custom all-reduce
- **gpu-memory-utilization=0.95** — max to fit 122GB FP8 + KV cache across 4×48GB GPUs
- **max-num-seqs=16** — KV cache was ~2% at 4 concurrent; 16 uses headroom. Single replica (`minReplicas=maxReplicas=1`, 4× L40S).

## Test Results (2026-06-11)
**23/23 passed, 3 expected failures, 0 failed**

All OpenAI and Anthropic endpoints working:
- ✅ Basic chat, streaming, system prompt
- ✅ Thinking toggle on/off via chat_template_kwargs
- ✅ Tool calling (qwen3_coder parser)
- ✅ Temperature, top_p, top_k, stop sequences
- ✅ Anthropic /v1/messages (basic, streaming, system, thinking disabled, tools)
- ✅ Vision correctly rejected (400)
- ✅ Catalog: vision=False, tools=True, reasoning=True, ctx=131072, max_out=32768

## Files
- `details.yaml` — ConfigMap (v2 card with param_translation, toggle mode)
- `inferenceservice.yaml` — KServe ISVC (vLLM v0.20.2, TP4, scale-to-zero 30m)
- `test.py` — 26-check gateway test
