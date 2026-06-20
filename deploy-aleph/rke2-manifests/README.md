# RKE2 auto-deploy manifests

Modular, version-controlled RKE2 auto-deploy manifests. Drop these on a node's manifests
path and RKE2 applies them at boot, so the **next Warewulf deployment brings most of the
platform up automatically**.

**This iteration's goal:** every component **installed and available**, in a default/ready
state, **one file per component** (HAMi, KubeRay, NFS, cert-manager, Traefik, Tyk, and the
serving stack split into Istio / Knative / KServe / Profiles). Site-specific wiring (macvlan
public-IP, `gpu=on` labels, Tyk secret, cert hostnames) is a **post-deploy customization
step** (see below). The set will be refined iteratively.

**Architecture:** cluster 232's front-door/TLS pattern, but **lean** — no full Kubeflow
(no Dex / Central Dashboard / Pipelines / oauth2-proxy), no Rancher, no certbot. Just the
serving stack: cert-manager + Istio/Knative/KServe + Tyk + Traefik, with HAMi + KubeRay + NFS.

## How RKE2 applies these

On a Warewulf-provisioned node, the overlay-baked `rke2-manifests.service` copies
`/etc/rancher/manifests/*.yaml` into `/var/lib/rancher/rke2/server/manifests/`, which RKE2
watches and applies at startup. So: copy this directory to `/etc/rancher/manifests/` on the
control-plane node (or place files directly in `…/server/manifests/` on a non-WW node).
RKE2's helm-controller reconciles each `HelmChart`; the job-controller runs each bootstrap
Job. File-number prefixes are for humans (controllers reconcile independently of filename
order).

## File list

| File | Installs | Source |
|---|---|---|
| `00-cert-manager.yaml` | cert-manager (CRDs on) | split from 230 `rancher.yaml`; **Rancher dropped** |
| `01-cluster-issuer.yaml` | Let's Encrypt `ClusterIssuer` (ACME HTTP-01 via traefik) | new |
| `10-hami.yaml` | HAMi vGPU scheduler + device plugin | 230 `hami.yaml` verbatim |
| `20-kuberay.yaml` | KubeRay operator 1.5.1 (pinned off GPU) | 230 `kuberay.yaml` + scheduling |
| `30-nfs.yaml` | nfs-subdir provisioner → **`nfs-models`** SC (default, OneFS-safe) | 230 `nfs.yaml` + `storage/nfs-models-storageclass.yaml` merged |
| `40-traefik.yaml` | Traefik (generic, service enabled) | 230/232 `traefik.yaml` minus macvlan |
| `50-tyk-redis.yaml` | Bitnami Redis (ns `tyk`) | `04-install-tyk-gateway.sh` |
| `51-tyk.yaml` | Tyk OSS gateway (ns `tyk`) | `configs/tyk-oss-values.yaml` |
| `60-istio.yaml` | Job: Istio + Kubeflow mesh scaffolding | kubeflow/manifests v1.11 slice |
| `61-knative.yaml` | Job: Knative Serving + `config-features` patch | kubeflow/manifests slice + post-install #1 |
| `62-kserve.yaml` | Job: KServe + `models` ns + config + Istio allow-all | kubeflow/manifests slice + post-install #2–4 |
| `63-profiles.yaml` | Job: Kubeflow Profiles (**optional**) | kubeflow/manifests slice |

`../examples/ray-cluster-template.yaml` — RayCluster skeleton (head→non-GPU, worker→GPU,
scale-to-zero). Lives **outside** this dir so RKE2 does **not** auto-apply it.

**Serving-stack Jobs (60–63):** split from the old monolithic `kubeflow-bootstrap` into one
Job per component, each with its own ServiceAccount and **self-ordering** via internal waits
(Istio→Knative→KServe→Profiles) and retries (`backoffLimit`). The former `02-post-install.sh`
patches are **folded in** so KServe is fully working, not just installed: Knative
`config-features` (enables PVCs, init containers, nodeSelectors, the nvidia runtime class) is
in `61-knative.yaml`; the KServe `inferenceservice-config`, the `models` namespace, and the
Istio ALLOW policy for `models` are in `62-kserve.yaml`.

## Site-config values to substitute before deploy

