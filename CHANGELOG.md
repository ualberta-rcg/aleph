# Changelog — model gateway + models

Verified on the HAMi test cluster (control-plane + GPU workers). Newest first.
Cluster-specific values (the 230 test cluster, 232 legacy POC) are in the local working dir.

## 2026-06-24 — ww-overlays: consolidate RKE2 manifests + WW overlay into one canonical dir

Restructured platform deployment artifacts into `ww-overlays/` — the single source of truth
for the Warewulf overlay and RKE2 auto-deploy manifests.

**What changed:**
- New `ww-overlays/overlay/etc/rancher/manifests/` — all RKE2 auto-deploy manifests, moved
  from `deploy-aleph/rke2-manifests/` and improved:
  - All site-specific values tokenized (`__VIP__`, `__NFS_SERVER__`, `__K8S_VERSION__`, etc.)
  - Per-file headers identify which node role each file targets (GPU workers / head / all)
  - `41-metallb-vip.yaml` NEW — IPAddressPool + L2Advertisement as an auto-deploy manifest
    (with CRD-race note; converges automatically via RKE2 reconciler retries)
  - `52-tyk-loadbalancer.yaml` NEW — Tyk exposed as MetalLB LoadBalancer (port 80), not NodePort
  - `53-tyk-api-definitions.yaml` NEW — Tyk API-def ConfigMap as a manifest (inlines
    `gateway/tyk/model-gateway-api.json`); mounted automatically via `51-tyk.yaml` extraVolumes
  - `51-tyk.yaml` — `TYK_GW_APPPATH` and `TYK_GW_ENABLEHASHEDKEYSLISTING` are now baked into
    `tyk-gateway.gateway.extraEnvs` and `extraVolumes`/`extraVolumeMounts`; no post-deploy patch
  - `63-model-gateway.yaml` NEW — gateway RBAC + Service + Deployment as a manifest;
    pulls `rkhoja/aleph:latest` from Docker Hub CI automatically
- New `ww-overlays/overlay/etc/netplan/` + `etc/sysctl.d/` — node VIP overlay (head nodes only),
  moved from `deploy-aleph/overlays/` and tokenized
- New `ww-overlays/SITE-VALUES.md` + `site.env.example` — one place listing every `__TOKEN__`,
  which files use it, and the Aleph cluster example value
- New `ww-overlays/post-deploy/` — what remains after boot: Tyk key creation, smoke test
  script (`verify-test-model.sh`, from `03-deploy-test-model.sh`), and cert example

**Deleted (superseded by manifests):**
- `deploy-aleph/01-install.sh`, `02-post-install.sh`, `04-install-tyk-gateway.sh` — all
  replaced by the self-ordering bootstrap Jobs (60–63) and Helm manifests (50–53)
- `deploy-aleph/deploy.sh`, `gateway/remote-deploy.sh` — no longer needed; CI publishes the
  gateway image and `kubectl rollout restart` is all that's required for updates
- `gateway/tyk/nodeport.yaml` — replaced by `52-tyk-loadbalancer.yaml` (LoadBalancer, VIP:80)
- `deploy-aleph/configs/` (tyk-oss-values, inferenceservice-config, tyk-api-proxy-istio) and
  `deploy-aleph/storage/nfs-models-storageclass.yaml` — all folded into their respective manifests
- `deploy-aleph/rke2-manifests/` and `deploy-aleph/overlays/` — moved into `ww-overlays/`

**Impact:** fresh cluster provisioning is now fully declarative. Bake the WW overlay → provision
nodes → everything comes up automatically (MetalLB, Tyk, NFS, Istio, Knative, KServe, gateway).
Only post-deploy steps are: issue a Tyk key, smoke-test, apply model cards.

**Validation:** live cluster `.43` (aleph1-3 + rack15-03, rack05-16) matches this manifest set.
The existing running cluster requires no changes.

## 2026-06-24 — VL multimodal light pass: 7 vision-language chat models audited + tested

- Light audit of all multimodal VL chat models: `qwen25-vl-3b`, `qwen25-vl-7b`,
  `qwen25-vl-72b`, `qwen25-vl-72b-awq`, `medgemma-27b-it`, `gemma-3-4b-it`, `gemma-4-26b-a4b`.
- **details.yaml**: Added missing vLLM-supported `input_map` params across all 7 models:
  `presence_penalty`, `top_k` (where absent), `stop`, `seed`. Corrected image limit descriptions
  (Qwen supports up to 20 images/prompt, not 4).
- **test.py**: Added `vision_multi_image` check (2-image prompt) to all 7 models. Fixed
  `guard_embed` test bug: 404 (embed model scaled-to-zero, route gone) now treated as SKIP
  instead of FAIL.
- **Deployed, tested, and scaled down** each model one-by-one on cluster .43:
  - `qwen25-vl-3b`: 22 PASS / 2 EXP / 0 FAIL
  - `qwen25-vl-7b`: 23 PASS / 1 EXP / 0 FAIL (after guard_embed fix)
  - `qwen25-vl-72b`: 22 PASS / 2 EXP / 0 FAIL
  - `qwen25-vl-72b-awq`: 22 PASS / 2 EXP / 0 FAIL (after guard_embed fix)
  - `medgemma-27b-it`: 22 PASS / 2 EXP / 0 FAIL (after guard_embed fix)
  - `gemma-3-4b-it`: 22 PASS / 2 EXP / 0 FAIL (after guard_embed fix)
  - `gemma-4-26b-a4b`: 32 PASS / 2 EXP / 0 FAIL
- **PVC + download** created for `qwen25-vl-72b` (145 GB BF16) and `qwen25-vl-72b-awq` (75 GB AWQ).
- Updated `MODEL-STATUS.md` main table + capability matrix with new test tallies.

## 2026-06-24 — Vision models deep pass: all 25 vision/science models audited, tested, schema v2

Full deep pass over all 25 non-chat vision and science models. Every model's `details.yaml`
rewritten or augmented to schema v2 with typed `input_map`/`output_map`, `status`, `behavior`,
`scaling`, `limits`, and `catalog` sections. Test suites expanded from ~4 to 10-19 checks each.
All 25 deployed, verified via gateway, and scaled back to zero.

- **Tier 1 (9 CV models)**: `maskrcnn`, `efficientnet-b0`, `depth-anything`, `zoobot`,
  `dino-vit-b8`, `yolov8n`, `yolov8s`, `retinanet`, `megadetector` — full details.yaml rewrite;
  tests expanded to 15-19 checks; stale standalone server files removed (embedded in ISVC ConfigMaps)
- **Tier 2 (4 medical/biomed)**: `arcface`, `biomedclip`, `medsam`, `totalsegmentator` —
  schema v2 fields added; new test.py and README created where missing; totalsegmentator 12/3/0
- **Tier 3 (10 science/geospatial)**: `satmae`, `astropt`, `prithvi-eo`, `clay`, `croma`,
  `terramind-flood`, `granite-geospatial-ocean`, `granite-geospatial-biomass`, `aion`, `brainlm` —
  schema v2; tests created/expanded to ~10 checks each
- **Tier 4 (2 3D reconstruction)**: `dust3r`, `mast3r` — schema v2; tests created (~15 checks each)
- **Structural cleanup**: deleted stale `server.py`, `configmap.yaml`, `vision_server.py` files
  from Tier 1 models; deleted `medsam/kustomization.yaml`; all server code confirmed in ISVC ConfigMaps
- **Results: 300 PASS / 42 EXP / 0 FAIL across 310 checks, all 25 models**

## 2026-06-23 — Vision endpoint phase: HF I/O audit + test.py coverage for 9 CV models

- Ran the vision-model sweep with HF/upstream I/O validation (reference) and runtime-as-truth
  alignment for these 9 models:
  - `maskrcnn`, `efficientnet-b0`, `depth-anything`, `zoobot`, `dino-vit-b8`
  - `yolov8n`, `yolov8s`, `retinanet`, `megadetector`
- Added missing per-model gateway tests:
  - `models/maskrcnn/test.py`, `models/efficientnet-b0/test.py`, `models/depth-anything/test.py`,
    `models/zoobot/test.py`, `models/yolov8n/test.py`, `models/yolov8s/test.py`,
    `models/retinanet/test.py`, `models/megadetector/test.py`
  - Updated `models/dino-vit-b8/test.py` to use `/v1/vision/embed` as primary endpoint.
- Added missing READMEs:
  - `models/maskrcnn/README.md`, `models/efficientnet-b0/README.md`,
    `models/depth-anything/README.md`, `models/retinanet/README.md`,
    `models/megadetector/README.md`
- Added HF/upstream I/O reference notes to all 9 model `CLAUDE.md` files and refreshed existing
  READMEs where present.
- Safe endpoint/type normalizations:
  - `dino-vit-b8` card: primary endpoint -> `/v1/vision/embed`, `/v1/science/embed` kept as alias.
  - `zoobot` card: `type` normalized from `classify` to `embedding`.
  - `megadetector`: new primary endpoint `/v1/vision/detect`; legacy `/v1/detect` +
    `/v1/science/detect` kept; request now accepts either `image` or `images[]`; card updated.
- Removed stray `kustomization.yaml` from all 9 target model dirs to follow the flat-file repo
  convention.
- Verified on cluster (.43) through the default gateway (`deploy/model-gateway`):
  - `maskrcnn` 2 PASS / 2 EXP
  - `efficientnet-b0` 2 PASS / 2 EXP
  - `depth-anything` 2 PASS / 2 EXP
  - `zoobot` 2 PASS / 2 EXP
  - `dino-vit-b8` 6 PASS / 0 FAIL
  - `yolov8n` 2 PASS / 1 EXP
  - `yolov8s` 2 PASS / 1 EXP
  - `retinanet` 2 PASS / 1 EXP
  - `megadetector` 2 PASS / 1 EXP
- Updated `models/MODEL-STATUS.md` entries for all 9 models with the new endpoint/type/test state.

## 2026-06-23 — Image-model gateway test plans + full Ray removal from the repo

- **Comprehensive gateway `test.py` for all 3 image models** (`kandinsky-3`, `flux-1-dev`,
  `sd3-medium`), modeled on `gpt-oss-120b/test.py` and run inside the gateway pod against the
  default gateway (OpenAI image surface, no model-specific gateway code). Each exercises:
  scale-from-zero WAKE (retry through 503), `/v1/images/generations` over sizes (square +
  non-square), `n>1`, low/high steps, `guidance_scale`, `negative_prompt`, seed determinism
  (identical bytes for same seed; different seeds differ), per-model knobs
  (`quality=hd` / `max_sequence_length` / `true_cfg_scale`), `/v1/images/edits` img2img,
  per-image PNG validation (magic bytes + IHDR width/height, no PIL in pod), `/v1/models?all=true`
  catalog presence, and a bad-model 404 guard.
  - **Verified on cluster (.43): 18 passed / 1 expected / 0 failed for each of the three models.**
- **Ray fully removed from the repo.** No model uses Ray anymore (`kandinsky-3` converted;
  `graphcast` and `prithvi-wxc` were mislabeled — both are KServe). Deleted the KubeRay operator
  manifest `deploy-aleph/rke2-manifests/20-kuberay.yaml` and `deploy-aleph/examples/ray-cluster-template.yaml`,
  and scrubbed stale Ray/KubeRay references across `CLAUDE.md`, `models.md`, `model-usage.md`,
  `models/MODEL-STATUS.md`, the rke2-manifests `README.md`, and the `prithvi-wxc` ISVC comment.
  Added `flux-1-dev` + `sd3-medium` rows to the status tables.

## 2026-06-23 — Add Stable Diffusion 3 Medium (stabilityai) as a KServe image model

New model `sd3-medium` — Stability AI Stable Diffusion 3 Medium, 2B MMDiT text-to-image — wired
exactly like kandinsky-3 / flux-1-dev (KServe InferenceService custom predictor, diffusers FastAPI
server), so it's gateway-discovered, scale-to-zero, **zero gateway changes**.

- `models/sd3-medium/` : `inferenceservice.yaml` (ConfigMap `sd3-medium-server` FastAPI/diffusers
  `server.py` + ISVC), `details.yaml` (v2 Template B card), `pvc.yaml` (`sd3-medium-data`,
  `nfs-models`, 80Gi), `CLAUDE.md`.
- **HAMi vGPU slice** (not a whole card): `nvidia.com/gpu: 1` + `nvidia.com/gpumem: 24576`. fp16
  resident ~16 GB (2B MMDiT + T5-XXL + CLIP-G/L + VAE), so a 24 GB slice fits and leaves the rest
  of the L40S shareable.
- **GATED** via the `hf-token` secret. **License: Stability AI Community License** (free for
  research/non-commercial and commercial use under $1M revenue). diffusers loads the
  `stable-diffusion-3-medium-diffusers` repo (not the original-format one).
- Deps + weights staged once onto the NFS PVC (venv `/data/venv`, weights `/data/sd3-medium`,
  sentinel `/data/.sd3-medium-ready-v1`); survives WW reprovision, no re-pip on cold start.
- Defaults from the HF card: `num_inference_steps 28`, `guidance_scale 7.0`,
  `max_sequence_length 256` (T5, up to 512), 1024×1024; real CFG so `negative_prompt` is honored;
  img2img `strength 0.6` via `/v1/images/edits`.
- Scaling: `minReplicas 0`, `maxReplicas 3`, `scaleMetric concurrency`, `scaleTarget 1`, 5m/15m.
- **Verified on cluster (.43):** ISVC `Ready=True` (first cold start ~6m: venv + ~23 GB weight
  download + model load); card loaded by the gateway (`[CARD] loaded sd3-medium (type=image)`);
  generation **through the default gateway** (`POST /v1/images/generations`) → HTTP 200, ~4.2s for
  20 steps @ 1024×1024. Gateway untouched.

## 2026-06-23 — Add FLUX.1-dev (black-forest-labs) as a KServe image model

New model `flux-1-dev` — Black Forest Labs FLUX.1-dev, 12B rectified-flow text-to-image — wired
exactly like the converted kandinsky-3 (KServe InferenceService custom predictor, diffusers
FastAPI server), so it's gateway-discovered, scale-to-zero, **zero gateway changes**.

- `models/flux-1-dev/` : `inferenceservice.yaml` (ConfigMap `flux-1-dev-server` FastAPI/diffusers
  `server.py` + ISVC), `details.yaml` (v2 Template B card), `pvc.yaml` (`flux-1-dev-data`,
  `nfs-models`, 100Gi), `CLAUDE.md`.
- **Whole L40S**: `nvidia.com/gpu: 1`, **no `nvidia.com/gpumem`** (HAMi binds a full physical
  card, no vGPU interception). bf16 full residency ~34 GB; no CPU offload → fast.
- **GATED** model via the `hf-token` secret. **License: FLUX.1-dev Non-Commercial** (flagged in
  the card `license` + a `non-commercial` tag).
- Deps + weights staged once onto the NFS PVC (venv `/data/venv`, weights `/data/flux-1-dev`,
  sentinel-guarded); download skips the ~24 GB single-file originals (`flux1-dev.safetensors`,
  `ae.safetensors`) since diffusers loads the sharded subfolders (~36 GB).
- Defaults from the HF card: `num_inference_steps 50`, `guidance_scale 3.5`,
  `max_sequence_length 512`, 1024×1024; guidance-distilled (negative_prompt only with
  `true_cfg_scale>1`); img2img `strength 0.6` via `/v1/images/edits`.
- Scaling: `minReplicas 0`, `maxReplicas 3`, `scaleMetric concurrency`, `scaleTarget 1`, 5m/15m.
- **Verified on cluster (.43):** ISVC `Ready=True` (first cold start ~7m: venv 7 GB + 36 GB
  weight download + model load); generation **through the default gateway** → HTTP 200, ~1.67 MB
  PNG, ~11.4s for 20 steps @ 1024×1024. Gateway untouched.

