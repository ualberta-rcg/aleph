# LLM Model Tracker

Track research, feature enablement, card config, and testing for all 29 chat-type LLMs.

**Status legend:** ✅ done | 🔧 needs work | — not applicable | ❌ broken | ? unknown

## Priority Order

We'll work through these one by one. Rough priority: reasoning models with most users first, then tool/vision models, then the rest.

| # | Model | Owner | Source | TP | vLLM | Served |
|---|-------|-------|--------|----|------|--------|
| 1 | qwen36-27b | Qwen | Qwen/Qwen3.6-27B | 2 | latest | vLLM |
| 2 | gpt-oss-120b | OpenAI | openai/gpt-oss-120b | 2 | v0.20.2 | vLLM+init |
| 3 | qwen3-32b | Qwen | Qwen/Qwen3-32B | 2 | v0.20.2 | vLLM |
| 4 | phi-4-reasoning | Microsoft | — | 2 | v0.20.2 | vLLM+init |
| 5 | gpt-oss-20b | OpenAI | — | 2 | v0.20.2 | vLLM+init |
| 6 | qwen35-122b | Qwen | — | 4 | v0.20.2 | vLLM |
| 7 | qwen3-235b | Qwen | — | 4 | v0.20.2 | vLLM |
| 8 | qwq-32b | Qwen | — | 2 | v0.20.2 | vLLM |
| 9 | r1-distill-qwen-32b | DeepSeek | — | 2 | v0.20.2 | vLLM |
| 10 | r1-distill-llama-70b | DeepSeek | — | 4 | v0.20.2 | vLLM |
| 11 | glm-4-32b | Zhipu-AI | — | 2 | v0.20.2 | vLLM |
| 12 | glm-z1-32b | Zhipu-AI | — | 2 | v0.20.2 | vLLM |
| 13 | glm-z1-rumination-32b | Zhipu-AI | — | 2 | v0.20.2 | vLLM |
| 14 | qwen25-coder-32b | Qwen | — | 2 | v0.20.2 | vLLM |
| 15 | qwen25-vl-72b | Qwen | — | 4 | v0.20.2 | vLLM |
| 16 | qwen25-vl-72b-awq | Qwen | Qwen/Qwen2.5-VL-72B-Instruct-AWQ | 2 | v0.20.2 | vLLM |
| 17 | qwen25-vl-7b | Qwen | — | 1 | v0.20.2 | vLLM+init |
| 18 | qwen25-vl-3b | Qwen | Qwen/Qwen2.5-VL-3B | 1 | v0.20.2 | vLLM+init |
| 19 | qwen36-35b-a3b | Qwen | — | 2 | v0.20.2 | vLLM |
| 20 | gemma-4-26b-a4b | Google | google/gemma-4-26B-A4B-it | 1 | v0.20.2 | vLLM+init |
| 21 | gemma-3-4b-it | Google | google/gemma-3-4b-it | 1 | v0.20.2 | vLLM+init |
| 22 | medgemma-27b-it | Google | google/medgemma-27b-it | 2 | v0.20.2 | vLLM+init |
| 23 | deepseek-v2-lite-16b | DeepSeek | deepseek-ai/DeepSeek-V2-Lite | 2 | v0.20.2 | vLLM+init |
| 24 | command-r-7b | Cohere | — | 1 | v0.20.2 | vLLM+init |
| 25 | openbiollm-70b | Saama | — | 4 | v0.20.2 | vLLM |
| 26 | oceangpt-30b | zjunlp | zjunlp/OceanGPT-basic-30B | 2 | v0.20.2 | vLLM+init |
| 27 | geogalactica | geobrain-ai | geobrain-ai/geogalactica | 1 | v0.20.2 | vLLM+init |
| 28 | tinyllama | TinyLlama | TheBloke/TinyLlama-1.1B | 1 | llama.cpp | custom |
| 29 | astrosage | astroMLab | AstroMLab/AstroSage-8B | 1 | custom | custom+init |

---

## Feature Tracking

