# MedGemma 27B IT

Google's **MedGemma 27B Instruct** — a medical multimodal model (Gemma 3-based, SigLIP medical image encoder) for radiology image understanding, clinical text, and medical Q&A. Served across 2× L40S (TP2).
[HuggingFace: google/medgemma-27b-it](https://huggingface.co/google/medgemma-27b-it) · Gemma license (**gated — HF_TOKEN required**)

## What it does
- **Medical multimodal**: text + medical images (up to 5 per prompt) via OpenAI `image_url` content blocks.
- **Context** 128K native, served at 32K (VRAM-limited: 27B BF16 ≈ 54 GB on 2× L40S). No tools, no reasoning mode.
- **Research use** — not for unsupervised clinical decisions.

## Call it
```bash
curl $GW/v1/chat/completions -H 'Content-Type: application/json' -d '{
  "model": "medgemma-27b-it",
  "messages": [{"role": "user", "content": [
    {"type": "text", "text": "What findings are visible in this chest X-ray?"},
    {"type": "image_url", "image_url": {"url": "data:image/png;base64,..."}}
  ]}],
  "max_tokens": 300
}'
```

## Resources
- 2× L40S (whole devices, TP2), `--disable-custom-all-reduce` (PCIe topology), `vllm/vllm-openai:v0.20.2`, bfloat16, `--trust-remote-code`. Weights ~54 GB on PVC `medgemma-27b-it` (gated repo).
- Scale-to-zero: 15-min idle retention, wake-on-demand; cold start ~3-4 min.

## Source
[HuggingFace: google/medgemma-27b-it](https://huggingface.co/google/medgemma-27b-it) · Gemma license (gated)
