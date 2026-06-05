# AstroSage-8B — Model Context

## What This Model Does

AstroSage-8B — Llama-3.1-8B fine-tuned on astronomy and astrophysics data. Trained on 250K+ arXiv astronomy papers (2007-2024) and 8.8M curated QA pairs. Achieves 80.9% on astronomy benchmarks, comparable to GPT-4o (80.4%). Expert at astrophysics Q&A, observation planning, literature review, and data analysis assistance. Uses a custom FastAPI server (NOT vLLM). 1x shared L40S GPU.

## Source Repo

**HuggingFace**: [AstroMLab/AstroSage-8B](https://huggingface.co/AstroMLab/AstroSage-8B)

Key recommendations from source:
- **Framework**: HuggingFace Transformers with `device_map="auto"`, `torch_dtype=torch.bfloat16`
- **Inference**: Simple `model.generate()` with `do_sample=True`, `max_new_tokens=128`
- **Architecture**: Based on Meta-Llama-3.1-8B (CPT + SFT + model merge)
- **Training data**: 3.3B tokens pre-training + 2.0B tokens fine-tuning
- **License**: Llama 3.1 Community License
- **Limitations**: Training data cutoff January 2024, hallucinations possible

## How The Server Works

- **Pattern**: Custom FastAPI server (NOT vLLM)
- **Container**: `python:3.11-slim` with venv on PVC
- **Server code**: Embedded ConfigMap (`astrosage-server`) mounted at `/app/server.py`
- **Init container**: Creates venv with torch, transformers, fastapi, uvicorn; downloads model weights
- **Startup**: ~3-5 minutes cold start (venv setup + loading 8B BF16 weights)
- **Health**: Custom `/health` endpoint (not `/v1/models`)
- **No shared memory**: No `/dev/shm` emptyDir (not needed for single-GPU transformers)
- **NFS PVC**: Uses NFS (ReadWriteMany) instead of block storage

## What We Configured vs Source Recommendations

- **Custom server**: We built a FastAPI wrapper around HuggingFace `pipeline("text-generation")`. Not using vLLM means slower inference but simpler setup.
- **max_tokens default=512**: Server defaults to 512, which is very low. Source examples use 128 but the model can generate much longer.
- **No streaming**: The custom server does not support SSE streaming.
- **No usage tracking**: Response does not include `usage` field (token counts).

## Gateway Integration

- **ISVC name**: `astrosage` (matches API id, no ISVC_NAME_MAP entry)
- **MODEL_TYPE**: chat
- **CONTEXT_WINDOW**: not listed in CONTEXT_WINDOWS (no truncation by gateway)
- **MODEL_MAX_TOKENS**: not listed (falls back to DEFAULT_MAX_TOKENS=8192)
- **REASONING_MODELS**: not listed
- **KSERVE_CUSTOM_MODELS**: yes — uses `/v1/` prefix
- **GPU_MODELS**: yes

## Deploy / Update / Test

```bash
# Deploy
kubectl apply -k models/astrosage/

# Check status
kubectl get pods -n models -l serving.kserve.io/inferenceservice=astrosage

# Logs
kubectl logs -n models -l serving.kserve.io/inferenceservice=astrosage -c kserve-container -f

# Test (internal)
curl http://astrosage-predictor.models.svc.cluster.local:8080/v1/chat/completions \
  -d '{"model":"astrosage","messages":[{"role":"user","content":"What are the main components of a galaxy?"}],"max_tokens":200}'

# Test (public)
curl -X POST https://inference.kubeflow.vulcan.alliancecan.ca/serving/api/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{"model":"astrosage","messages":[{"role":"user","content":"What are the main components of a galaxy?"}],"max_tokens":200}'
```

## Known Issues / Optimization Opportunities

1. **Not using vLLM**: The custom transformers-based server is significantly slower than vLLM for inference. Migrating to vLLM would provide 3-10x throughput improvement, proper OpenAI API compatibility, streaming, and usage tracking.

2. **No streaming support**: The custom server does not support SSE streaming, which breaks many client expectations for an OpenAI-compatible API.

3. **No usage/token counting**: Responses lack the `usage` field, making cost tracking impossible.

4. **Health endpoint mismatch**: Uses `/health` instead of `/v1/models`. Gateway health checks may not work correctly.

5. **NFS storage (ReadWriteMany)**: Uses NFS instead of block storage. NFS has higher latency and lower throughput, slowing model loading. Other models use ReadWriteOnce block PVCs.

6. **Embedded ConfigMap for server code**: The server.py is embedded in inferenceservice.yaml as a ConfigMap. This makes it hard to edit and version separately.

7. **No CONTEXT_WINDOWS entry**: Not listed in gateway CONTEXT_WINDOWS dict, so the gateway won't truncate long prompts.

8. **No MODEL_MAX_TOKENS entry**: Falls back to DEFAULT_MAX_TOKENS=8192. Should be explicitly set.

9. **Missing kustomization.yaml**: The model directory lacks a kustomization.yaml, requiring direct `kubectl apply -f` instead of `kubectl apply -k`.

10. **Data cutoff January 2024**: Model is not aware of astronomy developments after that date.

## Files

| File | Purpose |
|------|---------|
| `details.yaml` | ConfigMap with model metadata |
| `inferenceservice.yaml` | ISVC spec + embedded ConfigMap (server.py) + PVC — all-in-one file |
| `pvc.yaml` | NFS-based PVC (astrosage-data) — also duplicated inside inferenceservice.yaml |

**IMPORTANT: When changing this model's deployment config (inferenceservice.yaml), update details.yaml to match.**
