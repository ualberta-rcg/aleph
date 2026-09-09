# Qwen38-27b: live 256K boundary check

On 2026-09-09 a single synthetic OpenAI request through the running Aleph gateway passed near the 262144-token total context boundary. No separate engine was created and no model parameters were changed.

| Measurement | Result |
|---|---|
| Rendered input, counted by running tokenizer | 261888 tokens |
| Requested output allowance | 256 tokens |
| Combined requested budget | 262144 tokens |
| Server-reported prompt tokens | 261888 |
| Actual output / actual total | 33 / 261921 tokens |
| Completion | `stop`, complete SSE `[DONE]` |
| Beginning / middle / end markers | All three recalled |
| First output token | 119.75 seconds |
| Total long-request time | 120.15 seconds |
| Short controls before and after | Passed, 16 input + 2 output tokens each |
| Serving-pod restarts | Zero before and after |
| OOM / engine-death log counts | Zero in inspected interval |

Configuration: two whole GPUs, tensor parallel size 2, FP8 KV cache, memory utilization 0.88, max-model-len 262144, max-num-seqs 64, max-num-batched-tokens 16384. Engine image: `index.docker.io/vllm/vllm-openai@sha256:70a098d90dbab428a001d9e852fc0fc8d67da5beb03e7851a22247653bf35923`. Gateway: `gateway-b5e38cb`, digest `sha256:32986ae5c81ba03c85b8630e9390c209c3b8dacb2598a90fb7a3f652a32e8536`. Request used `reasoning_effort=none`, `temperature=0` and streaming usage reporting.

This establishes successful single-request near-boundary operation for synthetic text. It does not establish arbitrary-document recall, 256K concurrency, long-output generation, multimodal inputs, thinking-enabled boundary behavior or translated Anthropic token parity. The input contained repeated filler and three distinct markers. Short output means the actual sequence did not exhaust all 262144 tokens; the full requested budget was accepted and input accounting matched exactly.

The existing autoscaler requested a second predictor during the test; it was observed Pending afterward. No second model engine was manually deployed and no Pending pod was deleted. Existing autoscaling settings and serving capacity were preserved.

The companion `test-context-boundary.py` runs only when explicitly invoked with an internal gateway and tokenizer URL. It sends one long request without retries, enforces a 600-second inference deadline, and prints only counts/verdicts. Do not run the larger `stress.py` battery to reproduce this check.
