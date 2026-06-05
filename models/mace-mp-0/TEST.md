
## Verified 2026-06-05 (verification loop) — DEEP-FIXED
- Bug: defaulted pbc=[True,True,True] with cell=None -> periodic calc on a zero cell gave
  garbage (~ -3.5e13 eV). Now: non-periodic by default; PBC only when a cell is supplied.
- Also cache the MACE-MP medium model on the PVC (was re-downloading 42MB to ephemeral
  /root/.cache each cold start, making scale-from-zero slow/flaky).
- Test (direct): water -> -14.15 eV (physical), forces ~0.5 eV/A; NaCl crystal (with cell)
  -> -4.95 eV + stress tensor. PASS. status=production.
