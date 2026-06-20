# Model Cluster Audit

Paste this into a fresh Claude Code session (from the repo root) to run the full model audit.
Reusable across clusters — substitute the per-cluster values in §Context.

You are auditing a HAMi/KServe cluster that serves AI models via KServe InferenceServices. Go
through **every model** in `models/MODEL-STATUS.md`, inspect its live cluster state **and** its
repo-side config, record findings, and **create/fix missing files** where needed. Two passes:
first audit (read-only on cluster), then fix repo files (no cluster changes).

## Context (substitute per cluster)

- **Control-plane node:** `<head-node-ip>` (e.g. `kubeflow-head-node2`)
- **Worker / GPU node:** `<gpu-node-ip>` (e.g. `rack15-03`, 4× L40S 48GB)
- **kubectl from the login node:** a *non-interactive* SSH does NOT source the node profile, so
  `kubectl` is not on PATH — export it (this is an easy gotcha):
  ```bash
  sudo ssh root@<head-node-ip> "export PATH=\$PATH:/var/lib/rancher/rke2/bin; export KUBECONFIG=/etc/rancher/rke2/rke2.yaml; kubectl get nodes"
  ```
  Inside an *interactive* shell on the node, `kubectl` works without setup. Chain commands with
  `&&`/`;` inside one SSH string to batch round-trips.
- **Gateway:** the model-gateway ClusterIP in ns `models` — `kubectl get svc model-gateway -n models`.
- Each model lives in `models/<model-name>/` in this repo.
- Models use HAMi for GPU scheduling (`nvidia.com/gpu` whole-device or `nvidia.com/gpumem` vGPU
  split); GPU nodes carry the `gpu=on` label.
- Weight PVCs use the `nfs-models` StorageClass (NFS-backed, OneFS-safe mount options).

## Key reference files in the repo

Read these first — they define the conventions:

| File | What it tells you |
|---|---|
| `models/CLAUDE.md` | Directory contract, deploy process, GPU/HAMi conventions, storage, validation checklist |
| `models/CLAUDE-TEMPLATE.md` | Template for per-model `CLAUDE.md` notes (quirks, runtime, resources) |
| `models/DETAILS-TEMPLATE-LLM.md` | Templates for `details.yaml` ConfigMaps (vLLM LLM, science server, embedding). **Use to create missing details.yaml.** |

## Best production exemplars — study these first

The most complete, well-structured model dirs. Read them before auditing so you know "good":

| Model | Why it's good |
|---|---|
| `gpt-oss-120b/` | Gold-standard `CLAUDE.md` + `details.yaml`. Architecture, vLLM args, gateway integration, known issues, file inventory. |
| `gemma-4-26b-a4b/` | Clean vLLM LLM example. MoE, vision, tool calling. |
| `phi-4-reasoning/` | Reasoning model with `param_translation` effort maps in details.yaml. |
| `diffdock/` | Best science/custom-server example. `input_map`/`output_map`, subprocess inference backend. |
| `aurora/` | Weather forecast. `kserve_custom` routing, non-OpenAI endpoint patterns. |
| `medgemma-27b-it/` | Clean multimodal medical LLM. `--limit-mm-per-prompt`, license concerns. |

---

## Pass 1 — Cluster Audit (read-only)

### What to check for each model

#### From the live cluster:

1. **PVC exists and bound?** — `kubectl get pvc -n models`. Look for one matching the model
   name. Note `Bound` / `Pending` / missing.
2. **InferenceService exists and Ready?** — `kubectl get isvc <model> -n models -o wide`. Note
   READY, URL, warnings.
