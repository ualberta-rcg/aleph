# ProteinMPNN NIM

NVIDIA NIM for protein sequence design from backbone structures.

- **Image:** `nvcr.io/nim/ipd/proteinmpnn:1.1.0`
- **Endpoint:** `POST /v1/biology/ipd/proteinmpnn/predict`
- **Type:** predict
- **GPU:** HAMi vGPU slice (`nvidia.com/gpu: 1`, `nvidia.com/gpumem: 20480`)
- **License:** NVIDIA AI Product Agreement

## Example request

```bash
curl -s https://inference.vulcan.alliancecan.ca/v1/biology/ipd/proteinmpnn/predict \
  -H "Authorization: Bearer <TYK_KEY>" \
  -H "Content-Type: application/json" \
  -d '{
    "model": "proteinmpnn-nim",
    "input_pdb": "ATOM    1  N   GLY A   1 ...",
    "num_seq_per_target": 2,
    "sampling_temp": [0.1]
  }'
```

## Notes

- The gateway strips `/v1` before forwarding upstream (`routing.strip_v1_prefix: true`).
- The gateway removes the OpenAI-style `model` and `stream` fields for passthrough science NIMs.
- First cold start pulls the NIM image and loads weights; subsequent starts reuse the PVC cache.
- Scale-to-zero is enabled; the model idles down after 15 minutes.
