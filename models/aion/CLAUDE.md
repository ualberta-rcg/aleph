# aion Notes — BLOCKED (deferred)

## Status
**Not deployed / blocked.** The 232 server was a non-functional stub. Removed from
cluster 230. Manifests here are HAMi-converted but the server must be rewritten before
re-deploying.

## Why blocked
AION-base (Polymathic AI) is NOT a standard HuggingFace `transformers` model:
- `AutoModel.from_pretrained` fails: "Unrecognized model ... no `model_type`".
- It requires the `polymathic-aion` package (import name `aion`) with a `CodecManager`
  and per-modality dataclasses; raw float lists are not valid input.

The old server tried `transformers` then a bogus `polymathic_aion` import — both fail.

## Correct integration (for a future pass)
```python
pip install "polymathic-aion[torch]"   # import name: aion ; needs GPU, py3.12, torch>=2.4
from aion import AION
from aion.codecs import CodecManager
from aion.modalities import LegacySurveyImage, DESISpectrum, Z
model = AION.from_pretrained("/data/model").to("cuda").eval()
cm = CodecManager(device="cuda")
tokens = cm.encode(<modality object built from real astro arrays>)
emb = model.encode(tokens, num_encoder_tokens=600)   # downstream embedding
```
Needs: GPU slice, py3.12 base image, real modality inputs (spectrum/image/photometry
with correct shapes) to test. Weights ~1.8GB (38 per-modality tokenizers + model).

## Next steps
1. Rewrite `aion-server` to use the real `aion` API and accept one or more modalities
   (e.g. a DESI spectrum array → `DESISpectrum`).
2. Use a py3.12 image, cu121/cu124 torch, GPU slice + gpumem.
3. Test with a synthetic-but-correctly-shaped spectrum, verify embedding shape.
