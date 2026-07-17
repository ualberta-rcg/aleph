# Evo2-40b

NVIDIA NIM for the Arc Institute Evo2 40B genome modeling model.

- **Image:** `nvcr.io/nim/arc/evo2-40b:latest`
- **Endpoint:** `POST /v1/biology/arc/evo2/generate`
- **Type:** generate (DNA sequence generation)
- **GPU:** 1× L40S HAMi vGPU slice (`nvidia.com/gpu: 1`, `nvidia.com/gpumem: 43008`)
- **License:** Arc Institute

## Example request

```bash
curl -s https://inference.vulcan.alliancecan.ca/v1/biology/arc/evo2/generate \
  -H "Authorization: Bearer <TYK_KEY>" \
  -H "Content-Type: application/json" \
  -d '{
    "model": "evo2-40b",
    "sequence": "ATGCGATCGATCGATCGATCG",
    "num_tokens": 8,
    "temperature": 0.7,
    "top_k": 1,
    "top_p": 0.9
  }'
```

## Notes

- Native NIM endpoint is `/biology/arc/evo2/generate`; the gateway strips `/v1` and forwards.
- The model is designed for Hopper/H100 FP8 Transformer Engine; L40S (Ada) compatibility is not guaranteed.
- First cold start downloads the model into the PVC cache; subsequent starts reuse it.
- Scale-to-zero is enabled.
