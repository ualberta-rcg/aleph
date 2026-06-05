# Phi-4 Reasoning — Model Context

## What This Model Does

Microsoft Phi-4-reasoning 14B dense Transformer — a chain-of-thought reasoning model fine-tuned from Phi-4. Excels at math, science, and coding. Outputs a reasoning (Thought) block followed by a Solution block. 32K context window. 1x L40S GPU.

## Source Repo

**HuggingFace**: [microsoft/Phi-4-reasoning](https://huggingface.co/microsoft/Phi-4-reasoning)

Key recommendations from source:
- **Sampling**: temperature=0.8, top_k=50, top_p=0.95, do_sample=True — MUST use sampling, DO NOT use greedy decoding
- **max_new_tokens**: 32768 for complex queries, 4096+ for simpler ones
- **vLLM**: `vllm serve microsoft/Phi-4-reasoning --enable-reasoning --reasoning-parser deepseek_r1`
- **System prompt**: HF recommends a specific detailed system prompt about structured reasoning
- **License**: MIT
- **Context length**: 32K tokens

## How The Server Works

- **Pattern**: vLLM binary (Knative mode)
- **Container**: `vllm/vllm-openai:v0.8.4`
- **Weights**: Pre-downloaded to PVC by init container
- **Startup**: ~2-3 minutes cold start (loading 14B BF16 weights, ~28GB)
- **Health**: vLLM's built-in `/v1/models` endpoint
- **Shared memory**: 8Gi emptyDir at `/dev/shm`
- **Reasoning**: `--enable-reasoning --reasoning-parser=deepseek_r1` properly configured

## What We Configured vs Source Recommendations

- **max-model-len=32768**: Matches native context window — good.
- **gpu-memory-utilization=0.90**: Standard, adequate for 14B on 46GB L40S.
- **Reasoning flags**: Properly configured with `--enable-reasoning --reasoning-parser=deepseek_r1`.
- **Missing --max-num-seqs**: Not set, could limit under load.

## Gateway Integration

- **ISVC name**: `phi-4-reasoning` (matches API id, no ISVC_NAME_MAP entry)
- **MODEL_TYPE**: chat
- **CONTEXT_WINDOW**: 32768
- **MODEL_MAX_TOKENS**: 16000
- **REASONING_MODELS**: yes — gateway disables thinking for title/tags/followups
- **KSERVE_CUSTOM_MODELS**: yes — uses `/v1/` prefix
- **GPU_MODELS**: yes

## Deploy / Update / Test

```bash
# Deploy
kubectl apply -k models/phi-4-reasoning/

# Check status
kubectl get pods -n models -l serving.kserve.io/inferenceservice=phi-4-reasoning

# Logs
kubectl logs -n models -l serving.kserve.io/inferenceservice=phi-4-reasoning -c kserve-container -f

# Test (internal)
curl http://phi-4-reasoning-predictor.models.svc.cluster.local:8080/v1/chat/completions \
  -d '{"model":"phi-4-reasoning","messages":[{"role":"user","content":"What is the derivative of x^2?"}],"max_tokens":2048}'

# Test (public)
curl -X POST https://inference.kubeflow.vulcan.alliancecan.ca/serving/api/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{"model":"phi-4-reasoning","messages":[{"role":"user","content":"What is the derivative of x^2?"}],"max_tokens":2048}'
```

## Known Issues / Optimization Opportunities

1. **Missing --max-num-seqs**: Not set, vLLM uses default. Consider setting to 4-8 for a 14B model on a single GPU to prevent OOM under concurrent load.

2. **MODEL_MAX_TOKENS=16000 vs HF recommendation 32768**: The gateway caps output at 16K tokens, but HF recommends 32K for complex queries. For math olympiad-level problems, this cap may truncate the reasoning chain before it reaches a conclusion.

3. **English only**: Model is primarily trained on English text. Non-English performance will be significantly worse.

4. **minReplicas=0**: Scale-to-zero enabled. Cold start ~2-3 minutes.

5. **vLLM v0.8.4 pinned**: Good — pinned version.

## Files

| File | Purpose |
|------|---------|
| `details.yaml` | ConfigMap with model metadata |
| `inferenceservice.yaml` | ISVC spec: vLLM container + PVC mount + shared memory |
| `kustomization.yaml` | Kustomize resources |
| `pvc.yaml` | Dedicated PVC (phi-4-reasoning-data) |

**IMPORTANT: When changing this model's deployment config (inferenceservice.yaml), update details.yaml to match.**
