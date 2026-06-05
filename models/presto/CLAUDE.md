# Presto — Model Context

## What This Model Does
NASA Harvest Presto — lightweight transformer (~400K params) for multi-spectral time-series satellite data. Zero-shot crop type mapping and land use classification globally. CPU-capable.

## Source
[nasaharvest/presto](https://huggingface.co/nasaharvest/presto) — Apache-2.0

## Gateway Integration
- ISVC name: presto
- MODEL_TYPE: classify

## Files
| File | Purpose |
|------|---------|
| `details.yaml` | Model metadata ConfigMap |
| `inferenceservice.yaml` | ISVC spec |
| `pvc.yaml` | Dedicated PVC |

**IMPORTANT: When changing this model's deployment config, update details.yaml to match.**
