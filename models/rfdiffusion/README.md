# RFdiffusion

NVIDIA NIM for protein backbone design and binder generation.

- **Image:** `nvcr.io/nim/ipd/rfdiffusion:latest`
- **Endpoint:** `POST /v1/biology/ipd/rfdiffusion/generate`
- **Type:** protein design
- **GPU:** Whole L40S (`nvidia.com/gpu: 1`, no HAMi `gpumem`; the NIM needs >4 GiB of preallocated scratch that a fractional slice does not expose)
- **License:** BSD-3-Clause

## Example request

```bash
curl -s https://inference.vulcan.alliancecan.ca/v1/biology/ipd/rfdiffusion/generate \
  -H "Authorization: Bearer <TYK_KEY>" \
  -H "Content-Type: application/json" \
  -d '{
    "model": "rfdiffusion",
    "input_pdb": "<PDB ATOM records>",
    "contigs": "A19-42/0 5-10",
    "hotspot_res": ["A30"],
    "diffusion_steps": 5
  }'
```

## Notes

- The gateway strips the `/v1` prefix before forwarding to the NIM (`routing.strip_v1_prefix: true`).
- The gateway removes the `model` and `stream` fields for passthrough science NIMs.
- First cold start downloads the model into the PVC cache; subsequent starts reuse it.
- Scale-to-zero is enabled; the model idles down after 15 minutes.