| File | Value | 230 example |
|---|---|---|
| `30-nfs.yaml` | `nfs.server`, `nfs.path` | `manage.storage.data.vulcan.local` / `/aleph` |
| `10-hami.yaml` | `scheduler.kubeScheduler.imageTag` (match cluster k8s version) | `v1.36.1` |
| `01-cluster-issuer.yaml` | `acme.email` | `admin@alliancecan.ca` (maintainer `khoja1@ualberta.ca`) |
| `51-tyk.yaml` | `global.secrets.APISecret` (placeholder → real) | from `.env` `TYK_API_SECRET` |

## Post-deploy customization checklist

1. **Label GPU nodes:** `kubectl label node <gpu-node> gpu=on` (HAMi device-plugin needs it).
2. **Wait for charts:** `kubectl get helmchart -A -w` → all `Resolved`.
3. **NFS:** `kubectl get sc nfs-models` → default, mountOptions present.
4. **Serving stack (4 self-ordering Jobs):** `kubectl get jobs -n kube-system` → the
   `istio/knative/kserve/profiles-bootstrap` jobs all `Complete`; then
   `kubectl get pods -n istio-system,knative-serving,kubeflow` Running. They chain
   automatically; a failed one retries until its prerequisite is up.
5. **Traefik front door (customization, not manifests):** add the macvlan NetworkAttachmentDefinition
   + public IP, rebind Traefik entrypoints to that IP, set the hostname + TLS (mirrors 232's
   `rke2-manifests/traefik.yaml`). Also expose **port 80** for cert-manager HTTP-01.
6. **cert-manager:** set a real `acme.email`; once port 80 is reachable, add a `Certificate` CR
   per endpoint hostname → `kubectl get certificate` → `Ready`.
7. **Tyk:** inject the real admin secret from `.env` (`TYK_API_SECRET`) into
   `secrets-tyk-oss-tyk-gateway`, then load API definitions via `gateway/remote-deploy.sh`.
8. **Deploy the gateway + models** (`deploy.sh`, `kubectl apply -f models/<name>/`).

## What is NOT here (by design)

- **macvlan / public IP** — node customization (step 5).
- **Rancher** — dropped; cert-manager kept.
- **certbot** — cert-manager ACME replaces it (HTTP-01, port 80).
- **Full Kubeflow** (Dex/dashboard/pipelines) — the serving Jobs install only
  Istio/Knative/KServe. Kubeflow Profiles is an **opt-in file** (`63-profiles.yaml`) — delete
  it to omit Profiles entirely.
- **Warewulf overlay** (OS image, NVIDIA driver/toolkit, containerd nvidia runtime, RKE2
  install, `gpu=on` label) — lives on the WW server `172.26.92.10`, separate effort. These
  manifests assume nodes are already provisioned.

## Follow-ups (the manifests "will get better")

- **Double-Traefik:** RKE2 bundles `rke2-traefik`; deploying our own means two ingress
  controllers. Recommended: disable the bundled one via RKE2 server config (WW overlay)
  `disable: [rke2-traefik]` so only this managed Traefik serves the endpoint.
- **Model PVC convention:** `models/CLAUDE.md` says `storageClassName: nfs-client`; with
  `nfs-models` now the default/only SC, update that convention (and existing model PVCs) to
  `nfs-models`.
- **Retire redundant files:** `deploy-aleph/storage/nfs-models-storageclass.yaml` is now baked
  into `30-nfs.yaml`; the `configs/` Tyk values are captured in `50/51-tyk*.yaml`; the
  `02-post-install.sh` patches are folded into `61/62`. Keep as reference or remove in a
  cleanup pass.
- **nfs-subdir→nfs-csi:** `nfs-subdir-external-provisioner` is upstream-archived; migrate to
  `nfs-csi` (sig-storage) in a future iteration.
- **Capture the Warewulf overlay** from `172.26.92.10` for full node reproducibility.

## Verification

```bash
# 1. Local YAML validity (login node, cheap):
for f in deploy-aleph/rke2-manifests/*.yaml; do
  python3 -c "import yaml; list(yaml.safe_load_all(open('$f'))); print('ok $f')"
done

# 2. On the target cluster after copying to the manifests path:
kubectl get helmchart -A -w                       # → all Resolved
kubectl get sc nfs-models                         # → default, OneFS mountOptions
kubectl get clusterissuer letsencrypt-prod        # → Ready (after cert-manager up + :80)
kubectl get pods -n cert-manager,traefik,tyk,kuberay,nfs-provisioner
kubectl get jobs -n kube-system                   # → istio/knative/kserve/profiles-bootstrap Complete
kubectl logs -n kube-system job/kserve-bootstrap  # → "KServe bootstrap complete"
kubectl get pods -n istio-system,knative-serving,kubeflow
```
