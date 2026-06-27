# ProGen2 — Protein Sequence Generation

ProGen2-XLarge (6.4B, Salesforce Research) generates novel protein sequences by autoregressive
language modeling on amino-acid tokens. **Not a natural-language model** — it operates on
single-letter amino-acid codes only.

- **Source**: [hugohrban/progen2-xlarge](https://huggingface.co/hugohrban/progen2-xlarge) · BSD-3-Clause
- **Serving**: custom FastAPI server (`server.py` ConfigMap, transformers `AutoModelForCausalLM` with
  `trust_remote_code`) — **not vLLM**. Venv + weights on a RWX PVC (caduceus pattern; cold starts skip
  the reinstall/redownload). TP1 fractional GPU slice (gpumem 30720). Scale-to-zero.

## API
`POST /v1/completions` — `{prompt, max_tokens, temperature}`.
- `prompt`: amino-acid sequence to continue, single-letter codes (`A C D E F G H I K L M N P Q R S T V W Y`).
- Output: `choices[0].text` — the continued sequence (1 token ≈ 1 amino acid).

No chat, tools, vision, or streaming.

## Test
```bash
GW_URL=https://inference.vulcan.alliancecan.ca TYK_KEY=<key> GW_INSECURE=1 python3 models/progen2/test.py
```
