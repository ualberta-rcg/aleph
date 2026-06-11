# Qwen3.6-35B-A3B Model Card

## Identity
- **Model**: Qwen/Qwen3.6-35B-A3B (35B MoE, 3B active, hybrid Gated-DeltaNet)
- **Type**: Chat (thinking + tools + vision, hybrid attention architecture)
- **Framework**: vLLM v0.20.2, tensor-parallel 2
- **Source**: https://huggingface.co/Qwen/Qwen3.6-35B-A3B

## Capabilities
- **Thinking/Reasoning**: ✅ qwen3 parser — thinking via `chat_template_kwargs: {enable_thinking: true}`. NOT on by default.
- **Tool Calling**: ✅ qwen3_coder parser (`--tool-call-parser=qwen3_coder` + `--enable-auto-tool-choice`)
- **Vision**: ✅ Images + video (ViT encoder, dynamic resolution)
- **Context**: 256K native, deployed at 32K on 2× L40S
- **Architecture**: Hybrid — 30 Gated DeltaNet (linear attention) + 10 full softmax attention layers. 256 experts, 8+1 routed per token.
- **Active params**: 3B per token (35B total)

## vLLM Args
```
--model=/mnt/models
--served-model-name=qwen36-35b-a3b
--tensor-parallel-size=2
--max-model-len=32768
--dtype=auto
--gpu-memory-utilization=0.92
--max-num-seqs=8
--reasoning-parser=qwen3
--enable-auto-tool-choice
--tool-call-parser=qwen3_coder
--disable-custom-all-reduce
--port=8080
```

Env: `HF_HUB_OFFLINE=1`, `VLLM_ATTENTION_BACKEND=TRITON_ATTN_VLLM_V1`, `VLLM_WORKER_MULTIPROC_METHOD=spawn`, `OMP_NUM_THREADS=1`

## Recommended Sampling
| Mode | temperature | top_p | top_k | presence_penalty |
|------|-------------|-------|-------|------------------|
| Thinking | 1.0 | 0.95 | 20 | 1.5 |
| Precise coding | 0.6 | 0.95 | 20 | 0.0 |
| Non-thinking | 0.7 | 0.80 | 20 | 1.5 |

## Resources
- **GPU**: 2× L40S (48 GB each), whole-device allocation (`nvidia.com/gpu: "2"`)
- **CPU**: 8 req / 16 limit
- **Memory**: 24Gi req / 64Gi limit
- **SHM**: 12Gi (emptyDir Memory)
- **Cold start**: ~285s (~4.75 min) for 70 GB MoE over NFS + vLLM init
- **Can coexist** with another TP2 model on the same node

## Special Notes
- **Hybrid architecture** — Gated DeltaNet + softmax attention. Only 10 of 40 layers use traditional KV cache, making it very efficient at long contexts.
- **MoE efficiency** — 3B active params per token, very fast inference for a 35B model
- **Thinking NOT on by default** — requires `chat_template_kwargs: {enable_thinking: true}`. Gateway effort mode handles this.
- **No `/think` soft switch** — unlike Qwen3, Qwen3.6 uses API-only thinking control
- **256K native context** — deployed at 32K due to TP2 memory constraints
- **TRITON_ATTN_VLLM_V1 required** on L40S (SM89)
- **disable-custom-all-reduce required** for TP>=2 on HAMi
- **Requires vLLM >= 0.19.0** for `qwen3_5_moe` architecture support
- **Apache-2.0** license

## Test Results (2026-06-11)
**21/21 passed, 2 expected failures, 0 failed**

All OpenAI and Anthropic endpoints working:
- ✅ Basic chat, streaming, temp/top_p/top_k, stop sequences, system prompt
- ✅ Reasoning (with enable_thinking=true) — generates thinking content
- ✅ Tool calling (qwen3_coder) — 1/1 tool_calls on both OAI and ANT
- ✅ Vision (OAI + ANT) — correctly describes images
- ✅ max_tokens=32k accepted
- ✅ Catalog: vision=True, tools=True, reasoning=True, ctx=32768, max_out=32768
- Cold start: ~285s

## Files
- `details.yaml` — ConfigMap (v2 card, reasoning effort mode, supports_tools=true, supports_vision=true)
- `inferenceservice.yaml` — KServe ISVC (vLLM v0.20.2, TP2, reasoning+tools+vision parsers)
- `test.py` — 23-check gateway test with reasoning, tools, and vision
