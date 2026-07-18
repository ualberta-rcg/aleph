# MolMIM

NVIDIA NIM for generative molecular design around a seed SMILES.

- **Image:** `nvcr.io/nim/nvidia/molmim:1.0.0`
- **Endpoint:** `POST /v1/biology/nvidia/molmim/generate`
- **Type:** molecule generation
- **GPU:** HAMi vGPU slice (`nvidia.com/gpu: 1`, `nvidia.com/gpumem: 20480`)
- **License:** NVIDIA AI Product Agreement

## Example request

```bash
curl -s https://inference.vulcan.alliancecan.ca/v1/biology/nvidia/molmim/generate \
  -H "Authorization: Bearer <TYK_KEY>" \
  -H "Content-Type: application/json" \
  -d '{
    "model": "molmim",
    "smi": "CC(=O)Oc1ccccc1C(=O)O",
    "num_molecules": 3,
    "algorithm": "CMA-ES",
    "property_name": "QED",
    "particles": 5,
    "iterations": 1
  }'
```

## Notes

- The gateway routes public `/v1/biology/nvidia/molmim/generate` upstream as `/generate` (`routing.upstream_path: /generate`).
- The gateway removes the `model` and `stream` fields for passthrough science NIMs.
- First cold start downloads the model into the PVC cache; subsequent starts reuse it.
- Scale-to-zero is enabled; the model idles down after 15 minutes.
