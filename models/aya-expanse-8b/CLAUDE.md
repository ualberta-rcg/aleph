# aya-expanse-8b Notes

## Purpose
8B multilingual chat LLM from Cohere's Aya Expanse family. Requested by Montaser (upgrade from tiny-aya-global).

## Runtime
- Image: `vllm/vllm-openai:v0.20.2`
- Args: `serve /data/model --served-model-name aya-expanse-8b --max-model-len 8192 --dtype bfloat16 --tensor-parallel-size 1`
- HF: `CohereLabs/aya-expanse-8b` (8B, cohere, bf16, gated)
- GPU: HAMi slice — gpumem 32768 (~16GB bf16 weights + KV cache)

## Config
- hidden_size: 4096, vocab: 256000, max_position: 8192
- arch: CohereForCausalLM (same as command-r-7b)