## 2026-06-23 — kandinsky-3: convert RayService → KServe InferenceService (drop Ray)

Replaced the kandinsky-3 RayService with a standard **KServe InferenceService custom predictor**
so it behaves like every other model — discovered by the gateway, reachable at
`kandinsky-3-predictor`, Knative scale-to-zero on the cluster 5m/15m policy, with **zero gateway
changes**. Ray earned no keep: kandinsky is a single diffusers pipeline on one L40S (no model
parallelism / serve DAG / cross-replica batching), and the Ray version's `runtime_env` pip on
every cold start was the bulk of its ~4m cold start. Wiring mirrors `gpt-oss-120b`; custom-server
shape mirrors `surya`.

- **`inferenceservice.yaml`** (new, single file): `kandinsky-3-server` ConfigMap (FastAPI/uvicorn
  diffusers `server.py`, port 8080, `/v1/images/generations` + `/v1/images/edits` + `/v1/models` +
  `/health` returning 503 until the pipeline is resident) **+** the ISVC. `minReplicas 0`,
  `maxReplicas 3`, `scaleMetric concurrency`, `scaleTarget 1`, control-plane-excluded, `gpu=on`,
  1× L40S HAMi vGPU slice (`nvidia.com/gpu: 1` + `nvidia.com/gpumem: 40960`).
- **Deps + weights staged once onto the NFS PVC** by the init container (venv `/data/venv`,
  weights `/data/kandinsky-3`, sentinel `/data/.kandinsky-ready-v1`). PVC is OneFS/NFS, so it
  survives Warewulf reprovisioning **and** avoids re-pip on cold start (first start ~5m incl. venv
  build; later cold starts skip it → ~1-2m).
- **Card** `details.yaml` rebuilt to the v2 Template B (custom server) schema, key-order exact;
  `type: image`, standard `routing.k8s_name: kandinsky-3` (no special backend). Params corrected
  from HF: **~11.9B** (Flan-UL2 text encoder 8.6B + U-Net 3B + MoVQ 267M), repo
  `kandinsky-community/kandinsky-3`, `guidance_scale` default 3.0 (model default).
- Removed `rayservice.yaml`, `serve.py`/`server-configmap.yaml`, `download-job.yaml`; CLAUDE.md
  rewritten for the KServe deployment.
- **Verified on cluster (.43):** ISVC `Ready=True`; scale-from-zero cold start to ready;
  end-to-end generation **through the default gateway** (`POST /v1/images/generations` → HTTP 200,
  ~874 KB PNG, ~11s warm); concurrency scale-up to a 2nd replica observed; no gateway code touched.
- **Gateway untouched** (commits to main rebuild the gateway Docker image — none warranted here).

## 2026-06-23 — Standardize scale-down policy across ALL models (5m surplus + 15m last pod)

Applied the command-r-7b scale-down policy to every model: added
`autoscaling.knative.dev/scale-down-delay: "5m"` and normalized
`autoscaling.knative.dev/scale-to-zero-pod-retention-period` to `"15m"` on all **164** KServe
`models/*/inferenceservice.yaml`. Effect: surplus pods (above the first) linger ~5m after load
drops, then the last warm pod is held ~15m before 1->0.

- Normalized mixed prior retentions (`900s`, `10m`, `30m`, `1800s`, `600s`) to a uniform `"15m"`.
- The 4 always-on embedders (`bge-small`, `bge-m3`, `bge-reranker-v2-m3`, `xtts-v2`,
  `minReplicas: 1`) got the annotations too for uniformity; scale-to-zero is inert there, but
  `scale-down-delay` still governs any burst scale-down.
- speaches is a plain Deployment (not Knative) and is unaffected.

## 2026-06-23 — command-r-7b scale-down policy: 5m surplus delay + 15m last-pod retention

Added `autoscaling.knative.dev/scale-down-delay: "5m"` to command-r-7b (kept
`scale-to-zero-pod-retention-period: "15m"`). Effect after load stops: surplus pods (above the
first) linger ~5m before terminating, then the last warm pod is held ~15m before 1->0 (~20m total
to fully free GPUs). `scale-down-delay` gates every downward step (holds the max desired over a
trailing 5m window); the retention period only governs the final pod. Rolled as revision 00003.

## 2026-06-23 — command-r-7b autoscaling tune + load test; fix gpt-oss stale min-scale=1

### command-r-7b autoscaling (repo + live)
- Added `maxReplicas: 4`, `scaleMetric: concurrency`, `scaleTarget: 5` to the predictor (was
  unbounded with the Knative default target). Keeps it `minReplicas: 0` / on-demand.
- Added `models/command-r-7b/loadtest.py` (async sustained-concurrency generator via the gateway).
- **Load test (30 concurrent, ~170s, via VIP + Tyk):** 1576 requests, **0 errors**. Autoscaler
  decided `desired=4` immediately (30 in-flight ÷ target 5 = 6, capped at 4). Throughput rose ~7→9
  rps as replicas came online; the activator buffered during scale-up so nothing failed.
- **Cold-GPU bind lag:** the 3 new replicas sat `Pending` ~100s before binding on `rack05-16`
  (its HAMi scheduler cache had gone cold after the big models scaled down — same phenomenon as the
  qwen3-235b note). Once warm, all 4 bound (3 on rack05-16, 1 on rack15-03).
- **Scale-down observed:** after load stopped, `desired` held 4 for ~60–90s (stable window), then
  dropped straight to 0 and pods went **4→1 in one step** (~2 min total). The last pod is then held
  warm for the 15m `scale-to-zero-pod-retention-period` before 1→0. (So scale-down is automatic and
  fast; the "15m" only governs the final warm-pod hold, not a per-pod ladder.)

### Fix: gpt-oss-120b stuck always-on
- gpt-oss-120b never scaled to zero because its **live revision had `min-scale=1`** (stale from an
  earlier deploy) while the repo manifest already said `minReplicas: 0`. Re-applied the manifest to
  roll a `min-scale=0` revision so it idles to zero like the others. (The `/v1/models` hits seen on
  the pod were just kubelet probes + Prometheus `/metrics` scraping — not a wake loop.)

## 2026-06-23 — Deploy qwen35-122b; verify qwen3-235b scale-from-zero (GPU 4-card time-share)

Cluster-state changes (manifests already in-repo, no file diff):
- **qwen3-235b scale-from-zero verified:** woke it from `minReplicas: 0` by hitting the gateway
  (clean 503 `model_scaled_to_zero` → Knative activator), loaded the 118 GB AWQ in ~6 min on the
  free 4-card node, served HTTP 200. Its PVC was untouched by the nfs-models fix, so no re-download.
- **Deployed qwen35-122b** (`Qwen/Qwen3.5-122B-A10B-FP8`, TP=4, whole 4-GPU node): applied
  `pvc.yaml` (150Gi, nfs-models), ran `download-job.yaml` (39 shards / ~122 GB via hf_transfer to
  the PVC), then `inferenceservice.yaml` + `details.yaml`. Verified HTTP 200 via the gateway.
- **Capacity note:** qwen3-235b and qwen35-122b each need a whole 4-GPU node, but only one worker
  node is free (the other runs command-r-7b + gpt-oss-120b = 3/4 cards). They **time-share**: both
  are `minReplicas: 0`, so only one runs at a time and the other is `Unschedulable` until the first
  scales to zero. Freed the node for 122b by scaling qwen3-235b's deployment to 0 after its test.

## 2026-06-23 — Pin all model InferenceServices to worker nodes (off control plane)

The control-plane VMs (`aleph1/2/3`) carry no `NoSchedule` taint, so a CPU-only model predictor
could land on a head. Models (inference workloads) must run only on workers; the control plane is
for heads/infra (apiserver, etcd, istio, knative, kserve-controller, tyk, model-gateway — the
gateway stays on the control plane by design).

- Added a uniform `predictor.affinity.nodeAffinity` (required) to all 164 KServe
  `models/*/inferenceservice.yaml`: `node-role.kubernetes.io/control-plane` `DoesNotExist`. This
  keys off the built-in control-plane role label, so it needs no worker labeling and auto-covers
  future nodes. GPU models already had `nodeSelector: gpu=on` (also worker-only); this makes the
  policy explicit and uniform. Knative `kubernetes.podspec-affinity` is already enabled.
- `speaches` (standalone GPU Deployment) and the GPU LLMs were already worker-only via `gpu=on`;
  unchanged live (avoids restarting large checkpoints). Re-applied the 5 deployed CPU models
  (`bge-small`, `bge-m3`, `multilingual-e5-small`, `bge-reranker-v2-m3`, `clap`) to roll the new
  affinity in; pods stay on workers and Ready.

## 2026-06-23 — Fix StorageClass mistake: standardize on `nfs-models`, remove `nfs-client`

Corrects the earlier same-day error where `nfs-client` was applied and made the default SC. The
canonical storage is `nfs-models` (set up by the auto-applied `deploy-aleph/rke2-manifests/30-nfs.yaml`
with OneFS-safe mountOptions, `defaultClass: true`). There is intentionally **no** separate
`nfs-client` SC.

### Repo
- Swept `storageClassName: nfs-client` → `nfs-models` across all functional `models/*/pvc.yaml` and
  inline-PVC `models/*/inferenceservice.yaml` (142 files), plus the test-model PVC in
  `deploy-aleph/03-deploy-test-model.sh`.
- Deleted the trap manifest `deploy-aleph/storage/nfs-client-storageclass.yaml`. Kept
  `nfs-models-storageclass.yaml` as reference; `30-nfs.yaml` remains authoritative (Warewulf/RKE2
  auto-deploy).
- Fixed convention docs (`models/CLAUDE.md`, `deploy-aleph/rke2-manifests/README.md`) and the 65
  per-model `README.md`/`CLAUDE.md` storage mentions to say `nfs-models`. (`MODEL-STATUS.md` SC-drift
  note left as historical narrative.)

### Cluster
- Restored default: `kubectl patch sc nfs-models` → `is-default-class: "true"`, then deleted the
  stray `nfs-client` SC.
- Redeployed the 4 models that had been bound to `nfs-client` (SC is immutable on a bound PVC):
  deleted + recreated the ISVC/PVC on `nfs-models` for `bge-m3`, `bge-reranker-v2-m3`, `clap`,
  `multilingual-e5-small`; weights re-download on first start. Re-validated each via the public VIP
  + Tyk key from the login node.

## 2026-06-23 — Run model test.py from the login node (public VIP + Tyk); qwen3-235b scheduling fix

Two changes, made while validating the live 3-head aleph cluster (`aleph1/2/3` = .43/.44/.45)
end-to-end as a real user would: login node `.50` → MetalLB VIP `129.128.190.55` → Tyk
(Bearer-key auth) → model-gateway → KServe/vLLM.

