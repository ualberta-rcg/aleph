# OceanGPT 30B — Model Context

## What This Model Does

OceanGPT 30B A3B MoE — a domain-specific ocean science LLM based on Qwen3 MoE architecture. 30.5B total params (128 experts, ~3B active per token). Trained on marine biology, oceanography, climate, and fisheries data in English and Chinese. 2x L40S GPUs. Includes a VRAM guard startup script that retries if GPU memory is insufficient.

## Source Repo

**HuggingFace**: [zjunlp/OceanGPT-basic-30B-A3B-Instruct](https://huggingface.co/zjunlp/OceanGPT-basic-30B-A3B-Instruct)

Key recommendations from source:
- **Framework**: Transformers with `device_map="auto"` and `torch_dtype="auto"`
- **No specific vLLM guidance provided** — community deploys with standard vLLM MoE settings
- **Max new tokens**: Example uses 4096
- **License**: Academic use — not a product, may have hallucination issues
- **Based on Qwen3 MoE**: Architecture is Qwen3, needs `--trust-remote-code`

## How The Server Works

- **Pattern**: vLLM binary via bash wrapper with VRAM guard (Knative mode)
- **Container**: `vllm/vllm-openai:v0.8.4`
- **Startup**: Bash script checks VRAM availability before starting vLLM; retries 6 times with 10s sleep
- **Weights**: Pre-downloaded to PVC by init container
- **Health**: vLLM's built-in `/v1/models` endpoint
- **Shared memory**: 16Gi emptyDir at `/dev/shm`
- **VLLM_WORKER_MULTIPROC_METHOD**: spawn

## What We Configured vs Source Recommendations

- **max-model-len=8192**: Very conservative. Qwen3 MoE supports much longer contexts. Limited due to 128-expert weights (~61GB) on 2x L40S.
- **tensor-parallel-size=2**: Correct for 2 GPUs with 128 experts.
- **gpu-memory-utilization=0.90**: Standard.
- **VRAM guard**: Startup script requires 25GB free per GPU before starting. Prevents crashes on shared nodes.

## Gateway Integration

- **ISVC name**: `oceangpt-30b` (matches API id, no ISVC_NAME_MAP entry)
- **MODEL_TYPE**: chat
- **CONTEXT_WINDOW**: 8192
- **MODEL_MAX_TOKENS**: 8000
- **REASONING_MODELS**: not listed
- **KSERVE_CUSTOM_MODELS**: yes — uses `/v1/` prefix
- **GPU_MODELS**: yes

## Deploy / Update / Test

```bash
# Deploy
kubectl apply -k models/oceangpt-30b/

# Check status
kubectl get pods -n models -l serving.kserve.io/inferenceservice=oceangpt-30b

# Logs
kubectl logs -n models -l serving.kserve.io/inferenceservice=oceangpt-30b -c kserve-container -f

# Test (internal)
curl http://oceangpt-30b-predictor.models.svc.cluster.local:8080/v1/chat/completions \
  -d '{"model":"oceangpt-30b","messages":[{"role":"user","content":"What causes ocean currents?"}],"max_tokens":200}'

# Test (public)
curl -X POST https://inference.kubeflow.vulcan.alliancecan.ca/serving/api/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{"model":"oceangpt-30b","messages":[{"role":"user","content":"What causes ocean currents?"}],"max_tokens":200}'
```

## Known Issues / Optimization Opportunities

1. **Very small context window (8192)**: Qwen3 MoE supports 32K+ natively. The 128-expert weights (~61GB) on 2x L40S limit KV cache room, but 8192 is very conservative. Could likely increase to 16384-32768.

2. **VRAM guard adds startup delay**: The startup script retries 6 times with 10s sleep. On dedicated nodes, this is unnecessary. On shared nodes, it prevents crashes but adds up to 60s delay.

3. **Data volume read-write**: The PVC is mounted read-write (no `readOnly: true`), unlike most other models. This is needed for vLLM to write temp files but risks accidental weight corruption.

4. **Missing --max-num-seqs**: Not set. For a MoE model on 2 GPUs, should limit concurrent requests.

5. **Hallucination risk**: Source explicitly warns about hallucination issues. Ocean science answers should be verified.

6. **Missing --enable-reasoning**: Qwen3-based model supports thinking mode but reasoning is not enabled. May improve answer quality for complex ocean science questions.

7. **minReplicas=0**: Scale-to-zero enabled. Cold start ~5 minutes.

## Files

| File | Purpose |
|------|---------|
| `details.yaml` | ConfigMap with model metadata |
| `inferenceservice.yaml` | ISVC spec: vLLM with VRAM guard + PVC mount + shared memory |
| `kustomization.yaml` | Kustomize resources |
| `pvc.yaml` | Dedicated PVC (oceangpt-30b-data) |

**IMPORTANT: When changing this model's deployment config (inferenceservice.yaml), update details.yaml to match.**
