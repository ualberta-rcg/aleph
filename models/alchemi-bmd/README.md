# Alchemi BMD NIM

NVIDIA NIM for molecular dynamics using many-body atomic interaction models.

- **Image:** `nvcr.io/nim/nvidia/alchemi-bmd:1.0.0`
- **Endpoint:** `POST /v1/infer`
- **Type:** chemistry
- **GPU:** HAMi vGPU slice (`nvidia.com/gpu: 1`, `nvidia.com/gpumem: 40960`)
- **License:** NVIDIA AI Product Agreement

## Example request

```bash
curl -s https://inference.vulcan.alliancecan.ca/v1/infer \
  -H "Authorization: Bearer <TYK_KEY>" \
  -H "Content-Type: application/json" \
  -d '{
    "model": "alchemi-bmd-nim",
    "atoms": {
      "coord": [0.0, 0.0, 0.0, 0.74, 0.0, 0.0],
      "numbers": [1, 1],
      "cell": [10.0, 0.0, 0.0, 0.0, 10.0, 0.0, 0.0, 0.0, 10.0],
      "pbc": [false, false, false],
      "charge": 0,
      "mult": 1
    },
    "config": {
      "temperature": 300.0,
      "dt": 1.0,
      "nvt": true,
      "npt": false,
      "md_time_max": 0.01,
      "save_interval": 1
    },
    "info": "example"
  }'
```

## Notes

- The NIM's native endpoint is already `/v1/infer`, so the gateway forwards it verbatim.
- The gateway removes the OpenAI-style `model` and `stream` fields for passthrough science NIMs.
- First cold start pulls the NIM image and loads weights; subsequent starts reuse the PVC cache.
- Scale-to-zero is enabled; the model idles down after 15 minutes.
