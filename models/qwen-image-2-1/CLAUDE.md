# qwen-image-2-1 — operator notes

## Purpose

Qwen-Image-2.1 image model (t2i + reference-image editing + RGBA), public id
`qwen-image-2-1`, one whole L40S. **License: Qwen Research License (non-commercial
research use)** — stated in the card catalog; confirmed acceptable for this cluster's
research user base at deploy time.

## Runtime

- Image: `python:3.11`; serving runs `/data/venv/bin/python /app/server.py`
  (flux-1-dev pattern).
- Venv pins (built once by the initContainer, sentinel `/data/.qwen-image-2-1-ready`):
  `torch==2.12.1` (pytorch cu126 index), `transformers==5.17.0`,
  `diffusers @ git+…@51a454be9a43854939d2ef2d231565f46a41e366` (2026-09-28 main —
  `QwenImage21Pipeline` lives at `src/diffusers/pipelines/qwenimage21/`; NOT in any
  release). Reproducibility depends on that commit pin.
- Pipeline facts verified from the pinned source: class `QwenImage21Pipeline`;
  `__call__` takes `image` (condition/reference images → editing through the SAME
  pipeline, no separate edit class), `true_cfg_scale` (NOT `guidance_scale`; default
  1.0 — guidance-free by design), `num_inference_steps=40`, `output_resolution=1024`,
  dims must be divisible by 32 (`vae_scale_factor*2`), `use_kv_cache=True`,
  FlowMatchEulerDiscreteScheduler, `AutoencoderKLQwenImage21`, `Qwen3-VLForConditionalGeneration`
  text encoder; loads with `dtype=torch.bfloat16`.
- Server: VAE tiling on (2048² peak-VRAM mitigation); single asyncio.Lock generation;
  n≤2; size clamp 256–2048 ÷32; edits accept ≤4 b64 references.

## Engine route (researched 2026-09-28)

- Mainline vLLM (incl. v0.30.0): cannot load QwenImage21 — not in any tagged release.
- vLLM-Omni: serves it (images API + edits, 4.5 s/1024² on GB300) but only via unmerged
  PR #7759 nightly wheels — non-stock, unpinnable; rejected per fleet norms.
- SGLang: no image-generation serving for this model.
- **Chosen: diffusers custom server** (this dir). Upgrade path: when QwenImage21 merges
  into mainline vLLM (or omni releases), swap the serving container to the stock image.

## Resources / storage

- CPU 4/8, mem 24Gi/48Gi; `nvidia.com/gpu: "1"` requests+limits, **no gpumem** (whole
  card). Reference peak ~34 GB @1024²/40 steps; 2048² unverified on 48 GB → tiling +
  the battery's `QWEN21_BIG=1` probe.
- PVC `qwen-image-2-1` 100Gi RWX `nfs-models`; weights `/data/model` (full repo
  snapshot ~47 GB), venv `/data/venv`. Warm-cache gate: sentinel + venv/bin/python +
  `model_index.json`.

## Known quirks / gotchas

- No `guidance_scale` on the pipeline — the server maps `true_cfg` (and accepts
  `guidance_scale` as an alias) to `true_cfg_scale`.
- No strength/mask parameters: "edits" are reference-image conditioning; document this
  in user-facing examples.
- dims must be multiples of 32; the server rounds down.
- Serialized generations by design (kandinsky/flux parity) — burst tests assert
  queueing, not parallelism.

## Failed approaches

1. **Venv missing `fastapi`/`uvicorn`** (boot 1, 2026-09-28): server.py imports them at
   module top → instant crashloop (logs unretrievable, container died too fast for the
   shim). Fix: added to the install list AND an every-boot import-check heal step so a
   staged venv self-repairs.
2. **Venv missing `torchvision`** (boot 2): the Qwen3-VL processor loads
   `Qwen3VLVideoProcessor`, which requires torchvision —
   `ImportError … requires the Torchvision library` at pipeline load. Fix: pinned
   `torchvision==0.27.1` (pair with torch 2.12.1, cu126 index) in the install list and
   the heal step.
3. **Gateway cold-start guard doesn't re-arm a wake** when it remembers a prior
   "starting" state after an ISVC recreate: the public curl returns the fast 503 without
   forwarding. Reliable activation: probe the internal service from INSIDE a cluster pod
   (`kubectl exec deploy/model-gateway -- python3 urllib …
   http://qwen-image-2-1-predictor.models.svc.cluster.local/v1/models`) — a CP-node curl
   fails instantly (no cluster DNS on the node).

## Continuation

Deploy complete + proven 2026-09-28. Measured: staging ~6 min first boot; cached cold
wake 79 s; 512²/8-step 3.2 s; 4-burst serialized 11.5 s wall; 2048²/40-step peak
working set 32.7 GiB / 48 Gi limit; batteries 11/2/0 → 12/2/0 (BIG) → 12/2/0 (proof
after clean redeploy); 0 restarts. Remaining known-unknowns: idle scale-to-zero timing
under the 15m window (not explicitly timed — Knative policy is fleet-standard); image
quality assessment is subjective and left to users. First deploy hit two venv misses
(fastapi/uvicorn, torchvision — see Failed approaches) — the every-boot heal step now
covers both.
