# ProtGPT2

ProtGPT2 (~1.5B, GPT-2 architecture) generates **novel protein sequences** (amino-acid strings) from scratch or by continuing a partial seed. Trained on natural protein sequences to produce stable, structurally plausible proteins. Served by a custom (non-OpenAI) generation server.
[HuggingFace: nferruz/ProtGPT2](https://huggingface.co/nferruz/ProtGPT2) · MIT

## What it does
- **Protein generation**: from a seed (e.g. `M`, `MKLV`) it emits amino-acid sequences.
- **Custom endpoint** `POST /v1/completions` — not chat. No tools / vision / streaming.
- Context window 1024 tokens; ~1.5B params, GPU float16 (~2 GB VRAM).
- **Requires a non-empty seed** — an empty prompt 500s (`reshape tensor of 0 elements`).

## Call it
```bash
curl $GW/v1/completions -H 'Content-Type: application/json' -d '{
  "model": "protgpt2",
  "prompt": "M",
  "max_tokens": 120,
  "num_sequences": 1,
  "temperature": 0.7
}'
# -> { "model": "protgpt2", "sequences": ["MKLVVPAT..."] }
```

## Resources
- 1× HAMi GPU slice (L40S), custom FastAPI server (`python:3.11-slim` + venv). Weights on PVC `protgpt2-data`.
- Scale-to-zero: 15-min idle retention, wake-on-demand; cold start ~1-2 min.

## Testing
The non-reasoning battery runs inside the gateway pod (first check wakes a scaled-to-zero model):
```bash
cat models/protgpt2/test.py | kubectl exec -i -n models deploy/model-gateway -c gateway -- python3 -
```
Last run (2026-06-18): **6 PASS / 1 EXP / 0 FAIL (custom /v1/completions)**

## Source
[HuggingFace: nferruz/ProtGPT2](https://huggingface.co/nferruz/ProtGPT2) · MIT
