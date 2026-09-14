# Kubernetes and serving

This guide covers Aleph's Kubernetes configuration and serving behavior. Overlay
rendering and storage bindings belong in [Warewulf](WW-OVERLAYS.md); host services
and drivers belong in [System](SYSTEM.md). These notes describe repository
configuration, not a live inventory.

## Component map

| Namespace | Role |
|---|---|
| `kube-system` | RKE2 components, HAMi, and hardware discovery |
| `tyk` | API authentication and Redis |
| `models` | Model InferenceServices, cards, and the Aleph gateway |
| `istio-system` | Serving network |
| `knative-serving` | Revisions, activation, and autoscaling |
| `kubeflow` | KServe controller |
| `cert-manager` | Certificate management |

The numbered manifests under
`ww-overlays/overlays/control-plane/etc/rancher/manifests/` define the platform.
Individual model services live under `models/`.

## Placement and networking

The supplied Traefik configuration places ingress on control-plane nodes. The
Aleph gateway also targets control-plane nodes and excludes GPU workers. Review
those selectors when changing node roles.

Gateway replicas use preferred pod anti-affinity, so spreading is a preference,
not a guarantee of one replica per node. Replica count alone does not establish
availability during maintenance.

Traefik routes the public hostname to Tyk, which authenticates requests before
forwarding to the gateway. Model traffic then reaches KServe through Knative's
local gateway. Verify each layer separately when tracing a routing failure.
The Canal interface selection is an overlay setting documented in
[Warewulf](WW-OVERLAYS.md#overlay-settings-to-review).

## Model lifecycle

A details ConfigMap supplies the model card; an InferenceService supplies its
runtime. A catalog entry does not prove a predictor is ready. Gateway readiness
requires a card and completed discovery, not successful inference for every model.

Keep the card's `scaling` settings consistent with the model's replica settings.
A cold-start guard can return `503` with retry guidance; its capacity estimate is
advisory, not a reserved GPU allocation. Do not manually scale generated predictor
Deployments as a permanent configuration change: their lifecycle is controller-managed.

For InferenceService spec changes, delete the service, let old predictors and
revisions clear, and reapply the model files. Preserve PVCs. Hiding a card and
stopping execution are distinct operations; use [Add a model](ADD-A-MODEL.md)
for the complete workflow.

## Platform changes

Knative's bootstrap enables the pod features used by these models, including
PVC access, init containers, selectors, affinity, tolerations, and runtime classes.
Review `61-knative.yaml` when a previously valid predictor spec is rejected.

The gateway Deployment uses a pinned image, rolling updates, readiness probes,
and a termination grace period. Keep replica capacity, proxy timeouts, and
termination behavior consistent when adjusting it. Ready replicas during a rollout
do not prove that all existing streams finished successfully.

For an authorized platform update, change the owning manifest, synchronize its
rendered boot source, and validate the affected resources and request path.
Record what was checked in the dated changelog. Gateway behavior is documented
in [the gateway reference](../gateway/README.md); accounting and monitoring are
in [Logging and metrics](LOGGING.md).

## Verified findings

**2026-09-13 — zero initial replicas.** A read-only check of the running
`knative-serving/config-autoscaler` ConfigMap found `initial-scale: "0"` and
`allow-zero-initial-scale: "true"`. The committed `61-knative.yaml` enables pod
features but does not explicitly write these autoscaler values. A working live
configuration therefore does not prove a fresh bootstrap reproduces it. Review
and persist the intended autoscaler settings in the owning deployment source
before relying on that behavior after a rebuild. This documentation update does
not change the live ConfigMap or the bootstrap manifest.

## Bootstrap and request-path diagnostics

The older runbook combines several independent failure modes. Check the owning
component instead of restarting the entire stack:

| Symptom | Check |
|---|---|
| Serving bootstrap has stalled | Inspect the Jobs in `60-istio.yaml`, `61-knative.yaml`, and `62-kserve.yaml`, their prerequisite namespaces/controllers, and image/download reachability. Filenames alone do not enforce readiness. |
| Tyk starts but loads no APIs | `51-tyk.yaml` must both mount the `tyk-api-definitions` ConfigMap and set `TYK_GW_APPPATH` to that mount. Setting the path without mounting definitions is insufficient. |
| A GPU worker is Ready but advertises no HAMi resources | Check host GPUs first, then `09-gpu-autolabel.yaml` and the `gpu=on` selector that enables the GPU stack. |
| A model appears in the catalog but requests fail | Check its InferenceService, predictor readiness and startup, card route, then a valid request through the authenticated public endpoint. |
| A long request times out | Review the Tyk proxy limits, gateway upstream timeout, predictor settings, and client timeout together. Identify which layer ended the request before changing all of them. |
| A fresh worker starts a model slowly | Distinguish container-image pull, weight download, environment preparation, and loading weights into GPU memory. An existing weight PVC does not mean every startup cost is cached. |

Keep Tyk administration on the operator's internal path. User-facing HTTPS and
catalog checks do not establish that key administration or access to private
records is appropriately restricted; use [the Tyk guide](TYK-USERS.md) for that
interface. Keep usage-ledger access and metric semantics in
[Logging and metrics](LOGGING.md).

These checks were extracted from the local runbook and post-deploy notes and
reviewed against the committed bootstrap and Tyk manifests on 2026-09-13. The
old post-deploy smoke helper is not the acceptance path: it does not create the
cards the gateway needs. Deploy and test one complete model using
[Add a model](ADD-A-MODEL.md).

## HAMi diagnostics

Begin with the affected model and worker, not a stack restart:

```bash
kubectl get nodes -L gpu
kubectl get daemonsets,deployments -n kube-system
kubectl get pods -n models -l "serving.kserve.io/inferenceservice=$ISVC" -o wide
kubectl get events -n models --field-selector "involvedObject.name=$POD" \
  --sort-by=.metadata.creationTimestamp
```

Set `ISVC` and `POD` to the affected service/pod. Inspect only relevant events;
keep raw application logs and private data out of shared reports.

| Finding | Next check |
|---|---|
| No GPU resource advertised | Verify worker-side `nvidia-smi`, the `gpu=on` label, device-plugin readiness, NVIDIA toolkit/containerd runtime and `nvidia` RuntimeClass. The node image supplies drivers; installing another GPU Operator is not this deployment's repair procedure. |
| Scheduler fails after Kubernetes update | Compare the running Kubernetes version with the HAMi scheduler image selected by `__K8S_VERSION__` in `10-hami.yaml`. |
| Pending with insufficient resources | Inspect requests, selectors/affinity, tolerations, current HAMi assignments and old predictor revisions. Check fit on one suitable node for a multi-GPU replica, not fleet-wide free-slot totals. |
| Whole-device allocation fails despite free slots | `nvidia.com/gpu` allocatable represents sharing slots. Whole-device requests omit `gpumem`; existing tenants can prevent a whole-device allocation. Do not restore the historical near-full-memory workaround. |
| Shared model gets a memory-limit failure | Check `nvidia.com/gpumem` in MiB, runtime memory settings, context/concurrency, and actual loaded footprint. Free host VRAM does not override a tenant's allowance. |
| Pod scheduled but not ready | Separate image pulls, downloads/NFS writes, initialization, runtime OOM, and health-probe failures. HAMi scheduling success is not inference readiness. |
| Multi-GPU execution falls back or hangs | Check tensor-parallel configuration and the actual transport; use System's RDMA provider diagnostics if RDMA is required. |

For the exact assigned pod, inspect resource configuration without dumping its
entire environment:

```bash
kubectl get pod "$POD" -n models -o jsonpath='{.spec.nodeName}{"\n"}{range .spec.containers[*]}{.name}{": "}{.resources}{"\n"}{end}'
```

HAMi split counts and policies may come from chart defaults; source comments are
not proof of effective values. Inspect the deployed configuration before estimating
capacity. Preserve PVCs during service recreation and wait for old revisions to
release resources. Physical utilization measurement is covered in
[Logging and metrics](LOGGING.md#measure-physical-gpu-usage).