### Columns
- **Research**: HF docs checked for what the model actually supports
- **Features (HF)**: What the model CAN do per its docs
- **Reasoning**: Has thinking/CoT mode (`--reasoning-parser` in ISVC, thinking config in card)
- **Tools**: Function/tool calling (`--tool-call-parser` + `--enable-auto-tool-choice` in ISVC, `supports_tools` in card)
- **Vision**: Image input (vision in card)
- **Card**: Details.yaml has correct param_translation + behavior
- **ISVC**: InferenceService has correct vLLM args
- **Tested**: End-to-end tested through gateway (OpenAI + Anthropic style)

| # | Model | Research | Features (HF) | Reasoning | Tools | Vision | Card | ISVC | Tested |
|---|-------|----------|---------------|-----------|-------|--------|------|------|--------|
| 1 | **tinyllama** | ✅ | chat only, CPU, no stream | — | — | — | ✅ | ✅ (llama.cpp) | ✅ 14/14 |
| 2 | **qwen36-27b** | ✅ | reason,tools,vision,131K | ✅ effort | ✅ qwen3_coder | ✅ | ✅ | ✅ | ✅ 25/27 |
| 2 | **gpt-oss-120b** | ✅ | reason,tools,structured,128K | ✅ openai_gptoss | ✅ openai | — | ✅ v2 effort mode | ✅ scale-to-zero | ✅ 23/25 |
| 3 | **qwen3-32b** | ✅ | reason,tools,100+lang,40K ctx | ✅ effort (qwen3) | ✅ hermes | — | ✅ | ✅ | ✅ 23/25 |
| 4 | **phi-4-reasoning** | ✅ | reason,16K budget | ✅ deepseek_r1 | — | — | ✅ budget mode | ✅ vllm serve | ✅ 19/20 |
| 5 | **gpt-oss-20b** | ✅ | reason,tools,128K | ✅ openai_gptoss | ✅ openai | — | ✅ effort mode | ✅ | ✅ 23/25 |
| 6 | **qwen35-122b** | ✅ | reason,tools,131K,MoE FP8 | ✅ toggle (qwen3) | ✅ qwen3_coder | — | ✅ | ✅ | ✅ 23/23 |
| 7 | **qwen3-235b** | ✅ | tools,131K,MoE AWQ non-thinking | — (non-thinking) | ✅ hermes | — | ✅ | ✅ | ✅ 21/21 |
| 8 | **qwq-32b** | ✅ | reason,tools,32K,always-on CoT | ✅ deepseek_r1 | ✅ hermes | — | ✅ | ✅ | ✅ 21/21 |
| 9 | **r1-distill-qwen-32b** | 🔧 | reason only | ✅ deepseek_r1 | — | — | 🔧 no param_translation | ✅ | — |
| 10 | **r1-distill-llama-70b** | 🔧 | reason only | ✅ deepseek_r1 | — | — | 🔧 no param_translation | ✅ | — |
| 11 | **glm-4-32b** | ✅ | tools, 32K ctx | — | ⚠️ glm45 (text only, no struct) | — | ✅ v2 | ✅ vllm serve, glm45 tool parser | ✅ 15/19 |
| 12 | **glm-z1-32b** | ✅ | reason+tools, always-on CoT | ✅ toggle (template) | ⚠️ glm45 (text only) | — | ✅ v2 | ✅ vllm serve, glm45 tool parser | ✅ 17/20 |
| 13 | **glm-z1-rumination-32b** | ✅ | deep reason, no tools/sysprompt | ✅ toggle (template) | — | — | ✅ v2 | ✅ vllm serve, no parsers | ✅ 16/18 |
| 14 | **qwen25-coder-32b** | ✅ | code,tools,32K,131K native | — | ✅ hermes | — | ✅ | ✅ | ✅ 22/22 |
| 15 | **qwen25-vl-72b** | ✅ | vision,video,5img,32K BF16 | — | — | ✅ | ✅ | ✅ | ✅ 22/22 |
| 16 | **qwen25-vl-72b-awq** | ✅ | vision,video,20img,64K AWQ | — | — | ✅ | ✅ 64K ctx | ✅ vllm serve, 64K | ✅ 16/18 |
| 17 | **qwen25-vl-7b** | ✅ | vision,video,tools,20img,65K | — | ✅ hermes | ✅ | ✅ | ✅ | ✅ 22/22 |
| 18 | **qwen25-vl-3b** | ✅ | vision,video,OCR,20img,64K ctx | — | — | ✅ | ✅ | ✅ | ✅ 18/18 |
| 19 | **qwen36-35b-a3b** | ✅ | reason,tools,vision,64K ctx,hybrid attn | ✅ effort (qwen3) | ✅ qwen3_coder | ✅ | ✅ | ✅ | ✅ 21/21 |
| 20 | **gemma-4-26b-a4b** | ✅ | reason,tools,vision,video,256K,MoE FP8 | ✅ effort (gemma4) | ✅ gemma4 | ✅ | ✅ | ✅ | ✅ 22/25 |
| 21 | **gemma-3-4b-it** | ✅ | vision,128K,sigLIP,4B | — | — | ✅ | ✅ | ✅ | ✅ 17/20 |
| 22 | **medgemma-27b-it** | ✅ | vision,medical,128K,32K deployed | — | — | ✅ | ✅ | ✅ 32K ctx | ✅ 17/20 |
| 23 | **deepseek-v2-lite-16b** | ✅ | chat, MoE, bilingual | — | — | — | ✅ | ✅ | ✅ 14/14 |
| 24 | **command-r-7b** | ✅ | chat, RAG, multilingual | — | — | — | ✅ | ✅ | ✅ 16/16 |
| 25 | **openbiollm-70b** | ✅ | bio chat, 70B Llama3, DPO, 86% med | — | — | — | ✅ | ✅ | ✅ 14/14 |
| 26 | **oceangpt-30b** | ✅ | ocean MoE, 128exp, bilingual, tools | — | ✅ hermes | — | ✅ | ✅ 64K ctx | ✅ 14/14 |
| 27 | **geogalactica** | ✅ | geo, Galactica/OPT, 2048 ctx | — | — | — | ✅ | ✅ v0.20.2, chat-template | ✅ 14/14 |
| 28 | **tinyllama** | — | chat basic | — | — | — | — | — (llama.cpp) | — |
| 29 | **astrosage** | ✅ | astro, Llama3.1-8B, beats GPT-4o | — | — | — | ✅ no_stream | ✅ custom server | ✅ 14/14 |

