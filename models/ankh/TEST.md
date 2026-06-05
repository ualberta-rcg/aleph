
## Verified 2026-06-05 (verification loop) — FIXED
- T5 encoder ran in fp16 on GPU -> NaN/Inf embeddings ("Out of range float values are not
  JSON compliant"). Switched to fp32 + nan_to_num safety net.
- Test: protein seq -> 768-dim finite embedding. PASS. status=production.
