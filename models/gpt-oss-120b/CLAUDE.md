# GPT-OSS 120B — Model Context

## What This Model Does

OpenAI GPT-OSS 120B MoE — open-weight text-only model with MXFP4 quantization. 117B total params (5.1B active per token), 128 experts with 4 active per token. Configurable reasoning effort (low/medium/high), native function calling via harmony format, structured outputs, agentic capabilities. Apache 2.0 license. 2x L40S GPUs. 128K context window.

**Not multimodal** — text input only. No image, audio, or video support.

## Source

- **HuggingFace**: [openai/gpt-oss-120b](https://huggingface.co/openai/gpt-oss-120b)
- **Model card**: [arXiv:2508.10925](https://arxiv.org/abs/2508.10925)
- **License**: Apache 2.0

## Model Architecture

| Property | Value |
|----------|-------|
| Architecture | MoE Transformer (GptOssForCausalLM) |
| Total params | 117B |
| Active params/token | 5.1B |
| Experts | 128 total, 4 active per token |
| Layers | 36 (alternating sliding/full attention) |
| Hidden size | 2,880 |
| Attention heads | 64 |
| KV heads | 8 (GQA, group size 8) |
| Head dim | 64 |
| Context window | 65,536 tokens (model supports 131K) |
| Position encoding | RoPE + YaRN scaling (theta=150K, factor=32) |
| Activation | SiLU (SwiGLU) |
| Tokenizer | o200k_harmony |
| Response format | Harmony (not standard chat template) |

### Quantization

MXFP4 — only MoE expert MLP weights are quantized. Attention, router, embeddings, and LM head are full precision. Quantization is baked into the released weights (not optional).

## Capabilities

- **Reasoning**: Configurable effort (low/medium/high) via system prompt. Full CoT accessible. Trained with same RL as o3/o4-mini.
- **Tool calling**: Native function calling. Client-side orchestrator needed for actual execution.
- **Structured outputs**: JSON schema / guided decoding.
- **Web browsing / code execution**: Model generates tool calls; execution requires external orchestrator.
- **NOT supported**: Images, audio, video, multimodal input.

## How The Server Works

- **Pattern**: Standard vLLM image, no custom build
- **Image**: `vllm/vllm-openai:v0.20.2`
- **Attention**: Triton (auto-selected for L40S/SM89 — flash attention FA3 not available on L40S, v0.20.2 handles this natively)
- **Init container**: `python:3.12-slim` — downloads weights to PVC only
- **Main container**: Runs `vllm serve /data` directly from image
- **No venv, no pip, no overlays** — everything in the standard image
- **Startup**: ~90 seconds (weights load in ~53s, torch.compile + CUDA graphs ~35s)
- **Health**: vLLM's `/v1/models` endpoint
- **Shared memory**: 16Gi emptyDir at `/dev/shm`
- **Env**: `VLLM_WORKER_MULTIPROC_METHOD=spawn`, `OMP_NUM_THREADS=1`

### vLLM Args

```
serve /data
--served-model-name gpt-oss-120b
--port 8080
--tensor-parallel-size 2
--max-model-len 65536
--gpu-memory-utilization 0.92
--max-num-seqs 8
--reasoning-parser openai_gptoss
--tool-call-parser openai
--enable-auto-tool-choice
```

- No `--enforce-eager` — v0.20.2 uses Triton attention natively on L40S.
- `--reasoning-parser openai_gptoss` — separates reasoning from tool calls using harmony format.
- `--tool-call-parser openai` — enables tool call generation.
- `--enable-auto-tool-choice` — gpt-oss ignores this (always enabled), but vLLM requires it to activate the tool call parser.
- `tool_choice: "required"` is not supported.
- Prefix caching and chunked prefill are enabled by default in v0.20.2.

### Resource Usage

- GPU memory: ~34.4 GiB across 2x L40S
- KV cache: 276,650 tokens (4.22x concurrency at 65K context)
- Weights: 60.77 GiB on PVC (15 safetensor shards)

## Gateway Integration

- **ISVC name**: `gpt-oss-120b` (matches API id, no ISVC_NAME_MAP entry)
- **MODEL_TYPE**: chat
- **CONTEXT_WINDOW**: 65536
- **MODEL_MAX_TOKENS**: 16000
- **REASONING_MODELS**: yes — gateway disables thinking for title/tags/followups
- **KSERVE_CUSTOM_MODELS**: yes — uses `/v1/` prefix
- **GPU_MODELS**: yes

## Deploy / Update / Test

```bash
# Deploy
kubectl apply --server-side --force-conflicts -k models/gpt-oss-120b/

# Check status
kubectl get pods -n models -l serving.kserve.io/inferenceservice=gpt-oss-120b

# Logs
kubectl logs -n models -l serving.kserve.io/inferenceservice=gpt-oss-120b -c kserve-container -f

# Test (internal)
curl http://gpt-oss-120b-predictor.models.svc.cluster.local:8080/v1/chat/completions \
  -d '{"model":"gpt-oss-120b","messages":[{"role":"user","content":"Hello"}],"max_tokens":50}'

# Test (public)
curl -X POST https://inference.kubeflow.vulcan.alliancecan.ca/serving/api/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{"model":"gpt-oss-120b","messages":[{"role":"user","content":"Hello"}],"max_tokens":50}'
```

## Known Issues

1. **65K context (model supports 131K)**: Reduced from 131K for better concurrency (~4x vs 2.15x). Can increase back to 131K if needed for long-context workloads.

2. **Scale-to-zero cold start**: ~90 seconds from pod start to serving. Image pull adds several minutes if not cached on the node.

3. **tool_choice: "required" not supported**: vLLM's gpt-oss tool call parser only supports `auto` and `none`. The model may also only emit one tool call per turn.

4. **Gateway double-processing**: vLLM separates reasoning into `reasoning_content` field. The gateway also strips thinking tags — watch for double-processing.

## Startup Warnings (all harmless)

- `Auto-initialization of reasoning token IDs failed` — openai_gptoss parser uses token IDs directly, not string patterns. By design.
- `SymmMemCommunicator: Device capability 8.9 not supported` — L40S (SM89) lacks symmetric memory (H100/B200 feature). Expected.
- `For gpt-oss, we ignore --enable-auto-tool-choice` — gpt-oss always has tool use enabled. Flag kept because vLLM requires it to activate the tool call parser pipeline.

## Files

| File | Purpose |
|------|---------|
| `details.yaml` | ConfigMap with model metadata (must match this file) |
| `inferenceservice.yaml` | ISVC spec: vLLM v0.20.2 + PVC + shared memory |
| `kustomization.yaml` | Kustomize resources |
| `pvc.yaml` | Dedicated PVC (gpt-oss-120b) |

**IMPORTANT: When changing deployment config, update details.yaml and this file to match.**
