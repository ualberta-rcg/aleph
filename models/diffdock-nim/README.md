# DiffDock NIM

NVIDIA NIM for generative molecular blind docking.

- **Image:** `nvcr.io/nim/mit/diffdock:2.3`
- **Endpoint:** `POST /v1/molecular-docking/diffdock/generate`
- **Type:** chemistry
- **GPU:** HAMi vGPU slice (`nvidia.com/gpu: 1`, `nvidia.com/gpumem: 40960`)
- **License:** NVIDIA AI Product Agreement

## Example request

```bash
curl -s https://inference.vulcan.alliancecan.ca/v1/molecular-docking/diffdock/generate \
  -H "Authorization: Bearer <TYK_KEY>" \
  -H "Content-Type: application/json" \
  -d '{
    "model": "diffdock-nim",
    "protein": "ATOM    1  N   GLY A   1 ...",
    "ligand": "CCO",
    "ligand_file_type": "txt",
    "num_poses": 10,
    "steps": 18
  }'
```

## Notes

- The gateway strips `/v1` before forwarding upstream (`routing.strip_v1_prefix: true`).
- The gateway removes the OpenAI-style `model` and `stream` fields for passthrough science NIMs.
- First cold start pulls the NIM image and loads weights; subsequent starts reuse the PVC cache.
- Scale-to-zero is enabled; the model idles down after 15 minutes.
