# gpt-oss-20b Notes

## Purpose
Primary reasoning-capable OSS chat model behind OpenAI and Anthropic compatible gateway endpoints.

## Runtime
- Runtime: vLLM OpenAI server
- Image: `vllm/vllm-openai:v0.20.2`
- API via gateway: `/v1/chat/completions`, `/v1/messages`

## Behavior in this platform
- Model is reasoning-capable.
- Gateway may strip reasoning fields from final responses to keep client output clean.
- For very small `max_tokens` requests, gateway may disable thinking unless explicitly requested,
  to avoid empty final answers.

## Resources / scheduling
- HAMi fractional GPU allocation via `nvidia.com/gpumem` in manifest.
- Confirm requested gpumem is sufficient for expected context + concurrency.

## Deploy checklist
1. Ensure `hf-token` secret exists in `models` namespace.
2. Apply PVC and InferenceService manifests.
3. Wait for pod readiness / first-load completion.
4. Validate OpenAI + Anthropic endpoint behavior (including reasoning levels).

## Validation smoke tests
- OpenAI: `reasoning_effort` levels accepted and produce answer text.
- Anthropic: adaptive effort / budget-style requests map successfully.
- No leaked reasoning/thinking content in response body when strip policy is enabled.