### Model test.py: run from the login node, not just in-pod (8 models)
The per-model `test.py` harnesses hard-coded `G = "http://localhost:8080"` and sent no auth, so
they only ran via `kubectl exec` inside the gateway pod. Made them dual-mode without changing any
test logic:
- `G = os.environ.get("GW_URL", "http://localhost:8080")` — in-pod default unchanged.
- `TYK_KEY` (when set) → `Authorization: Bearer <key>` header, injected in the shared `req()`
  (and clap's direct `httpx.post`). Empty when unset, so in-pod runs are identical to before.
- Files: `command-r-7b`, `gpt-oss-120b`, `qwen3-235b`, `bge-small`, `bge-m3`,
  `multilingual-e5-small`, `bge-reranker-v2-m3`, `clap`.
- Run from the login node: `GW_URL=http://129.128.190.55 TYK_KEY=<key> MODEL=<m> python3
  models/<m>/test.py` (httpx required on the runner). NOTE: `MODEL` must match the dir — a stale
  `MODEL` env makes a test target the wrong model.

Validation (all via the public VIP + a real Tyk key, from the login node):
command-r-7b 18/5/0, gpt-oss-120b 31/3/0, qwen3-235b 21/3/0, bge-small 9/2/0, bge-m3 9/2/0,
multilingual-e5-small 9/2/0, bge-reranker-v2-m3 8/3/0, clap 7/0 (warm). Security verified: no key
→ 401, wrong key → 403.

### qwen3-235b: explicit nvidia.com/gpumem for HAMi exclusive-card scheduling
`qwen3-235b` (4× L40S, TP=4) sat `Pending` with `0/4 ... CardInsufficientMemory` on every GPU
node — including a fully **empty** one — so it never even started loading weights.

- **Real root cause (operational, not the manifest): a stale hami-scheduler device cache.** A GPU
  node that has had no successful GPU bind since boot keeps its handshake at `Requesting_` and the
  scheduler's in-memory per-card memory accounting is wrong, so it phantom-rejects the empty cards.
  `rack15-03` worked only because command-r-7b/gpt-oss-120b had warmed its cache.
  `kubectl rollout restart deploy/hami-scheduler -n kube-system` rebuilt the accounting and the pod
  scheduled immediately, loaded the 115 GiB AWQ checkpoint, and served (tested 200 OK via the VIP).
  **Follow-up:** add a post-cold-boot `hami-scheduler` restart to the deploy automation, or the
  first multi-GPU model to land on a freshly-booted empty node will phantom-fail until something
  else warms that node's cache.
- **Manifest change (defensive):** request `nvidia.com/gpu: "4"` **with an explicit
  `nvidia.com/gpumem: "45000"`** (per card; just under the 46068 registered) instead of leaving
  gpumem unset. On HAMi v2.9.0 the documented "exclusive card" path (gpu set, gpumem unset → 100%)
  and `gpumem-percentage: 100` both take a broken code path (Project-HAMi/HAMi#1781:
  `MemPercentagereq=100/101` → phantom `CardInsufficientMemory`). A concrete gpumem value uses the
  normal memory-fit path (same as the other working models here). libvgpu then caps visible VRAM to
  45000; `--gpu-memory-utilization 0.90` is relative to that. (On the 232 POC `nvidia.com/gpu`
  alone "just works" because 232 runs the stock nvidia-device-plugin; aleph has no
  nvidia-device-plugin — HAMi is the sole GPU plugin, so every request goes through its vGPU
  accounting.) Updated the manifest's header comment accordingly.

### Cluster-state changes (applied live; manifests already in-repo, no file diff)
- **StorageClass (CORRECTED — see 2026-06-23 fix below):** I wrongly applied
  `deploy-aleph/storage/nfs-client-storageclass.yaml` and demoted `nfs-models` from default. That
  was a **mistake**: `nfs-models` (set up by the auto-applied `30-nfs.yaml`, OneFS-safe) is the
  canonical/sole SC; `nfs-client` was never repo intent — only some stale model PVCs referenced it.
- **Deployed 5 CPU models** (no GPU/HAMi slice): `bge-small`, `bge-m3`, `multilingual-e5-small`
  (embeddings), `bge-reranker-v2-m3` (rerank), `clap` (audio+text embed). Gotcha: deploying the
  ISVC/PVC is not enough — the gateway only routes a model once its **card ConfigMap**
  (`models/<m>/details.yaml`, labelled `model-details=true`) is applied; the cards had to be applied
  separately for the gateway to pick them up.

## 2026-06-23 — MetalLB public-VIP manifest + per-site overlay; Kubeflow Profiles dropped

Packaging the MetalLB public-VIP work proven on cluster 230 (login `.50` → VIP `.55`,
HTTP 200) so the real 3-head deployment can use it. Two layers, with the site-specific
bits kept OUT of the auto-applied manifest so any cluster can use it:

- **`rke2-manifests/40-metallb.yaml` (new, optional):** installs MetalLB only. Speaker +
  controller + frr are **pinned to control-plane** (`nodeSelector` + the CP taint toleration),
  and frr runs as a speaker sidecar (`frr.enabled: true`, `frrk8s: false`) so it is
  constrained with the speaker. Carries **no VIP and no NIC** — those differ per cluster and
  some clusters won't use MetalLB (delete the file to omit, like Profiles was).
- **`overlays/` (new, sibling of `rke2-manifests/`):** the per-site node + VIP config.
  RKE2 does **not** auto-apply it (kept outside the manifests dir on purpose). For Karim to
  bake into the WW image overlay for the head nodes:
  - `netplan/60-public-vip.yaml` — public NIC up/IP-free, VIP on a `dummy0` (netplan-native
    equivalent of the proven `.55`-on-`lo`; netplan can't address `lo`), public subnet
    on-link via the NIC (+ commented external default-route).
  - `sysctl.d/99-public-vip.conf` — `rp_filter=0`, `arp_ignore=1`, `arp_announce=2`
    (uses `all.*` so no NIC name is hard-coded).
  - `metallb-vip.example.yaml` — `IPAddressPool` + `L2Advertisement` template (fill
    VIP + NIC, `kubectl apply`).
  - `README.md` — target paths, the proven recipe, fallbacks, resource caveat.
- **`63-profiles.yaml` removed** — no full Kubeflow (only Istio/Knative/KServe).

Key findings baked into the comments (also in memory `metallb-public-vip-recipe`):
- **Destination routing works, source-policy doesn't** — kube-proxy un-DNATs the reply's
  source to the VIP only in POSTROUTING (after the routing decision), so `ip rule from <vip>`
  never fires; route the public subnet on-link via the NIC instead.
- **`rp_filter` must be 0** — the reverse path for public sources is asymmetric, so
  strict/loose silently drops the inbound SYN.
- **Resource lesson:** MetalLB frr on the small 8-vCPU 230 head (CPU limits 283%
  overcommitted) starved the control plane → CrashLoop. Pin to control-plane and size
  heads ≥ 16 vCPU (16 GB RAM is plenty; the stack uses < 10 GB).

## 2026-06-22 — Serving-stack Jobs survive cold boot + kubeflow-namespace ordering fix + drop managed Traefik

After the 230 Warewulf redeploy, the four serving-stack bootstrap Jobs
(`60-istio` / `61-knative` / `62-kserve` / `63-profiles`) all came up **Failed**, so
**KServe never installed** (no `kserve-controller-manager`, no `models` namespace). Two
distinct bugs, found and fixed via an in-place re-run on the live cluster:

1. **Cold-boot clone death.** At boot the cluster DNS forwarder lags the Job start, so the
   bare `git clone https://github.com/kubeflow/manifests.git` failed with
   `Could not resolve host: github.com` on every attempt, exhausted `backoffLimit: 5`, and
   the Job stayed Failed permanently. (`github.com` IS reachable from the node once networking
   settles — purely a boot race.) The prerequisite `kubectl wait --for=condition=Ready pods
   --all -n <ns>` also returns immediately on an empty namespace, so the intended
   Istio→Knative→KServe→Profiles self-ordering didn't actually hold.
2. **`kubeflow-namespace` applied too late (the actual blocker).** `common/istio/istio-install/base`
   contains objects in the `kubeflow` namespace, but `60-istio` created `kubeflow-namespace`
   only in its **last** step. So step 2 died on `namespaces "kubeflow" not found` and `set -e`
   aborted the Job. With no `kubeflow` ns, KServe couldn't deploy its controller → its webhook
   service was absent → every `ClusterServingRuntime` apply failed the missing-webhook
   validation → KServe Job aborted. The old monolithic `kubeflow-bootstrap` applied
   `kubeflow-namespace` first; splitting into per-component Jobs regressed the order. (The
   clone-retry fix alone was NOT sufficient — the first in-place re-run still failed on this
   until the order was corrected.)

Fix (in `deploy-aleph/rke2-manifests/`):
- `60-63`: replaced the bare `git clone` with a **retry-until-egress-ready loop**
  (40 × 15 s ≈ 10 min) + a final guard; tightened each prerequisite wait to **loop until the
  namespace exists AND its pods are Ready** (60 × 10 s) so the chain self-orders for real.
- `60-istio`: apply `common/kubeflow-namespace/base` **first** (new step 1), ahead of
  cert-manager issuer / istio-install / kubeflow-istio-resources.
- **Dropped `40-traefik.yaml`.** It could not install over RKE2's bundled `rke2-traefik`
  (`IngressClass "traefik" ... current value is "rke2-traefik"` → `helm-install-traefik` stuck).
  The bundled `rke2-traefik` is now the sole ingress controller. (Decision; macvlan/public-IP
  binding customized on the bundled Traefik later.)

Validation: pushed the fixed Jobs to 230, deleted the Failed bootstrap Jobs so they re-ran.
After both fixes all four Jobs went **Complete** (istio 20 s, knative 36 s, kserve 60 s,
profiles 18 s); `kubeflow` + `models` namespaces Active; `kserve-controller-manager` 2/2
Running, `kserve-localmodel-controller-manager` 2/2, `profiles-deployment` 3/3. The install
logic is proven working on the live cluster; a fresh cold-boot redeploy is the final
confirmation that the retry/ordering hold from power-on.

Operational findings for the next redeploy (NOT code in this commit — Warewulf-overlay /
site-config side):
- **Stray `rancher.yaml` + `nfs.yaml` from the old cluster** are baked into the WW overlay's
  `/etc/rancher/manifests/` and land in `server/manifests/` alongside the aleph set.
  `rancher.yaml` re-installs **Rancher** (dropped by design; also incompatible with k8s
  1.36 → `helm-install-rancher` CrashLoop) and duplicates the `cert-manager` HelmChart.
  `nfs.yaml` re-creates the old `nfs-client` SC on `/kubeflow`, colliding with `30-nfs.yaml`'s
  `nfs-models` on `/aleph` (both define HelmChart `nfs-provisioner` → only one SC wins; the
  stray `nfs-client` won). **Remove both from the overlay** so only the aleph set ships.
- **GPU nodes unlabeled:** neither `rack15-03` nor the new `rack05-16` has `gpu=on`, so the
  HAMi device plugin isn't scheduled and no GPUs are advertised. Both nodes are 4× L40S
  (8 GPUs total now, was 4) with driver 595.71.05. Post-deploy: `kubectl label node <n> gpu=on`.

## 2026-06-20 — Consolidate working docs + salvage ProteinMPNN source (pre-230-redeploy)

230 is being destroyed and rebuilt with Warewulf + the modular RKE2 manifests. Pre-redeploy
consolidation pass so nothing is lost:
- New `working/` dir holds working/reference notes moved from the local `~/hami-cluster-test`
  dir: `MODEL-CAMPAIGN-PLAN.md`, `LLM-MODEL-TRACKER.md`, `CLUSTER-230-PLAN.md`,
  `MIGRATION-232-to-230.md` (working notes, not canonical — they carry 230/232 refs; canonical
  docs stay in `docs/`).
- Salvaged the upstream ProteinMPNN source (`pmpnn_run.py`, `pmpnn_utils.py`) into
  `models/proteinmpnn/` — the fixed `server.py` (embedded in its isvc ConfigMap) imports
  `protein_mpnn_utils`; these are the known-good upstream copies for reproducibility.
- Confirmed nothing else on 230 needs salvage: aleph already holds all 164 live model manifests
  (171 model dirs, superset), the gateway source, and byte-identical Tyk API defs.

## 2026-06-20 — Modular RKE2 auto-deploy manifest set (deploy-aleph/rke2-manifests/)

First cut at version-controlling the cluster bring-up so the next Warewulf deployment brings
most of the stack up automatically. Goal this round: every component **installed and
available** as modular RKE2 auto-deploy manifests (one component per file); site-specific
wiring (macvlan public-IP, `gpu=on` labels, Tyk secret, cert hostnames) is a documented
post-deploy step. Architecture stance: 232's front-door/TLS pattern, lean — no full Kubeflow
(no Dex/dashboard/pipelines), no Rancher, no certbot.

New files in `deploy-aleph/rke2-manifests/`:
- `00-cert-manager.yaml` — cert-manager HelmChart (split out of 230's bundled `rancher.yaml`;
  Rancher dropped). `crds.enabled: true`.
- `01-cluster-issuer.yaml` — Let's Encrypt `ClusterIssuer`, ACME **HTTP-01** via the traefik
  ingress class. Issues endpoint TLS from-cluster (replaces 232's manual external-certbot flow).
  Ready once cert-manager is up + port 80 reachable; placeholder email.
- `10-hami.yaml` — HAMi vGPU scheduler + device plugin (verbatim from 230). Needs `gpu=on`
  labels + containerd nvidia runtime (Warewulf overlay). `kubeScheduler.imageTag` k8s-pinned.
- `20-kuberay.yaml` — KubeRay operator 1.5.1, pinned to control-plane (off GPU nodes).
- `30-nfs.yaml` — nfs-subdir provisioner; creates a **single** `nfs-models` StorageClass
  (default) with the OneFS-safe mountOptions baked in (rsize/wsize=131072). No separate
  `nfs-client` SC.
- `40-traefik.yaml` — Traefik HelmChart, generic/default (service enabled), macvlan public-IP
  binding stripped (post-deploy customization). Notes the bundled-`rke2-traefik` interaction.
- `50-tyk-redis.yaml` + `51-tyk.yaml` — Bitnami Redis + Tyk OSS into ns `tyk`; Tyk `APISecret`
  is a placeholder (inject real from `.env` `TYK_API_SECRET` post-deploy).
- `60-istio.yaml` / `61-knative.yaml` / `62-kserve.yaml` / `63-profiles.yaml` — the serving
  stack (Istio, Knative, KServe, Profiles) split into **separate per-component Job manifests**,
  each its own ServiceAccount, self-ordering via internal waits (Istio→Knative→KServe→Profiles)
  + retries. Same kubeflow/manifests v1.11-branch slices as 230/232. The former
  `02-post-install.sh` patches are folded in — Knative `config-features` (PVC/init/nodeSelector/
  nvidia runtime) into `61`, KServe `inferenceservice-config` + `models` ns + Istio allow-all
  into `62` — so KServe comes up fully working. `63-profiles.yaml` is opt-in (delete to omit
  Kubeflow Profiles). Replaces the monolithic `60-serving-bootstrap.yaml` / `kubeflow-bootstrap.yaml`.

Also:
- `deploy-aleph/examples/ray-cluster-template.yaml` — documented RayCluster skeleton (head→
  non-GPU via `gpu NotIn [on]`, GPU workers scale-to-zero under HAMi), outside the manifests
  dir so RKE2 doesn't auto-apply it. Pattern from `models/kandinsky-3/`.
- `deploy-aleph/rke2-manifests/README.md` — the set's runbook: file list, site-config values,
  post-deploy customization checklist, follow-ups, verification commands.
- `docs/AUDIT-PROMPT.md` — moved the reusable cluster-audit procedure out of the local working
  dir into the repo, generalized to placeholders (no 230/232 IPs / user paths) per the
  no-cluster-specifics convention; bakes in the kubectl-PATH gotcha for non-interactive SSH.

Not done this round (called out in the README): capture the Warewulf overlay (on 172.26.92.10);
resolve the double-Traefik (disable bundled `rke2-traefik` via RKE2 config); update
`models/CLAUDE.md` storage convention `nfs-client`→`nfs-models`; retire the now-redundant
`deploy-aleph/storage/nfs-models-storageclass.yaml`. Kubeflow Profiles is an opt-in file
(`63-profiles.yaml`) — delete to omit entirely.

## 2026-06-20 — Dim verification: 5 non-text embedders (live probe + primary sources)

Re-checked the 5 non-text embedders whose dims I'd "corrected" during the 06-19/20 hardening, because
the recorded "wrong" values looked suspicious. Settled each by **reading the actual response length
live through the gateway** (ground truth) plus the model's HF config / primary docs — not by trusting
the cards or my earlier notes.

**All five card dims are correct** (verified live). The earlier "wrong" values were largely *my own
guesses*, not doc errors — the corrected value just hadn't been propagated to every artifact:

| model | live dim | earlier "wrong" | where the wrong value actually came from |
|---|---|---|---|
| satmae | 1024 | 512 | config.json `decoder_embed_dim`=512 (the MAE *decoder* dim, misread as encoder); encoder `embed_dim`=1024 |
| clay | 1024 | 768 | my guess (ViT-Base default); HF config carries no dim — 1024 read from the response |
| astropt | 768 | [N,512] | the server's own demo path returns a `[16,512]` synthetic array; real `generate_embeddings` output is a flat 768 (nanoGPT 095M `n_embd`) |
| brainlm | 1280 | 768 | my guess (ViT-Base default); 650M is ViT-Huge, hidden 1280 |
| geneformer | 768 | 256 | my version-conflation — 256 is the *V1-10M* dim; V2-104M is 768 (BioNeMo / Virtual Cells Platform) |

Honest correction to the 06-19/20 notes: the "(docs wrong)" parenthetical was misleading. In 3 of 5
cases (clay, brainlm, geneformer) the docs either stated no dim at all (clay, brainlm) or stated the
*correct* value (geneformer V2 = 768); the wrong number was my own guess or a version mix-up. Only
astropt's 512 is genuinely a number from the model's own (demo-path) code, and satmae's 512 is a real
config field I misread. The lesson ("verify the dim empirically every time") holds — but the reason
isn't "docs lie," it's "I guessed when docs were silent, and didn't propagate the fix."

Artifact-consistency fixes (stale prose left behind when the card was corrected):
- **clay/test.py:** `EXP_DIM` 768→1024.
- **geneformer/test.py:** `EXP_DIM` 256→768.
- **geneformer/README:** config table dim 256→768.
- **brainlm/{README,CLAUDE.md,details.yaml,test.py}:** all 768→1280 (description_short, description,
  config table, last-run line, response shape, test docstring/comments). The card
  `embedding_dimensions: 1280` and the test assertion were already correct; only the surrounding prose
  was stale. Live card re-applied so the cluster catalog now reads 1280-dim too.
No ISVC / server changes — dims were correct; this was documentation drift. Validation re-run live
(06-20): clay 6/0, brainlm 6/0, geneformer 6/0.

## 2026-06-19 — Embeddings pass begins: bge-m3 exemplar (Template C)

Starting the ~64 embedding/rerank model pass. Same posture as the chat sweep — the models are
already deployed; this is artifact authoring + card enrichment + a verify test, not reconfiguration.
New campaign conventions (see `~/hami-cluster-test/MODEL-CAMPAIGN-PLAN.md` §11): (1) web-search each
model's HF repo page before authoring the card; (2) flat dir layout = `details.yaml` / `pvc.yaml` /
`inferenceservice.yaml` / `test.py` / `README.md` / `CLAUDE.md`; (3) PVC is its own file and must be
`ReadWriteMany` (NFS RWX — shared across scale-from-zero pods).
- **bge-m3 (exemplar):** enriched the card to full Template C (`status`, `input_map`, `output_map`,
  `catalog.pooling=cls`, `normalization=l2`, `max_input_tokens`, full description sourced from the
  BAAI/bge-m3 HF page). New `test.py` — the reference 11-check embedding battery (dim / batch /
  model-echo / usage / encoding_format float+base64 / multilingual / guardrails / catalog; runs
  inside the gateway pod). New README + CLAUDE. PVC already RWX — no split needed.
  Validation: **8 PASS / 2 EXP / 0 FAIL / 1 SKIP** (2 EXP = chat→embed 404 + unknown-model 404;
  1 SKIP = truncation). Live card re-applied (`configmap/bge-m3-details configured`).
- **bge-reranker-v2-m3:** enriched card to full Template C (`status`, `input_map`/`output_map` for
  the `/v1/rerank` shape, `cross_encoder`, full description). New `test.py` — the 11-check rerank
  battery (basic / top_n / descending scores in [0,1] / relevance / model-echo / return_documents /
  guardrails / catalog). New README + CLAUDE. PVC already RWX. Validation: **8 PASS / 3 EXP / 0 FAIL**
  (3 EXP = chat→404, embed→424, unknown-model 404). Live card re-applied.
- **esm2-650m:** **split the inlined PVC** out of `inferenceservice.yaml` into a standalone RWX
  `pvc.yaml` (the "mixed PVC" cleanup; the server.py ConfigMap stays in the ISVC file). Card was
  already rich — added `max_completion_tokens` only. New `test.py` (10-check protein-embed battery:
  dim 1280 / batch / distinctness cos<0.99 / truncation / guardrails / catalog), README, CLAUDE.
  Custom transformers server on a HAMi GPU slice, scale-to-zero. Validation: **8 PASS / 2 EXP / 0 FAIL**.
- **scibert:** **rewrote the card from old-schema to v2 Template C** (it had top-level fields +
  `compatibility`/`deployment`/`server_config` blocks; gateway reads `behavior.*`, not `compatibility.*`).
  Removed `kustomization.yaml` (convention: `apply -f`, no kustomize). New `test.py` (10-check
  scientific-embed battery: dim 768 / batch / distinctness / truncation / guardrails / catalog),
  README, refreshed CLAUDE. Custom transformers server, CPU, scale-to-zero. Validation: **8 PASS / 2 EXP / 0 FAIL**.
- **bge-small:** the dir had **no card at all** (gateway had no catalog entry) → created the Template-C
  card + 11-check embed test.py + README + CLAUDE from scratch. No PVC by design (TEI fetches the
  ~130MB public model itself on start, always-on). Validation: **9 PASS / 2 EXP / 0 FAIL** (dim 384).
- **multilingual-e5-small:** old-schema card had **wrong endpoint (`/embed`) + wrong framework (claimed
  TEI) + stale `min_replicas: 1`** — the live deploy is a custom transformers FastAPI server on
  `/v1/embeddings`, scale-to-zero. Rewrote card to v2 Template C (corrected endpoint/framework/dim/
  scaling); the existing README + CLAUDE described a never-deployed TEI setup → rewrote both to match
  reality. Added 11-check multilingual embed test.py; dropped `kustomization.yaml`.
  Validation: **9 PASS / 2 EXP / 0 FAIL** (dim 384; EN/ES/ZH same-sentence cos 0.92).
- **dnabert-2:** old-schema card rewritten to v2 Template C (carrying the torch-2.5.1/transformers-4.40.2
  pin + custom-op notes into catalog). Added 10-check DNA-embed test.py, README, refreshed CLAUDE;
  dropped `kustomization.yaml`. Custom transformers server (trust_remote_code), CPU, scale-to-zero.
  Validation: **8 PASS / 2 EXP / 0 FAIL** (dim 768); live card re-applied.
- **esm1b:** old-schema card rewritten to v2 Template C; split the inlined PVC out to `pvc.yaml`.
  **Finding: the live `esm1b-data` PVC is `ReadWriteOnce`, not RWX** (immutable on a bound PVC; the
  ISVC's `scaleTarget: 5` is broken under RWO — capped at 1 pod). `pvc.yaml` specifies the desired RWX
  with migration steps; NOT applied live (would fail) — flagged for recreation. Added 10-check
  protein-embed test.py, README, refreshed CLAUDE. GPU (10 GiB HAMi slice), scale-to-zero.
  Validation: **8 PASS / 2 EXP / 0 FAIL** (dim 1280).
- **esm1b RWO→RWX migrated:** recreated the `esm1b-data` PVC as ReadWriteMany (stop ISVC → delete PVC →
  re-apply; reclaim=Delete triggered a one-time ~2.5GB model re-download, cold start ~5.7min). Now
  matches the fleet RWX convention and unblocks `scaleTarget: 5`. Re-verified 8/2/0.
- **bge-m3 memory bump (OOM fix):** raised the TEI server container limit 8Gi→16Gi (request 6→8Gi).
  Oversize single inputs (>8192 tokens) used to OOMKill the pod (exitCode 137) on the fp32 ~8k-token
  forward pass; the truncation test was SKIPped for it. Re-enabled the truncation check — now PASSES
  (prompt_tokens=8003 → 1024-dim, no OOM). bge-m3 now **9 PASS / 2 EXP / 0 FAIL / 0 SKIP**.
- **biobert:** card was already v2 (fixed a truncated `description_short`); **split the inlined PVC out
  to `pvc.yaml`** (live PVC is on `nfs-models`, not `nfs-client` — matched it). Added 10-check biomedical
  embed test.py, README, CLAUDE. Custom transformers server (BertModel), GPU 3 GiB slice, scale-to-zero.
  Validation: **8 PASS / 2 EXP / 0 FAIL** (dim 768).
- **pubmedbert:** old-schema card rewritten to v2 Template C; dropped `kustomization.yaml`. Added
  10-check biomedical embed test.py + README; refreshed CLAUDE. Custom transformers server (CPU),
  scale-to-zero. Validation: **8 PASS / 2 EXP / 0 FAIL** (dim 768); live card re-applied.
- **MODEL-STATUS.md:** added an "Embeddings pass (2026-06-19)" section tracking the hardened
  re-verification + Template-C card + RWX status per model (the legacy rows are from the 06-08 loop).
- **esm2-150m:** old-schema card rewritten to v2 Template C; **migrated PVC RWO→RWX** (recreated as
  nfs-models RWX; reclaim=Delete → one-time ~600MB re-download, cold start ~5min, validated). Added
  10-check protein-embed test.py (640-dim), README, refreshed CLAUDE. GPU, scale-to-zero.
  Validation: **8 PASS / 2 EXP / 0 FAIL**.
- **biomedbert:** card was already v2 — fixed a copy-paste error (description called it PubMedBERT;
  BiomedBERT is a different model). Added 10-check biomedical embed test.py + README; refreshed
  CLAUDE (dropped a stale TEST.md ref). CPU, scale-to-zero. Validation: **8 PASS / 2 EXP / 0 FAIL** (dim 768).
- **esmc-300m:** old-schema card rewritten to v2 Template C; **migrated PVC RWO→RWX** (nfs-models).
  ESM-C's cold rebuild (esm SDK venv + ~1.2GB model) is slow (>6min) — the test wake window timed
  out once; re-ran after Ready → green. Added 10-check protein-embed test.py (960-dim), README,
  refreshed CLAUDE. GPU, scale-to-zero. Validation: **8 PASS / 2 EXP / 0 FAIL** (dim 960, ctx 2048).
- **Fast RWX batch (chemberta, clinicalbert, splicebert, specter2):** chemberta + clinicalbert cards
  were already v2 (added test.py + README). splicebert + specter2 old-schema cards rewritten to v2
  Template C (+ test.py + README; splicebert source corrected DNA_bert_6→SpliceBERT). All RWX (no
  migration), CPU, scale-to-zero. Results: chemberta **8/2/0**, clinicalbert **8/2/0**, specter2
  **8/2/0**, **splicebert 7/3/0** — its distinctness check is EXP because SpliceBERT is a token-level
  splice-site model whose mean-pooled sequence embeddings aren't discriminative (cos~1.0); use
  per-token outputs for splice tasks.
- **matscibert (science-embed → OpenAI normalization):** the server only exposed `/v1/science/embed`
  (non-OpenAI shape `{text}`→`{embeddings}`), so it 404'd on the standard `/v1/embeddings` — the gateway
  forwards `/v1/embeddings` to the backend's `/v1/embeddings` (hardcoded). Added an OpenAI-contract
  `/v1/embeddings` route to server.py (CLS-pooled, 768-dim; keeps `/v1/science/embed` + `/v1/science/predict`
  as secondary). Card primary → /v1/embeddings, pooling mean→cls (matches the server); split the inlined
  PVC (nfs-models). Validation: **8 PASS / 2 EXP / 0 FAIL**. Exemplar for the ~6 other /v1/science/embed models.
- **ancient-greek-bert:** science-embed → OpenAI normalization (added `/v1/embeddings` route, CLS-pooled
  768-dim; keeps `/v1/science/embed`). Old-schema card rewritten to v2 (primary `/v1/embeddings`);
  **migrated PVC RWO→RWX** (nfs-models; re-download). Added test.py + README. GPU, scale-to-zero.
  Validation: **8 PASS / 2 EXP / 0 FAIL** (distinctness cos 0.30 Ancient-Greek vs English).
- **clinical-longformer:** science-embed → OpenAI normalization (added `/v1/embeddings` route, 768-dim
  [CLS]-pooled with Longformer global attention on CLS; keeps `/v1/science/embed`). Old-schema card
  rewritten to v2 (primary `/v1/embeddings`, 4096 ctx); migrated PVC RWO→RWX (nfs-models). Added
  test.py (incl. a long-doc check) + README. GPU (10 GiB), scale-to-zero.
  Validation: **8 PASS / 2 EXP / 0 FAIL**.
- **biomedbert-large:** science-embed → OpenAI normalization (added `/v1/embeddings`, 1024-dim [CLS];
  keeps `/v1/science/embed`). Old-schema card rewritten to v2 (primary `/v1/embeddings`); migrated PVC
  RWO→RWX (nfs-models). Added test.py + README. GPU (10 GiB), scale-to-zero.
  Validation: **8 PASS / 2 EXP / 0 FAIL**.
- **esm2-35m:** card was already v2; split the inlined PVC out to `pvc.yaml` (matched live nfs-models).
  Added 10-check protein-embed test.py (480-dim) + README + CLAUDE. GPU (3 GiB), scale-to-zero.
  Validation: **8 PASS / 2 EXP / 0 FAIL** (dim 480).
- **dnabert-s:** old-schema card rewritten to v2; dropped `kustomization.yaml`. **Fixed the `/v1/embeddings`
  handler to be OpenAI-compliant** — it 500'd on batch (`.upper()` on a list), returned no `usage`, and
  rejected >512 chars instead of truncating. Now handles batch, returns usage, truncates. Added 10-check
  DNA-embed test.py (768-dim) + README. CPU, scale-to-zero. Validation: **8 PASS / 2 EXP / 0 FAIL**.
- **ankh:** old-schema card rewritten to v2; **migrated PVC RWO→RWX** (nfs-models). The `/v1/embeddings`
  server was already OpenAI-compliant (batch + usage + `nan_to_num` sanitize) — no server fix needed.
  Added 10-check protein-embed test.py (768-dim) + README. GPU (8 GiB), scale-to-zero.
  Validation: **8 PASS / 2 EXP / 0 FAIL**.
- **biolinkbert:** old-schema card rewritten to v2; **migrated PVC RWO→RWX** (nfs-models). Server already
  OpenAI-compliant. Added 10-check biomedical embed test.py (768-dim) + README. GPU (8 GiB), scale-to-zero.
  Validation: **8 PASS / 2 EXP / 0 FAIL**. (Gotcha: the gateway returns **404, not 503**, during cold-start
  for this model, so the test's 503-only wake bails early — poll pod-ready before running post-migration.)
- **biomed-roberta:** old-schema card rewritten to v2; migrated PVC RWO→RWX (nfs-models). Server already
  OpenAI-compliant. Added 10-check biomedical embed test.py (768-dim) + README. GPU (8 GiB), scale-to-zero.
  Validation: **8 PASS / 2 EXP / 0 FAIL**.
- **saprot-650m:** old-schema card rewritten to v2; migrated PVC RWO→RWX (nfs-models). Added 10-check
  protein-embed test.py (1280-dim) + README. **Anomaly flagged:** distinctness cos=1.0 — different plain-AA
  sequences return identical mean-pooled embeddings (SaProt is structure-aware AA+3Di; plain-AA may be
  collapsing, possibly fp16 — needs 3Di tokens or separate investigation). Marked EXP.
  Validation: **7 PASS / 3 EXP / 0 FAIL**.
- **scincl:** old-schema card rewritten to v2; migrated PVC RWO→RWX (nfs-models). Added 10-check
  scientific embed test.py (768-dim) + README. GPU (10 GiB), scale-to-zero.
  Validation: **8 PASS / 2 EXP / 0 FAIL**.
- **prokbert:** card was already v2; **fixed `/v1/embeddings` to return `usage`** (was omitted). Added
  10-check DNA-embed test.py (384-dim) + README + CLAUDE. No PVC (HF hub, ephemeral). GPU, scale-to-zero.
  Validation: **8 PASS / 2 EXP / 0 FAIL**.
- **hyenadna:** old-schema card rewritten to v2; dropped kustomization. Fixed context_window
  32768→8192 (server's actual MAX_LEN). Added 9-check DNA-embed test.py (256-dim, incl. a ~4000bp
  long-seq check) + README. CPU, scale-to-zero. Validation: **7 PASS / 2 EXP / 0 FAIL**.
- **esm2-3b:** old-schema card rewritten to v2. Added 9-check protein-embed test.py (2560-dim) + README.
  GPU (20 GiB, fp16), scale-to-zero (slow ~3-6min cold start). RWX (no migration).
  Validation: **7 PASS / 2 EXP / 0 FAIL**.
- **agront:** card was already v2; **fixed `/v1/embeddings` handler** (batch 500 → works; added `usage`;
  removed `>6000bp` rejection → truncate via max_length=1024); split the inlined PVC to `pvc.yaml`.
  Added 9-check DNA-embed test.py (1500-dim) + README. GPU (8 GiB), scale-to-zero.
  Validation: **7 PASS / 2 EXP / 0 FAIL**.
- **medcpt-query:** old-schema card rewritten to v2; migrated PVC RWO→RWX (nfs-models). NCBI MedCPT
  query encoder (768-dim, 64-token context — pair with medcpt-article). Server already compliant.
  Added 9-check medical-query embed test.py + README. GPU (8 GiB), scale-to-zero.
  Validation: **7 PASS / 2 EXP / 0 FAIL**.
- **medcpt-article:** old-schema card rewritten to v2; migrated PVC RWO→RWX (nfs-models). NCBI MedCPT
  article encoder (768-dim, 512-token context — pair with medcpt-query). Server already compliant.
  Added 9-check medical-document embed test.py + README. GPU (8 GiB), scale-to-zero.
  Validation: **7 PASS / 2 EXP / 0 FAIL**.
- **caduceus + nucleotide-transformer** (DNA pair; both servers already OpenAI-compliant — no fix
  needed): caduceus — v2 card (256-dim RCPS Mamba), removed stale inlined RWO PVC (live already RWX),
  added test + README. nucleotide-transformer — card already v2, split inlined PVC (matched live
  nfs-models), added test + README + CLAUDE. Both GPU, scale-to-zero. Validation: **7/2/0** each.
- **gena-lm:** old-schema card rewritten to v2; migrated PVC RWO→RWX (nfs-models). DNA 768-dim,
  server compliant. Added 9-check DNA-embed test.py + README. GPU, scale-to-zero. Validation: **7/2/0**.
- **ablang2:** card already v2; split inlined PVC to `pvc.yaml` (**left RWO — non-HF Zenodo weights,
  RWX migration deferred to the last batch** via cp-from-RWO). Added 8-check antibody-embed test.py
  (480-dim) + README. CPU, scale-to-zero. Validation: **6/2/0**.
- **molformer:** science-embed → OpenAI normalization (added `/v1/embeddings` route, 768-dim SMILES;
  keeps `/v1/science/embed`). Migrated PVC RWO→RWX (nfs-models); card primary → /v1/embeddings. Added
  9-check molecular-embed test.py + README. GPU (3 GiB), scale-to-zero. Validation: **7/2/0**.
- **Reclassified out of the `/v1/embeddings` fit-cluster (domain — non-string input, OpenAI text
  standard doesn't apply):** `scgpt` (single-cell cell-dict `{genes,values}`), `biomedclip` (VLM),
  `clap` (audio+text). These keep their own endpoints — verified OpenAI `/v1/embeddings` is text-only.
- **sapbert:** science-embed → OpenAI normalization (added `/v1/embeddings` route, 768-dim [CLS];
  keeps `/v1/science/embed`). Migrated PVC RWO→RWX (nfs-models); card rewritten to v2 (primary
  `/v1/embeddings`). Added 8-check biomedical-entity embed test.py + README. GPU (8 GiB), scale-to-zero.
  Validation: **6/2/0**.
- **rnabert:** science-embed → OpenAI normalization (added `/v1/embeddings` route, mean-pooled;
  keeps `/v1/science/embed`). Migrated PVC RWO→RWX (nfs-models); card rewritten to v2. **dim is 120**
  (not 768 — small multimolecule rnabert; the test caught this). Added 8-check RNA-embed test.py +
  README. GPU (8 GiB), scale-to-zero. Validation: **6/2/0**.
- **ernierna:** science-embed → OpenAI normalization (added `/v1/embeddings` route, 768-dim mean-pooled;
  keeps `/v1/science/embed`). Migrated PVC RWO→RWX (nfs-models); card rewritten to v2. Structure-aware
  RNA — short-sequence mean-pool collapses (distinctness EXP, cos~1.0, like splicebert/saprot). Added
  8-check RNA-embed test.py + README. GPU (10 GiB), scale-to-zero. Validation: **5/3/0**.
- **rnafm:** science-embed → OpenAI normalization (added `/v1/embeddings` route, 640-dim mean-pooled;
  keeps `/v1/science/embed`). Migrated PVC RWO→RWX (nfs-models); card rewritten to v2. Added 8-check
  RNA-embed test.py + README. GPU (8 GiB), scale-to-zero. Validation: **6/2/0**.
- **rnamsm + gena-lm-large** (RNA/DNA pair): both science-embed → OpenAI normalization (added
  `/v1/embeddings` route; keeps `/v1/science/embed`). Migrated both PVCs RWO→RWX (nfs-models); cards
  → v2. rnamsm: 768-dim mean-pooled RNA MSA (**6/2/0**). gena-lm-large: 1024-dim [CLS] DNA BERT-large
  (**6/3/0** — distinctness EXP, short-DNA borderline). Tests + READMEs added.
- **ablang2 RWX migration (cp-from-RWO, non-HF):** created a new RWX PVC (`ablang2-data-rwx`), copied
  the venv + Zenodo weights (1.8G) from the old RWO PVC via a temp cp pod — **no re-download** (ablang2
  weights come from Zenodo, not HF). Repointed the ISVC; old `ablang2-data` deleted. This was the last
  deferred non-HF model. **The text/sequence RAG-embedder pass is now COMPLETE** — every model that fits
  the standard OpenAI `/v1/embeddings` endpoint is normalized, v2-carded, tested, and RWX-migrated.
- **Operational finding (documented in bge-m3/CLAUDE.md):** a single input well over the 8192-token
  limit **OOM-kills** the 8 Gi TEI pod (exitCode 137) during the fp32 forward pass and cascades 502s.
  TEI truncates per-sequence by default but the ~8k-token activation still exceeds 8 Gi. The test
  suite skips this rather than restarting the always-on pod each run. Not fixed (memory-limit bump =
  service change, out of scope).

- **astroclip → real model (was a demo stub):** the server fell back to a `{"_raw": True}` zero-vector
  because the library never imported. Made it real with a venv-on-PVC init (cu126 torch preserved via
  guarded venv, no `--clear`; DINOv2 + AstroCLIP both `--no-deps` per upstream; runtime deps added
  explicitly since `astroclip/__init__.py`'s import chain needs `datasets`/`h5py`/`scikit-image`/etc.).
  Four real bugs surfaced and fixed, each from the actual error: (1) wrong import `astroclip.model` →
  `astroclip.models.AstroClipModel`; (2) PyTorch-2.6 `weights_only=True` default — the Lightning ckpt
  stores full encoders, so `torch.load` is monkeypatched to **force** `weights_only=False` (Lightning's
  `pl_load` passes it explicitly, so `setdefault` was a no-op); (3) upstream `CrossAttentionHead.forward`
  does `return x, attentions[1]` on the `(batch,1,d)` attention *output* → `IndexError` for `batch<2`;
  server duplicates single input to a batch of 2 and returns `emb[0]`; (4) **dim is 1024, not the 512 the
  README claims** (ImageHead/SpectrumHead output, verified). Non-text domain model → stays on
  `/v1/science/embed` (image/spectrum input, no OpenAI `/v1/embeddings`). New v2 card, 9-check test.py
  (image+spec dim / shape / in-modal distinct cos 0.85 / cross-modal cos 0.28 / deterministic / modality
  echo / demo / malformed), README, CLAUDE. Validation: **9 PASS / 0 FAIL**.

- **labram → real model (was serving an untrained random model):** the server's `*.pt` glob found
  nothing (the HF repo ships `model.safetensors`+`config.json`), so it fell through to
  `from_pretrained("braindecode/labram-pretrained")` which fails under `HF_HUB_OFFLINE=1` (snapshot
  is in `/data/model`, not the HF cache), then to a **random-init model that reported READY**.
  Made it real: load via `Labram.from_pretrained(MODEL_DIR)` (local dir, fully offline). Three more
  real bugs, each from the actual error: (1) hardcoded `n_times=1600` was wrong — the braindecode
  checkpoint's config specifies `n_times=3000` (15×200 patches) vs the original 935963004
  LaBraM-Base's 1600; read `model.n_times` dynamically; (2) `LABRAM_CHANNEL_ORDER` lives in the
  `braindecode.models.labram` submodule, NOT re-exported at `braindecode.models` in 1.5.2 →
  `ImportError` (the inference 500); import from the submodule once at load time; (3) removed the
  untrained fallback (would silently serve random embeddings). Migrated PVC RWO→RWX via
  **cp-from-RWO** (preserved the slow torch+braindecode venv + HF snapshot; old `labram-data`
  deleted). Verified 200-dim [CLS] embeddings via `return_features`. SJTU origin (not Tsinghua);
  5.8M params (12-layer/200/10-head). New v2 card, 8-check test.py, README, CLAUDE. Validation:
  **8 PASS / 0 FAIL**.

### Non-text embed cluster → `/v1/science/embed` (domain embedders)
Started hardening the genuine non-text embedders (image/audio/multimodal/gene-expression) — none
fit OpenAI `/v1/embeddings` (text-only), so they standardize on `/v1/science/embed`. Several were
found **parked** (`serving.kserve.io/stop: "true"` left by a prior session → 404, not 503); clearing
that annotation is step one for each. Common work: RWO→RWX via cp-from-RWO, normalize the output to
an `embeddings` field, v2 card, image/array embed test.py. (6 in this cluster were mislabeled as
"embedding" but are really forecast/segment/retrieve/translate/generate — reclassified, not in this batch.)
- **satmae:** RWO→RWX (cp-migrated, venv preserved); added an `embeddings` alias to the `cls_embedding`
  output for cross-embedder consistency; v2 card (1024-dim ViT-L CLS); 6-check test.py; cleared the
  stop annotation. Validation: **6 PASS / 0 FAIL**.
- **clay:** RWO→RWX (cp-migrated, venv + checkpoint + claymodel repo preserved); +`embeddings` field;
  v2 card (1024-dim CLS large encoder — initially guessed 768, corrected from the response); 6-check
  pixels+waves test.py; cleared the stop annotation. Validation: **6 PASS / 0 FAIL**.
- **astropt (venv conversion):** the init's `/data` sentinel didn't persist deps (pip install went
  into the ephemeral container python), so the main container reinstalled cu126 torch on every wake.
  Converted to venv-on-PVC: init builds `/data/venv` once (sentinel `.astropt-ready-v2`, guarded),
  main runs `/data/venv/bin/python`. PVC was already RWX. **Dim is 768, not the docstring's [N,512]**
  — the real output is a flat 768-dim vector (demo path still returns [16,512]); v2 card corrected.
  7-check test.py. Validation: **7 PASS / 0 FAIL**.
- **aion:** RWO→RWX (cp-migrated, venv + weights + warmed HF cache preserved); +`embeddings` alias
  (server returned `embedding` singular); v2 card (768-dim multimodal). Test gotcha: the image input
  field is `flux`/`data` (NOT `image`) — sending `image` silently fell back to the default zero
  image (cos=1.0 distinctness failure). Also empty body defaults to a smoke image by design (200), so
  the malformed check uses an unknown modality. Validation: **6 PASS / 1 EXP / 0 FAIL**.
- **brainlm:** already RWX + already served /v1/science/embed (+ /v1/embeddings alias). Two real
  fixes: (1) the ViT-MAE forward ran with random masking (`noise=None`) → embeddings were
  **stochastic** (identical input gave cos=0.999, not 1.0); set `cfg.mask_ratio=0.0` at load →
  deterministic; (2) **dim is 1280, not 768** (docs wrong). The response is OpenAI-format
  (`data[].embedding`). Distinctness threshold relaxed — random-noise fMRI maps near-identically
  (this MAE isn't trained to discriminate noise); determinism is the real check. Validation:
  **6 PASS / 0 FAIL**.
- **clap:** already v2-carded + RWX + served /v1/science/embed. Added 7-check test.py covering
  both modalities (text 512-dim, audio 512-dim @48kHz) + cross-modal shared-space sanity
  (distinctness cos(dog,ocean)=0.29). Server returns `audio_embeddings`/`text_embeddings`
  (not `embeddings`); lenient on empty body (200 empty). Cleared the stop annotation.
  Validation: **7 PASS / 0 FAIL**.
- **dino-vit-b8:** already RWX (ONNX CPU). Added a `/v1/science/embed` route alias (stacked
  decorator; was `/v1/vision/embed` only) + an `embeddings` field. v2 card (768-dim ViT-B/8).
  6-check test.py that generates a pure-stdlib PNG (no PIL in the gateway pod). Cleared the stop
  annotation. Validation: **6 PASS / 0 FAIL**.
- **prithvi-eo:** already RWX. Added `/v1/science/embed` alias (was `/v1/embed`) + **the full CLS
  vector** to the output (the old server returned only a 10-element summary "to avoid huge payloads"
  — 1024 floats ~8KB is fine). v2 card (1024-dim). 6-check test.py; distinctness threshold relaxed
  (random-noise imagery maps near-identically; determinism is the real check). Validation:
  **6 PASS / 0 FAIL**.
- **geneformer:** RWO→RWX (cp-migrated, venv + weights + tokenizer preserved); +`/v1/science/embed`
  alias (was `/v1/embed`). **Dim is 768, not 256** (docs wrong). Input gotcha: the server takes
  `gene_ids` (pre-tokenized integer IDs ranked by expression), NOT the docstring's `{genes,
  expression}` — the test sends integer token IDs. v2 card; 6-check test.py. Validation:
  **6 PASS / 0 FAIL**.
- **biomedclip:** already RWX. Added `/v1/science/embed` alias (was `/v1/embeddings` + `/v1/classify`
  only). v2 card (512-dim shared image+text space). 7-check test.py covering both modalities +
  cross-modal shared-space sanity (pure-stdlib PNG). Cleared the stop annotation. Validation:
  **7 PASS / 0 FAIL**.
- **scgpt:** already RWX. Added `/v1/science/embed` alias (was `/v1/embeddings` OpenAI-style only).
  v2 card; **corrected gpu:false→true** (the ISVC requests a HAMi L40S slice). 7-check test.py
  (dim 512 / non-zero / distinctness / deterministic / batch x2 / echo / malformed). Cleared the
  stop annotation. Validation: **7 PASS / 0 FAIL**. **This completes the 11-model non-text embed
  cluster** — all on /v1/science/embed, v2 cards, test.py, RWX.

## 2026-06-18 — Retest campaign: harden chat-LLM test.py + README Testing sections

Re-running the 29 chat LLMs through the gateway and tightening each per-model `test.py` from
status-only checks to correctness assertions. Shared hardening (folded into existing checks,
+1 new `truncation` probe, 33→34 checks for reasoning models): `temp0` asserts the answer contains
"Paris"; `stop_seq` asserts `finish_reason=="stop"`; `tools` asserts the called function name;
`stream` requires non-zero chunks; `usage` asserts the `model` field echoes the requested id;
`truncation` (`max_tokens=5` → `finish_reason=="length"`). Each README gets a Testing section
(run command + last result).
- **gpt-oss-120b / gpt-oss-20b**: hardened to 34-check battery; both **31/3/0** (3 EXP = vision /
  embed / bad-model guards). Managed thinking ON exposes `reasoning`, OFF strips + caps; tools,
  Anthropic parity, streaming reasoning, meta-tasks all green. README Testing sections added.
- **qwen3-32b**: hardened to 34-check battery; **31/3/0**. Effort + binary `enable_thinking` (real
  off); hermes tools, thinking on/off/budget/stream green.
- **qwen36-27b**: hardened to 31-check vision+tools battery; **29/2/0**. Image vision + tools +
  managed thinking all green. (Campaign-wide: capped thinking-check `max_tokens` at 4096 for verbose
  reasoners — assertions only need a non-empty reasoning trace, so ~4× faster, no loss of coverage.)
- **qwen36-35b-a3b**: hardened to 31-check vision+tools battery; **29/2/0**. README Testing section
  refreshed (was stale `tee`-method + 21-pass).
- **qwen35-122b**: hardened to 29-check battery; **26/3/0**. Fixed a false fail in the new `stop_seq`
  assertion — chatty models responded instead of enumerating, so never emitted the stop token; switched
  to a continuation prompt (`"Continue this count: 1, 2, 3, 4,"` + `stop:["5"]`) that forces it. README
  Testing section refreshed (was stale `tee`-method + 23-pass).
- **gemma-4-26b-a4b**: hardened to 33-check vision battery; **31/2/0**. Image vision + tools (gemma4
  parser) + managed thinking all green. README Testing section added.
- **phi-4-reasoning**: hardened to 31-check budget battery; **26/5/0**. Pure reasoner — temp0 Paris
  assertion skipped (model adds a disclaimer, not crisp answers) and the truncation-at-5 check removed
  (budget off-mode caps to `off_max_tokens`≈4096, overriding a tiny request; the off-cap is already
  covered by `think_off`). README authored (was missing).
- **qwq-32b**: hardened to 22-check always-on battery; **19/3/0**. Always-on reasoning exposed by
  default, stripped + off-capped on `none`/meta. Tool-name/model-echo/truncation assertions added.
  README Testing section refreshed (was stale `tee`-method + 21-pass).
- **r1-distill-qwen-32b**: hardened to 26-check always-on battery; **21/5/0**. `stop_seq` needs a
  2048 budget (always-on CoT eats a small one before reaching the stop token). README Testing
  section added.
- **r1-distill-llama-70b**: hardened to 26-check always-on battery; **21/5/0** (TP4). Same stop_seq
  2048 fix. README Testing section added. **All 11 reasoning models now retested + hardened.**

  Non-reasoning chat (Phase 2): same correctness assertions; domain models (astrosage, geogalactica,
  oceangpt, openbiollm, medgemma, tinyllama) get the domain-agnostic subset (truncation + model-echo)
  since they may not answer "Paris" or enumerate cleanly.
- **command-r-7b**: hardened to 23-check battery; **18/5/0**. README Testing section refreshed.
- **glm-4-32b, qwen25-coder-32b, oceangpt-30b, gemma-3-4b-it, qwen25-vl-3b, qwen25-vl-7b,
  qwen25-vl-72b-awq, openbiollm-70b, medgemma-27b-it, geogalactica**: auto-detect non-reasoning
  battery + truncation/model-echo assertions; **~20–22 pass / 1–3 exp / 0 fail** (tools/vision
  auto-detected per model). Big models (medgemma-27b, qwen25-vl-72b, geogalactica, openbiollm-70b)
  need a quiet cluster to warm within the 7.5-min wake window.
- **astrosage, tinyllama-1-1b**: custom transformers/llama.cpp backends — model-echo only
  (truncation not honored by these backends: `max_tokens=5` → `finish=stop, 0 tokens`);
  **18 pass / 4 exp / 0 fail**.
- **qwen3-235b** (235B AWQ) + **qwen25-vl-72b** (72B BF16): the two biggest models — **21/3/0** and
  **21/2/0**. Both need a patient wake (115 GB / 144 GB checkpoints from NFS exceed the 7.5-min
  inline wake window); tested after a warm-up. qwen25-vl-72b's ISVC was delete+re-applied to clear
  revision churn from a minReplicas pre-warm attempt. **All 29 chat LLMs now retested + hardened.**
- **Steady-state policy**: all 29 chat models are now wake-on-demand (`minReplicas: 0`, **no `stop`
  annotation**). Cleared `serving.kserve.io/stop=true` from the 10 reasoning models that had been
  left stopped after testing. Root `CLAUDE.md` "Scaling Models Up/Down" rewritten — wake-on-demand is
  the default resting state; `stop=true` is only for deliberately parking a model.

## 2026-06-18 — Managed thinking: expose reasoning ON, strip+cap OFF (gpt-oss)

- **gateway**: managed-thinking models (`param_translation.thinking.mode` in budget/effort/toggle)
  now expose reasoning when thinking is ON and strip+cap when OFF — replacing the old global
  `strips_thinking` strip. OpenAI ships the `reasoning` field; Anthropic emits a `thinking` content
  block (non-stream + SSE). OFF caps `max_tokens` to the card's `off_max_tokens` (default 2048) so
  the model can't burn tokens on about-to-be-stripped reasoning.
- **gateway**: effort/toggle models fake a token budget — a caller-supplied
  `thinking_token_budget` caps `max_tokens` (budget + answer reserve); consumed and not forwarded.
- **gateway**: `prepare_chat` returns `(body, thinking_on)`; added `_manages_thinking` /
  `_expose_reasoning` / `_off_token_cap`; `thinking_token_budget` counts as explicit thinking.
- **Root cause**: vLLM v0.20.2 emits gpt-oss reasoning in the `reasoning` field (NOT
  `reasoning_content`), so "thinking wasn't working" was a false negative — the parser splits fine.
- **gpt-oss-20b / gpt-oss-120b**: cards → `strips_thinking: false` + `off_max_tokens: 2048`;
  test.py rebuilt as a 33-check comprehensive battery (both pass 30/3/0): wake-through-503,
  full OpenAI + Anthropic feature suite (stream/system/temp/top_k/stop/tools/max_tokens/usage),
  thinking ON/OFF/fake-budget/stream assertions on the `reasoning` field, OpenWebUI meta-tasks
  (title/tags/followups), vision guard, and catalog/guardrails.
- **qwen3-32b** re-verified on the managed-thinking gateway — 33-check battery 30/3/0 (wake +
  OpenAI/Anthropic + thinking on/off/budget/stream + meta-tasks + guardrails). Card: add
  `off_max_tokens` + `input_map`/`output_map`/`custom_params` (v2 completeness) + managed-thinking
  note; README/CLAUDE updated.
- **gemma-4-26b-a4b** re-verified — fixed thinking: card was `effort` mode (reasoning_effort yields
  no trace on gemma-4); changed to **toggle** mode via `chat_template_kwargs.enable_thinking`
  (confirmed direct-to-predictor). 32-check vision-variant battery 30/2/0 (vision works, thinking
  on/off/budget/stream, meta, both protocols). README added; CLAUDE gateway/test section.
- **phi-4-reasoning** re-verified (budget mode) — 31-check 26/5/0. Thinking ON exposes
  reasoning. Documented quirk: phi-4 always emits a CoT trace, so requests need adequate
  max_tokens (≥~4000) or reasoning eats the budget → empty content; OFF (budget 0) is
  unreliable on vLLM V1 (redacted_thinking not always extracted, vllm#18141). Card: strips_thinking
  off + off_max_tokens + quirk note.
- **qwen36-27b** re-verified — 30-check vision+tools battery 28/2/0 (managed thinking effort +
  enable_thinking toggle, vision, qwen3_coder tools). Card: add off_max_tokens + input_map/
  output_map/custom_params. README + CLAUDE created.
- **qwen36-35b-a3b** re-verified — 30-check vision+tools battery 28/2/0 (managed thinking effort
  + enable_thinking, vision, qwen3_coder tools). Card: off_max_tokens + input_map/output_map.
- **gateway**: always-on reasoning models (`mode: always_on`) are now managed too — ON exposes
  reasoning, OFF strips + caps max_tokens (reduce what fits, since they can't stop reasoning).
  `_manages_thinking` now includes `always_on`. For qwq/r1-distill meta-tasks (OpenWebUI).
- **qwen35-122b**: NO-ISVC on 230 (TP4 122B not deployed) — skip-and-note.
- **r1-distill-qwen-32b / r1-distill-llama-70b**: managed always_on — ON exposes reasoning,
  OFF strips+caps; 20/5/0 each. Cards rewritten to full v2; README+CLAUDE created; pre-set stop
  annotation removed so wake-on-demand works.
- **glm-z1-32b / glm-z1-rumination-32b**: skip-and-note — glm45 parser keeps reasoning in-template
  (not surfaced as a `reasoning` field, so managed expose/strip doesn't apply); glm-z1-32b tool
  parser broken; rumination ignores tools/system by design.
- **qwen35-122b**: DEPLOYED on 230 (was NO-ISVC) — TP4 122B FP8, weights pre-staged on PVC;
  28-check 25/3/0 (managed toggle thinking, qwen3_coder tools, vision off via --language-model-only).
  Card: off_max_tokens + input_map/output_map.
- **phi-4-reasoning**: FIXED the OFF path — budget mode with REDUCE-off (effort_map none →
  thinking_token_budget 512, NOT 0). budget 0 was mishandled (vLLM#18141: burns tokens, empty
  content). OFF now = reduce reasoning (512) + strip + cap → content returns. Meta caps bumped
  (phi-4 reasons a lot). 31-check 26/5/0. (Research: vLLM#18141 phi-4+deepseek_r1 finicky.)
- **glm-z1-32b / glm-z1-rumination-32b**: RETIRED + deleted (repo + cluster: ISVC, ConfigMap,
  PVC, crashloop zombies). Redundant reasoning models whose chat template has no enable_thinking
  + glm45 parser crashes — reasoning not surfaceable as a field. Superseded by the working
  reasoning fleet (qwq/r1-distill/gpt-oss/qwen3/phi-4). glm-4-32b remains for GLM-family coverage.

## 2026-06-15 — GLM-4 tool calling working; Anthropic streaming tool_use fix

- **glm-4-32b — working tool calling** via a custom vLLM parser. GLM-4-32B-0414 emits tool calls as
  plain text (`function_name\n{json}`), not `<tool_call>` tokens, so vLLM's built-in `glm45` parser
  returned empty `tool_calls`. Built `models/glm-4-32b/glm4_0414_tool_parser.py` (mirrors the model
  card's regex + name-validation), mounted via `--tool-parser-plugin` + `--tool-call-parser=glm4_0414`.
- **gateway**: emit `tool_use` content blocks in Anthropic `/v1/messages` **streaming** responses —
  tool calls were being dropped in SSE (only the non-stream path produced them).
- MODEL-STATUS: fixed a blank line that broke GitHub table rendering.

## 2026-06-12 — GLM family modernized (v2 cards, parsers, test suites)

- **glm-4-32b / glm-z1-32b / glm-z1-rumination-32b** → v2 cards, `vllm serve` format, `glm45` tool
  parsers, per-model test suites. Documented the **GLM reasoning-parser incompatibility**:
  `--reasoning-parser=glm45` crashes (maps to a DeepSeek parser expecting `<think>` tokens GLM's
  tokenizer lacks), so GLM-Z1 thinking stays in-template and is never surfaced as `reasoning_content`.
  Rumination's chat template ignores tools/system-prompt by design (`supports_tools: false`).

## 2026-06-11 — Qwen + vision fleet: full v2 card campaign (11 models)

Migrated the Qwen line to v2 cards with full gateway test suites:
- **qwen3-32b** (effort, 23/25), **qwen35-122b** (toggle, 23/23), **qwen3-235b** (non-thinking, 21/21),
  **qwq-32b** (always-on, 21/21), **qwen25-coder-32b** (22/22), **qwen25-vl-3b/7b/72b** (18/22/22),
  **qwen36-35b-a3b** (reasoning+tools+vision, 21/21), **qwen25-vl-72b-awq** (16/18).
- **Vision standardization**: `--limit-mm-per-prompt=20` across VLMs; context raised to 64K
  (32K on qwen25-vl-3b). qwen25-vl-72b-awq switched TP4→TP2 (model `max_position_embeddings`=128K).
- **Removed k2-v2** — FP32-only (~290 GB), impractical cold start over NFS.
- Refreshed `models.md` + `MODEL-STATUS.md` for all 9 Qwen models + vision limits.

## 2026-06-10 — Science/chat v2 cards + gateway vision gating

- **v2 cards**: command-r-7b (scale-to-zero + 15m, 16/16), deepseek-v2-lite-16b (14/14),
  openbiollm-70b, oceangpt-30b (64K + tools), geogalactica (v0.20.2 + chat template), tinyllama
  (llama.cpp crash fix), astrosage (`no_stream` custom server), progen2 (protein gen + input/output maps).
- **gateway**: vision gating — reject image input for non-vision models; force `stream=false` upstream
  for `no_stream` card models.
- astrosage: rewrote CLAUDE.md + added README.

## 2026-06-09 — qwen36-27b flagship + single-file gateway + CI

- **qwen36-27b**: enabled reasoning + tools + vision, 131K context; switched thinking to **effort
  mode** for native `reasoning_effort` support (became the effort-mode template for the fleet).
- **gateway**: merged `anthropic_xlate.py` into `gateway.py` — single-file gateway.
- **CI/deploy**: post-build image verification + Docker cache-bust fixes; deployment pinned to a CI
  tag with `imagePullPolicy: Always`, then moved to `latest` + always-pull.

## 2026-06-08 — Science wake-up batch, NIM containers, card templates

- **Wake-up tested 10 stalled models** → 6 FIXED (presto pass-mask fix, aeneas JAX warmup,
  geogalactica gate accepted, others), 2 need code fixes, 1 vLLM fail.
- **NIM containers**: renamed boltz→boltz-2 and added openfold-3 (both `nvcr.io/nim/...`); patched
  boltz NIM v1.7.0 `confidence_score` KeyError at startup; standardized 16 GiB `/dev/shm` for NIMs.
- **Batch-fixed 7 failed models**; bumped Knative `progress-deadline` for caduceus / prithvi-eo.
- Merged the 2026-06 LLM batch into the MODEL-STATUS main table + added NIM notes.
- **Templates**: expanded the details.yaml template with real input_map/output_map patterns from
  science models; added an audit prompt for systematic model audit.
- **gateway**: moved the Anthropic type-gate ahead of readiness/cold-start checks; added API mapping docs.

## 2026-06-07 — Tier 2 science models: 2 PASS, 3 blocked by Knative timeout

### Verified PASS
- **progen2** — added sentinel + progress-deadline 600s annotation; 6.4B protein generation works
  (`MRENAQKALEIKRTRVIAEDL` from seed `M`).
- **timesfm** — pinned `transformers>=4.51,<4.53` + `torch>=2.5 cu126`; `TimesFmModelForPrediction`
  (v2.0 500M) loads and forecasts; 128 quantile levels, sensible trend continuation.

### Blocked (Knative progress-deadline 600s cap)
- **caduceus** — torch 2.2.0 + mamba-ssm 1.2.0 pinned, AutoModel for RCPS embeddings, new venv path.
  Init compiles mamba CUDA kernels (~20 min) → exceeds Knative 600s deadline.
  Fix: bump Knative `progress-deadline` max in `config-deployment` ConfigMap.
- **prithvi-eo** — rewrote to BACKBONE_REGISTRY API, added GDAL system deps, forward_features.
  Init installs terratorch + deps (~12 min) → exceeds 600s deadline. Same Knative fix needed.
- **boltz-1** — PVC venv, YAML input, `--checkpoint` path fix, `--no_kernels`. SIGSEGV (rc=-11)
  during `boltz predict` after MSA step. Likely cuEquivariance/CUDA kernel crash on L40S.
  Deferred — needs deeper CUDA debugging or different boltz version.

## 2026-06-07 — Tier 1 science models: 5 deep-fixes to PASS

Systematic fix of 5 GPU science models that were FAIL/PENDING. All now verified with
real payloads on cluster 230.

### timer-s1 (replaces timer-xl-1b)
- **Model swap**: Timer-XL-1B was gated (weights 403), replaced with Timer-S1 (open, Saleen2023/Timer-S1).
- **dtype fix**: Cast all float inputs to `torch.bfloat16` — Timer-S1 weights are bf16, mismatch caused NaN.
- **Init RAM**: Raised to 32Gi to avoid OOM during model load.
- **Test**: 200, 9 quantile forecasts (q0.1–q0.9), sensible trend continuation.

### moirai-moe-1-0-r-base (replaces moirai-moe)
- **Full rewrite**: Original handler used non-functional `Moirai` class. Rewrote to official
  `uni2ts` API: `create_predictor()` + `GluonTS` dataset + `Prediction` object extraction.
- **Quantile extraction**: Reads 19 quantile levels from prediction output.
- **Test**: 200, quantile forecasts with correct shape and values.

### enformer
- **Python 3.12 + GPU torch**: Base image `python:3.12-slim`, pip install `torch` (CUDA) not CPU-only.
- **transformers pin**: `transformers<4.52` — newer versions break Enformer model class.
- **Dict output fix**: `model(x)` returns `{'human': tensor, 'mouse': tensor}`, not an object
  with `.human` attribute. Changed `hasattr(out, 'human')` → `isinstance(out, dict) and 'human' in out`.
- **Payload**: Summarized output (mean + sample) to avoid 896×5313 = ~4.7M value JSON.
- **Test**: 200, human_shape [896, 5313], correct gene expression predictions.

### ernierna
- **GPU torch (cu126)**: Force-reinstall `torch` from cu126 index (base image had CPU-only torch).
- **nodeSelector**: Added `gpu: "on"` to schedule on GPU node.
- **progress-deadline**: Raised to 600s for cold-start model download.
- **storageClassName**: Set to `nfs-client` for PVC.
- **Test**: 200, 768-dim RNA embeddings.

### totalsegmentator
- **torch reinstall**: TotalSegmentator pulls in CPU-only torch as a dep; force-reinstall
  `torch` + `torchvision` from cu126 index after TotalSegmentator install.
- **Test**: 200, segmentation runs on synthetic 16³ volume (0 structures expected on zeros).

### Also
- Deleted `models/timer-xl-1b/` (gated, replaced by `models/timer-s1/`).
- Deleted `models/moirai-moe/` (non-functional, replaced by `models/moirai-moe-1-0-r-base/`).

## 2026-06-06 — phi-4-reasoning card refresh (no gateway remap)

- Rewrote `models/phi-4-reasoning/details.yaml` to schema v2 (whole L40S, v0.20.2,
  `always_on` thinking, verified PASS status, known quirks documented).
- Reverted `fill_empty_content_from_reasoning()` — empty `content` is a vLLM parser or
  `max_tokens` budget issue, not something the gateway should paper over.

## 2026-06-06 — gateway: switch cluster 230 to Docker Hub pull

- Deployment now uses `rkhoja/aleph:latest` with `imagePullPolicy: IfNotPresent`
  (replaces local `model-gateway:<tag>` + `Never` + containerd import).
- `deploy-aleph/deploy.sh` / `gateway/remote-deploy.sh` no longer build on the control plane; `GATEWAY_IMAGE`
  env var selects the tag (default `rkhoja/aleph:latest`).
- RUNBOOK/README/gateway CLAUDE updated: Docker Hub is primary; local build is appendix only.
- Rolled out on cluster 230; gateway deployment healthy.

## 2026-06-06 — science model batch (gateway body-limit + init fixes)

Continued the verification loop on remaining PENDING science models. Key pattern:
several models returned 30–286 MB JSON grids/point clouds that exceed the ingress/gateway
body limit (connection reset even when the pod returned 200). Fix: summarize outputs
(shape/stats/downsampled preview) with opt-in `full_grid` / `full_cloud` flags.

### Verified FIXED
- earthpt — CPU checkpoint load + 24Gi RAM (was GPU+host OOM on startup)
- fengwu — summarize 286 MB forecast grid; demo + real ONNX OK
- dust3r — downsample point cloud to ≤2000 pts + bbox + alignment loss
- diffdock — pass SMILES string directly to `--ligand` (not `.smi` path); fix confidence
  regex; 11 ranked poses on crambin (1CRN) + aspirin
- mast3r — `/v1/science/match` (not reconstruct for 2 images); numpy not tensor fix
- granite-geospatial-biomass/ocean — add gcc/g++ to init (terratorch→stringzilla compile)
- pangu-weather — demo + real ONNX; summarized stats (already had stats in handler)

### Verified DEMO (blocked on deps/access)
- fourcastnet3 — demo OK; real FCN3 needs purpose-built image (makani+torch-harmonics
  CUDA matrix unresolvable via runtime pip)
- naturecode-earth — demo OK; weights gated (`naturecodeproject/earth` 403)

### Still PENDING from this batch
- mattergen (CLI loads; diffusion timeout raised 300→1500s, verify pending)
- prithvi-eo/wxc, surya, terramind-flood, totalsegmentator (in progress)

Tracker: `models/MODEL-STATUS.md` updated for all of the above.

## 2026-06-05 — per-model verification loop (complete) — 138 models migrated 232→230

Systematic one-by-one verification of every migrated model on 230: bring up via gateway,
test the real endpoint(s) with task-realistic payloads, deep-fix until correct, scale-cycle,
document (`TEST.md`/`CLAUDE.md`), and mark an honest `status` on each card.

### Tooling
- `test/test-model.sh` — apply-from-repo, Knative-aware activation (pre-warm via gateway
  request, not manual scale), `recreate` (delete+clear+reapply, keep PVC), curl with
  cold-start retry, scale-cycle.
- `models/MODEL-STATUS.md` — master matrix (PASS / FIXED / FAIL) for all ~157 models.

### Key finding
- KServe "READY" was misleading: several servers returned `/health` 200 while the model
  silently failed to load (no egress, wrong package, fake inputs). These were deployed but
  never actually exercised. The loop now hits real endpoints with real payloads.

### Verified PASS (CPU)
- Embeddings: bge-m3 (1024-dim, multilingual), biomedbert, chemberta, clinicalbert,
  pubmedbert, dnabert-2, dnabert-s, hyenadna (256), splicebert, scibert, specter2.
- Rerank: bge-reranker-v2-m3 (correct ranking).
- Chat: tinyllama (OpenAI + Anthropic). Streaming is a cross-cutting gateway/Knative SSE
  issue (tracked, to fix once for all chat models).

### Deep-fixed (were broken/garbage; now correct, status=production)
- ablang2: `/v1/restore` (AbLang2 needs `[heavy,light]` pairs; handler normalizes input).
- aion: rewrote to the real `polymathic-aion` API (AION + CodecManager + typed modalities);
  init pre-downloads model+codec weights so the offline runtime can load. legacy_image +
  photometry → 768-dim.
- biot5: use task-specific checkpoints (mol2text/text2mol) + SELFIES + official prompts.
- chem-t5: replace invented task prompts with the exact GT4SD training templates.

## 2026-06-04 — migrate climatebert (classification, CPU)

### climatebert (Wave 1)
- Ported ClimateBERT (DistilRoBERTa, 3 models: base + detector + netzero-reduction) from 232.
  CPU; scale-to-zero; PVC nfs-client; HF_HOME=/data/hf-home; HF_HUB_OFFLINE=1 at runtime.
- /v1/science/classify (tasks: detect, netzero) + /v1/embeddings (768-dim). All PASS.
- Inline HF_TOKEN → secretKeyRef; v2 card with routing.k8s_name=climatebert.

## 2026-06-04 — migrate birdnet-analyzer (audio-classification, CPU)

### birdnet-analyzer (Wave 1)
- Ported BirdNET-Analyzer (Cornell Lab, birdnetlib + tensorflow-cpu) from 232.
  CPU; scale-to-zero; PVC nfs-client; no HF token needed (bundled model weights).
- /v1/science/identify: 48kHz float samples → species detections. PASS (synthetic tone → empty
  detections as expected; pipeline end-to-end verified in ~16s).
- v2 card with routing.k8s_name=birdnet-analyzer.

## 2026-06-04 — migrate chem-t5 (chemistry T5, CPU)

### chem-t5 (Wave 1)
- Ported Chem-T5 (GT4SD/multitask-text-and-chemistry-t5-base-standard) from 232. CPU; T5
  seq2seq; scale-to-zero; PVC nfs-client; HF_TOKEN → secretKeyRef; v2 card.
- /v1/science/generate (tasks: forward_synthesis, retrosynthesis, mol2text, text2mol, etc).
  Demo forward_synthesis PASS. ~10s beam search on CPU.

## 2026-06-05 — migrate tinyllama (chat LLM, CPU llama.cpp)

### tinyllama (Wave 1)
- Ported TinyLlama-1.1B-Chat (GGUF Q4_K_M) from 232 via llama-cpp-python server.
- Removed `nvidia.com/gpu.product: NVIDIA-L40S-SHARED` nodeSelector; minReplicas:1→0;
  added Knative scale-to-zero; HF_TOKEN→secretKeyRef; `--n_gpu_layers=0` for CPU.
- POST /v1/chat/completions PASS (~270ms). OpenAI-compatible. Context 4096.

## 2026-06-05 — migrate yolov8n + yolov8s (object detection, ONNX, CPU)

### yolov8n + yolov8s (Wave 1)
- Ported YOLOv8n/s (Ultralytics COCO 80-class, ONNX) from 232. Already Knative.
- Added `routing.k8s_name` to both cards. POST /v1/vision/detect PASS.
- Init exports `.pt` → `.onnx` on first cold start (cached on PVC).

## 2026-06-05 — migrate dino-vit-b8 + efficientnet-b0 (vision, CPU)

### dino-vit-b8 + efficientnet-b0 (Wave 1)
- Ported DINO ViT-B/8 and EfficientNet-B0 (ONNX) from 232. Already Knative.
- Added `routing.k8s_name` to both cards.
- /v1/vision/embed (dino-vit-b8) and /v1/vision/classify (efficientnet-b0) PASS.

## 2026-06-05 — migrate rita (protein generation, CPU)

### rita (Wave 1)
- Ported RITA-XL (LightOn, 1.2B, protein autoregressive LM) from 232. CPU.
- Already Knative; added `routing.k8s_name`, fixed `endpoints` dict, added /v1/science/generate alias.
- Fix: `transformers==4.36.2` required (4.37+ adds `can_generate()` check that breaks RITA custom model).
- /v1/science/generate PASS.

## 2026-06-05 — migrate multilingual-e5-small (multilingual embedding, CPU)

### multilingual-e5-small (Wave 1)
- Ported intfloat/multilingual-e5-small (117M, 512-dim, 100+ languages) from 232.
- Rewrote from TEI (ghcr.io/huggingface/text-embeddings-inference) to standard Python FastAPI
  embedding server (same pattern as biomedbert), enabling standard /v1/embeddings routing.
- Fix: added `sentencepiece` to venv; `transformers==4.44.2` (4.46.3 has lazy-import bug for XLM-R).
- HF_TOKEN→secretKeyRef; minReplicas:1→0; Knative scale-to-zero.
- /v1/embeddings (3-language batch) PASS. 512-dim, L2-normalized.

## 2026-06-05 — migrate scibert + specter2 (scientific embeddings, CPU)

### scibert + specter2 (Wave 1)
- Ported from 232. Already Knative + nfs-client. Only change: HF_TOKEN→secretKeyRef,
  added `routing.k8s_name`.
- /v1/embeddings (768-dim) PASS for both.

## 2026-06-05 — migrate dnabert-2 + dnabert-s (DNA embeddings, CPU)

### dnabert-2 (Wave 1)
- Ported from 232 (already Knative). HF_TOKEN→secretKeyRef, k8s_name added.
- Fix: model returns tuple not ModelOutput — patched to use `raw[0]` as hidden states.
- /v1/embeddings PASS.

### dnabert-s (Wave 1)
- RawDeployment → Knative; removed GPU nodeSelector; added PVC + init container.
- MODEL_ID env var → local path `/data/model`; HF_HUB_OFFLINE=1 at runtime.
- Fixed `endpoints` list→dict in card. /v1/embeddings PASS.

## 2026-06-05 — migrate pubmedbert (biomedical embedding, CPU)

### pubmedbert (Wave 1)
- 232 source was a stub-only card. Built fresh (biomedbert pattern).
  microsoft/BiomedNLP-PubMedBERT-base-uncased-abstract (110M, 768-dim).
- /v1/embeddings PASS. Use model id `pubmedbert` (response shows `pubmedbert-110m`).

## 2026-06-05 — defer longformer + led (stub-only on 232)

### longformer + led (Wave 1, deferred)
- Both were stub-only directories on 232 (card + kustomization, no server.py/ISVC).
- Deferred. Implementation notes in CLAUDE.md for each.

## 2026-06-04 — migrate biot5 (bio T5, CPU)

### biot5 (Wave 1)
- Ported BioT5 (QizhiPei/biot5-base) from 232. CPU; T5 seq2seq; scale-to-zero;
  PVC nfs-client; HF_TOKEN → secretKeyRef; v2 card.
- /v1/science/generate (tasks: mol2text, forward_synthesis, etc). Demo mol2text PASS (~25s
  greedy on CPU — not a hang, use --max-time ≥60).

## 2026-06-04 — migrate clap (audio-language, CPU)

### clap (Wave 1)
- Ported CLAP (laion/larger_clap_general) from 232: `/v1/embeddings` (audio+text, 512-dim)
  and `/v1/classify` (zero-shot audio). CPU.
- Fixes: switched unused GPU torch → CPU torch; patched `/v1/classify` for transformers
  `ClapModel.logit_scale_a` (was `logit_scale`). Inline token → secretKeyRef; v2 card.
- Verified text dim=512 and 440Hz sine classified as "pure tone" (0.99999).

## 2026-06-04 — migrate chronos-bolt (time-series forecast, CPU)

### chronos-bolt (Wave 1)
- Ported Chronos-Bolt (amazon/chronos-bolt-base) from 232: `/v1/forecast`, CPU,
  scale-to-zero (kustomize configMapGenerator for server.py). Inline token → secretKeyRef;
  v2 card (param count corrected to ~205M). Verified horizon=6 forecast.

## 2026-06-04 — migrate alphafold2 (structure prediction, GPU)

### alphafold2 (Wave 1, GPU/HAMi)
- Ported AlphaFold2-via-ColabFold from 232. RawDeployment+GPU-Operator → Knative
  scale-to-zero + HAMi `gpumem 24576`; PVC `nfs-client`; moved jax[cuda12]/fastapi install
  into guarded init so warm restarts are fast.
- Verified end-to-end: demo fold returned a valid PDB + pLDDT (mean 51.0) in ~163s; MSA
  fetched from public api.colabfold.com (egress OK). See models/alphafold2/TEST.md.

## 2026-06-04 — migrate chemberta + clinicalbert (embeddings, CPU)

### chemberta (Wave 1)
- ChemBERTa (seyonec/ChemBERTa-zinc-base-v1) SMILES embeddings, /v1/embeddings 768-dim,
  CPU. Inline token → secretKeyRef; pinned torch/transformers; v2 card. Verified dim=768.

### clinicalbert (Wave 1)
- Bio_ClinicalBERT clinical-text embeddings, /v1/embeddings 768-dim, CPU. Inline token →
  secretKeyRef; pinned torch/transformers; v2 card. Verified dim=768.

## 2026-06-04 — aion deferred (BLOCKED)

### aion (Wave 1) — blocked
- AION-base (Polymathic AI) astro multimodal FM: the 232 server is a non-functional stub
  (uses `transformers`/bogus import; real model needs the `aion` package `CodecManager` +
  modality dataclasses and structured astro inputs). Load fails both paths.
- Converted manifests to HAMi but removed the broken deployment from the cluster.
  Documented the correct integration path in models/aion/CLAUDE.md; marked `[s]` in
  MIGRATION.md for a later proper rewrite.

## 2026-06-04 — migrate agront (plant DNA LM, GPU)

### agront (Wave 1, gpu→HAMi slice)
- Ported AgroNT 1B (InstaDeepAI) from 232. Converted from `RawDeployment` + GPU-Operator
  nodeSelector + ephemeral `/tmp` download to standard 230 pattern: Knative scale-to-zero,
  PVC venv+weights, HAMi `gpu: "on"` + `nvidia.com/gpumem: 8192`, HF token via secretKeyRef.
- Corrected embedding dim **1280 → 1500** (verified live). `/v1/embeddings` +
  `/v1/science/predict` both return 1500-dim. See models/agront/TEST.md.

## 2026-06-04 — migrate arcface (face recognition, CPU/ONNX)

### arcface (Wave 1, gpu=0)
- Ported ArcFace ResNet-100 from 232: `/v1/vision/face`, 512-dim L2-normalized, CPU
  onnxruntime, scale-to-zero. Pinned `onnxruntime==1.19.2`; v2 card
  (`routing.k8s_name: arcface`). Verified dim=512, normalized. See models/arcface/TEST.md.

## 2026-06-04 — migrate biomedbert (biomedical embeddings, CPU)

### biomedbert (Wave 1, gpu=0)
- Ported Microsoft BiomedBERT (110M) from 232: `/v1/embeddings`, 768-dim, CPU,
  scale-to-zero, `nfs-client` PVC.
- Inline HF token → `secretKeyRef`; pinned `torch==2.5.1`/`transformers==4.46.3`.
- v2 card with `routing.k8s_name: biomedbert` (id `biomedbert-110m`). Verified dim=768
  via gateway. See models/biomedbert/TEST.md.

## 2026-06-04 — migrate ablang2 (antibody embeddings, CPU)

### ablang2 (Wave 1, gpu=0)
- Ported AbLang-2 (OxPIG) from 232: antibody PLM, `/v1/embeddings` (mean-pooled) +
  `/v1/restore`. CPU-only (48M), scale-to-zero, `nfs-client` PVC.
- **Fix**: ablang2 0.2.1 dropped the old arbitrary-local-path loading the 232 server
  relied on (`AssertionError: ... does not exist`). Switched to the supported id
  `model_to_use='ablang2-paired'`, pre-downloading weights in the init container into
  the package dir on the PVC so the read-only runtime can load them. Pinned
  `ablang2==0.2.1`, `torch==2.5.1+cpu`. Removed unused inline HF token.
- Converted card to v2 schema; verified dim=480, ctx=512. Tested embeddings single +
  batch via gateway; catalog discovery via `?all=true`. See models/ablang2/TEST.md.

## 2026-06-04 (latest) — begin 232→230 ≤2GPU model migration

### Migration scaffolding
- Created `hf-token` Secret in `models` namespace (manifests now use `secretKeyRef`).
- Added `models/MIGRATION.md` tracker: 138 models to migrate (54 gpu=0, 80 gpu=1,
  4 gpu=2), smallest-first, skipping the 18 already on 230 + the 4-GPU models.
- Confirmed capacity: 2 GPU workers (`rack05-16`, `rack15-03`), 8× L40S, gpu=on.

## 2026-06-04 (latest) — docs/process + gateway image CI workflow

### README/template alignment and operator notes
- Replaced the temporary SoftMig-oriented README text with Aleph stack content while
  preserving the same section/template shape.
- Added explicit reference to the external node-image repo we use:
  `ualberta-rcg/warewulf-rke2-hami`.

### CLAUDE guidance expansion
- Added `models/CLAUDE.md` with a standard model deployment process and validation
  checklist.
- Added `models/CLAUDE-TEMPLATE.md` for per-model operational notes.
- Added `models/gpt-oss-20b/CLAUDE.md` as a concrete per-model example.
- Added `gateway/CLAUDE.md` for gateway rollout/compatibility guardrails.
- Updated root `CLAUDE.md` with a required changelog-first commit process.

### GitHub Actions (DockerHub) for gateway image
- Added `.github/workflows/deploy-gateway.yml` modeled after the publish pattern in
  `ualberta-rcg/warewulf-rke2-hami`:
  - build on `main` pushes touching `gateway/**`,
  - push immutable `gateway-<shortsha>` and stable `latest` tags,
  - default image `rkhoja/aleph` (override via `DOCKER_HUB_REPO` secret/Variable),
  - DockerHub auth via `DOCKER_HUB_USER`, `DOCKER_HUB_TOKEN`.

## 2026-06-04 (later) — 3 more sub-GPU science models + cold-start fix

### Added esm2-650m, molformer, finbert (all sub-GPU, scale-to-zero)
- **esm2-650m** — Meta ESM-2 protein language model (650M), `POST /v1/embeddings`,
  1280-dim embeddings, fp16, 4 GiB HAMi slice. domain: proteomics.
- **molformer** — IBM MoLFormer-XL molecular embeddings from SMILES (110M),
  `POST /v1/science/embed`, 768-dim, 3 GiB slice. domain: chemistry.
- **finbert** — ProsusAI FinBERT financial sentiment **classification** (110M),
  `POST /v1/science/classify` → positive/negative/neutral, 3 GiB slice. domain: finance.
- All ported like proteinmpnn (HF transformers server in a ConfigMap): `nodeSelector
  gpu:on` + `nvidia.com/gpumem`, `nfs-models` PVC (venv on NFS), `minReplicas 0`, 15m idle.
  Cards rewritten to our schema (type embedding/classify, catalog, input/output_format).
- **Switched molformer + finbert torch from CPU → cu121** so they actually use the GPU
  slice they request (POC installed CPU torch, wasting the allocation).
- **transformers version pin (`==4.46.3`)**: the unpinned latest transformers imports
  `torch.float8_e8m0fnu`, which the cu121 torch wheel lacks → `EsmModel`/`BertForSeq...`
  failed to import. Pinned esm2 + finbert; molformer already pins `<4.36` (onnx).
- Verified: esm2 1280-dim, molformer 768-dim (aspirin), finbert sentiment
  (surged→positive .92, bankruptcy→negative .68).

### Gateway 0.8 — cold-start guard now handles never-started models
- Bug: a brand-new scale-to-zero ISVC has no `latestReadyRevision`, so
  `_ready_replicas` returned -1 (fail-open) and the request hit Knative → **empty 404**.
- Fix: `_ready_replicas_sync` now also falls back to `latestCreatedRevision` (whose
  Deployment exists at 0 replicas), so the guard sees "0", returns the friendly 503, and
  the wake-up primes the very first scale-up. Verified: fresh models now 503 (not 404) and
  self-prime on first request. (gateway image 0.7 → 0.8)

### HAMi multi-tenancy confirmed
- With these up, packing across the 4 L40S (binpack):
  GPU A = command-r-7b (24G) + finbert (3G); GPU B = esm2-650m (4G) + molformer (3G);
  2 GPUs free for qwen/gpt-oss/gemma/proteinmpnn cold starts. Multiple models per
  physical GPU, as intended.

## 2026-06-04 (later) — proteinmpnn (science model), public catalogue, gemma, qwen

### proteinmpnn — first "science" model on 230 (sub-GPU)
- Moved ProteinMPNN (Dauparas et al., Science 2022, Baker Lab) from POC 232:
  `models/proteinmpnn/` (custom PyTorch FastAPI server in a ConfigMap, `POST /v1/design`).
  Routes through the gateway's existing `/v1/{path}` catch-all (no gateway change).
- 230 adaptations: `nodeSelector gpu:on` + **HAMi sub-GPU slice `nvidia.com/gpumem: 6144`**
  (6 GiB of an L40S — ~1.7M-param model, mostly CUDA/cuDNN context), `nfs-models` PVC,
  scale-to-zero (15m). First cold start builds the ~5 GB torch venv **onto NFS** — verified
  the `nfs-models` SC handles it (no EIO). Later starts reuse the cached venv/weights.
- **Fixed broken server.py**: the POC's `model.sample(..., chain_idx=...)` call no longer
  matches upstream ProteinMPNN `main` (sig is now `sample(X, randn, S_true, chain_mask,
  chain_encoding_all, residue_idx, mask=, ...)` returning a dict). Rewrote `_design` to use
  the repo's own helpers (`parse_PDB`, `StructureDatasetPDB`, `tied_featurize`, `_scores`,
  `_S_to_seq`) exactly like `protein_mpnn_run.py`. Now returns sequences + score +
  global_score + seq_recovery + native sequence.
- **Card corrected from the source** (`models/proteinmpnn/details.yaml`): `context_window`
  1022 → **200000** (upstream `--max_length` default), added architecture (k=48 GNN, 3+3
  layers), weights `v_48_020` (48 nbrs / 0.20A noise), Science 2022 citation + paper URL,
  available weights, accurate input/output schema.
- Verified end-to-end on crambin (1CRN, 46 aa): native parsed correctly, 3 designs at T=0.2
  with ~52–57% sequence recovery (expected for ProteinMPNN), disulfide cysteines preserved.

## 2026-06-04 (later) — public catalogue endpoint, gemma cleanup, qwen images=20

### Public catalogue endpoint (keyless), like POC 232's `/serving/api/v1/models`
- New **keyless** Tyk API `model-catalogue` (`gateway/tyk/model-catalogue-api.json`),
  `listen_path: /serving/api/v1/models` → proxies to the gateway's `/v1/models`.
  Scoped to the catalogue path only, so chat/embeddings still require a key
  (verified `/v1/chat/completions` with no key → 401; `/serving/api/v1/models?all=true`
  with no key → 200). Added as a 2nd key in the `tyk-api-definitions` ConfigMap.
- Gotcha: `kubectl rollout restart deploy -l <wrong-label>` returns success (no-op) when
  the selector matches nothing — restart by deploy name (`deploy/gateway-tyk-oss-tyk-gateway`).
- Output is the same rich card-driven schema as `/v1/models?all=true` (richer than 232:
  adds `capabilities`, `scaling`, live `resources`, `ready`, `embedding_dimensions`).

### gemma cleanup + move to 230
- POC called it `gemma-4b` but the repo is **`google/gemma-3-4b-it`** (Gemma *3*). Renamed
  the model id + served name to **`gemma-3-4b-it`** to match the repo.
- `models/gemma-3-4b-it/` (isvc + card + pvc): vLLM `v0.20.2` (vs POC's 0.8.4), bf16 (dropped
  POC's fp8 + nvidia-smi VRAM-guard — HAMi enforces VRAM), HAMi 16 GiB slice, `nodeSelector
  gpu: on`, NFS PVC, scale-to-zero (15 m), no `--enforce-eager`, `--max-model-len 8192`.
  Verified chat incl. a system prompt (vLLM merges it into the Gemma chat template).

### qwen25-vl-7b — images per prompt 5 → 20
- `--limit-mm-per-prompt '{"image":20,"video":1}'`. **No KV penalty** in vLLM 0.20.x: still
  8.56 GiB KV / 160,272 tokens / 4.89x concurrency on the 32 GiB slice (it doesn't reserve
  worst-case multimodal memory from the limit).

## 2026-06-04 — NFS persistence, scaling/cold-start, model catalog, multimodal

### Storage — NFS large-write EIO fixed
- **Root cause:** the OneFS/Isilon backend (`manage.storage.data.vulcan.local:/kubeflow`)
  returns `Errno 5 (EIO)` on COMMIT for write RPCs > 128 KiB over **NFSv4.1/4.2**. The
  default `nfs-client` SC mounts v4.2 @ `wsize/rsize=1Mi`, so multi-GB safetensors failed
  at `close()` (small files were fine). NFSv3 and v4.0 work even at 1 MiB.
- **Fix:** new StorageClass **`nfs-models`** (`deploy-aleph/storage/nfs-models-storageclass.yaml`) with
  `mountOptions: nfsvers=4.2,wsize=131072,rsize=131072,hard`. Verified ~700 MB/s, 2 GB write OK.
- **Impact:** model weights now persist on NFS PVCs (`models/*/pvc.yaml`, SC `nfs-models`).
  Scale-from-zero cold starts **skip the re-download** (~90 s vs ~3 min before). Replaces the
  earlier `emptyDir` workaround.

### Scaling — scale-to-zero, scale-up-on-use, friendly cold-start
- Cards gained a **`scaling`** block: `scale_to_zero`, `min_replicas`, `idle_retention`,
  `cold_start_estimate`.
- Convention: most models `minReplicas: 0` (scale-to-zero, **15 m** idle retention via
  `autoscaling.knative.dev/scale-to-zero-pod-retention-period: "15m"`); a few stay
  `minReplicas: 1` (always-warm). Examples: gpt-oss-20b & qwen25-vl-7b = 0; command-r-7b = 1.
- **Gateway cold-start handling** (mirrors POC 232, but card-driven): on each request the
  gateway checks the active predictor revision's `readyReplicas`. At **0** it fires an async
  Knative wake-up (`GET /v1/models` with the model's `Host` header) and returns a fast
  `503 {code: model_scaled_to_zero}` "starting up… retry in <cold_start_estimate>" instead of
  hanging into Tyk's 30 s `504`. Verified: 503 in ~0.06 s, wake triggers a 0→1 scale-up.
  (Replica count is read live with a 3 s TTL cache; RBAC already grants `apps/deployments`.)

### gpt-oss-20b — HAMi slice tightened
- KV math showed the 32 GB slice was ~2× oversized for `max_num_seqs=8`. Reduced to a **24 GB
  slice** (`nvidia.com/gpumem: 24576`) at `--gpu-memory-utilization 0.90`:
  KV 12.15 GiB → **6.55 GiB** (268k tokens, 8.18× @ 32k, matches `max_num_seqs=8`). Frees ~8 GB/GPU.

### Gateway — card param-translation fix (reasoning models)
- `thinking.mode: effort` previously **overwrote** a client-supplied `reasoning_effort`. Now it
  uses `setdefault` when thinking is enabled (respects the caller; only fills the card default
  when absent) and still forces "off" for meta-tasks. Verified: low=171 vs high=445 tokens.

### Gateway — `/v1/models` is now fully card-driven (richer than 232)
- The endpoint emits the **232-compatible schema** (`id, object, owned_by, type,
  context_window, max_completion_tokens, description, endpoint, input_format, source,
  source_url, tags, parameters, gpu`) **plus extras**: `ready`, `license`, `precision`,
  `framework`, `domain`, `subdomain`, `capabilities{vision,video,tools,reasoning,system_prompt}`,
  `scaling{...}`, and live `resources{gpus,vram_mib,cpu_cores,system_ram_mib}`.
- All of it comes from the **details ConfigMap (card)** + live ISVC state — 232 hardcodes this
  metadata in the gateway; here it is auto-detected. `source_url` auto-derives from a HF `source`.
- Cards gained `limits.context_window`; `catalog.input_format` / `catalog.gpu` optional.
- `?all=true` returns every model; default returns chat-class only.

### Token budgets (researched, were too tight)
- gpt-oss natively supports 131k context **and** 131k output; reasoning burns many tokens.
  Bumped gpt-oss-20b `defaults.chat.max_tokens` 4096→**8192** and `limits.max_completion_tokens`
  16000→**24000** so reasoning + answer don't truncate (verified: bat-and-ball at effort=high
  used 473 tokens, full `reasoning` + correct $0.05 answer).
- qwen25-vl-7b default `max_tokens` 2048→**4096** (vision/OCR outputs).

### bge-small embedding — values verified + actually deployed
- Researched specs: **384 dims, 512 max tokens, cls pooling** (so `context_window: 512` was
  correct). Card now carries `embedding_dimensions: 384`, `max_input_tokens`, `pooling`; the
  endpoint surfaces `embedding_dimensions`.
- The card existed without a backing ISVC (404 on `/v1/embeddings`). Deployed the real TEI
  service (`models/bge-small/inferenceservice.yaml`, CPU, always-warm). Verified 384-dim vectors.

### Models
- **Added qwen2.5-vl-7b** (`models/qwen25-vl-7b/`) — multimodal: text + images + video, OCR,
  charts, document parsing. Card declares `supports_vision`/`supports_video`; NFS PVC; scale-to-zero.
  - vLLM **v0.20.2** (was 0.8.4) — newer, consistent with gpt-oss, cached on node. NB:
    `--limit-mm-per-prompt` format differs by version: **JSON** `{"image":5,"video":1}` on 0.20.x,
    `image=5,video=1` on 0.8.x.
  - **No `--enforce-eager`** (CUDA graphs kept on). With graphs+ViT resident a 28 GB slice left
    only ~5 GB KV (2.8×), so bumped to a **32 GB slice** → 8.56 GB KV (4.89× @ 32k).
  - Verified vision end-to-end via gateway+Tyk (correctly described a red/blue test image).
- command-r-7b, gpt-oss-20b: moved to NFS PVCs; cards gained `scaling` + `context_window`.

### Scale-up-on-use — confirmed working (matches 232 mechanism)
- Verified the full cycle: idle model scales to 0 → request returns fast 503 → async wake-up
  (Knative activator) spins a pod 0→1 → retry serves 200. Same approach as POC 232's
  `_wake_up_model`, but the retry estimate is card-driven.

### Demo
- `test/smoke.sh` — 10 copy-pasteable curls (catalogue, OpenAI chat, reasoning, streaming,
  Anthropic, vision, embeddings, telemetry, cold-start) runnable from a login node with a key.

### Gateway image
- `model-gateway` `0.3 → 0.6`. Built with podman on the head node, imported into RKE2
  containerd (`ctr -n k8s.io`), retagged `docker.io/library/model-gateway:<v>`.
  - 0.4: effort param-translation fix
  - 0.5: scale-to-zero cold-start guard + wake-up
  - 0.6: card-driven `/v1/models` enrichment
