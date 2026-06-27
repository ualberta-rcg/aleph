# Model Deploy Playbook — vLLM LLMs on the Aleph cluster

The operational standards + per-model loop used to bring the **chat-LLM fleet onto cluster 43
(aleph1)**. Proven across 20+ models (reasoning, vision, tool, code). Reuse it as the template for
later passes — **NIM and science models are handled by separate, tweaked plans** (not this doc).

> Scope of this playbook: the vLLM-served chat/completions/reasoning/vision LLMs. NIM containers,
> custom science servers, and the still-on-v1 science/forecast/force-field conversions each get their
> own plan (the standards below still apply, but the init/runtime specifics differ).

## Context

Cluster **43 (aleph1, 172.26.92.43)** — 3 control-plane VMs + **5 GPU workers (20× L40S)**. The
model-gateway is up (`rkhoja/aleph:latest`); the public edge is Traefik on VIP **129.128.190.56** with
Tyk behind it (internal ClusterIP). **Cards are the discovery mechanism** — a model is catalogued only
when its v2 `details.yaml` is applied as a ConfigMap labeled `model-details: "true"`. All chat LLMs are
already v2, so they're detected once applied.

Every model is done **strictly one at a time, by hand — no agents/subagents** — driven to a passing
test, then proven by a clean delete + redeploy from the repo files, then left deployed at scale 0,
with no mess left behind before moving on. Already-deployed workloads are **do not touch**.

---

## Working mode (hard rules)

- **One model at a time. No agents, no subagents, no parallel models.** Finish a model completely —
  passing test, clean redeploy verified, deployed at scale 0, repo committed, no stray pods/state —
  **before** starting the next.
- **Drive to a real pass, then prove it's reproducible.** Iterate (apply → test → tweak) until the
  test battery is only PASS/EXP; then do the clean delete-all + redeploy + re-test; only then record.
- **No mess between models:** no half-deployed ISVCs, no leftover pods, no patched-live drift, no
  uncommitted repo changes carried forward.
- **Source of truth = the repo files.** The live cluster must be reproducible from
  `models/<m>/{pvc,inferenceservice,details}.yaml` alone. Whatever you tweak live, you put back into
  the repo before finishing the model.
- **Don't lean on RUNBOOK/AUDIT-PROMPT** — the standards below are self-contained.

---

## Standards (the contract every model dir meets)

Templates: `models/DETAILS-TEMPLATE-LLM.md` (A=vLLM chat, B=science, C=embed/rerank),
`models/test.template.py`, `models/CLAUDE-TEMPLATE.md`, `models/CLAUDE.md`.
Exemplars: **`gemma-4-26b-a4b/` is the venv-on-PVC standard to copy**; `gpt-oss-120b/`, `gpt-oss-20b/`
for the card/reasoning args; `gpt-oss-120b/` for the clean `<model>` PVC naming.

> **Two different venvs — don't confuse them.** (1) **Login-node test venv** = only for running
> `test.py` from *this* node; `httpx` is already importable here, so **nothing to build**. (2)
> **Deployment venv** = a helper-venv built **on the model's PVC inside the initContainer** (gemma-4
> pattern), persisted so cold starts don't reinstall it. We **do** want (2); see Standard #3.

1. **Flat 6-file layout** (no subdirs, **no `kustomization.yaml`**):
   `details.yaml` · `inferenceservice.yaml` · `pvc.yaml` · `test.py` · `README.md` · `CLAUDE.md`.
   Keep model-specific extras only when genuinely required (e.g. `geogalactica/chat_template.jinja`,
   `glm-4-32b/glm4_0414_tool_parser.py` + `parser-configmap.yaml`).
2. **Card = v2** (`schema_version: 2`), ConfigMap `name: <model>-details`, label
   `model-details: "true"`, `data.details.json`. Gateway reads only `id/type/endpoints/routing/
   limits/scaling/behavior/param_translation/defaults`; everything else in `catalog`.
