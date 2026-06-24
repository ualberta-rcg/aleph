# sd3-medium — Model Context

Stable Diffusion 3 Medium (`stabilityai/stable-diffusion-3-medium`), **2B MMDiT** text-to-image
(Stability AI) + three text encoders (OpenCLIP-ViT/G, CLIP-ViT/L, T5-XXL) + VAE, fp16 via
diffusers `StableDiffusion3Pipeline`. Text-to-image + image-to-image (img2img).

- **GATED model** — requires the `hf-token` secret (HF account access granted).
- **License: Stability AI Community License** (free for research/non-commercial and commercial use
  under $1M annual revenue; Enterprise license required above that).
- diffusers loads the **`stable-diffusion-3-medium-diffusers`** repo (not the original-format one).

## Serving (standard KServe custom predictor — wired exactly like kandinsky-3 / flux-1-dev)

KServe InferenceService custom predictor (diffusers FastAPI server): gateway-discovered,
reachable at `sd3-medium-predictor`, Knative scale-to-zero on the cluster 5m/15m policy,
**zero gateway changes**.

- Single file `inferenceservice.yaml` holds both the `sd3-medium-server` ConfigMap (FastAPI/
  uvicorn `server.py`) and the InferenceService. Endpoints: `POST /v1/images/generations`,
  `POST /v1/images/edits`, `GET /v1/models`, `GET /health` (503 until the pipeline is resident).
- **HAMi vGPU slice** (not a whole card): `nvidia.com/gpu: 1` + `nvidia.com/gpumem: 24576`. fp16
  SD3-medium is ~16 GB resident (2B MMDiT + T5-XXL + CLIP-G/L + VAE), so a 24 GB slice fits and
  leaves the rest of the L40S shareable.
- **Deps + weights staged once onto the NFS PVC** by the init container: venv `/data/venv`,
  weights `/data/sd3-medium`, sentinel `/data/.sd3-medium-ready-v1`. Survives WW reprovision; no
  re-pip on cold start.
- Scaling: `minReplicas 0`, `maxReplicas 3`, `scaleMetric concurrency`, `scaleTarget 1`, 5m/15m.

## Defaults (from the HF model card / diffusers)

`num_inference_steps 28`, `guidance_scale 7.0`, `max_sequence_length 256` (T5; up to 512),
1024x1024. SD3 uses real CFG, so `negative_prompt` is honored. img2img `strength` default 0.6.

## Gateway integration

Card `details.yaml` (`sd3-medium-details`, v2 Template B / custom server): `type: image`,
standard `routing.k8s_name: sd3-medium`. The generic catch-all `/v1/{path}` handler forwards
`/v1/images/generations` through the knative-local-gateway like any other model.

## Deploy / test

```bash
kubectl apply -f models/sd3-medium/pvc.yaml
kubectl apply -f models/sd3-medium/inferenceservice.yaml
kubectl apply -f models/sd3-medium/details.yaml

curl -X POST https://inference.kubeflow.vulcan.alliancecan.ca/serving/api/v1/images/generations \
  -H "Content-Type: application/json" \
  -d '{"model":"sd3-medium","prompt":"a cat holding a sign that says hello world","n":1,"size":"1024x1024"}'
```

## Files

| File | Purpose |
|------|---------|
| `inferenceservice.yaml` | ConfigMap `sd3-medium-server` (FastAPI diffusers `server.py`) + the KServe InferenceService |
| `details.yaml` | Model card ConfigMap (`sd3-medium-details`, v2 schema, `model-details: "true"`) |
| `pvc.yaml` | Dedicated PVC (`sd3-medium-data`, NFS `nfs-models`) for the venv + weights |

**IMPORTANT: when changing the server or ISVC config, update `details.yaml` to match.**