---

## Thinking Mode Reference

| Mode | When to use | Example models | Mechanism |
|------|------------|----------------|-----------|
| **budget** | Model supports `thinking_token_budget` param | phi-4-reasoning | Maps effort → token count (0/1024/4096/12288/24576/null) |
| **effort** | Model has native `reasoning_effort` or binary thinking via chat_template_kwargs | qwen36-27b, gpt-oss-20b | Maps effort aliases → on/off or passthrough |
| **toggle** | Model has simple thinking on/off | qwen35-122b | Injects `chat_template_kwargs: {enable_thinking: bool}` |
| **none** | Non-reasoning model, no thinking params | gemma-3-4b-it | No thinking translation needed |

---

## Workflow Per Model

For each model we work on:

1. **Research** — WebSearch the HuggingFace page, check what features the model actually supports (reasoning, tools, vision, context length)
2. **Enable ISVC** — Add missing `--reasoning-parser`, `--tool-call-parser`, `--enable-auto-tool-choice` flags
3. **Update card** — Add `param_translation.thinking` (pick mode: budget/effort/toggle), set correct `behavior.*` flags, add limits
4. **Apply to cluster** — `kubectl apply -f details.yaml` and/or `kubectl apply -f inferenceservice.yaml`
5. **Test** — Run through gateway: basic chat, streaming, thinking on/off, tools, vision (if supported), Anthropic-style `/v1/messages` endpoint
6. **Mark complete** — Update this tracker

---

