# kandinsky-3 — Model Context

Kandinsky 3.0 (`kandinsky-community/kandinsky-3`), ~11.9B text-to-image diffusion model
(Sber AI): Flan-UL2 text encoder 8.6B + Latent Diffusion U-Net 3B + Sber-MoVQGAN 267M.
fp16 via diffusers `AutoPipeline`. Text-to-image + image-to-image (img2img).

## Serving (standard KServe custom predictor)

Converted from a RayService to a **KServe InferenceService** so it behaves like every other
model on the cluster — discovered by the gateway, reachable at `kandinsky-3-predictor`,
Knative scale-to-zero with the cluster 5m/15m policy, **zero gateway changes**. Wiring
mirrors `gpt-oss-120b`; the custom-server shape mirrors `surya`.

- Single file `inferenceservice.yaml` holds both the `kandinsky-3-server` ConfigMap (the
  FastAPI/uvicorn `server.py`) and the InferenceService.
- Custom predictor: `python:3.11` container runs `/data/venv/bin/python /app/server.py` on
  port 8080. Endpoints: `POST /v1/images/generations`, `POST /v1/images/edits`,
  `GET /v1/models`, `GET /health` (returns 503 until the pipeline is resident so Knative
  gates traffic on real readiness).
- **Deps + weights staged once onto the NFS PVC** by the init container: venv at
  `/data/venv`, weights at `/data/kandinsky-3`, guarded by `/data/.kandinsky-ready-v1`.
  PVC is OneFS/NFS (not node-local), so this survives Warewulf reprovisioning **and** avoids
  re-pip on every cold start (the main cost that made the Ray version slow).
- GPU: single L40S HAMi vGPU slice — `nvidia.com/gpu: 1` + `nvidia.com/gpumem: 40960` (TP=1
  fractional recipe per `models/CLAUDE.md`).
- Scaling: `minReplicas 0`, `maxReplicas 3`, `scaleMetric concurrency`, `scaleTarget 1`;
  `scale-down-delay 5m` + `scale-to-zero-pod-retention-period 15m`.

## Gateway integration

- Card `details.yaml` (`kandinsky-3-details`, v2 schema — Template B / custom server):
  `type: image`, `routing.k8s_name: kandinsky-3` (standard Knative-host routing, no special
  backend). The generic catch-all `/v1/{path}` handler forwards `/v1/images/generations`
  through the knative-local-gateway like any other model.
- Scale-to-zero cold-start guard, `/v1/models` listing, and resource footprint all come for
  free from the gateway's existing KServe/Knative code.

## Deploy / update / test

```bash
# 1. PVC  2. ISVC (creates the server ConfigMap + InferenceService; init stages venv+weights)
kubectl apply -f models/kandinsky-3/pvc.yaml
kubectl apply -f models/kandinsky-3/inferenceservice.yaml
kubectl apply -f models/kandinsky-3/details.yaml

# status / logs
kubectl get isvc,pods -n models | grep kandinsky-3
kubectl logs -n models -l serving.kserve.io/inferenceservice=kandinsky-3 -c kserve-container -f

# test externally via gateway VIP + Tyk auth
GW_URL=http://<GATEWAY_VIP> TYK_KEY=<key> python3 models/kandinsky-3/test.py

# or a direct image request through the gateway VIP
curl -X POST http://<GATEWAY_VIP>/v1/images/generations \
  -H "Authorization: Bearer <key>" -H "Content-Type: application/json" \
  -d '{"model":"kandinsky-3","prompt":"a red fox in snow","n":1,"size":"1024x1024"}'
```

Editing `server.py` (inside `inferenceservice.yaml`) requires a new revision / pod restart
to take effect (mounted as a subPath ConfigMap). Bump the `SENTINEL` suffix if you change
the venv dependency set so the init container rebuilds it.

## Files

| File | Purpose |
|------|---------|
| `inferenceservice.yaml` | ConfigMap `kandinsky-3-server` (FastAPI diffusers `server.py`) + the KServe InferenceService |
| `details.yaml` | Model card ConfigMap (`kandinsky-3-details`, v2 schema, `model-details: "true"`) |
| `pvc.yaml` | Dedicated PVC (`kandinsky-3-data`, NFS `nfs-models`) for the venv + weights |

No `kustomization.yaml`, no RayService, no separate download job — plain `kubectl apply -f`
per the repo convention (`models/CLAUDE.md`).

**IMPORTANT: when changing the server or ISVC config, update `details.yaml` to match.**
