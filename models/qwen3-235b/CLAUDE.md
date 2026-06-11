# Qwen3-235B Model Card

## Identity
- **Model**: Qwen/Qwen3-235B-A22B-Instruct-2507 (235B total / 22B active, sparse MoE, AWQ int4)
- **Type**: Chat (non-thinking instruct variant, tool calling)
- **Framework**: vLLM v0.20.2, tensor-parallel 4
- **Source**: https://huggingface.co/QuantTrio/Qwen3-235B-A22B-Instruct-2507-AWQ

## Capabilities
- **Thinking/Reasoning**: ❌ No — this is the Instruct-2507 non-thinking variant. Explicitly does NOT generate `<think` blocks.
- **Tool Calling**: Hermes parser (`--tool-call-parser=hermes` + `--enable-auto-tool-choice`)
- **Vision**: ❌ No (text-only model, no vision encoder)
- **Context**: 262K native, deployed at 131,072 on 4× L40S
- **Architecture**: Sparse MoE — 128 experts, 8 activated per token, 22B active params
- **Quantization**: AWQ int4 (QuantTrio), ~116 GB model files

## vLLM Args
```
--model=/mnt/models
--served-model-name=qwen3-235b
--tensor-parallel-size=4
--quantization=awq_marlin
--max-model-len=131072
--dtype=float16
--gpu-memory-utilization=0.90
--max-num-seqs=4
--enable-auto-tool-choice
--tool-call-parser=hermes
--disable-custom-all-reduce
--port=8080
```

Env: `HF_HUB_OFFLINE=1`, `VLLM_ATTENTION_BACKEND=TRITON_ATTN_VLLM_V1`, `VLLM_WORKER_MULTIPROC_METHOD=spawn`, `OMP_NUM_THREADS=1`

## Best Sampling (HF recommended)
- `temperature=0.7`, `top_p=0.8`, `top_k=20`, `min_p=0`
- Output length: 16,384 tokens for most queries
- `presence_penalty` 0-2 to reduce repetition (may cause language mixing at higher values)

## Resources
- **GPU**: 4× L40S (48 GB each), whole-device allocation (`nvidia.com/gpu: "4"`)
- **CPU**: 8 req / 16 limit
- **Memory**: 64Gi req / 128Gi limit
- **SHM**: 32Gi (emptyDir Memory)
- **Cold start**: ~4 minutes (116 GB AWQ int4 over NFS + vLLM init)
- **Requires dedicated GPU node** — TP4 takes all 4 GPUs on a node

## Special Notes
- **TRITON_ATTN_VLLM_V1 required** on L40S (SM89) — FlashAttention-3 unavailable
- **disable-custom-all-reduce required** — TP=4 on HAMi triggers P2P stall with custom all-reduce
- **gpu-memory-utilization=0.90** — fits 116GB AWQ + KV cache across 4×48GB GPUs
- **max-num-seqs=4** — bounds concurrent requests given memory constraints
- **Non-thinking variant** — does NOT support `enable_thinking` or reasoning mode
- **Scheduling conflict** — cannot run simultaneously with other TP4 models (takes all GPUs on a node)

## Test Results (2026-06-11)
**21/21 passed, 3 expected failures, 0 failed**

All OpenAI and Anthropic endpoints working:
- ✅ Basic chat, streaming, system prompt
- ✅ No reasoning content (confirmed non-thinking)
- ✅ Tool calling (hermes parser)
- ✅ Temperature, top_p, top_k, stop sequences
- ✅ Anthropic /v1/messages (basic, streaming, system, tools)
- ✅ Vision correctly rejected (400)
- ✅ Catalog: vision=False, tools=True, reasoning=False, ctx=131072, max_out=32768

## Files
- `details.yaml` — ConfigMap (v2 card, non-thinking, no param_translation for thinking)
- `inferenceservice.yaml` — KServe ISVC (vLLM v0.20.2, TP4, scale-to-zero 30m)
- `test.py` — 24-check gateway test
