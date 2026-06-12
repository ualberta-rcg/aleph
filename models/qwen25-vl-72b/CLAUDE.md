# Qwen2.5-VL-72B Model Card

## Identity
- **Model**: Qwen/Qwen2.5-VL-72B-Instruct (72.2B dense, vision-language)
- **Type**: Chat (vision + text, no thinking/reasoning mode)
- **Framework**: vLLM v0.20.2, tensor-parallel 4
- **Source**: https://huggingface.co/Qwen/Qwen2.5-VL-72B-Instruct
- **Quantization**: BF16 (full precision)
- **Variant**: For 64K context, use `qwen25-vl-72b-awq` (4-bit AWQ, same model)

## Capabilities
- **Vision**: ✅ Dynamic resolution images, video up to 1+ hour, up to 5 images per prompt
- **Tool Calling**: ❌ No structured tool/function calling (visual grounding for GUI agents only)
- **Thinking/Reasoning**: ❌ No — not a reasoning model
- **Context**: 32,768 deployed (131K with YaRN, not recommended for VL tasks)
- **Architecture**: Qwen2.5-based, 72.2B dense, 80 layers, GQA (64Q/8KV heads)
- **Visual Grounding**: Supports bounding box / GUI agent use cases

## Memory Constraints (BF16)
BF16 weights use **34.43 GiB/GPU** (TP4). On L40S (48 GiB):
- `gpu-memory-utilization=0.92` → 44.2 GiB budget
- After weights: ~9.7 GiB for KV + encoder cache
- **Context limited to 32K** — 64K OOMs during CUDA graph profiling (tested 2026-06-12)
- For 64K context, use the AWQ variant (`qwen25-vl-72b-awq`) at ~17 GiB/GPU

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
- **BF16 memory limit** — 34.43 GiB/GPU for weights leaves little headroom; 32K context max
- **AWQ variant available** — `qwen25-vl-72b-awq` uses ~17 GiB/GPU, supports 64K context
- **Vision model** — supports images, video, up to 20 images per prompt
- **No tool calling** — visual grounding for GUI agents only, not structured function calling
- **Non-reasoning** — no thinking/reasoning mode
- **TRITON_ATTN_VLLM_V1 required** on L40S (SM89)
- **disable-custom-all-reduce required** for TP>=2 on HAMi
- **TP4 requires all 4 GPUs on one node** — cannot coexist with other GPU workloads on same node
- **Qwen License** — permissive except 100M+ MAU commercial threshold

## Test Results (2026-06-12)
**6/6 passed** (gateway test via model-gateway pod)

All endpoints working after reverting to original settings:
- ✅ Basic chat, system prompt, stop sequences
- ✅ Anthropic /v1/messages
- ✅ Streaming (10 chunks)
- ✅ Vision (solid green image described correctly)
- Cold start: ~15s (pod already warm from probe)

**Previous test (2026-06-05): 22/22 passed, 2 expected failures, 0 failed**

## Regression Note (2026-06-12)
64K context (commit 20d2d7e) caused persistent OOM during CUDA graph profiling.
BF16 weights at 34.43 GiB/GPU + 64K KV cache + encoder cache exceeds L40S 48 GiB.
**Fix: reverted to original 32K context.** AWQ variant provides 64K context.

## Files
- `details.yaml` — ConfigMap (v2 card, supports_vision=true, supports_tools=false, context=32768)
- `inferenceservice.yaml` — KServe ISVC (vLLM v0.20.2, TP4, 32K ctx, 0.85 util, scale-to-zero 15m)
- `pvc.yaml` — 200Gi NFS PVC for BF16 weights (~145 GB)
- `download-job.yaml` — One-shot job to pre-stage weights from HuggingFace
- `test.py` — Gateway test suite with vision checks
