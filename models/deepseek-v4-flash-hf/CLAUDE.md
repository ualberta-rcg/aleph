# deepseek-v4-flash (HF) — operator notes

Deployment dir for public model id **`deepseek-v4-flash`**, served from the HuggingFace
checkpoint `deepseek-ai/DeepSeek-V4-Flash-0731` (MIT, ungated, 48 shards, 155.5 GiB).
K8s objects carry the `-hf` suffix; the card routes via `routing.k8s_name:
deepseek-v4-flash-hf` (deliberate dir≠id bend, operator decision 2026-09-27). Predecessor:
`models/deepseek-v4-flash/` (the NGC NIM — removed 2026-09-27; NGC matrix H100+ only).

## Runtime

- Image: stock `vllm/vllm-openai:v0.30.0` (newest release, 2026-09-22, carries the most
  DeepSeek-V4 work). Digest-pin at commit time like qwen38-27b does.
- Entry: `vllm serve /data/model --served-model-name=deepseek-v4-flash` TP4, parsers
  `deepseek_v4` (reasoning + tool-call), `--kv-cache-dtype fp8`, max-model-len 131072,
  util 0.95, max-num-seqs 4, `--disable-custom-all-reduce` (fleet TP rule),
  `VLLM_ATTENTION_BACKEND=TRITON_ATTN_VLLM_V1` (SM89 fleet rule).
- Why stock: operator direction 2026-09-27 — it runs on normal vLLM on other L40S
  clusters; my earlier fork-first plan was rejected. No special SM89 build, no
  venv-served runtime, no out-of-band staging: exactly the qwen38-27b pattern.
- First boot = helper venv + 155.5 GiB download inside the initContainer under a 3600s
  progress deadline (one-time); later wakes are engine-init only (~5-10 min).

## Research record (2026-09-27)

- Checkpoint facts (HF API): `DeepseekV4ForCausalLM`, fp8 quant + fp4 experts,
  DSpark draft heads in-checkpoint, no Jinja chat template in the repo (the
  `encoding/` scripts + tokenizer handle formatting; if stock vLLM needs an explicit
  `--tokenizer-mode`/template flag the first boot's argparse/logs will say — that is a
  settings-iteration item, not a redesign).
- Upstream vLLM release notes v0.28.0-v0.30.0 mention DeepSeek-V4 + DSpark throughout;
  sparse-MLA notes headline SM90/SM100/ROCm only — but release notes are not exhaustive
  and the operator reports stock vLLM serving this model on L40S elsewhere. **The first
  boot is the empirical decision gate.**
- Recommended sampling (HF card): temperature 1.0, top_p 0.95. reasoning_effort enum:
  low/high/max.

## Resources

- CPU 16 req / 32 lim; memory 96Gi / 128Gi; `nvidia.com/gpu: "4"` requests+limits
  (whole devices, NO gpumem — TP4 rule); shm 16Gi emptyDir.
- Placement: `gpu: on`, anti-control-plane affinity; no hard node pin (HAMi finds the
  node with 4 tenant-free cards — currently rack09-01 only, hence maxReplicas 1).

## Storage

- PVC `deepseek-v4-flash-hf`, 200Gi RWX `nfs-models`, dynamic class. Weights at
  `/data/model`, helper venv at `/data/venv` (download-only: huggingface_hub +
  hf_transfer; the serving runtime comes from the image, like all 28 vLLM models).
- Warm-cache condition: `/data/model/config.json` present → init skips download;
  `/data/venv/bin` present → skips venv build.
- The claim was created fresh for this deploy and was empty at first apply. If it ever
  needs repurposing for a different checkpoint, clear `/data/model` (and `/data/venv`)
  first — never delete the claim, never touch another model's PVC.

## API and card

- Public id `deepseek-v4-flash`; card ConfigMap `deepseek-v4-flash-details`; type chat;
  tools + system prompt true, vision false (gateway rejects image content).
