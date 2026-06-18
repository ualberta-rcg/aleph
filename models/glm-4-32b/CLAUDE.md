# glm-4-32b — Model Context

GLM-4-32B-0414 (Zhipu-AI) — a 32B dense instruct model with strong function calling / agentic workflows (BFCL-v3 ≈ GPT-4o). Served by vLLM across 2× L40S (TP2). Text-only.

## Serving
- Image `vllm/vllm-openai:v0.20.2`, **TP2 whole devices** (`nvidia.com/gpu: "2"`, no `gpumem` — gpumem would force HAMi vGPU mode and break TP P2P). `--max-model-len 32768`, `--dtype auto` (bf16), `--gpu-memory-utilization 0.92`, `--max-num-seqs 8`.
- **Tool calling**: `--tool-call-parser glm4_0414` + a **custom plugin** (`--tool-parser-plugin=/opt/glm4_parser/glm4_0414_tool_parser.py`, mounted from ConfigMap `glm4-0414-parser`) + `--enable-auto-tool-choice`. GLM-4 emits tool calls in its native `name\n{json}` text format; the plugin parses them into OpenAI-compatible `tool_calls`.
- `--disable-custom-all-reduce` (L40S PCIe/CPU topology, no NVLink P2P → NCCL fallback is correct + fast). `VLLM_ATTENTION_BACKEND=TRITON_ATTN_VLLM_V1` (SM89). `--enable-prefix-caching --enable-chunked-prefill`.
- Weights ~64 GB on PVC `glm-4-32b-data` at `/mnt/models` (`HF_HUB_OFFLINE=1`). `minReplicas: 0` + 15m idle; cold start ~3 min.

## Gateway integration
- Card `details.yaml`: **Template A (tools)**, `schema_version: 2`. Endpoints OpenAI `/v1/chat/completions` + `/v1/models`.
- Behavior gates: tools supported (via the `glm4_0414` parser+plugin), vision rejected (`400 vision_unsupported`), no reasoning. `param_translation.thinking.mode: none`.

## Deploy / test
```bash
kubectl apply -f models/glm-4-32b/        # details.yaml + inferenceservice.yaml + pvc.yaml + glm4-0414-parser ConfigMap
cat models/glm-4-32b/test.py | kubectl exec -i -n models deploy/model-gateway -c gateway -- env MODEL=glm-4-32b python3 -
```
Last result: see test run — comprehensive battery; tools work, vision rejected.

## Notes
- Scheduling: TP2 = 2 whole GPUs — cannot run alongside another whole-GPU model on the same 4-GPU node.
- The custom tool-parser plugin is **mandatory** — without it, tool calls come back as raw text.
- No reasoning mode — GLM-4 is a plain instruct/tool model.
