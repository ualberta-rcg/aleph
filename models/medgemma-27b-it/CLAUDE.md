# MedGemma 27B IT — Model Context

## What This Model Does

Google MedGemma 27B instruction-tuned multimodal model for medical AI. Fine-tuned from Gemma 3 on medical text, chest X-rays, dermatology images, ophthalmology (fundus), and histopathology slides. Accepts text and base64 images. Based on Gemma 3 architecture with a SigLIP image encoder pre-trained on de-identified medical data. 128K context (deployed at 32K). Uses 2 GPUs.

## Source Repo

**HuggingFace**: [google/medgemma-27b-it](https://huggingface.co/google/medgemma-27b-it)

Key recommendations from source:
- **vLLM**: Requires `--trust-remote-code` and `--limit-mm-per-prompt` for image inputs
- **dtype**: bfloat16 recommended
- **Context length**: At least 128K supported
- **Max output tokens**: 8192 recommended
- **License**: Health AI Developer Foundations Terms of Use (NOT Apache-2.0)
- **Not evaluated for multi-image tasks** — primarily tested on single-image inputs
- **Not evaluated for multi-turn conversations**

## Identity
- **Model**: google/medgemma-27b-it (27B, Gemma 3-based, medical multimodal)
- **Type**: Chat (vision + text, no thinking/reasoning mode)
- **Framework**: vLLM v0.20.2, tensor-parallel 2
- **Source**: https://huggingface.co/google/medgemma-27b-it
- **Precision**: BF16

## Capabilities
- **Vision**: ✅ SigLIP medical image encoder (chest X-ray, derm, fundus, histo), up to 5 images
- **Tool Calling**: ❌ No structured tool/function calling
- **Thinking/Reasoning**: ❌ No — not a reasoning model
- **Context**: 32,768 deployed (128K native, limited by 27B BF16 on 2x L40S)
- **Architecture**: Gemma 3-based, 27B, GQA, decoder-only transformer

## How The Server Works

- **Pattern**: vLLM binary (Knative mode, `vllm serve` format)
- **Container**: `vllm/vllm-openai:v0.20.2`
- **Weights**: Pre-downloaded to PVC by init container
- **Startup**: ~3-5 minutes cold start (loading 27B BF16 weights into 2 GPUs)
- **Health**: vLLM's built-in `/v1/models` endpoint
- **Shared memory**: 16Gi emptyDir at `/dev/shm` (required for tensor parallelism)
- **VLLM_WORKER_MULTIPROC_METHOD**: spawn (required for multi-GPU)

## vLLM Args
```
vllm serve /data
--served-model-name=medgemma-27b-it
--port=8080
--tensor-parallel-size=2
--max-model-len=32768
--dtype=bfloat16
--gpu-memory-utilization=0.92
--trust-remote-code
--limit-mm-per-prompt={"image": 5}
--disable-custom-all-reduce
--max-num-seqs=4
```

## Memory Budget (2x L40S 48GB)
- BF16 weights: ~54 GB total (~27 GB/GPU with TP2)
- Available at 0.92 util: ~44.2 GB/GPU
- Remaining for KV/activations: ~17 GB/GPU
- 32K context is safe; 128K would OOM

## Resources
- **GPU**: 2× L40S (48 GB each), whole-device allocation (`nvidia.com/gpu: "2"`)
- **CPU**: 8 req / 16 limit
- **Memory**: 32Gi req / 64Gi limit
- **SHM**: 16Gi (emptyDir Memory)
- **Cold start**: ~3-5 minutes (54 GB BF16 over NFS + vLLM init)
- **Requires half a node** — 2 of 4 GPUs

## Special Notes
- **Medical model** — fine-tuned for medical text and image comprehension
- **32K context** — 128K native but limited by BF16 memory on 2x L40S
- **Single-image optimized** — not evaluated for multi-image tasks
- **No tool calling** — no tool parser needed
- **No reasoning** — no thinking parser needed
- **Health AI Developer Foundations license** — NOT Apache-2.0
- **Gated model** — requires HF_TOKEN for download
- **disable-custom-all-reduce required** for TP>=2 on HAMi
- **Not evaluated for multi-turn** — primarily tested on single-turn

## Gateway Integration

- **ISVC name**: `medgemma-27b-it` (matches API id, no ISVC_NAME_MAP entry)
- **MODEL_TYPE**: chat
- **CONTEXT_WINDOW**: 32768 (aligned with ISVC max-model-len)
- **MODEL_MAX_TOKENS**: 8192
- **REASONING_MODELS**: not listed (correct — not a reasoning model)
- **KSERVE_CUSTOM_MODELS**: yes — uses `/v1/` prefix
- **GPU_MODELS**: yes

## Test Results

*(To be filled after gateway testing)*

## Files

| File | Purpose |
|------|---------|
| `details.yaml` | ConfigMap (v2 card, supports_vision=true, context=32768) |
| `inferenceservice.yaml` | ISVC spec: vLLM v0.20.2, TP2, 32K ctx, scale-to-zero 15m |
| `pvc.yaml` | Dedicated PVC (medgemma-27b-it, 60Gi NFS) |
| `test.py` | Gateway test suite (20 tests) |
| `CLAUDE.md` | This file — model context |

**IMPORTANT: When changing this model's deployment config (inferenceservice.yaml), update details.yaml to match.**
