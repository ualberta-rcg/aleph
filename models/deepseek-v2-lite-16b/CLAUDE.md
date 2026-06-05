# DeepSeek V2 Lite 16B — Model Context

## What This Model Does

DeepSeek V2 Lite 16B MoE Chat — a compact MoE model using innovative Multi-head Latent Attention (MLA) and DeepSeekMoE architecture. 15.7B total params, 2.4B active per token (2 shared + 64 routed experts, 6 activated). Strong at reasoning, code, and bilingual (English/Chinese) tasks. 24K context. 1x L40S GPU.

## Source Repo

**HuggingFace**: [deepseek-ai/DeepSeek-V2-Lite-Chat](https://huggingface.co/deepseek-ai/DeepSeek-V2-Lite-Chat)

Key recommendations from source:
- **Hardware**: 40GB GPU required for BF16 inference (1 GPU)
- **vLLM example**: `LLM(model=model_name, tensor_parallel_size=1, max_model_len=8192, trust_remote_code=True, enforce_eager=True)`
- **Sampling**: temperature=0.3, max_tokens=256 in their example
- **License**: MIT (code), Model License (weights, supports commercial use)

## How The Server Works

- **Pattern**: vLLM binary (Knative mode)
- **Container**: `vllm/vllm-openai:v0.7.2`
- **Weights**: Pre-downloaded to PVC by init container
- **Startup**: ~2-3 minutes cold start (16B BF16 weights, ~32GB)
- **Health**: vLLM's built-in `/v1/models` endpoint
- **Shared memory**: 16Gi emptyDir at `/dev/shm`
- **VLLM_WORKER_MULTIPROC_METHOD**: spawn

## What We Configured vs Source Recommendations

- **max-model-len=32768**: We use 32K, exceeding HF's example of 8192. The model supports ~24K natively (with YaRN could go longer). 32K may cause issues for very long sequences.
- **--enforce-eager**: Matches HF recommendation. MLA architecture may require this.
- **gpu-memory-utilization=0.90**: Standard.
- **tensor-parallel-size=1**: Correct for single GPU.

## Gateway Integration

- **ISVC name**: `deepseek-v2-lite-16b` (matches API id, no ISVC_NAME_MAP entry)
- **MODEL_TYPE**: chat
- **CONTEXT_WINDOW**: 24000
- **MODEL_MAX_TOKENS**: 8000
- **REASONING_MODELS**: not listed
- **KSERVE_CUSTOM_MODELS**: yes — uses `/v1/` prefix
- **GPU_MODELS**: yes

## Deploy / Update / Test

```bash
# Deploy
kubectl apply -k models/deepseek-v2-lite-16b/

# Check status
kubectl get pods -n models -l serving.kserve.io/inferenceservice=deepseek-v2-lite-16b

# Logs
kubectl logs -n models -l serving.kserve.io/inferenceservice=deepseek-v2-lite-16b -c kserve-container -f

# Test (internal)
curl http://deepseek-v2-lite-16b-predictor.models.svc.cluster.local:8080/v1/chat/completions \
  -d '{"model":"deepseek-v2-lite-16b","messages":[{"role":"user","content":"Write quicksort in C++"}],"max_tokens":200}'

# Test (public)
curl -X POST https://inference.kubeflow.vulcan.alliancecan.ca/serving/api/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{"model":"deepseek-v2-lite-16b","messages":[{"role":"user","content":"Write quicksort in C++"}],"max_tokens":200}'
```

## Known Issues / Optimization Opportunities

1. **max-model-len=32768 exceeds native context**: The model's native context is ~24K (trained with 4K max sequence length, extended with YaRN). Setting 32768 may produce degraded output for very long sequences. Consider aligning with gateway CONTEXT_WINDOWS value of 24000.

2. **Very old vLLM version (v0.7.2)**: This is significantly outdated (current is v0.8.4+). MLA support has improved in newer versions. Should upgrade to at least v0.8.4.

3. **--enforce-eager**: Disables flash attention. This was required for MLA in older vLLM versions. Newer versions may support flash attention for DeepSeek V2, which would improve throughput.

4. **minReplicas=1**: Always-on deployment. Consider scale-to-zero for cost savings.

5. **Missing --max-num-seqs**: Not set. Should limit for single GPU deployment.

6. **CONTEXT_WINDOW mismatch**: Gateway says 24000 but max-model-len is 32768. Should align.

## Files

| File | Purpose |
|------|---------|
| `details.yaml` | ConfigMap with model metadata |
| `inferenceservice.yaml` | ISVC spec: vLLM container + PVC mount + shared memory |
| `kustomization.yaml` | Kustomize resources |
| `pvc.yaml` | Dedicated PVC (deepseek-v2-lite-16b) |

**IMPORTANT: When changing this model's deployment config (inferenceservice.yaml), update details.yaml to match.**
