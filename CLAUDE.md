# Aleph — RKE2 / Warewulf / HAMi Inference Platform

This repo (`ualberta-rcg/aleph`) holds the manifests, gateway, model definitions, and
docs for a self-deploying inference platform: an RKE2 Kubernetes cluster with HAMi
vGPU scheduling, KServe/Knative model serving, and a FastAPI gateway fronted by
Tyk (auth) and Traefik (public TLS edge).

> **Secrets live in `.env` (gitignored), never in committed files.** See
> [Secrets & `.env`](#secrets--env) below. Copy `.env.example` → `.env` and fill it in.
> Site-specific deployment values (VIP, NFS server, NIC names) are `__TOKEN__`ized —
> see `docs/SITE-VALUES.md`.

## Repo Layout

| Path | What |
|---|---|
| `gateway/` | FastAPI inference gateway (OpenAI + Anthropic compatible), Dockerfile, k8s manifests, Tyk config |
| `models/` | Per-model KServe `InferenceService` + `PVC` + `details.yaml` card + `test.py` battery (template: `models/test.template.py`) |
| `ww-overlays/` | Warewulf overlays + RKE2 auto-deploy manifests (baked into node images); site-value tokens + post-deploy steps |
| `gateway/test.py` | Model-agnostic gateway checks (catalog, health, guardrails, auth); `FLEET=1` warms + probes every model |
| `scripts/` | Ops helpers — `test-model.sh` (apply / recreate / up / status / cycle a model) |
| `docs/` + `CHANGELOG.md` | Site-neutral docs (`SITE-VALUES`, `ENDPOINTS`, `WW-OVERLAYS`, `LOGGING`, `TYK-USERS`) + `CHANGELOG` |

## Cluster Overview

HA RKE2 cluster: 3 control-plane nodes (VMs, no GPUs) + a dynamic pool of
Warewulf-provisioned stateless GPU workers (nodes are added/removed by booting them
with the right profile — never hardcode a worker inventory). Kubernetes v1.36,
CNI Canal + Multus, ingress Traefik (RKE2-bundled), storage NFS (`nfs-models`
StorageClass, the default).

### Access

All cluster commands run via SSH to any control-plane node; `kubectl` works
unrestricted inside that shell. One-liners from an admin host need the RKE2
PATH/KUBECONFIG exports:

```bash
ssh <control-plane-node> "export PATH=\$PATH:/var/lib/rancher/rke2/bin; \
  export KUBECONFIG=/etc/rancher/rke2/rke2.yaml; kubectl get nodes"
```

### Public endpoint

`https://<public-hostname>` → MetalLB L2 VIP → `rke2-traefik-public` (TLS terminate,
cert-manager/Let's Encrypt) → Tyk (auth + rate-limit) → model-gateway (FastAPI,
3 replicas) → KServe pods via knative-local-gateway. Bare-IP requests 404 — routing
is by Host header.

## Warewulf + Stateless Nodes

Nodes are provisioned via **Warewulf** — stateless, recreated from image + overlays.
The image determines the role: boot the Aleph worker profile and the node joins the
inference pool, which lets hardware move between batch computing and inference as
demand shifts. RKE2 auto-deploy manifests ride the control-plane overlay into
`/etc/rancher/manifests` → `rke2-manifests.service` stages them → RKE2 applies on
boot. Deploy lineage: **repo → bake on the Warewulf server (`__TOKEN__` substitution
per `SITE-VALUES.md`) → overlay → node boot → RKE2 auto-deploy.**

## GPU Setup (No GPU Operator)

- **No NVIDIA GPU Operator.** Drivers are baked into the GPU-worker OS image;
  `nvidia-container-cli` on the host handles container GPU injection.
- **HAMi** provides the device plugin + vGPU scheduler (replaces nvidia-device-plugin
  and GPU Operator). The device plugin DaemonSet requires the `gpu=on` node label
  (applied automatically at boot by `09-gpu-autolabel.yaml` when NVIDIA hardware is
  detected).
- Each GPU is split into 10 vGPU slices (`deviceSplitCount: 10`) → allocatable
  `nvidia.com/gpu` = 10 × physical cards per worker (a scheduling-slot count, not
  physical GPUs). VRAM requested via `nvidia.com/gpumem` in MiB for a slice, or
  whole devices via `nvidia.com/gpu: "<N>"` for large/tensor-parallel models.

## Workloads / Namespaces

| Namespace | Purpose |
|---|---|
| kube-system | Core + HAMi scheduler/device-plugin, RKE2 components |
| models | Model InferenceServices + model-gateway Deployment |
| tyk | Tyk OSS API gateway + Redis (auth layer) |
| istio-system | Istio service mesh (serving stack) |
| knative-serving | Knative Serving (scale-to-zero, revisions) |
| kubeflow | KServe controller |
| cert-manager | TLS cert automation |

## Gateway Stack

```
Internet → MetalLB VIP → Traefik (TLS, LE via cert-manager) → Tyk OSS (auth, rate-limit)
  → model-gateway (FastAPI, ClusterIP in models ns)
    → KServe pods via knative-local-gateway (scale-to-zero)
```

- **Gateway image**: pinned immutable `rkhoja/aleph:gateway-<sha>@sha256:…` in
  `ww-overlays/.../63-model-gateway.yaml` (CI also pushes `:latest`, but production
  never follows it).
- **Gateway deploy**: after CI publishes `gateway-<newsha>`, bump the pin in
  `63-model-gateway.yaml` and `kubectl set image deploy/model-gateway -n models
  gateway=rkhoja/aleph:gateway-<newsha>`. `imagePullPolicy: IfNotPresent` — a bare
  `rollout restart` does **not** pull a new build.
- **Tyk keys**: `tyk-admin.sh` on a control-plane node, or `gateway/tyk/tyk-keys.sh`
  from an admin host (see [TYK-USERS.md](TYK-USERS.md)).

## Secrets & `.env`

Secrets are **not** committed. The repo root has a gitignored `.env` (real values)
and a committed `.env.example` (template). Required values:

- `HF_TOKEN` — HuggingFace token used by model init/download containers.
- `TYK_SECRET` / `TYK_API_SECRET` — Tyk OSS gateway `APISecret` (admin API).

### HuggingFace token → k8s Secret

Model manifests reference the token via a Secret (`hf-token` in the `models`
namespace), not an inline value. Create/refresh it from `.env` before deploying
models:

```bash
set -a; source .env; set +a
kubectl create secret generic hf-token -n models \
  --from-literal=token="$HF_TOKEN" \
  --dry-run=client -o yaml | kubectl apply -f -
```

### Tyk secret

`gateway/tyk/tyk-keys.sh` reads `TYK_SECRET` / `TYK_API_SECRET` from the
environment. Export from `.env` before running.

## Changelog-First Commit Process

Every code/config change must be reflected in `CHANGELOG.md` **before** creating a
commit.

1. Group related edits into one logical change.
2. Add/update a dated entry in `CHANGELOG.md` (newest-first): what changed, why,
   deployment/operational impact, validation performed.
3. If the change is partial/in-progress, mark it clearly as follow-up required.
4. Stage `CHANGELOG.md` in the same commit as the code/manifests it describes.

Do **not** commit if code changed but `CHANGELOG.md` was not updated (typos /
comment-only changes excepted — note it in the commit message).

## Card Templates (v2 Schema — one standard)

`models/DETAILS-TEMPLATE-LLM.md` is the single source of truth for card format. All
3 templates use the **v2 compact schema** tested against the gateway.

**v2 schema structure** (gateway reads only these top-level keys):
`id`, `type`, `endpoints`, `routing`, `limits`, `scaling`, `behavior`,
`param_translation`, `defaults`, `custom_params`, `schema_version`, `input_map`,
`output_map`, `catalog`

Everything else (`owned_by`, `license`, `tags`, `description`, `deployment`,
`server_config`, etc.) goes inside `catalog` — the gateway ignores it but the
UI/catalog uses it.

**Do NOT use `compatibility` or `deployment` blocks.** The gateway reads `behavior.*`
only.

| Template | Use for |
|---|---|
| **A — vLLM chat LLM** | Chat models + completions-only + reasoning |
| **B — Custom science server** | FastAPI science models — 5 I/O patterns documented |
| **C — Embedding/rerank/audio/classification** | Non-LLM standard-endpoint models |

All templates include `input_map`/`output_map` (documentation-only; the gateway
does not read them).

- Thinking/reasoning: `param_translation.thinking` with `"mode": "budget"` maps
  effort → `thinking_token_budget`; always include `"disabled_effort": "none"`;
  `"mode": "none"` for non-reasoning models.
- OpenWebUI compat: `defaults.meta_tasks` (title/tags/followups) and `defaults.chat`.
- Anthropic endpoint: only `type: "chat"` models get `/v1/messages` translation;
  other types → 400.

## Working Conventions

- This repo is the source of truth for manifests, gateway code, and model
  definitions.
- Run kubectl via SSH to any control-plane node.
- Scale changes and park/stop semantics below are standing rules — follow them.

## Scaling Models Up/Down

**Always-up** is the catalog flag `details.scaling.scale_to_zero: false` (not merely
`minReplicas ≥ 1`). Those models run `minReplicas: 1` and stay in `/v1/models`.
Scale-to-zero models have `scale_to_zero: true` and `minReplicas: 0`.

**Never `kubectl patch` an InferenceService** (min/max/`scaleTarget`/args/image or
anything else). A patch creates a new Knative revision that fights the old one for
GPUs. Always **delete the ISVC and re-apply YAML**; **never delete the PVC**.

### Restart / bounce an ISVC (keep weights)
```bash
kubectl delete isvc <model> -n models
# do not delete the PVC
kubectl apply -f models/<model>/inferenceservice.yaml
# re-apply the card only if it should stay in the catalog:
kubectl apply -f models/<model>/details.yaml
```

### Park a model (hide from catalog)

**Parked means only this: delete the details ConfigMap from the cluster.** The
InferenceService and PVC stay; the card YAML stays in the repo. Un-park later by
re-applying that ConfigMap — nothing else.

```bash
# park (catalog hides it; ISVC/PVC untouched)
kubectl delete cm <model>-details -n models

# un-park (lists it again in /v1/models)
kubectl apply -f models/<model>/details.yaml
```

Park is not `stop`.

### `serving.kserve.io/stop` (different from park)

`stop=true` fully stops the InferenceService: no pods, and it will **not** wake on
demand. Knative honors this even when `minReplicas: 1`. The card still lists the
model in `/v1/models` if the ConfigMap is present. Use this when a model must not
run, not to hide it from the catalog.

```bash
# stop — no pods, blocks wake-on-demand
kubectl annotate isvc <model> -n models serving.kserve.io/stop=true --overwrite

# clear stop — wake-on-demand again (min 0) or stay always-up (min 1)
kubectl annotate isvc <model> -n models serving.kserve.io/stop- --overwrite
```

Just setting `minReplicas: 0` is not enough to stop a model; without `stop`, the
first request wakes it. Do not `kubectl patch` the ISVC spec to toggle this — if
the YAML must change, delete the ISVC, keep the PVC, re-apply.

### Check readiness
```bash
kubectl get isvc <model> -n models -o jsonpath='{.status.conditions[?(@.type=="Ready")].status}'
```
