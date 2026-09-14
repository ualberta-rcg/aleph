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
