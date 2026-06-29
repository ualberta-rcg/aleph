# kandinsky-3-1-flash

Kandinsky 3.1 **Flash** — the distilled fast-sampling text-to-image variant of
AI Forever / Sber's Kandinsky 3.1, served as an OpenAI-compatible image model
using the upstream `ai-forever/Kandinsky-3` Python package and the
`ai-forever/Kandinsky3.1` Hugging Face weights.

This is the fast text-to-image deployment. For img2img and inpainting (the full
feature set that ran on the old Ray setup), use the separate full-featured
`kandinsky-3-1` deployment.

## Runtime

- KServe custom predictor in namespace `models`
- Runtime source staged from `https://github.com/ai-forever/Kandinsky-3`
- Weights staged from `https://huggingface.co/ai-forever/Kandinsky3.1`
  (`weights/kandinsky3_flash.pt`, `weights/movq.pt`, `weights/flan_ul2_encoder/`)
- **Whole GPU** — `nvidia.com/gpu: "1"`, **no** HAMi `nvidia.com/gpumem`
- Always-on: `minReplicas: 1`, `maxReplicas: 1`
- PVC: `kandinsky-3-1-flash`, `ReadWriteMany`, `nfs-models`, `100Gi`

## API

Supported endpoint:

- `POST /v1/images/generations`

Mapped inputs:

- `prompt` (required)
- `negative_prompt`
- `n` (server cap: 2)
- `size` (`WIDTHxHEIGHT`, clamped to 256-1024 and rounded to multiples of 64)
- `num_inference_steps` / `steps` (accepted for compatibility; Flash uses its
  fixed fast schedule)
- `guidance_scale`
- `seed`

Outputs:

- `created`
- `data[].b64_json` as base64-encoded PNG

`/v1/images/edits` returns `501` here — img2img/inpainting live on the full
`kandinsky-3-1` deployment.

## Test

Through the gateway from the login node (public edge serves a self-signed cert):

```bash
GW_URL=https://inference.vulcan.alliancecan.ca TYK_KEY=<TYK_KEY> GW_INSECURE=1 \
  MODEL=kandinsky-3-1-flash python3 models/kandinsky-3-1-flash/test.py
```

Or inside the gateway pod:

```bash
cat models/kandinsky-3-1-flash/test.py | kubectl exec -i -n models deploy/model-gateway -c gateway -- python3 -
```
