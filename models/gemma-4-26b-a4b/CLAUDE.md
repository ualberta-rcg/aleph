# Gemma 4 26B A4B — Model Context

## What This Model Does

Google Gemma 4 26B A4B MoE instruction-tuned model. 25.2B total params, 3.8B active (128 experts, 8 active + 1 shared). Configurable thinking mode, multimodal (text+image+video), 256K native context (deployed at 131K), native function calling. FP8 quantization. Hybrid attention with sliding window + global layers. 1x L40S GPU.

## Source Repo

**HuggingFace**: [google/gemma-4-26B-A4B-it](https://huggingface.co/google/gemma-4-26B-A4B-it)

Key recommendations from source:
- **Sampling**: temperature=1.0, top_p=0.95, top_k=64 (standardized across all use cases)
- **Thinking mode**: Enabled by `<|think|>` token in system prompt; parsed via `<|channel>thought\n` blocks
- **Context length**: 256K tokens for 26B A4B model (we deploy at 131K for VRAM safety)
- **Image processing**: Place images before text in prompts for best performance
- **Image token budgets**: 70/140/280/560/1120 per image (variable resolution)
- **License**: Apache 2.0

## vLLM Deployment — HF Recommendations vs Our Config

**HF recommended inference:**
```python
# Transformers (not vLLM)
model = AutoModelForCausalLM.from_pretrained("google/gemma-4-26B-A4B-it", dtype="auto", device_map="auto")
# or for image processing:
model = AutoModelForMultimodalLM.from_pretrained("google/gemma-4-26B-A4B-it", dtype="auto", device_map="auto")
```

Note: Gemma 4 IS natively supported in vLLM v0.20.2+ as `Gemma4ForConditionalGeneration` — no longer needs the Transformers fallback.

**What we have vs what's recommended:**
| Setting | Our Config | Notes |
|---------|-----------|-------|
| quantization | fp8 | Required — BF16 weights (~50GB) won't fit on 1x L40S |
| max-model-len | 131072 | Half of 256K native. Safe for 1x L40S with ~17GB KV room |
| enforce-eager | **removed** | Was disabling flash attention. Now enabled by default. |
| limit-mm-per-prompt | {"image": 16} | Up to 16 images. v0.20.2 expects JSON format |
| max-num-seqs | 8 | MoE with 3.8B active params handles concurrency well |
| gpu-memory-utilization | 0.92 | Standard |
| tool-call-parser | gemma4 | Correct for Gemma 4 |
| reasoning-parser | gemma4 | Correct for Gemma 4 thinking mode |
| vLLM version | v0.20.2 | Native Gemma4 support with gemma4 tool/reasoning parsers |
| max-num-batched-tokens | 4096 | Required for multimodal (max_tokens_per_mm_item=2496) |
| tensor-parallel-size | 1 | Single GPU — correct |

## How The Server Works

- **Pattern**: vLLM via image-native binary (no venv needed for serving)
- **Container**: `vllm/vllm-openai:v0.20.2` — uses image's built-in vllm directly
- **Init container**: Creates lightweight venv (huggingface_hub only) + downloads weights (both idempotent)
- **PVC layout**: `/data/venv/` (download deps only) + `/data/model/` (weights)
- **Startup**: ~3 minutes (weight loading from NFS ~68s, torch compile ~53s, CUDA graphs ~4s)
- **Health**: vLLM's built-in `/v1/models` endpoint
- **Shared memory**: 8Gi emptyDir at `/dev/shm`
- **VLLM_WORKER_MULTIPROC_METHOD**: spawn

## GPU Memory Budget (1x L40S 46GB)

- FP8 weights: ~25 GB
- Available at 0.92 util: ~42.3 GB
- Remaining for KV/activations: ~17 GB
- Hybrid attention (sliding window 1024 + global) bounds KV cache
- 16 images at 280 tokens each = 4,480 tokens — well within budget

## Gateway Integration

- **ISVC name**: `gemma-4-26b-a4b` (matches API id, no ISVC_NAME_MAP entry)
- **MODEL_TYPE**: chat
- **CONTEXT_WINDOW**: 131072 (matches deployment)
- **MODEL_MAX_TOKENS**: 8000
- **REASONING_MODELS**: yes — gateway enables thinking by default, disables for meta-tasks
- **KSERVE_CUSTOM_MODELS**: yes — uses `/v1/` prefix
- **GPU_MODELS**: yes

## Deploy / Update / Test

```bash
# Deploy (first time or force update)
kubectl apply --server-side --force-conflicts -k models/gemma-4-26b-a4b/

# Check status
kubectl get pods -n models -l serving.kserve.io/inferenceservice=gemma-4-26b-a4b

# Logs
kubectl logs -n models -l serving.kserve.io/inferenceservice=gemma-4-26b-a4b -c kserve-container -f

# Logs (init container)
kubectl logs -n models -l serving.kserve.io/inferenceservice=gemma-4-26b-a4b -c setup -f

# Test (internal)
curl http://gemma-4-26b-a4b-predictor.models.svc.cluster.local:8080/v1/chat/completions \
  -d '{"model":"gemma-4-26b-a4b","messages":[{"role":"user","content":"Hello"}],"max_tokens":50}'

# Test (public)
curl -X POST https://inference.kubeflow.vulcan.alliancecan.ca/serving/api/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{"model":"gemma-4-26b-a4b","messages":[{"role":"user","content":"Hello"}],"max_tokens":50}'
```

## Outstanding Issues

1. **PVC has old venv with vllm 0.9.2**: The `/data/venv/` on PVC still has the old vllm install from when the init container built it. Not used by the main container (uses image-native vllm), but wastes ~5 GB on the PVC. Can be cleaned up with `rm -rf /data/venv` from a debug pod if space is needed.

## Files

| File | Purpose |
|------|---------|
| `details.yaml` | ConfigMap with model metadata |
| `inferenceservice.yaml` | ISVC spec: init container (downloads only) + vLLM container + PVC + shared memory |
| `kustomization.yaml` | Kustomize resources |
| `pvc.yaml` | Dedicated PVC (gemma-4-26b-a4b-data, 60Gi NFS) |

**IMPORTANT: When changing this model's deployment config (inferenceservice.yaml), update details.yaml to match.**
