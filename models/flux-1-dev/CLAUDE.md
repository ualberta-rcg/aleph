# flux-1-dev — Model Context

FLUX.1-dev (`black-forest-labs/FLUX.1-dev`), **12B rectified-flow transformer** text-to-image
(Black Forest Labs) + T5-XXL & CLIP-L text encoders + VAE, bf16 via diffusers `FluxPipeline`.
Text-to-image + image-to-image (img2img).

- **GATED model** — requires the `hf-token` secret (access already granted on the HF account).
- **License: FLUX.1-dev Non-Commercial License** (NOT open/commercial — see model card).

## Serving (standard KServe custom predictor — wired exactly like kandinsky-3)

KServe InferenceService custom predictor (diffusers FastAPI server) so it behaves like every
other model: gateway-discovered, reachable at `flux-1-dev-predictor`, Knative scale-to-zero on
the cluster 5m/15m policy, **zero gateway changes**.

- Single file `inferenceservice.yaml` holds both the `flux-1-dev-server` ConfigMap (FastAPI/
  uvicorn `server.py`) and the InferenceService. Endpoints: `POST /v1/images/generations`,
  `POST /v1/images/edits`, `GET /v1/models`, `GET /health` (503 until the pipeline is resident).
- **Whole L40S**: `nvidia.com/gpu: 1` with **no `nvidia.com/gpumem`** so HAMi binds a tenant-free
  physical card (full 48 GB, no vGPU interception). FLUX bf16 is ~34 GB resident (12B transformer
  + T5-XXL ~9.5 GB + CLIP + VAE) — full residency fits, no CPU offload, so it's fast.
- **Deps + weights staged once onto the NFS PVC** by the init container: venv `/data/venv`,
  weights `/data/flux-1-dev`, sentinel `/data/.flux-1-dev-ready-v1`. Download skips the ~24 GB
  single-file originals (`flux1-dev.safetensors`, `ae.safetensors`) — diffusers loads the sharded
  subfolders. PVC is OneFS/NFS (survives WW reprovision; no re-pip on cold start).
- Scaling: `minReplicas 0`, `maxReplicas 3`, `scaleMetric concurrency`, `scaleTarget 1`;
  `scale-down-delay 5m` + `scale-to-zero-pod-retention-period 15m`.

## Defaults (from the HF model card / diffusers)

`num_inference_steps 50`, `guidance_scale 3.5`, `max_sequence_length 512`, 1024x1024. FLUX.1-dev
is guidance-distilled: `negative_prompt` only applies when `true_cfg_scale > 1`. img2img
`strength` default 0.6.

## Gateway integration

Card `details.yaml` (`flux-1-dev-details`, v2 Template B / custom server): `type: image`,
standard `routing.k8s_name: flux-1-dev`. The generic catch-all `/v1/{path}` handler forwards
`/v1/images/generations` through the knative-local-gateway like any other model.

## Deploy / test

```bash
kubectl apply -f models/flux-1-dev/pvc.yaml
kubectl apply -f models/flux-1-dev/inferenceservice.yaml
kubectl apply -f models/flux-1-dev/details.yaml

curl -X POST https://inference.kubeflow.vulcan.alliancecan.ca/serving/api/v1/images/generations \
  -H "Content-Type: application/json" \
  -d '{"model":"flux-1-dev","prompt":"a cat holding a sign that says hello world","n":1,"size":"1024x1024"}'
```

## Files

| File | Purpose |
|------|---------|
| `inferenceservice.yaml` | ConfigMap `flux-1-dev-server` (FastAPI diffusers `server.py`) + the KServe InferenceService |
| `details.yaml` | Model card ConfigMap (`flux-1-dev-details`, v2 schema, `model-details: "true"`) |
| `pvc.yaml` | Dedicated PVC (`flux-1-dev-data`, NFS `nfs-models`) for the venv + weights |

**IMPORTANT: when changing the server or ISVC config, update `details.yaml` to match.**
