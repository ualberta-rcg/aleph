# Tiny Aya Global — Multilingual Chat

3.35B parameter multilingual chat LLM from Cohere's Aya family. Supports 23+ languages.
Compact and fast. 8K context. vLLM bf16 on a HAMi GPU slice.

**HF**: [CohereLabs/tiny-aya-global](https://huggingface.co/CohereLabs/tiny-aya-global)

## Usage
```bash
curl -s https://inference.vulcan.alliancecan.ca/v1/chat/completions \
  -H "Authorization: Bearer $KEY" -H "Content-Type: application/json" \
  -d '{"model":"tiny-aya-global","messages":[{"role":"user","content":"Bonjour!"}],"max_tokens":100}'
```
