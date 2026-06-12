# Qwen2.5-VL-72B-AWQ Model Card

## Identity
- **Model**: Qwen/Qwen2.5-VL-72B-Instruct-AWQ (72.2B dense, vision-language, 4-bit AWQ quantized)
- **Type**: Chat (vision + text, no thinking/reasoning mode)
- **Framework**: vLLM v0.20.2, tensor-parallel 4
- **Source**: https://huggingface.co/Qwen/Qwen2.5-VL-72B-Instruct-AWQ
- **Quantization**: AWQ 4-bit (official, auto-detected from model config)
- **BF16 variant**: `qwen25-vl-72b` — same model, full precision, limited to 32K context

## Capabilities
- **Vision**: ✅ Dynamic resolution images, video up to 1+ hour, up to 20 images per prompt
- **Tool Calling**: ❌ No structured tool/function calling (visual grounding for GUI agents only)
- **Thinking/Reasoning**: ❌ No — not a reasoning model
- **Context**: 65,536 deployed (128K max positions with YaRN)
- **Architecture**: Qwen2.5-based, 72.2B dense, 80 layers, GQA (64Q/8KV heads)
- **Visual Grounding**: Supports bounding box / GUI agent use cases

## Memory (AWQ 4-bit)
AWQ weights use **~17 GiB/GPU** (TP4). On L40S (48 GiB):
- `gpu-memory-utilization=0.92` → 44.2 GiB budget
- After weights: ~27 GiB for KV + encoder cache
- **64K context fits comfortably** — unlike BF16 variant (34.43 GiB/GPU, limited to 32K)

## vLLM Args
```
--model=/mnt/models
--served-model-name=qwen25-vl-72b-awq
--tensor-parallel-size=4
--max-model-len=65536
--dtype=auto
--gpu-memory-utilization=0.92
--max-num-seqs=4
--limit-mm-per-prompt={"image": 20, "video": 1}
--disable-custom-all-reduce
--port=8080
```

Env: `HF_HUB_OFFLINE=1`, `VLLM_ATTENTION_BACKEND=TRITON_ATTN_VLLM_V1`, `VLLM_WORKER_MULTIPROC_METHOD=spawn`, `OMP_NUM_THREADS=1`

Note: `--quantization=awq` is NOT needed — vLLM auto-detects from model's `config.json`.

## Recommended Sampling
- Deterministic (vision analysis): `temperature=0.1`, `top_p=0.001`, `repetition_penalty=1.05`
- General chat: `temperature=0.7`, `top_p=0.8`, `top_k=20`

## Resources
- **GPU**: 4× L40S (48 GB each), whole-device allocation (`nvidia.com/gpu: "4"`)
- **CPU**: 8 req / 16 limit
- **Memory**: 32Gi req / 128Gi limit
- **SHM**: 16Gi (emptyDir Memory)
- **Cold start**: ~3 minutes (75 GB AWQ over NFS + vLLM init)
- **Requires full node** — all 4 GPUs on one node for TP4

## Special Notes
- **AWQ vs BF16**: Same model, 4-bit quantization reduces weights from ~144 GB to ~72 GB
- **64K context** — double the BF16 variant's 32K, thanks to lower weight memory footprint
- **20 images per prompt** — more than BF16's 5, due to extra memory headroom
- **Auto-detected quantization** — no explicit `--quantization` flag needed
- **Vision model** — supports images, video, up to 20 images per prompt
- **No tool calling** — visual grounding for GUI agents only, not structured function calling
- **TRITON_ATTN_VLLM_V1 required** on L40S (SM89)
- **disable-custom-all-reduce required** for TP>=2 on HAMi
- **TP4 requires all 4 GPUs on one node**
- **Qwen License** — permissive except 100M+ MAU commercial threshold

## Files
- `details.yaml` — ConfigMap (v2 card, supports_vision=true, context=65536)
- `inferenceservice.yaml` — KServe ISVC (vLLM v0.20.2, TP4, 64K ctx, scale-to-zero 15m)
- `pvc.yaml` — 100Gi NFS PVC for AWQ weights (~72 GB)
- `download-job.yaml` — One-shot job to pre-stage weights from HuggingFace
