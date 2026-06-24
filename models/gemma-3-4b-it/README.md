# Gemma 3 4B IT

Google's **Gemma 3 4B Instruct** — a lightweight open multimodal model (SigLIP vision tower) accepting text + images in OpenAI chat format, with strong multilingual instruction-following for its size. Served on a single HAMi GPU slice.
[HuggingFace: google/gemma-3-4b-it](https://huggingface.co/google/gemma-3-4b-it) · Gemma license

## What it does
- **Multimodal chat**: text + images (up to 8 images per prompt) via OpenAI `image_url` content blocks.
- **Context** 128K native, served at 64K. No tools, no reasoning mode.
- Text-only requests work normally; images are analyzed inline.

## Call it
```bash
curl $GW/v1/chat/completions -H 'Content-Type: application/json' -d '{
  "model": "gemma-3-4b-it",
  "messages": [{"role": "user", "content": [
    {"type": "text", "text": "Describe this image."},
    {"type": "image_url", "image_url": {"url": "data:image/png;base64,..."}}
  ]}],
  "max_tokens": 200
}'
```

## Resources
- 1× HAMi GPU slice (L40S, 20 GiB `gpumem`), TP1, `vllm/vllm-openai:v0.20.2`, bfloat16. CUDA graphs on (no `--enforce-eager`). `--limit-mm-per-prompt '{"image":8}'`. Weights on PVC `gemma-3-4b-it-data`.
- Scale-to-zero: 15-min idle retention, wake-on-demand; cold start ~1-2 min.

## Testing
The non-reasoning battery runs inside the gateway pod (first check wakes a scaled-to-zero model):
```bash
# External via gateway VIP + Tyk auth (preferred)
GW_URL=http://<GATEWAY_VIP> TYK_KEY=<key> python3 models/gemma-3-4b-it/test.py

# Or inside the gateway pod (no auth)
cat models/gemma-3-4b-it/test.py | kubectl exec -i -n models deploy/model-gateway -c gateway -- python3 -
```
Last run (2026-06-18): **21 PASS / 2 EXP / 0 FAIL (vision)**

## Source
[HuggingFace: google/gemma-3-4b-it](https://huggingface.co/google/gemma-3-4b-it) · Gemma license
