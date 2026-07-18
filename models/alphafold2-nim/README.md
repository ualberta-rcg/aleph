# AlphaFold2 NIM

NVIDIA NIM for protein structure prediction from amino-acid sequences.

- **Image:** `nvcr.io/nim/deepmind/alphafold2:2.1.1`
- **Endpoint:** `POST /v1/biology/deepmind/alphafold2/predict`
- **Type:** structure prediction
- **GPU:** HAMi vGPU slice (`nvidia.com/gpu: 1`, `nvidia.com/gpumem: 40960`)
- **PVC:** 1 Ti RWX cache for reference databases
- **License:** NVIDIA AI Product Agreement

## Example request

```bash
curl -s https://inference.vulcan.alliancecan.ca/v1/biology/deepmind/alphafold2/predict \
  -H "Authorization: Bearer <TYK_KEY>" \
  -H "Content-Type: application/json" \
  -d '{
    "model": "alphafold2-nim",
    "sequence": "MKTAYIAKQRQISFVKSHFSRQLEERLGLIEVQAPILSRVGDGTQDNLSGAEKAVQVKVKALPDAQFEVVHSLAKWKRQTLGQHDFSAGEGLYTHMKALRPDEDRLSPLHSVYVDQWDWERVMGDGERQFSTLKSTVEAIWAGIKATEAAVSEEFGLAPFLPDQIHFVHSQELLSRYPDLDAKGRERAIAKDLGAVFLVGIGGKLSDGHRHDVRAPDYDDWSTPSELGHAGLNGDILVWNPVLEDAFELSSMGIRVDADTLKHQLALTGDEDRLELEWHQALLRGEMPQTIGGGIGQSRLTMLLLQLPHIGQVQAGVWPAAVRESVPSLL"
  }'
```

## Notes

- The gateway routes the public path upstream as `/predict` (`routing.upstream_path: /predict`).
- The gateway removes the `model` and `stream` fields for passthrough science NIMs.
- An `initContainers` downloader runs `download-to-cache --all` on first start to populate the PVC cache.
- First cold start downloads the AlphaFold2 reference databases (hundreds of GB); subsequent starts reuse the cache.
- Scale-to-zero is enabled; the model idles down after 15 minutes once the cache is populated.
