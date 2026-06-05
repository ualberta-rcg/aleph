# BiomedCLIP — Model Context

## What This Model Does
Microsoft BiomedCLIP — CLIP variant pre-trained on 15M PubMed figure-caption pairs. Embeds biomedical images and text into shared 512-dim space. State-of-the-art biomedical image classification and cross-modal retrieval.

## Source
[microsoft/BiomedCLIP-PubMedBERT_256-vit_base_patch16_224](https://huggingface.co/microsoft/BiomedCLIP-PubMedBERT_256-vit_base_patch16_224) — Apache-2.0

## Gateway Integration
- ISVC name: biomedclip
- MODEL_TYPE: embed (gateway says "embed")
- GPU_MODELS: yes

## Files
| File | Purpose |
|------|---------|
| `details.yaml` | Model metadata ConfigMap |
| `inferenceservice.yaml` | ISVC spec |
| `pvc.yaml` | Dedicated PVC |

**IMPORTANT: When changing this model's deployment config, update details.yaml to match.**
