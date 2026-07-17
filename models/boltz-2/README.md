# Boltz-2

NVIDIA NIM for biomolecular structure prediction and binding affinity.

- **Image:** `nvcr.io/nim/mit/boltz2:latest`
- **Endpoint:** `POST /v1/biology/mit/boltz2/predict`
- **Type:** structure prediction
- **GPU:** HAMi vGPU slice (`nvidia.com/gpu: 1`, `nvidia.com/gpumem: 20480`)
- **License:** MIT

## Example request

```bash
curl -s https://inference.vulcan.alliancecan.ca/v1/biology/mit/boltz2/predict \
  -H "Authorization: Bearer <TYK_KEY>" \
  -H "Content-Type: application/json" \
  -d '{
    "model": "boltz-2",
    "polymers": [
      {
        "id": "A",
        "molecule_type": "protein",
        "sequence": "MALWMRLLPLLALLALWGPDPAAAFVNQHLCGSHLVEALYLVCGERGFFYTPKTRREAEDLQVGQVELGGGPGAGSLQPLALEGSLQKRGIVEQCCTSICSLYQLENYCN"
      }
    ],
    "recycling_steps": 3,
    "sampling_steps": 50,
    "diffusion_samples": 1,
    "output_format": "mmcif"
  }'
```

## Notes

- The gateway strips the `/v1` prefix before forwarding to the NIM (`routing.strip_v1_prefix: true`).
- The NIM container includes a startup patch for a `confidence_score` KeyError in NIM v1.7.0.
- First cold start downloads the model into the PVC cache; subsequent starts reuse it.
- Scale-to-zero is enabled; the model idles down after 15 minutes.
