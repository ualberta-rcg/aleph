# aion — Test Report

Cluster 230, gateway ClusterIP `http://10.43.79.101:80`. Type: embed (astronomy multimodal, CPU). id `aion`.

## Status: FIXED + verified 2026-06-05
Was deployed but **non-functional** ("READY" but model never loaded): no egress in the
runtime container, server imported the wrong package, and used a fake `inputs_embeds` hack.
Rewritten to the real AION API (`AION.from_pretrained` + `CodecManager` + typed modalities).

## Verified this pass

### POST /v1/science/embed — legacy_image — PASS
```bash
# zero default image
curl -s -X POST $GW/v1/science/embed -H 'Content-Type: application/json' \
  -d '{"model":"aion","modality":"legacy_image"}'
# real 4-band image (any HxW; server resizes to 96x96)
# flux: nested [4,H,W] g,r,i,z
```
→ 768-dim object embedding. PASS.

### POST /v1/science/embed — photometry — PASS
```bash
curl -s -X POST $GW/v1/science/embed -H 'Content-Type: application/json' \
  -d '{"model":"aion","modality":"photometry","flux_g":1.2,"flux_r":2.3,"flux_i":3.1,"flux_z":4.0}'
```
→ 768-dim embedding. PASS.

### GET /v1/science/info — capabilities list. PASS.

## Key fixes
- Package: real `polymathic-aion` (import `aion`), not `polymathic_aion`. Added torchvision.
- Pre-download model **and codec weights** in the init container (init has egress; runtime
  runs `HF_HUB_OFFLINE=1`). Warmup encodes an image + photometry to cache those codecs.
- Server builds typed modality objects (`LegacySurveyImage`, `LegacySurveyFluxG/R/I/Z`),
  resizes images to 96x96 (codec needs 576 image tokens), mean-pools encoder output -> 768.

## Card parity
id=aion, type=embed, dim=768, gpu=false, status=production. Modalities: legacy_image,
photometry (extensible: hsc_image, desi/sdss spectra need their codecs warmed too).
