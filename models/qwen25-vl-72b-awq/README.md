# Qwen2.5-VL-72B-Instruct (AWQ)

Qwen's **Qwen2.5-VL-72B-Instruct**, **AWQ 4-bit** quantized — a large vision-language model handling text, dynamic-resolution images, and video. AWQ fits the 72B model onto 2× L40S.
[HuggingFace: Qwen/Qwen2.5-VL-72B-Instruct-AWQ](https://huggingface.co/Qwen/Qwen2.5-VL-72B-Instruct-AWQ) · Apache-2.0

## What it does
- **Multimodal**: images (up to 20 per prompt) + video (1 per prompt), OCR, document/chart parsing, visual grounding.
- **Context** 128K native, served at 64K (128K OOMs on L40S 48 GB). No tools, no reasoning mode.
- AWQ 4-bit (smaller footprint than the BF16 `qwen25-vl-72b`).

## Call it
```bash
curl $GW/v1/chat/completions -H 'Content-Type: application/json' -d '{
  "model": "qwen25-vl-72b-awq",
  "messages": [{"role": "user", "content": [
    {"type": "text", "text": "What is in this image?"},
    {"type": "image_url", "image_url": {"url": "data:image/png;base64,..."}}
  ]}],
  "max_tokens": 200
}'
```

## Resources
- 2× L40S (whole devices, TP2), AWQ 4-bit (~20 GiB/GPU), `--disable-custom-all-reduce`, `VLLM_ATTENTION_BACKEND=TRITON_ATTN_VLLM_V1`, `vllm/vllm-openai:v0.20.2`. Weights on PVC `qwen25-vl-72b-awq-data`.
- Scale-to-zero: 15-min idle retention, wake-on-demand; cold start ~3-4 min.

## Testing
The non-reasoning battery runs inside the gateway pod (first check wakes a scaled-to-zero model):
```bash
cat models/qwen25-vl-72b-awq/test.py | kubectl exec -i -n models deploy/model-gateway -c gateway -- python3 -
```
Last run (2026-06-18): **21 PASS / 2 EXP / 0 FAIL (vision, AWQ)**

## Source
[HuggingFace: Qwen/Qwen2.5-VL-72B-Instruct-AWQ](https://huggingface.co/Qwen/Qwen2.5-VL-72B-Instruct-AWQ) · Apache-2.0
