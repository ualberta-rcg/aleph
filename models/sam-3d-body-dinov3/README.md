# sam-3d-body-dinov3 — SAM 3D Body (single-image 3D human mesh recovery)

**Source:** [`facebook/sam-3d-body-dinov3`](https://huggingface.co/facebook/sam-3d-body-dinov3) (gated, access approved)
**Code:** [github.com/facebookresearch/sam-3d-body](https://github.com/facebookresearch/sam-3d-body)
**Type:** single-image full-body 3D human mesh recovery · **GPU:** HAMi slice (16 GB) · **Scale-to-zero:** yes

## What it does

Give SAM 3D Body an image containing one or more people and it returns, per person, a
**3D body mesh** (`pred_vertices`), **3D and 2D keypoints**, **camera translation**,
estimated **focal length**, and body/hand **pose + shape params** — robust to occlusion,
hard poses, and unusual viewpoints. Uses the Momentum Human Rig (MHR).

## Endpoint

`POST /v1/science/pose3d`

```json
{ "model": "sam-3d-body-dinov3", "image": "<base64 JPEG/PNG>", "bbox_thr": 0.5, "return_vertices": false }
```

Response (per detected person):

```json
{
  "model": "sam-3d-body-dinov3", "task": "pose3d", "count": 1,
  "persons": [{
    "keypoints_2d": [[x,y], ...], "keypoints_3d": [[x,y,z], ...],
    "cam_t": [tx, ty, tz], "focal_length": 1500.0,
    "vertex_count": 6890, "vertex_bounds": [[min...],[max...]],
    "shape_params": [...], "body_pose_params": [...], "hand_pose_params": [...]
  }]
}
```

Set `return_vertices: true` to add the full `vertices` (N×3) array per person — large.

## Cold start

**15–25 min on first boot**: the init container builds a torch cu128 venv, installs the
science/CV stack, **compiles detectron2** (CPU-only), clones MoGe + the sam-3d-body repo,
and downloads the gated checkpoints. Subsequent cold starts reuse the cached venv/checkpoints
(~2–3 min). ViTDet human detection runs on CPU; the 3D model + MoGe FOV run on GPU.

## Run the test

```bash
GW_URL=https://inference.vulcan.alliancecan.ca TYK_KEY=<key> GW_INSECURE=1 \
  python3 models/sam-3d-body-dinov3/test.py
```
