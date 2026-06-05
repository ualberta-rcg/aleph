# Qwen2.5-VL 3B — Model Context

## What This Model Does

Qwen2.5-VL 3B Instruct — a compact vision-language model for image and video understanding. Processes images at dynamic resolution, supports OCR, chart reading, document parsing, visual localization (bounding boxes/points), structured output, and agentic computer/phone use. Uses dynamic FPS sampling for video and mRoPE for temporal understanding. 1x shared L40S GPU.

## Source Repo

**HuggingFace**: [Qwen/Qwen2.5-VL-3B-Instruct](https://huggingface.co/Qwen/Qwen2.5-VL-3B-Instruct)

Key recommendations from source:
- **Transformers**: Requires latest transformers (built from source) for `qwen2_5_vl` architecture
- **Flash attention**: HF recommends enabling `flash_attention_2` for better performance
- **Image resolution**: Configurable via `min_pixels` and `max_pixels` (default 4-16384 tokens per image)
- **Context length**: 32768 native, YaRN can extend further
- **License**: Apache-2.0

## How The Server Works

- **Pattern**: vLLM binary (Knative mode)
- **Container**: `vllm/vllm-openai:v0.8.4`
- **Weights**: Pre-downloaded to PVC by init container
- **Startup**: ~1-2 minutes cold start (3B BF16 weights, ~6GB)
- **Health**: vLLM's built-in `/v1/models` endpoint
- **Shared memory**: 4Gi emptyDir at `/dev/shm`
- **GPU**: Shared L40S on rack15-03 (time-sliced)
- **No tensor-parallel-size specified**: Defaults to 1, correct for single GPU

## What We Configured vs Source Recommendations

- **max-model-len=4096**: Very conservative vs 32K native. Limited by shared GPU.
- **limit-mm-per-prompt=image=4**: Limits to 4 images per request. Reasonable for shared GPU.
- **Missing --enforce-eager**: Not set, which is good — allows flash attention.

## Gateway Integration

- **ISVC name**: `qwen25-vl-3b` (matches API id, no ISVC_NAME_MAP entry)
- **MODEL_TYPE**: chat (not in MODEL_TYPES dict — defaults to chat)
- **CONTEXT_WINDOW**: 8192
- **MODEL_MAX_TOKENS**: 2048
- **REASONING_MODELS**: not listed
- **KSERVE_CUSTOM_MODELS**: yes — uses `/v1/` prefix
- **GPU_MODELS**: yes

## Deploy / Update / Test

```bash
# Deploy
kubectl apply -k models/qwen25-vl-3b/

# Check status
kubectl get pods -n models -l serving.kserve.io/inferenceservice=qwen25-vl-3b

# Logs
kubectl logs -n models -l serving.kserve.io/inferenceservice=qwen25-vl-3b -c kserve-container -f

# Test (internal — text only)
curl http://qwen25-vl-3b-predictor.models.svc.cluster.local:8080/v1/chat/completions \
  -d '{"model":"qwen25-vl-3b","messages":[{"role":"user","content":"Describe a sunset"}],"max_tokens":100}'

# Test (public — with image)
curl -X POST https://inference.kubeflow.vulcan.alliancecan.ca/serving/api/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{"model":"qwen25-vl-3b","messages":[{"role":"user","content":[{"type":"text","text":"What is in this image?"},{"type":"image_url","image_url":{"url":"data:image/jpeg;base64,..."}}]}],"max_tokens":100}'
```

## Known Issues / Optimization Opportunities

1. **Very small context (4096 vs 32K native)**: The model natively supports 32K context. 4096 is extremely conservative and limits multi-image and document understanding use cases.

2. **Very small max_tokens (2048)**: Gateway caps output at 2048 tokens. For OCR/document extraction tasks, this may truncate results.

3. **No video limit**: --limit-mm-per-prompt only covers images, not video. A video could generate many visual tokens and OOM.

4. **Missing --max-num-seqs**: Not set. On shared GPU, concurrent requests could cause VRAM contention.

5. **minReplicas=0**: Scale-to-zero enabled. Good for shared GPU.

6. **vLLM v0.8.4 pinned**: Good.

## Files

| File | Purpose |
|------|---------|
| `details.yaml` | ConfigMap with model metadata |
| `inferenceservice.yaml` | ISVC spec: vLLM container + PVC mount + shared memory |
| `kustomization.yaml` | Kustomize resources |
| `pvc.yaml` | Dedicated PVC (qwen-vl-3b-data) |

**IMPORTANT: When changing this model's deployment config (inferenceservice.yaml), update details.yaml to match.**