3. **initContainer inside `inferenceservice.yaml` builds a persisted venv on the PVC + downloads
   weights — the gemma-4 pattern** (`models/gemma-4-26b-a4b/inferenceservice.yaml`). On the PVC (`/data`):
   - build `/data/venv` **once** with the download helper (`python -m venv /data/venv` +
     `pip install huggingface_hub`), gated by `if [ ! -d /data/venv/bin ]` so cold starts **skip it**;
   - download weights to `/data/model`, gated by `if [ -f /data/model/config.json ]`;
   - main container = prebuilt `vllm/vllm-openai:v0.20.2` serving `/data/model`.
   This is what makes **future cold starts fast** — both the venv and the weights are cached on the
   RWX PVC, so nothing is reinstalled/redownloaded. **Never** a separate `download-job.yaml`; **never**
   a fresh `pip install huggingface_hub` on every cold start. (Custom science models use the heavier
   caduceus pattern: a full venv with torch+model deps on the PVC — see the science plan.)
   **First-start fragility:** the venv build is the vulnerable step — if it's disrupted mid-deploy,
   delete the venv on the PVC (`kubectl exec <pod> -c setup -- rm -rf /data/venv`, or bump the gate)
   and let the initContainer rebuild it from scratch; never try to patch a half-built venv.
4. **PVC = standalone `pvc.yaml`, `accessModes: [ReadWriteMany]`, `storageClassName: nfs-models`.**
   RWX so scale-from-zero cold starts share NFS weights.
5. **Scale-to-zero: `minReplicas: 0`, no `serving.kserve.io/stop` annotation.** Card
   `scaling.idle_retention` (15m default) mirrors ISVC annotation `scale-to-zero-pod-retention-period`.
6. **GPU/HAMi** — the rule is **whole device vs fractional slice by VRAM need**:
   - **Needs >40 GB/card → whole devices: `nvidia.com/gpu: "<N>"` and NO `nvidia.com/gpumem`** (all
     TP≥2 models *and* large TP1 models). The previous `gpumem:45000` workaround for HAMi#1781's
     broken exclusive path is **obsolete** — NCCL/exclusive issues are cleared up, whole devices
     schedule cleanly (verified on qwen3-235b TP4).
   - **Fits in a slice (<40 GB) → `nvidia.com/gpu: "1"` + `nvidia.com/gpumem: "<MiB>"`** (small TP1
     models, e.g. gemma-3-4b-it gpumem 20480).
   - **TP≥2 always:** + `--disable-custom-all-reduce` (L40S = PCIe/NODE topology, no NVLink P2P →
     custom all-reduce hangs at engine init; NCCL fallback is correct+fast). `VLLM_ATTENTION_BACKEND=
     TRITON_ATTN_VLLM_V1` on L40S (SM89). `nodeSelector: {gpu: "on"}`, anti-affinity off control-plane.
   - vLLM `vllm/vllm-openai:v0.20.2` **except** models whose arch needs newer (qwen36-27b uses `:latest`).
7. **Secrets from the `hf-token` Secret** (`models` ns), never inline. Refresh before gated models:
   `set -a; source .env; set +a; kubectl create secret generic hf-token -n models
   --from-literal=token="$HF_TOKEN" --dry-run=client -o yaml | kubectl apply -f -`
8. **test.py convention** (test.template.py): `GW_URL` + `TYK_KEY` env overrides, no hardcoded
   IPs/hostnames in committed files; all calls carry `Authorization: Bearer $TYK_KEY`. Add the
   env-gated `GW_INSECURE` toggle (`verify=False` for httpx, an unverified `ssl` context for urllib)
   because the edge serves a self-signed cert.

## Naming standard

Use the model's canonical name consistently **everywhere** (the `gpt-oss-120b` shape):

| Object | Name |
|---|---|
| `InferenceService.metadata.name` | `<model>` |
| card `id` and `routing.k8s_name` | `<model>` |
| card ConfigMap `metadata.name` | `<model>-details` |
| `PersistentVolumeClaim.metadata.name` **and** the ISVC volume `name` **and** the `claimName` ref | `<model>` |
| server ConfigMap (science models) | `<model>-server` |

Common "funny" names to fix: PVC/volume `model-data`, `data`, `<model>-data`; volume name ≠ claimName.
(Do **not** rename anything for already-deployed/do-not-touch models.)

## Specifics learned (read before each model)

