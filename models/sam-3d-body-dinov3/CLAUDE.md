# sam-3d-body-dinov3 — serving notes & quirks

## Model
- **Repo:** `facebook/sam-3d-body-dinov3` (gated; access approved). Checkpoints: `model.ckpt`
  + `assets/mhr_model.pt` + `model_config.yaml` (downloaded to `/data/ckpt` via snapshot_download).
- **Code:** `github.com/facebookresearch/sam-3d-body` — NOT a pip package (no setup.py). Cloned
  to `/data/sam-3d-body`; the server does `sys.path.insert(0, "/data/sam-3d-body")` so both
  `sam_3d_body/` and `tools/` import as top-level packages.

## Serving
- **Custom FastAPI server** (ConfigMap `sam-3d-body-server` → `/app/server.py`), Template B.
- Mirrors `demo.py`: `load_sam_3d_body(ckpt, device=cuda, mhr_path=…)` → `SAM3DBodyEstimator`
  with `HumanDetector(vitdet, device="cpu")` + `FOVEstimator(moge2, device=cuda)`.
- `estimator.process_one_image(rgb_array, bbox_thr, use_mask=False)` → list of per-person dicts.
- Endpoint `POST /v1/science/pose3d`. `return_vertices=false` by default (full mesh is huge);
  returns `vertex_count` + `vertex_bounds` always, full `vertices` only on request.

## Environment / heavy deps
- Base `python:3.11-slim`. apt installs build tools + GL/Mesa libs (gcc g++ make python3-dev
  libgl1 libglib2.0-0 libsm6 libxext6 libxrender1) for opencv/detectron2/pyrender.
- torch **cu128**; full science/CV stack (pytorch-lightning, opencv, timm, hydra, roma, fvcore,
  xtcocotools, etc.). numpy pinned `<2`.
- **detectron2** compiled CPU-only (`FORCE_CUDA=0`, empty `TORCH_CUDA_ARCH_LIST`) because the slim
  image has no `nvcc`. → ViTDet detector runs on **CPU** (slower but works headless); the 3D model
  + MoGe run on GPU. If GPU-accelerated detection is ever needed, switch to a CUDA-devel base image.
- **MoGe** (moge2 FOV) installed from git; its install is non-fatal if it fails (estimator still
  runs, FOV defaults).
- ViTDet weights auto-downloaded from `dl.fbaipublicfiles.com` (cached under `TORCH_HOME=/data/torch_cache`).

## Resources / quirks
- PVC **60 Gi** (heavy venv ~15-20 GB + checkpoints). gpumem 16384. `progress-deadline: 3600s`.
- All output tensors cast to `.cpu().float()` lists before JSON (some are bf16/fp16).
- `process_one_image` accepts an RGB numpy array (per the HF README example) — not just a path.
- `sam_3d_body/__init__` does NOT import visualization (pyrender/matplotlib), so the server avoids
  headless-rendering import failures; only call `visualize_*` if a display/GL stack is available.
