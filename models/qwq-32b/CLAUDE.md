# QwQ-32B Model Card

## Identity
- **Model**: Qwen/QwQ-32B (32.5B dense, reasoning model)
- **Type**: Chat (always-on chain-of-thought reasoning, tool calling)
- **Framework**: vLLM v0.20.2, tensor-parallel 2
- **Source**: https://huggingface.co/Qwen/QwQ-32B

## Capabilities
- **Thinking/Reasoning**: ✅ Always-on — generates `<think/>` blocks via deepseek_r1 parser. No toggle needed.
- **Tool Calling**: Hermes parser (`--tool-call-parser=hermes` + `--enable-auto-tool-choice`)
- **Vision**: ❌ No (text-only model)
- **Context**: 131,072 native, deployed at 32,768 on 2× L40S
- **Architecture**: Qwen2.5-based, 32.5B dense, 64 layers, GQA (40Q/8KV heads)

## vLLM Args
```
--model=/mnt/models
--served-model-name=qwq-32b
--tensor-parallel-size=2
--max-model-len=32768
--dtype=auto
--gpu-memory-utilization=0.92
--max-num-seqs=8
--reasoning-parser=deepseek_r1
--enable-auto-tool-choice
--tool-call-parser=hermes
--disable-custom-all-reduce
--port=8080
```

Env: `HF_HUB_OFFLINE=1`, `VLLM_ATTENTION_BACKEND=TRITON_ATTN_VLLM_V1`, `VLLM_WORKER_MULTIPROC_METHOD=spawn`, `OMP_NUM_THREADS=1`

## Best Sampling (HF recommended)
- `temperature=0.6`, `top_p=0.95`, `top_k=20-40`, `min_p=0`
- Do NOT use greedy decoding (causes endless repetitions)
- `presence_penalty` 0-2 to reduce repetition (may cause language mixing at higher values)

## Resources
- **GPU**: 2× L40S (48 GB each), whole-device allocation (`nvidia.com/gpu: "2"`)
- **CPU**: 8 req / 16 limit
- **Memory**: 24Gi req / 64Gi limit
- **SHM**: 12Gi (emptyDir Memory)
- **Cold start**: ~2 minutes (64 GB FP16 over NFS + vLLM init)
- **Can coexist** with another TP2 model on the same node (2 GPUs each × 2 = 4 total)

## Special Notes
- **Always-on reasoning** — no thinking toggle. Model always generates `<think/>` blocks. deepseek_r1 parser handles stripping from API output.
- **TRITON_ATTN_VLLM_V1 required** on L40S (SM89)
- **disable-custom-all-reduce required** for TP>=2 on HAMi
- **gpu-memory-utilization=0.92** — fits 64GB FP16 + KV cache across 2×48GB GPUs
- **max-num-seqs=8** — allows multiple concurrent requests
- **max-model-len=32768** — 32K context (131K native but 32K is sufficient for most use cases with TP2 memory)
- **For prompts >8192 tokens**, YaRN should be enabled (rope_scaling config) — not currently set in deployment

## Test Results (2026-06-11)
**21/21 passed, 3 expected failures, 0 failed**

All OpenAI and Anthropic endpoints working:
- ✅ Basic chat with reasoning content present
- ✅ Streaming (101 chunks)
- ✅ Temperature, top_p, top_k, stop sequences
- ✅ System prompt
- ✅ Tool calling (hermes parser, both OAI and ANT)
- ✅ Reasoning always present (deepseek_r1 parser)
- ✅ Anthropic /v1/messages (basic, streaming, system, tools)
- ✅ Vision correctly rejected (400)
- ✅ Catalog: vision=False, tools=True, reasoning=True, ctx=32768, max_out=32768

## Files
- `details.yaml` — ConfigMap (v2 card, reasoning_model=true, supports_tools=true)
- `inferenceservice.yaml` — KServe ISVC (vLLM v0.20.2, TP2, scale-to-zero 15m)
- `test.py` — 24-check gateway test