## Notes

- Models 28-29 (tinyllama, astrosage) use custom/llama.cpp servers — not standard vLLM. Lower priority.
- crysta-llm, progen2, protgpt2 removed — science/generation models, not chat LLMs.
- k2-v2 removed — ships FP32-only (~290GB), impractical cold start over NFS; outperformed by modern 65B+ models.
- Models with `+init` use init containers to pip-install vLLM — slower startup, less control over args.
- qwen36-27b is the most recently configured (today) and can serve as the template for effort-mode models.
- gpt-oss-120b needs param_translation added (reasoning + tools already in ISVC).
- gpt-oss-120b: Card rewritten from v1 to v2 (removed compatibility.*, deployment.*, server_config.*). Added behavior (tools=true, reasoning=true, strips_thinking=true), param_translation.thinking (effort mode, maps none→low since always-on reasoning), input_map/output_map, scaling. Fixed context_window 65536→131072 to match ISVC max-model-len. Scale-to-zero enabled (minReplicas 0, 15m retention). 23/25 tests pass (2 expected failures: embed guard, bad model guard). No reasoning_content in responses (strips_thinking=true working). Tool calling works (OAI + Anthropic).
- gpt-oss-20b: Card updated with input_map/output_map/scaling blocks. Already had correct v2 behavior and param_translation. Scale-to-zero already enabled. 23/25 tests pass (2 expected failures). Same reasoning pattern as 120b (always-on, effort mode).
- phi-4-reasoning: ISVC modernized to `vllm serve /data` format (was `--model=/data`). Timeout 150→300. Annotation 900s→15m. Card already correct v2 with budget mode thinking. 19/20 tests pass (1 expected failure). Uses thinking_token_budget parameter (0=off, 4096/12288/24576 for effort levels). Some Anthropic tests returned empty text (max_tokens too small for model output format).
- qwen25-vl-72b-awq: ISVC crashed on 128K context (OOM on L40S 48GB). Reduced max-model-len to 65536. Modernized command from `python3 -m vllm.entrypoints.openai.api_server` to `vllm serve` format. Updated card context_window to 65536. AWQ weights ~20 GiB/GPU with TP2. Encoder cache budget 65536 tokens. Cold start ~3 min (torch.compile). 16/18 tests pass (2 expected failures). Vision confirmed working with base64 images.
- qwen3-235b: confirmed non-thinking Instruct-2507 variant — `reasoning_model: false` is correct, no reasoning parser needed.
- qwq-32b: always-on reasoning (deepseek_r1 parser), no thinking toggle. Tools via hermes. ISVC was stuck (Stopped since June 6), deleted+recreated to fix. 21/21 tests pass.
- qwen25-coder-32b: non-reasoning code specialist. No thinking parser needed. Tools via hermes. 131K native context deployed at 32K. ISVC was stuck, deleted+recreated. 22/22 tests pass. Cold start ~90s.
- qwen25-vl-72b: vision-language model (72.2B dense, TP4). No tools, no reasoning. Dynamic-resolution images, video, up to 20 images per prompt. 64K deployed context (128K max positions). max-num-seqs reduced to 4 for KV headroom. ISVC was stuck, deleted+recreated. 22/22 tests pass. Cold start ~285s.
- qwen25-vl-7b: vision-language + tools (7B dense + ViT, TP1 gpumem 32GB). Hermes tool parser (forced, model has no native tool_call_parser). Vision (dynamic-res, video, 20 images), 65K context. ISVC was stuck, deleted+recreated. 22/22 tests pass. Cold start ~120s.
- qwen25-vl-3b: vision-language only (3B dense + ViT, TP1 gpumem 24GB). No tools, no reasoning. Vision (dynamic-res, video, up to 20 images, OCR), 64K ctx (KV cache ~2.3GB fits in 24GB slice). ISVC was stuck, deleted+recreated. 18/18 tests pass. Cold start ~120s.
- qwen36-35b-a3b: Hybrid Gated-DeltaNet MoE (35B total, 3B active, 256 experts). Thinking + tools + vision. Reasoning via qwen3 parser with effort mode (NOT on by default — needs enable_thinking=true). Tools via qwen3_coder. Vision (ViT encoder, images+video). 256K native ctx deployed at 64K. vLLM v0.20.2, TP2 whole-device. Card was completely wrong (said no vision/tools/reasoning). ISVC was stuck, deleted+recreated. 21/21 tests pass. Cold start ~285s.
- gemma-4-26b-a4b: Google Gemma 4 MoE (25.2B total/3.8B active, 128 experts, FP8). Reasoning + tools + vision. Card rewritten to v2 (was v1 with compatibility.*). Reasoning via gemma4 parser (effort mode, reasoning_effort param). Tools via gemma4 native parser. Scale-to-zero enabled (minReplicas 0). 22/25 tests pass (1 vision-URL failure, external image fetch doesn't work in cluster). Cold start ~4 min (FP8 MoE, torch.compile).
- gemma-3-4b-it: Google Gemma 3 4B Instruct with SigLIP vision. No tools, no reasoning. Card was nearly v2 — added image input_map, output_map descriptions. ISVC already correct (v0.20.2, 64K ctx, scale-to-zero). 17/20 tests pass (1 vision-URL failure). Cold start ~2 min.
- medgemma-27b-it: Google MedGemma 27B (Gemma 3-based, medical multimodal). SigLIP medical image encoder. Card rewritten to v2. ISVC modernized: max-model-len 8K→32K, vllm serve format, max-num-seqs=4, timeout 300s. Context aligned to 32K across card/ISVC/CLAUDE.md. 17/20 tests pass (1 vision-URL failure). Cold start ~4 min (27B BF16 TP2).
- All 3 Google models had `serving.kserve.io/stop: "true"` annotation from prior stop — had to `kubectl annotate isvc <name> serving.kserve.io/stop-` to wake them.
- **glm-4-32b**: Zhipu-AI GLM-4-32B (32B dense, TP2). Card rewritten to v2 Template A. ISVC modernized to `vllm serve` with `--tool-call-parser=glm45 --enable-auto-tool-choice`. No reasoning parser (non-reasoning model). glm45 tool parser doesn't produce structured `tool_calls` — model returns text responses referencing tools instead of proper function call format. 15/19 tests pass (2 expected failures: embed guard + bad model, 2 tool calling failures: glm45 parser limitation). Known issue: GLM uses proprietary tool format not fully convertible by vLLM's glm45 parser.
- **glm-z1-32b**: Zhipu-AI GLM-Z1-32B-0414 (32B dense, TP2). Reasoning + tools model. Card rewritten to v2 with `param_translation.thinking: {mode: "toggle", default: true}`. ISVC has `--tool-call-parser=glm45` but NO reasoning parser — `--reasoning-parser=glm45` crashes because it maps to DeepSeekV3ReasoningParser which expects `<think</think` tokens not present in GLM tokenizer. Thinking is always-on via chat template (not extracted as reasoning_content). glm45 tool parser has same limitation as glm-4-32b. 17/20 tests pass (1 expected, 2 tool calling failures).
- **glm-z1-rumination-32b**: Zhipu-AI GLM-Z1-Rumination-32B-0414 (32B dense, TP2). Deep reasoning/extended thinking model. Custom tools are IGNORED by rumination chat template. Custom system prompts are IGNORED. Card rewritten to v2 with `supports_tools: false`, `supports_system_prompt: false`. ISVC has NO parsers at all (no tool parser, no reasoning parser — both crash or are irrelevant). 32K context. Thinking always-on via template.
- GLM reasoning parser incompatibility: vLLM's `--reasoning-parser=glm45` maps to `DeepSeekV3ReasoningWithThinkingParser` which expects `<think</think` tokens in the tokenizer. GLM-Z1 models don't have these tokens — the parser crashes at startup. The model still thinks (it's in the chat template), but reasoning_content won't be extracted separately. No workaround until vLLM adds a proper GLM reasoning parser.
