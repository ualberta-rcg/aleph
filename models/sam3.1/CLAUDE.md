# sam3.1 — serving notes & quirks

## Model
- **Repo:** `facebook/sam3` (gated; access approved for our HF token — `facebook/sam3.1`
  also accessible). **Checkpoint:** `sam3.pt` (~3.4 GB fp32), 848M params.
- **Why not sam3.1_multiplex.pt?** The "Object Multiplex" 3.1 checkpoint is a *video
  tracking* optimisation. For single-image segmentation the documented path is
  `build_sam3_image_model()`, which loads `sam3.pt` from `facebook/sam3`. Served model id
  is `sam3.1` to match the user request / install (latest sam3 package with 3.1 support).

## Serving
- **Custom FastAPI server** (ConfigMap `sam3-1-server` → `/app/server.py`), Template B.
- Uses the official package: `build_sam3_image_model(checkpoint_path=…, load_from_HF=False)`
  + `Sam3Processor`. Flow: `processor.set_image(PIL)` → `processor.set_text_prompt(state, text)`
  → `{masks, boxes, scores}`.
- Endpoint `POST /v1/science/segment` (+ alias `/v1/vision/segment`). Gateway catch-all
  forwards `/v1/{path}` to the ISVC, resolving the model from the body `model` field.
- `return_masks=false` by default (masks are H×W — huge). When true, each instance carries
  a base64 PNG (`mask_png`).

## Environment
- Base image `python:3.11-slim` (package supports ≥3.8). torch **cu128** pip wheel bundles
  the CUDA runtime, so no CUDA base image needed under HAMi GPU injection.
- initContainer builds `/data/venv`: torch+torchvision (cu128), numpy<2, Pillow, fastapi,
  uvicorn, then `pip install git+https://github.com/facebookresearch/sam3.git` (pulls timm,
  ftfy, iopath, huggingface_hub, etc.). Requires `git` → apt-installed in-container.
- Checkpoint pre-downloaded to `/data/model/sam3.pt` (gate checks for the file, not
  config.json). `HF_TOKEN` from secret.

## Resources / quirks
- GPU slice `nvidia.com/gpumem: 10240` (10 GB). Model fp32 ~3.4 GB + ViT-L activations at
  img_size 1008. Bump to 16384 if OOM.
- `progress-deadline: 3000s` — first cold start is long (venv build + 3.4 GB download).
- Output shapes are normalised defensively: masks squeezed from `[N,1,H,W]`→`[N,H,W]`,
  boxes reshaped to `[N,4]`, scores flattened. Handles tensor → numpy via `.detach().cpu()`.
- `set_text_prompt` requires a prompt; falls back to env `SAM3_DEFAULT_PROMPT` ("object").