3. **Scale-to-zero configured?** — `kubectl get isvc <model> -n models -o jsonpath='{.spec.predictor.minReplicas}'`.
   `0` = scale-to-zero; `1+` = always-on (note if it shouldn't be).
4. **GPU resource requests sensible?** — pull full ISVC JSON once (see Approach); per model check
   `nvidia.com/gpu` (whole device, TP≥2) vs `nvidia.com/gpumem` (HAMi vGPU split, small
   single-GPU). Note wrong patterns.
5. **Pod status (if running)?** — `kubectl get pods -n models -l serving.kserve.io/inferenceservice=<model>`.

#### From the repo (local filesystem):

6. **`details.yaml` exists and complete?** — check key fields (`id`, `type`, `endpoints`,
   `source`, `deployment`, `routing`, `compatibility`) against the templates in
   `DETAILS-TEMPLATE-LLM.md`. Note placeholders/shortcomings.
7. **`CLAUDE.md` exists and useful?** — covers purpose, runtime, resources, quirks. Note stubs.
8. **Kustomization present and valid?** — `ls models/<model>/kustomization.yaml`; scan for
   obvious issues.

### How to record Pass 1 results

Add a column **`Audit`** to `MODEL-STATUS.md` (after the `Note` column). Short status string:

| Tag | Meaning |
|---|---|
| `PVC:ok`/`PVC:missing`/`PVC:pending` | PVC state |
| `ISVC:ready`/`ISVC:notready`/`ISVC:missing` | InferenceService state |
| `SCALE:zero`/`SCALE:always`/`SCALE:?` | minReplicas |
| `GPU:ok`/`GPU:odd` | GPU request sanity |
| `DETAILS:ok`/`DETAILS:thin`/`DETAILS:missing` | details.yaml state |
| `CARD:ok`/`CARD:stub`/`CARD:missing` | CLAUDE.md state |
| `KUST:ok`/`KUST:issue` | kustomization state |
| `POD:running`/`POD:crash`/`POD:scaled` | pod state |

Separate tags with `; `. e.g. `PVC:ok; ISVC:ready; SCALE:zero; GPU:ok; DETAILS:ok; CARD:ok; KUST:ok; POD:scaled`.

---

## Pass 2 — Fix Repo Files (no cluster changes)

Create/improve repo files for models that need it. **Do not change anything on the cluster — no
`kubectl apply`.**

### What to create/fix

1. **Missing `details.yaml`** — use the matching template from `DETAILS-TEMPLATE-LLM.md`
   (vLLM LLM → A, custom science → B, embedding → C). Fill `CHANGEME` from the model's
   `inferenceservice.yaml`, `CLAUDE.md`, and HuggingFace metadata.
2. **Thin `details.yaml`** — add missing key fields (routing, compatibility, deployment,
   `input_map`) from `inferenceservice.yaml`.
3. **Missing `CLAUDE.md`** — use `CLAUDE-TEMPLATE.md`; fill from `inferenceservice.yaml` +
   `details.yaml`.
4. **Stub `CLAUDE.md`** — add: what the model does, image + runtime, GPU/memory, API path(s),
   known quirks from `MODEL-STATUS.md`.

### What NOT to create

- No `details.yaml`/`CLAUDE.md` for `NO-ISVC` or `CANCELLED` models (not deployed).
- No `inferenceservice.yaml`/`pvc.yaml` — deploy files, out of audit scope.

---

## Approach

### Bulk-fetch cluster state first (saves N SSH round-trips)

```bash
HEAD=<head-node-ip>
K='export PATH=$PATH:/var/lib/rancher/rke2/bin; export KUBECONFIG=/etc/rancher/rke2/rke2.yaml; kubectl'
sudo ssh root@$HEAD "$K get isvc -n models -o json"   > /tmp/all-isvc.json
sudo ssh root@$HEAD "$K get pvc -n models -o wide"    > /tmp/all-pvc.txt
sudo ssh root@$HEAD "$K get pods -n models -o wide"   > /tmp/all-pods.txt
```

Parse `all-isvc.json` locally (jq/python) for per-model Ready status, minReplicas, GPU requests,
image, args.

### Then iterate model-by-model

For each model in `MODEL-STATUS.md`: look up cluster state from the bulk files; read its
`details.yaml`, `CLAUDE.md`, `kustomization.yaml`; record audit tags; note what needs fixing.

### After all models audited

1. Write the updated `MODEL-STATUS.md` with the `Audit` column (preserve existing content/formatting).
2. Create/fix the flagged `details.yaml` and `CLAUDE.md` files.
3. Commit but **do not push** until reviewed.

### Important constraints

- **Read-only on the cluster.** No `kubectl apply`/`delete`/`edit`/`patch` — only `get`,
  `describe`, `logs`.
- **No heavy commands on the login node.** SSH to the kube node for kubectl; don't run Python
  model work locally. A trivial YAML parse of small files is fine.
- **Batch SSH calls** — pull bulk data in one shot.
- When creating `details.yaml`, follow `DETAILS-TEMPLATE-LLM.md` exactly (same structure/field names).