**Model-specific exceptions (preserve, don't "standardize" away):**
- **qwen36-27b** uses `vllm/vllm-openai:latest` (NOT v0.20.2) — its Gated-DeltaNet hybrid arch needs a newer vLLM.
- **glm-4-32b** keeps a custom `glm4_0414` tool parser: `parser-configmap.yaml` (ConfigMap `glm4-0414-parser`) mounted at `/opt/glm4_parser` + `--tool-parser-plugin` flag. Apply it alongside the ISVC. Repo moved `THUDM→zai-org` (`zai-org/GLM-4-32B-0414`).
- **qwen3-235b** is AWQ (`--quantization awq_marlin`, repo `QuantTrio/Qwen3-235B-A22B-Instruct-2507-AWQ`); whole-device (no gpumem).
- **geogalactica** (OPT) needs `--chat-template`; the init ensures `/data/model/chat_template.jinja` exists (snapshot's, else a minimal fallback).

**Operational specifics:**
- **Apply each file in its own `kubectl apply -f -`** (pvc → [parser-cm] → isvc → details). Concatenating fuses the YAML ("ConfigMap unknown field spec"); `--server-side --force-conflicts` also breaks on ConfigMaps → use plain `apply`.
- **Run test.py in the background** (`> /tmp/<m>-test.log 2>&1 &`) — the full reasoning battery exceeds the 10-min foreground cap.
- **`GW_INSECURE=1`** for login-node tests — the public edge (`https://inference.vulcan.alliancecan.ca`, Traefik on VIP .56) serves a self-signed `cert-manager.local` cert. httpx 0.28.1 is already importable on the login node (no venv needed there).
- **Tyk timeout** is 600 s in `51-tyk.yaml` (`TYK_GW_PROXYDEFAULTTIMEOUT`/read/write) — the old 30 s default 504'd long reasoning gens; fixed.
- **Gated models OK**: hf-token has access to google/gemma-3-4b-it, google/medgemma-27b-it, zai-org/GLM-4-32B-0414, geobrain-ai/geogalactica.
- **`guard_embed` can 404**: the auto-detect test's "embed via chat" guard picks the first embedder from `/v1/models?all=true` and may 404 — a cross-cutting guard/catalog artifact, **not** a per-model defect. Note + move on.
- **Wait for Ready via a background 30 s poller** watching ISVC Ready + pod phase; exit on Ready or CrashLoop/OOM/Failed. Heavy/TP4 models may Pending briefly on GPU contention (scale-to-zero frees cards within the 15 m retention).

---

## The per-model loop (do exactly this, in order, for every model)

1. **Standardize the repo files first** (before any apply): set the names above, fold any
   `download-job.yaml` into the ISVC initContainer (+ delete the file), drop `kustomization.yaml`,
   ensure the 6-file set exists (create missing `README.md`/`CLAUDE.md`/`test.py` from templates),
   confirm `minReplicas: 0`, v2 card, RWX pvc.
2. **Apply once:** `pvc.yaml` → `inferenceservice.yaml` (+ any `-configmap.yaml`) → `details.yaml`.
   Then **wait** for the initContainer to finish staging and the pod to go `Ready`. Do **not**
   re-apply/patch/scale while it's downloading/building (two writers on the RWX PVC → corrupted
   venv/weights → crashes). Big models: 4–20 min first time.
3. **Test from the login node** against the public edge:
   `GW_URL=https://inference.vulcan.alliancecan.ca TYK_KEY=<key> GW_INSECURE=1 MODEL=<id> python3 models/<m>/test.py`
   Reasoning models = full battery (copy `gpt-oss-120b/test.py`); vision models include the image
   block; non-reasoning = trimmed set.
4. **Tweak until only PASS/EXP remain.** Real failure → small fix only (missing parser flag, wrong
   `--max-model-len`, a name mismatch). Each tweak: fix the repo file, then **delete + re-create**
   the ISVC cleanly (`kubectl delete isvc <m>` → re-apply) so the initContainer rebuilds from a clean
   state — never patch a running/staging pod. Hard problem → skip-and-note, move on.
5. **Prove reproducibility — clean delete-all + redeploy:** delete the ISVC + card ConfigMap (+ any
   server `-configmap`), then re-apply the repo `pvc.yaml`+`inferenceservice.yaml`+`details.yaml` and
   re-run the test → **must PASS**. (Keep the weight PVC across this — it's a cache; the initContainer
   sees weights present and skips re-download, so this is fast. Delete/recreate the PVC only if its
   name had to change.) This guarantees the live model is reproduced purely from the repo.
6. **Leave deployed, scale to 0:** `minReplicas: 0`, no stop annotation; confirm 0 pods after the
   idle window and that the next request wakes it (503-with-ETA → 200).
7. **Record + commit:** `models/MODEL-STATUS.md` row + dated `CHANGELOG.md` entry (changelog-first),
   commit to `main`.
8. **Confirm no mess** (no stray pods, no half-state, working tree clean), **then** start the next model.

---

## Prerequisites (do once, before model 1)

- **`nfs-models` SC healthy:** via SSH to 43, `kubectl get sc nfs-models -o jsonpath='{.mountOptions}'`
  must be non-empty (`nfsvers=4.2,wsize=131072,rsize=131072`). If empty, STOP (weight writes EIO; the
  SC is immutable and must be deleted + `30-nfs.yaml` re-applied).
- **GPU nodes labeled `gpu=on`** → expect 5 workers.
- **`hf-token` Secret** present + current (gated models: gemma, medgemma, glm, geogalactica).
- **A Tyk key** for login-node testing (existing keys in `.env`, or `tyk-admin.sh add-user …`). Smoke
  test: `GW_URL=https://inference.vulcan.alliancecan.ca; curl -sk $GW_URL/v1/models -H "Authorization: Bearer $TYK_KEY"`.

---

## Phase A — Chat-LLM fleet

The 29 chat/completions LLMs **minus the 4 already on 43** (`gpt-oss-120b`, `gpt-oss-20b`,
`gemma-4-26b-a4b`, `qwen25-vl-7b` — do-not-touch).

**Reasoning models (verify thinking ON exposes `reasoning`, OFF strips+caps):**
`qwen3-32b`, `qwen3-235b`, `qwen35-122b`, `qwen36-27b`, `qwen36-35b-a3b`, `qwq-32b`,
`r1-distill-qwen-32b`, `r1-distill-llama-70b`, `phi-4-reasoning`, `glm-4-32b`, `gemma-3-4b-it`,
`medgemma-27b-it`.

**Vision/tool/chat:** `qwen25-coder-32b`, `qwen25-vl-3b`, `qwen25-vl-72b`, `qwen25-vl-72b-awq`,
`deepseek-v2-lite-16b`, `command-r-7b`, `openbiollm-70b`, `oceangpt-30b`, `geogalactica`,
`tinyllama-1-1b`, `astrosage`, `progen2` (completions), `crysta-llm`.

Per-model repo tidy notes:
- **Fold `download-job.yaml` → ISVC initContainer** (delete the file) for the 13 that have one.
- **Drop `kustomization.yaml`** (`tinyllama-1-1b` is the only chat LLM with one).
- Keep `glm-4-32b`'s `glm4_0414_tool_parser.py` + `parser-configmap.yaml`; keep `geogalactica/chat_template.jinja`.
- TP4 models (`qwen3-235b`, `qwen35-122b`, `openbiollm-70b`, `r1-distill-llama-70b`, `qwen25-vl-72b`)
  each bind 4 tenant-free L40S — fine at scale-0, but don't expect many hot at once.

> **Progress (2026-06-27):** 20 of these are live + committed — phi-4-reasoning, qwen3-32b, qwq-32b,
> qwen36-27b, r1-distill-qwen-32b, qwen36-35b-a3b, gemma-3-4b-it, medgemma-27b-it, glm-4-32b,
> qwen3-235b, qwen35-122b, r1-distill-llama-70b, qwen25-coder-32b, command-r-7b, deepseek-v2-lite-16b,
> oceangpt-30b, qwen25-vl-3b, qwen25-vl-72b-awq, qwen25-vl-72b, openbiollm-70b — all green.
> Remaining: geogalactica, tinyllama-1-1b, astrosage, progen2, crysta-llm. See `models/MODEL-STATUS.md`
> for per-model results + the `CHANGELOG.md` dated entries.

---

## Out of scope for this playbook

- **NIM models** (`boltz-2`, `openfold-3` cards; `rfdiffusion`, `evo2-40b`, `molmim`, `genmol`,
  `deepseek-v3.2`, `mistral-small-4` new) — separate plan (NGC keys, NIM container specifics).
- **49 v1-schema science/forecast/force-field conversions** (aurora, diffdock, graphcast, mace-*,
  esmfold, ithaca, moment, timesfm, …) — separate plan (custom servers / caduceus venv pattern).
- **The 4 always-on** (`bge-m3`, `bge-reranker-v2-m3`, `bge-small`, `xtts-v2`) and all other
  already-deployed workloads — **do not touch**.
- **`science-embed`** (plain Deployment, superseded) and **`mattergen`** (Knative rejects 1500s
  timeout > 600 max) — skip-and-note.

---

## Verification (per model, end-to-end)

- `GW_URL=https://inference.vulcan.alliancecan.ca TYK_KEY=… GW_INSECURE=1 MODEL=<id> python3 models/<m>/test.py` → only PASS/EXP remain.
- After the clean redeploy, the test **still passes** (repo is the source of truth).
- Model stays in the catalog; `kubectl get isvc <m> -n models` is `READY=True`, no CrashLoop, 0 pods
  after idle, wakes on next request.

## Tracking
- `models/MODEL-STATUS.md` (committed, source of truth) — refresh rows + chat matrix.
- `CHANGELOG.md` — dated entry per model/dir commit (changelog-first).
