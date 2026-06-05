# MedGemma 27B IT — Model Context

## What This Model Does

Google MedGemma 27B instruction-tuned multimodal model for medical AI. Fine-tuned from Gemma 3 on medical text, chest X-rays, dermatology images, ophthalmology (fundus), and histopathology slides. Accepts text and base64 images. Based on Gemma 3 architecture with a SigLIP image encoder pre-trained on de-identified medical data. 128K context. Uses 2 GPUs.

## Source Repo

**HuggingFace**: [google/medgemma-27b-it](https://huggingface.co/google/medgemma-27b-it)

Key recommendations from source:
- **vLLM**: Requires `--trust-remote-code` and `--limit-mm-per-prompt` for image inputs
- **dtype**: bfloat16 recommended
- **Context length**: At least 128K supported
- **Max output tokens**: 8192 recommended
- **License**: Health AI Developer Foundations Terms of Use (NOT Apache-2.0)
- **Not evaluated for multi-image tasks** — primarily tested on single-image inputs

## How The Server Works

- **Pattern**: vLLM binary (Knative mode)
- **Container**: `vllm/vllm-openai:v0.8.4`
- **Weights**: Pre-downloaded to PVC by init container
- **Startup**: ~3-5 minutes cold start (loading 27B BF16 weights into 2 GPUs)
- **Health**: vLLM's built-in `/v1/models` endpoint
- **Shared memory**: 16Gi emptyDir at `/dev/shm` (required for tensor parallelism)
- **VLLM_WORKER_MULTIPROC_METHOD**: spawn (required for multi-GPU)

## What We Configured vs Source Recommendations

- **max-model-len=32768**: We limit to 32K despite model supporting 128K. Reason: 128K context on 2x L40S (92GB total VRAM) would OOM with a 27B BF16 model (~54GB weights alone). 32K is a safe limit.
- **limit-mm-per-prompt=image=5**: Limits to 5 images per request, reasonable for clinical use.
- **gpu-memory-utilization=0.92**: Slightly aggressive but fine for this model size on 2x L40S.

## Gateway Integration

- **ISVC name**: `medgemma-27b-it` (matches API id, no ISVC_NAME_MAP entry)
- **MODEL_TYPE**: chat
- **CONTEXT_WINDOW**: 120000 (gateway value; actual deployed at 32768)
- **MODEL_MAX_TOKENS**: 8000
- **REASONING_MODELS**: not listed
- **KSERVE_CUSTOM_MODELS**: yes — uses `/v1/` prefix
- **GPU_MODELS**: yes

## Deploy / Update / Test

```bash
# Deploy
kubectl apply -k models/medgemma-27b-it/

# Check status
kubectl get pods -n models -l serving.kserve.io/inferenceservice=medgemma-27b-it

# Logs
kubectl logs -n models -l serving.kserve.io/inferenceservice=medgemma-27b-it -c kserve-container -f

# Test (internal — text only)
curl http://medgemma-27b-it-predictor.models.svc.cluster.local:8080/v1/chat/completions \
  -d '{"model":"medgemma-27b-it","messages":[{"role":"user","content":"What are signs of bacterial pneumonia?"}],"max_tokens":200}'

# Test (public — with image)
curl -X POST https://inference.kubeflow.vulcan.alliancecan.ca/serving/api/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{"model":"medgemma-27b-it","messages":[{"role":"user","content":[{"type":"text","text":"Describe this X-ray"},{"type":"image_url","image_url":{"url":"data:image/jpeg;base64,..."}}]}],"max_tokens":200}'
```

## Known Issues / Optimization Opportunities

1. **CONTEXT_WINDOW mismatch**: Gateway says 120000 but actual max-model-len is 32768. This means the gateway will not truncate prompts correctly — a 100K token prompt would pass through gateway truncation but fail at vLLM. Should align gateway value with deployed value.

2. **Missing --max-num-seqs**: Not set, vLLM uses default. For a 27B model on 2 GPUs, consider setting to 4-8 to prevent OOM under concurrent load.

3. **License concern**: Deployed under Health AI Developer Foundations Terms of Use, not Apache-2.0. Verify compliance with those terms.

4. **Not in REASONING_MODELS**: Correct — this is not a reasoning model.

5. **minReplicas=0**: Scale-to-zero enabled. Cold start takes ~3-5 minutes.

6. **vLLM v0.8.4 pinned**: Good — pinned version, not `latest`.

## Files

| File | Purpose |
|------|---------|
| `details.yaml` | ConfigMap with model metadata |
| `inferenceservice.yaml` | ISVC spec: vLLM container + PVC mount + shared memory |
| `kustomization.yaml` | Kustomize resources |
| `pvc.yaml` | Dedicated PVC (medgemma-27b-it) |

**IMPORTANT: When changing this model's deployment config (inferenceservice.yaml), update details.yaml to match.**
