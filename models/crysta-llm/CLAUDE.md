# crysta-llm — Model Context

CrystaLLM-pi_base (~25M, GPT-2 architecture) generates crystal structures in **CIF format** from a chemical formula. A custom (non-OpenAI) generation server — **not** a chat model.

## Serving
- Custom FastAPI server (image `python:3.11-slim`, venv at `/data/venv`) on a HAMi vGPU slice (1× L40S). Server code + custom tokenizer ship as ConfigMaps.
- Weights on PVC `crysta-llm-data` at `/data/model`; CIF tokenizer (vocab=377, from `lantunes/CrystaLLM`) at `/app/tokenizer`.
- **NOT vLLM.** `transformers.GPT2LMHeadModel`, float16. Request timeout 300s.
- No streaming (`routing.no_stream: true` → the gateway forces non-streaming). `minReplicas: 0` + 15m idle retention; cold start ~1-2 min.

## Gateway integration
- Card `details.yaml`: **Template B (custom science)**, `schema_version: 2`. Primary endpoint `POST /v1/science/generate`.
- Behavior gates: no vision, no tools, no system prompt, no streaming, no reasoning. `type: chat` with a custom pass-through endpoint (the gateway routes `/v1/science/generate` straight to the server).
- Input `{formula, temperature, max_new_tokens, num_samples}` → output `{structures: [CIF strings]}`.

## Deploy / test
```bash
kubectl apply -f models/crysta-llm/        # details.yaml + inferenceservice.yaml + pvc.yaml
# Test (external via gateway VIP + Tyk auth)
GW_URL=http://<GATEWAY_VIP> TYK_KEY=<key> MODEL=crysta-llm python3 models/crysta-llm/test.py
# Or in-pod (no auth):
cat models/crysta-llm/test.py | kubectl exec -i -n models deploy/model-gateway -c gateway -- env MODEL=crysta-llm python3 -
```
Last result: **5 pass / 1 expected / 0 fail** (custom generation battery: wake + NaCl/LiFePO4/MgO generation, temperature, num_samples, health, catalog).

## Notes
- Non-OpenAI generation only — chat/tools/vision/Anthropic batteries don't apply.
- Output is CIF text; validate the generated structures downstream (geometry, charge balance).
- Very small model (25M) — fast, but domain-narrow (crystallography only).
