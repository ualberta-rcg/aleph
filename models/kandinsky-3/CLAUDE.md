# Kandinsky-3 -- Model Context

## What This Model Does

Kandinsky-3 (ai-forever/Kandinsky-3) is a text-to-image diffusion model by Sber AI. Generates images from text prompts and supports image-to-image editing. Uses HuggingFace diffusers `AutoPipelineForText2Image` and `AutoPipelineForImage2Image` with fp16 variant. Deployed via Ray Serve (not KServe) with a dedicated head pod (no GPU) + GPU worker architecture. OpenAI-compatible `/v1/images/generations` endpoint.

## Source Repo

**HuggingFace**: [ai-forever/Kandinsky-3](https://huggingface.co/ai-forever/Kandinsky-3)

- **License**: Apache-2.0
- **Architecture**: Latent diffusion model (diffusers-based)
- **Recommended**: diffusers `AutoPipelineForText2Image` with `variant="fp16"`, `torch_dtype=torch.float16`
- **Model size**: ~5B parameters (large UNet + text encoders)

## How The Server Works

- **Pattern**: Ray Serve (NOT KServe InferenceService)
- **K8s resource**: `RayService` (ray.io/v1) instead of InferenceService
- **Image**: `rayproject/ray:2.44.1-py311-gpu` (not python:3.11-slim)
- **Architecture**: Two Ray deployments:
  - `APIIngress` (head pod, no GPU): FastAPI app that handles HTTP routing
  - `Kandinsky3` (GPU worker, 1x L40S): Loads diffusers pipelines, runs inference
- **PVC**: `kandinsky-3-data` (50Gi, NFS) -- stores model weights (must be pre-populated via download-job.yaml)
- **Health**: `/healthz` on the ingress
- **GPU**: 1x L40S (dedicated, not time-sliced)
- **CPU offload**: `enable_model_cpu_offload()` for memory management
- **Dependencies**: Declared in Ray Serve `runtime_env` (pip list in rayservice.yaml)
- **Service**: Ray Serve exposes port 8000; K8s Service `kandinsky-serve-svc` (auto-created by Ray operator)

## Our Config vs Source Recommendations

| Aspect | Source | Our Config | Notes |
|--------|--------|-----------|-------|
| Precision | fp16 | fp16 (variant="fp16") | Correct |
| Pipeline | AutoPipelineForText2Image | Same + AutoPipelineForImage2Image | Both supported |
| Image size | Variable | 1024x1024 default | Configurable |
| Steps | 25-50 | 25 default, 50 for "hd" quality | Reasonable |
| Guidance | 4.0 default | 4.0 default | Matches source |
| Max images | Variable | 4 per request | Safety limit |

## Gateway Integration

- **NOT an InferenceService**: This is a Ray Serve deployment
- **Registered in EXTRA_MODELS**: `{"backend": "http://kandinsky-serve-svc.models.svc.cluster.local:8000", "health_path": "/v1/models"}`
- **MODEL_TYPE**: image
- **GPU_MODELS**: yes
- **Always-on**: minReplicas=1, maxReplicas=1 (Ray worker)
- **NOT in KSERVE_CUSTOM_MODELS**: Handled via EXTRA_MODELS routing

## Deploy / Update / Test

```bash
# Deploy (requires download-job to have populated PVC first)
kubectl apply -k models/kandinsky-3/

# Force update
kubectl apply --server-side --force-conflicts -k models/kandinsky-3/

# Check status
kubectl get rayservice -n models kandinsky
kubectl get pods -n models -l ray.io/cluster=kandinsky

# Logs
kubectl logs -n models -l ray.io/cluster=kandinsky -c ray-worker -f

# Test (public)
curl -X POST https://inference.kubeflow.vulcan.alliancecan.ca/serving/api/v1/images/generations \
  -H "Content-Type: application/json" \
  -d '{"model":"kandinsky-3","prompt":"a cat sitting on a windowsill","n":1,"size":"1024x1024"}'
```

## Known Issues / Optimization Opportunities

1. **Always-on GPU**: minReplicas=1 means a dedicated L40S is permanently allocated. Ray Serve does not natively support scale-to-zero like KServe/Knative.

2. **Large PVC**: 50Gi PVC is needed for the model weights. The download-job.yaml must be run before deploying the RayService.

3. **CPU offload overhead**: `enable_model_cpu_offload()` moves model weights between CPU and GPU for each request, adding latency. Using full GPU residency would be faster but requires more VRAM.

4. **Ray Serve complexity**: More complex than KServe deployments. Requires Ray operator to be installed and running.

5. **No init container for weights**: Model weights must be pre-populated via a separate download-job.yaml. If PVC is empty, the deployment will fail.

6. **Single replica**: maxReplicas=1 means no horizontal scaling. If throughput is needed, would need to increase replicas and GPU allocation.

7. **ConfigMap mounted as subPath**: `serve-code` ConfigMap mounted as subPath files, which means ConfigMap changes require pod restart to take effect.

## Files

| File | Purpose |
|------|---------|
| `details.yaml` | ConfigMap with model metadata |
| `rayservice.yaml` | Ray Serve config (head + worker specs) |
| `serve.py` | Ray Serve application code (APIIngress + Kandinsky3 deployments) |
| `kustomization.yaml` | Kustomize resources + configMapGenerator |
| `pvc.yaml` | Dedicated PVC (kandinsky-3-data, 50Gi NFS) |
| `download-job.yaml` | One-time job to download model weights to PVC |
| `README.md` | Original documentation |

**IMPORTANT: When changing this model's deployment config (rayservice.yaml, serve.py), update details.yaml to match.**
