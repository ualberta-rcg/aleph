# TinyLlama 1.1B

TinyLlama 1.1B Chat v1.0, quantized to GGUF Q4_K_M (~640 MB) and served on **CPU** via llama-cpp-python. Pretrained on 3T tokens and fine-tuned with the Zephyr recipe; same architecture/tokenizer as Llama 2. Small, fast, and the cluster's only CPU model.
[HuggingFace: TheBloke/TinyLlama-1.1B-Chat-v1.0-GGUF](https://huggingface.co/TheBloke/TinyLlama-1.1B-Chat-v1.0-GGUF) · Apache-2.0

## What it does
- **Chat**: OpenAI `/v1/chat/completions` (system + user turns). Zephyr prompt template.
- **No streaming** — `stream:true` is accepted but the gateway returns a single JSON completion (`no_stream` card).
- **No tools / vision / reasoning.** Context 4096 tokens; 1.1B params, Q4_K_M.

## Call it
```bash
curl $GW/v1/chat/completions -H 'Content-Type: application/json' -d '{
  "model": "tinyllama-1-1b",
  "messages": [{"role": "user", "content": "Hello!"}],
  "max_tokens": 50
}'
```

## Resources
- **CPU only** (no GPU), llama-cpp-python, `--n_gpu_layers=0`. ~4 vCPU / 3 Gi. GGUF on PVC `tinyllama-1-1b-models`.
- Scale-to-zero: 15-min idle retention, wake-on-demand; cold start ~30 s.

## Testing
The non-reasoning battery runs inside the gateway pod (first check wakes a scaled-to-zero model):
```bash
cat models/tinyllama-1-1b/test.py | kubectl exec -i -n models deploy/model-gateway -c gateway -- python3 -
```
Last run (2026-06-18): **18 PASS / 4 EXP / 0 FAIL (CPU/llama.cpp — model-echo only)**

## Source
[HuggingFace: TheBloke/TinyLlama-1.1B-Chat-v1.0-GGUF](https://huggingface.co/TheBloke/TinyLlama-1.1B-Chat-v1.0-GGUF) (base: [TinyLlama/TinyLlama-1.1B-Chat-v1.0](https://huggingface.co/TinyLlama/TinyLlama-1.1B-Chat-v1.0)) · Apache-2.0
