# DeepSeek-V4-Flash

NVIDIA NIM for DeepSeek-V4-Flash MoE chat.

- **Image:** `nvcr.io/nim/deepseek-ai/deepseek-v4-flash:latest`
- **Endpoint:** `POST /v1/chat/completions`
- **Type:** chat
- **GPU:** 4× L40S whole devices (`nvidia.com/gpu: 4`, no HAMi `gpumem`)
- **License:** DeepSeek

## Example request

```bash
curl -s https://inference.vulcan.alliancecan.ca/v1/chat/completions \
  -H "Authorization: Bearer <TYK_KEY>" \
  -H "Content-Type: application/json" \
  -d '{
    "model": "deepseek-v4-flash",
    "messages": [{"role": "user", "content": "Hello"}],
    "max_tokens": 128,
    "temperature": 0.7
  }'
```

## Notes

- 284B total / 13B active parameters, FP8 inference, up to 1M context.
- First cold start downloads the model into the PVC cache; subsequent starts reuse it.
- Scale-to-zero is enabled; the model idles down after 15 minutes.