- Thinking: `mode: effort`, enum low/high/max, aliases none→low / medium→high /
  xhigh,max→max; `off` = effort low + strip + `off_max_tokens` 2048. Same managed-thinking
  policy as gpt-oss-120b (always reasons internally; no fully-off mode).
- Meta-task max_tokens values are floors for reasoning models (gateway detail) — 384 is
  fine. `cold_start_estimate: "5-10 minutes"` → Retry-After 600s (largest integer × 60).

## Failed / rejected approaches (history)

1. **NGC NIM** (predecessor dir): `NIMProfileIDNotFound` crashloop — NGC matrix
   B200/H100/H200/H20 only. Removed from the cluster 2026-09-27 (ISVC + 200Gi PVC + PV
   deleted; that removal freed rack09-01's 4 cards for THIS deployment).
2. **yhfgyyf SM89-fork image + custom battery + out-of-band pre-stage pod** (this
   session, before the operator redirect): rejected — deploy must be the standard fleet
   pattern (stock image, helper venv only, in-ISVC staging). Fork wheel pins recorded
   below for reference.
3. **Stock vLLM v0.30.0 (2026-09-28, the definitive attempt — VERDICT: not
   L40S-compatible):** two full boots. Weight staging fine (155.5 GiB / 6 min);
   `DeepseekV4ForCausalLM` resolves; tokenizer_mode auto-defaults; **MARLIN MXFP4 MoE,
   fp8_ds_mla KV, FP8 indexer all select SM89-safe kernels** — but engine init dies at
   `deepgemm-src/csrc/apis/hyperconnection.hpp:56: Unsupported architecture`. The
   DeepSeek-V4 hyperconnection op is hard-wired to DeepGEMM (SM90+) in stock 0.30.0;
   **`--linear-backend=triton` does NOT bypass it** (verified — identical assert on
   boot 2). What's missing upstream is exactly the sparse-MLA/SM8x portability stack
   (vllm-project/vllm#55177 + #47629, Draft/needs-rebase as of 2026-09-27). Operator
   verdict: remove from cluster, record incompatibility. Serving this model on L40S
   needs a patched build:
   - fork image `ghcr.io/yhfgyyf/vllm-deepseek-v4-sm89:0.28.1rc1-vision11-sm89-sm120-cu130`
     (vllm wheel sha256
     `e1c8313e6a8b58ec3feecaffb37fc3fda8e61ba4ecff624853b24216b7eb97ed`, paired
     FlashInfer `0.6.18+glm53.dsv41.vision2.sm89sm120.cu130.pt213`, sha
     `078aa7682d699c67dce619fc8acf29ec41934ab5ba916268d1fe6f8850459de8`), or
   - wait for the upstream portability PRs to merge, or
   - whatever patched build other "normal vLLM on L40S" clusters actually run.
   Operational footnotes from the attempt: a crashlooping vLLM TP4 pod can wedge in
   Terminating past its 600s grace (hung multiproc + istio native sidecar) holding all 4
   whole cards — force-delete the pod object to release them; and `kubectl wait
   --for=delete` can time out while the pod later clears, so verify pods AND revisions
   explicitly before re-applying.

## Open items / continuation

- [ ] First boot: record attention + MoE backend selection, KV pool size (GiB + tokens),
      engine-init time, `nvidia-smi topo -m` from the pod.
- [ ] Decision gate: if engine init errors with an SM89/arch/kernel error, STOP, capture
      the exact error, report to the operator (fork = documented fallback, not default).
- [ ] Settings iteration candidates: `--kv-cache-dtype` (drop if rejected),
      `VLLM_ATTENTION_BACKEND` (drop if it conflicts with the DSv4 backend), max-num-seqs
      4→8 if the KV pool allows, DSpark `--speculative-config` (v0.30.0 knows DSpark) if
      the base serves cleanly.
- [ ] Battery until only PASS/EXP; then the s1-s7 stress suite; then the clean
      delete+redeploy proof (pods AND revisions cleared before re-apply).
- [ ] Digest-pin the image at commit time; dated CHANGELOG entry; MODEL-STATUS row.
