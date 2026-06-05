
## Verified 2026-06-05 (verification loop) — DEEP-FIXED
- Encoder was called as model(cube, waves, gsd) (3 positional args) but Clay v1.5 encoder
  takes a single datacube dict {pixels[B,C,H,W], time[B,4], latlon[B,4], waves, gsd}.
  Rewrote to build the datacube (sin/cos time+latlon from optional lat/lon/time).
- Test (6-band 32x32 + waves + gsd): cls_embedding returned. PASS.
