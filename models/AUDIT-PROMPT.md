# Model Cluster Audit Prompt

Paste this into a fresh Claude Code session (from `~/hami-cluster-test/`) to run the full model audit.

---

## Prompt

You are auditing the HAMI Kubernetes cluster that serves AI models via KServe InferenceServices. Your job is to go through **every model** listed in `/scratch/rahimk/repos/aleph/models/TEST-STATUS.md`, inspect its live cluster state **and** its repo-side config files, record findings, and **create missing/incomplete files** where needed. You have two passes: first audit (read-only on cluster), then fix repo files (no cluster changes).

### Context

- **Control plane node:** `172.26.92.230` (kubeflow-head-node2)
- **Worker node:** `172.26.93.227` (rack15-03, 4× L40S 48GB)
- **Kubectl on the head node** works without PATH/KUBECONFIG setup — just SSH in first
- **From Vulcan login node**, chain kubectl through SSH:
  ```bash
  sudo ssh root@172.26.92.230 "kubectl get isvc -A"
  ```
- **Gateway ClusterIP:** `http://10.43.79.101:80` (in-cluster only)
- Each model lives in its own directory under `/scratch/rahimk/repos/aleph/models/<model-name>/`
- Models use HAMi for GPU scheduling (`nvidia.com/gpu` or `nvidia.com/gpumem` resource requests).
- The cluster uses NFS-backed `PersistentVolumeClaims` (PVCs) for model weights cache.

### Key reference files in the repo

Before starting, **read these** — they define the conventions:

| File | What it tells you |
|---|---|
| `/scratch/rahimk/repos/aleph/models/CLAUDE.md` | Directory contract, deploy process, GPU/HAMi conventions, storage, validation checklist |
| `/scratch/rahimk/repos/aleph/models/CLAUDE-TEMPLATE.md` | Template for per-model `CLAUDE.md` notes (quirks, runtime, resources) |
| `/scratch/rahimk/repos/aleph/models/DETAILS-TEMPLATE.md` | Templates for `details.yaml` ConfigMaps (3 patterns: vLLM LLM, science server, embedding). **Use this to create missing details.yaml files.** |

### Best production exemplars — study these first

These are the most complete, well-structured model dirs. Read them before auditing so you know what "good" looks like:

| Model | Why it's good |
|---|---|
| `gpt-oss-120b/` | Gold-standard `CLAUDE.md` (144 lines) and `details.yaml` (155 lines). Covers architecture, vLLM args, gateway integration, known issues, startup warnings, file inventory. |
| `gemma-4-26b-a4b/` | Clean vLLM LLM example. Good `details.yaml` with MoE, vision, tool calling. Moderate complexity. |
| `phi-4-reasoning/` | Good reasoning model example with `param_translation` effort maps in details.yaml. |
| `diffdock/` | Best science/custom server example. Clean `details.yaml` with input_map/output_map, subprocess inference backend. |
| `aurora/` | Good weather forecast example. Shows `kserve_custom` routing, non-OpenAI endpoint patterns. |
| `medgemma-27b-it/` | Clean multimodal medical LLM. Shows `--limit-mm-per-prompt`, license concerns documented. |

---

## Pass 1 — Cluster Audit (read-only)

### What to check for each model

#### From the live cluster:

1. **PVC exists and bound?**
   ```bash
   sudo ssh root@172.26.92.230 "kubectl get pvc -n models"
   ```
   Look for a PVC matching the model name. Note if `Bound`, `Pending`, or missing.

2. **InferenceService exists and Ready?**
   ```bash
   sudo ssh root@172.26.92.230 "kubectl get isvc <model-name> -n models -o wide"
   ```
   Note READY (True/False), URL, warnings.

