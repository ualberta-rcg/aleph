
## Verified 2026-06-05 (verification loop) — FIXED
- Root cause of empty responses: missing `routing.k8s_name` (gateway looked up isvc
  `depth-anything-v2` = the catalog id, but isvc is `depth-anything` -> 404). Fixed.
- Also reworked output: was dumping full HxW depth float array (MBs JSON the gateway
  can't proxy). Now returns `depth_png_base64` (full-res PNG) + `depth_grid_64` + stats.
- Test (bus.jpg, 810x1080): 4.2KB PNG, stats raw_min .31/raw_max 1.04/mean .69. PASS.
