# Mistral Small 4 (119B-2603)

NVIDIA NIM for Mistral Small 4 chat.

- **Image:** `nvcr.io/nim/mistralai/mistral-small-4-119b-2603:latest`
- **Endpoint:** `POST /v1/chat/completions`
- **Type:** chat
- **GPU:** 2× L40S whole devices (`nvidia.com/gpu: 2`, no HAMi `gpumem`)
- **License:** Mistral AI

## Example request

```bash
curl -s https://inference.vulcan.alliancecan.ca/v1/chat/completions \
  -H "Authorization: Bearer <TYK_KEY>" \
  -H "Content-Type: application/json" \
  -d '{
    "model": "mistral-small-4-119b-2603",
    "messages": [{"role": "user", "content": "Hello"}],
    "max_tokens": 128,
    "temperature": 0.7
  }'
```

## Notes

- 119B-parameter MoE chat model served as a pre-built NVIDIA NIM.
- First cold start downloads the model into the PVC cache; subsequent starts reuse it.
- Scale-to-zero is enabled; the model idles down after 15 minutes.
