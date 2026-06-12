# Gemma 3 4B IT — Model Context

## What This Model Does

Google Gemma 3 4B Instruct. Lightweight multimodal model (SigLIP vision tower) accepting text + images in OpenAI chat format. 128K-capable context (served at 64K). Strong multilingual instruction-following for its size. Served on a HAMi vGPU slice (20 GiB). No tool calling or reasoning mode.

## Source Repo

**HuggingFace**: [google/gemma-3-4b-it](https://huggingface.co/google/gemma-3-4b-it)

Key recommendations from source:
- **Vision**: SigLIP vision tower, images normalized to 896×896, encoded to 256 tokens each
- **Context length**: 128K for 4B size
- **Max output**: 8192 tokens
- **License**: Gemma terms

## Identity
- **Model**: google/gemma-3-4b-it (4B dense, vision-language)
- **Type**: Chat (vision + text, no thinking/reasoning mode)
- **Framework**: vLLM v0.20.2, tensor-parallel 1
- **Source**: https://huggingface.co/google/gemma-3-4b-it
- **Quantization**: None (BF16)

## Capabilities
- **Vision**: ✅ SigLIP vision tower, images at 896×896, up to 8 images per prompt
- **Tool Calling**: ❌ No structured tool/function calling
- **Thinking/Reasoning**: ❌ No — not a reasoning model
- **Context**: 65,536 deployed (128K native)
- **Architecture**: Gemma 3, 4B dense, GQA

## vLLM Args
```
vllm serve /data
--served-model-name=gemma-3-4b-it
--port=8080
--tensor-parallel-size=1
--max-model-len=65536
--dtype=bfloat16
--gpu-memory-utilization=0.90
--trust-remote-code
--limit-mm-per-prompt={"image":8}
```

Env: `VLLM_WORKER_MULTIPROC_METHOD=spawn`

## Recommended Sampling
- General chat: `temperature=1.0`, `top_p=0.95`, `top_k=64`
- Deterministic: `temperature=0`

## Resources
- **GPU**: 1× HAMi vGPU slice (20 GiB, `nvidia.com/gpumem: "20480"`)
- **CPU**: 4 req / 8 limit
- **Memory**: 16Gi req / 24Gi limit
- **SHM**: 4Gi (emptyDir Memory)
- **Cold start**: ~1-2 minutes (small model, BF16 ~8 GB weights)
- **Lightweight** — runs on a single vGPU slice, doesn't need a whole GPU

## Special Notes
- **HAMi vGPU** — uses gpumem slice, not whole-device allocation
- **4B model** — smallest Gemma 3 multimodal variant, fast inference
- **No tool calling** — no tool parser needed
- **No reasoning** — no thinking parser needed
- **Gemma terms** — not Apache-2.0, check Gemma license
- **64K context** — half of 128K native, safe for 20 GiB vGPU slice

## Test Results

*(To be filled after gateway testing)*

## Files

| File | Purpose |
|------|---------|
| `details.yaml` | ConfigMap (v2 card, supports_vision=true, context=65536) |
| `inferenceservice.yaml` | KServe ISVC (vLLM v0.20.2, TP1 vGPU, 64K ctx, scale-to-zero 15m) |
| `pvc.yaml` | Dedicated PVC (gemma-3-4b-it-data, 20Gi NFS) |
| `test.py` | Gateway test suite (20 tests) |
| `CLAUDE.md` | This file — model context |
