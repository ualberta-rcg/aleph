# qwen-image-2-1

**STATUS: PRODUCTION (deployed + proven 2026-09-28).**

## Purpose and supported API

Qwen-Image-2.1 (`Qwen/Qwen-Image-2.1`, **Qwen Research License — non-commercial research
use**): 7.1B single-stream DiT + Qwen3-VL-8B text encoder (bf16) + 16× RGBA VAE, ~33.1 GB
safetensors. Text-to-image up to 2048×2048 across seven aspect ratios, image editing from
prompt instructions with reference images, and RGBA transparent output. Guidance-free
sampling by design (`true_cfg` default 1.0).

Endpoints (OpenAI-style, through the gateway's custom forwarding):

- `POST /v1/images/generations` — `{prompt, n≤2, size "WxH" (256–2048, ÷32),
  num_inference_steps (default 40, 4–50), true_cfg / guidance_scale, negative_prompt,
  seed}` → `data[].b64_json` PNG
- `POST /v1/images/edits` — same params + `image`: base64 PNG/JPEG reference (single or
  list, ≤4); image-conditioned editing through the same pipeline
- `GET /health`

## Deploy and use

```bash
# via aleph1 (172.26.92.43), each file in its own apply:
kubectl apply -f models/qwen-image-2-1/pvc.yaml
kubectl apply -f models/qwen-image-2-1/inferenceservice.yaml   # ISVC + server ConfigMap
kubectl apply -f models/qwen-image-2-1/details.yaml

# test through the public edge (background it):
GW_URL=https://inference.vulcan.alliancecan.ca TYK_KEY=<key> MODEL=qwen-image-2-1 \
    python3 models/qwen-image-2-1/test.py
```

First-ever boot builds the venv and downloads ~47 GB inside the initContainer (one-time,
3600s progress deadline); every later wake is pipeline-load only (~5-10 min).

## Tested configuration

- Runtime: diffusers **@ git main `51a454be9a43854939d2ef2d231565f46a41e366`** (pinned —
  `QwenImage21Pipeline` is not in a diffusers release yet), `transformers==5.17.0`,
  `torch==2.12.1` (cu126 wheels), on `python:3.11`; FastAPI server in the
  `qwen-image-2-1-server` ConfigMap; VAE tiling enabled; serialized generations.
- GPU: **one whole L40S** (`nvidia.com/gpu: "1"`, no gpumem). Reference peak ~34 GB at
  1024²/40 steps.
- Storage: PVC `qwen-image-2-1`, 100Gi RWX `nfs-models` (repo + venv).
- Scaling: scale-to-zero, min 0 / max 1, idle 15m.
- Engine choice: mainline vLLM cannot load QwenImage21 (no tagged release); vLLM-Omni
  serves it only via unmerged PR #7759 nightly wheels — rejected as non-stock. Swap to
  the stock vLLM image when upstream merges.

## Validation and limitations

- **2026-09-28 (first deploy, proven same day):** full battery through the public edge —
  3 runs, all green: 11/2/0 (standard), **12/2/0 incl. the 2048×2048/40-step peak
  probe**, and **12/2/0 again after the clean proof redeploy** (ISVC + both ConfigMaps
  deleted, verified cleared, recreated purely from these repo files, PVC kept).
  Covered: wake, dims incl. the ÷32 non-square clamp, n=2, negative/true_cfg, **seed
  determinism (identical PNG bytes)**, **edits with a reference fixture**, **RGBA
  (color_type 6)**, guards, catalog.
- Measured (login-node battery, L40S): first-ever staging ~6 min (venv + 47 GB);
  **cached cold wake 79 s** (0 → serving); 512²/8-step gen **3.2 s**; 4-way concurrent
  burst serialized by the lock ~2.9 s apart (11.5 s wall, all 200); **peak working set
  after 2048² generation: 32.7 GiB of the 48 Gi limit**; 0 restarts, no OOM lines.
- Known limits: generations serialized (one at a time; n≤2); edits are reference-image
  conditioning (no strength/mask parameter on this pipeline); RGBA depends on the prompt
  engaging the alpha path (the plain apple prompt already emitted RGBA).
