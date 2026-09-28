# DeepSeek-V4-Flash

> **STATUS: REMOVED FROM CLUSTER 2026-09-27 — DO NOT DEPLOY ON THIS FLEET.**
> This NIM cannot run on Aleph's L40S (Ada) GPUs. The files in this directory
> are kept only as the deployment record. See Notes below.

NVIDIA NIM for DeepSeek-V4-Flash MoE chat.

- **Image:** `nvcr.io/nim/deepseek-ai/deepseek-v4-flash:latest`
- **Endpoint:** `POST /v1/chat/completions`
- **Type:** chat
- **GPU:** 4× L40S whole devices (`nvidia.com/gpu: 4`, no HAMi `gpumem`)
- **License:** DeepSeek

## Example request

```bash
curl -s https://inference.vulcan.alliancecan.ca/v1/chat/completions \
  -H "Authorization: Bearer <TYK_KEY>" \
  -H "Content-Type: application/json" \
  -d '{
    "model": "deepseek-v4-flash",
    "messages": [{"role": "user", "content": "Hello"}],
    "max_tokens": 128,
    "temperature": 0.7
  }'
```

## Notes

- 284B total / 13B active parameters, FP8 inference, up to 1M context.
- First cold start downloads the model into the PVC cache; subsequent starts reuse it.
- Scale-to-zero is enabled; the model idles down after 15 minutes.
- **Why it was removed (2026-09-27):**
  - **The NGC support matrix for this NIM is B200/H100/H200/H20 only — there
    is no Ada/L40S profile.** The container pulls and schedules fine, then
    fails at startup with `NIMProfileIDNotFound` and crashloops (623 restarts
    observed while the pod held 4 whole cards). This is not a scheduling,
    flag, or image-tag problem; nothing on the current fleet can fix it.
  - Doubly infeasible regardless: 284B FP8 ≈ 284 GB of weights vs 4× 48 GB =
    192 GB available.
  - Timeline: parked (details card deleted) 2026-09-25; the pod kept
    crashlooping and holding rack09-01's 4 L40S until 2026-09-27, when it was
    stopped (`serving.kserve.io/stop=true`), then the InferenceService, the
    PVC (`deepseek-v4-flash`, 200Gi) and its static PV were deleted at
    operator request. rack09-01's cards were reclaimed for other TP4 work.
- **If this is ever redeployed** (requires Hopper/Blackwell GPUs on the
  fleet): recreate the PVC first — the old one is deleted; verify the NGC
  secrets (`ngc-api-key`, `ngc-registry-secret`) still exist; and check the
  NGC matrix for the target GPU before applying these files.
