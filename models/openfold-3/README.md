# OpenFold-3

NVIDIA NIM for biomolecular complex structure prediction.

- **Image:** `nvcr.io/nim/openfold/openfold3:latest`
- **Endpoint:** `POST /v1/biology/openfold/openfold3/predict`
- **Type:** structure prediction
- **GPU:** HAMi vGPU slice (`nvidia.com/gpu: 1`, `nvidia.com/gpumem: 20480`)
- **License:** Apache-2.0

## Example request

```bash
curl -s https://inference.vulcan.alliancecan.ca/v1/biology/openfold/openfold3/predict \
  -H "Authorization: Bearer <TYK_KEY>" \
  -H "Content-Type: application/json" \
  -d '{
    "model": "openfold-3",
    "inputs": [
      {
        "input_id": "test",
        "molecules": [
          {
            "type": "protein",
            "id": "A",
            "sequence": "MALWMRLLPLLALLALWGPDPAAAFVNQHLCGSHLVEALYLVCGERGFFYTPKTRREAEDLQVGQVELGGGPGAGSLQPLALEGSLQKRGIVEQCCTSICSLYQLENYCN",
            "msa": {
              "main_db": {
                "csv": {
                  "alignment": "key,sequence\n-1,MALWMRLLPLLALLALWGPDPAAAFVNQHLCGSHLVEALYLVCGERGFFYTPKTRREAEDLQVGQVELGGGPGAGSLQPLALEGSLQKRGIVEQCCTSICSLYQLENYCN",
                  "format": "csv"
                }
              }
            }
          }
        ]
      }
    ],
    "diffusion_samples": 1,
    "output_format": "cif"
  }'
```

## Notes

- Protein sequences require a non-empty MSA. Provide at least the query sequence as a CSV MSA (`key,sequence\n-1,<QUERY>`).
- The gateway strips the `/v1` prefix before forwarding to the NIM (`routing.strip_v1_prefix: true`).
- The gateway removes the `model` and `stream` fields for passthrough science NIMs.
- First cold start downloads the model into the PVC cache; subsequent starts reuse it.
- Scale-to-zero is enabled; the model idles down after 15 minutes.