3. **Scale-to-zero configured?**
   ```bash
   sudo ssh root@172.26.92.230 "kubectl get isvc <model-name> -n models -o jsonpath='{.spec.predictor.minReplicas}'"
   ```
   `0` = scale-to-zero. `1+` = always-on (note if it shouldn't be).

4. **GPU resource requests sensible?**
   Pull full ISVC JSON once (see Approach below) and check per-model:
   - `nvidia.com/gpu` = whole device (correct for TP≥2)
   - `nvidia.com/gpumem` = HAMi vGPU split (correct for small single-GPU models)
   - Note if wrong pattern used (e.g., `gpu` instead of `gpumem` for embedding model)

5. **Pod status (if running)?**
   ```bash
   sudo ssh root@172.26.92.230 "kubectl get pods -n models -l serving.kserve.dev/inferenceservice=<model-name>"
   ```

#### From the repo (local filesystem):

6. **`details.yaml` exists and complete?**
   - Read `/scratch/rahimk/repos/aleph/models/<model-name>/details.yaml`
   - Check it has the key fields: `id`, `type`, `endpoints`, `source`, `deployment`, `routing`, `compatibility`
   - Compare against the templates in `DETAILS-TEMPLATE.md`
   - Note if missing fields, has placeholder values, or is much shorter than similar models

7. **`CLAUDE.md` exists and useful?**
   - Read `/scratch/rahimk/repos/aleph/models/<model-name>/CLAUDE.md`
   - Check it covers at minimum: purpose, runtime, resources, known quirks
   - Note if it's a stub (just the template with no real content) or genuinely useful

8. **Kustomization present and valid?**
   ```bash
   ls /scratch/rahimk/repos/aleph/models/<model-name>/kustomization.yaml
   ```
   Quick scan for obvious issues (wrong image, missing PVC reference, etc.).

### How to record Pass 1 results

Add a new column **`Audit`** to the TEST-STATUS.md table (after the existing `Note` column). For each model, write a short status string using these tags:

| Tag | Meaning |
|---|---|
| `PVC:ok` | PVC exists and is Bound |
| `PVC:missing` | No PVC found |
| `PVC:pending` | PVC exists but not Bound |
| `ISVC:ready` | InferenceService reports Ready=True |
| `ISVC:notready` | InferenceService exists but not Ready |
| `ISVC:missing` | No InferenceService found |
| `SCALE:zero` | Scale-to-zero configured (minReplicas=0) |
| `SCALE:always` | Always-on (minReplicas≥1) |
| `SCALE:?` | Can't determine |
| `GPU:ok` | GPU request looks reasonable |
| `GPU:odd` | GPU request looks unusual (note why) |
| `DETAILS:ok` | details.yaml exists and has key fields |
| `DETAILS:thin` | details.yaml exists but missing fields (note which) |
| `DETAILS:missing` | No details.yaml at all |
| `CARD:ok` | CLAUDE.md exists with real content |
| `CARD:stub` | CLAUDE.md is just the unfilled template |
| `CARD:missing` | No CLAUDE.md |
| `KUST:ok` | Kustomization looks fine |
| `KUST:issue` | Kustomization has something off (note what) |
| `POD:running` | Pod is Running |
| `POD:crash` | Pod in CrashLoopBackOff or similar |
| `POD:scaled` | No pod (scaled to zero — expected) |

Separate tags with `; `. Example: `PVC:ok; ISVC:ready; SCALE:zero; GPU:ok; DETAILS:ok; CARD:ok; KUST:ok; POD:scaled`

---

## Pass 2 — Fix Repo Files (no cluster changes)

After the audit, go back and **create or improve** repo-side files for models that need it. **Do not change anything on the cluster — no kubectl apply.**

### What to create/fix

1. **Missing `details.yaml`** — Create one using the appropriate template from `DETAILS-TEMPLATE.md`:
   - vLLM LLM → Template A
   - Custom science server → Template B
   - Embedding model → Template C
   - Fill in all `CHANGEME` fields by reading the model's `inferenceservice.yaml`, `CLAUDE.md` (if exists), and checking HuggingFace for model metadata.

2. **Thin `details.yaml`** — If it's missing key fields (routing, compatibility, deployment, input_map), add them. Look at the model's `inferenceservice.yaml` to fill in the real values.

3. **Missing `CLAUDE.md`** — Create one using `CLAUDE-TEMPLATE.md`. Fill in from `inferenceservice.yaml` and `details.yaml`.

4. **Stub `CLAUDE.md`** — If it's just the template with no real content, fill it in. At minimum add:
   - What the model does
   - Image and runtime
   - GPU/memory resources
   - API path(s)
   - Any known quirks from TEST-STATUS.md Note column

### How to get info for missing cards

For each model that needs a new/improved file:
- Read its `inferenceservice.yaml` → gives you image, resources, args, env vars, PVC mount
- Read its `details.yaml` (if exists) → gives you description, source, type
- Read its `kustomization.yaml` → gives you file inventory
- Check the HuggingFace page (web search for `huggingface.co <source>`) for model card info
- Look at the TEST-STATUS.md Note column for known quirks

### What NOT to create

- Don't create `details.yaml` or `CLAUDE.md` for models with `NO-ISVC` or `CANCELLED` status (they're not deployed).
- Don't create `inferenceservice.yaml` or `pvc.yaml` — those are deploy files, not audit scope.

---

## Approach

### Bulk-fetch cluster state first

```bash
# One big pull — saves 150 SSH round-trips
sudo ssh root@172.26.92.230 "kubectl get isvc -n models -o json" > /tmp/all-isvc.json
sudo ssh root@172.26.92.230 "kubectl get pvc -n models -o wide" > /tmp/all-pvc.txt
sudo ssh root@172.26.92.230 "kubectl get pods -n models -o wide" > /tmp/all-pods.txt
```

Parse `all-isvc.json` locally with python/jq to extract per-model: Ready status, minReplicas, GPU requests, container image, args.

### Then iterate model-by-model

For each model in TEST-STATUS.md:
1. Look up cluster state from the bulk-fetched files
2. Read the model's `details.yaml`, `CLAUDE.md`, `kustomization.yaml` locally
3. Record audit tags
4. Note what needs creating/fixing

### After all models audited

1. Write the updated TEST-STATUS.md with the `Audit` column
2. Create/fix the flagged `details.yaml` and `CLAUDE.md` files
3. Commit everything but **do not push** until the user reviews

### Important constraints

- **Read-only on the cluster.** No `kubectl apply`, `kubectl delete`, `kubectl edit`, or any mutation. Only `get`, `describe`, `logs`.
- **Do not run heavy commands on the Vulcan login node.** SSH to the kube nodes for kubectl, don't run Python locally.
- **Batch your SSH calls** — pull bulk data in one shot.
- **Don't change any ISVCs or cluster state.** Only repo files (`details.yaml`, `CLAUDE.md`) in Pass 2.
- The file is at `/scratch/rahimk/repos/aleph/models/TEST-STATUS.md`. Read it first, then add the `Audit` column, preserving all existing content and formatting.
- When creating new `details.yaml`, follow the templates in `DETAILS-TEMPLATE.md` exactly — same structure, same field names.
