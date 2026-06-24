# RKE2 auto-deploy manifests

Modular, version-controlled RKE2 auto-deploy manifests. Drop these on a node's manifests
path and RKE2 applies them at boot, so the **next Warewulf deployment brings most of the
platform up automatically**.

**This iteration's goal:** every component **installed and available**, in a default/ready
state, **one file per component** (HAMi, NFS, cert-manager, Traefik, Tyk, MetalLB, and the
serving stack split into Istio / Knative / KServe). Site-specific wiring (MetalLB
VIP/public NIC, `gpu=on` labels, Tyk secret, cert hostnames) is a **post-deploy customization
step** (see below). The set will be refined iteratively.

**Architecture:** cluster 232's front-door/TLS pattern, but **lean** — no full Kubeflow
(no Dex / Central Dashboard / Pipelines / oauth2-proxy), no Rancher, no certbot. Just the
serving stack: cert-manager + Istio/Knative/KServe + Tyk, with HAMi + NFS.
**Ingress uses RKE2's bundled `rke2-traefik`** — there is intentionally no managed Traefik
manifest (see "Double-Traefik" resolution below).

## How RKE2 applies these

On a Warewulf-provisioned node, the overlay-baked `rke2-manifests.service` copies
`/etc/rancher/manifests/*.yaml` into `/var/lib/rancher/rke2/server/manifests/`, which RKE2
watches and applies at startup. So: copy this directory to `/etc/rancher/manifests/` on the
control-plane node (or place files directly in `…/server/manifests/` on a non-WW node).
RKE2's helm-controller reconciles each `HelmChart`; the job-controller runs each bootstrap
Job. File-number prefixes are for humans (controllers reconcile independently of filename
order).

## ⚠ Before redeploy: strip stale files from the Warewulf overlay

The WW overlay on `172.26.92.10` bakes `/etc/rancher/manifests/`, and `rke2-manifests.service`
copies **everything** in it to `server/manifests/`. The old cluster's `rancher.yaml` and
`nfs.yaml` are still in that overlay, so on the 2026-06-22 redeploy they landed next to this
aleph set and caused three failures:

- **`rancher.yaml`** re-installs **Rancher** (dropped by design) AND duplicates the
  `cert-manager` HelmChart. Rancher is also `kubeVersion < 1.36.0` — incompatible with this
  cluster, so `helm-install-rancher` CrashLoops forever.
- **`nfs.yaml`** re-creates the old `nfs-client` StorageClass on `/kubeflow`. It collides with
  `30-nfs.yaml` (both define `HelmChart/nfs-provisioner`); the stray `nfs-client` wins and the
  intended `nfs-models` (`/aleph`, with the OneFS-safe mountOptions) never takes effect.

**Fix on the WW server:** remove `rancher.yaml` and `nfs.yaml` from the overlay's
`/etc/rancher/manifests/` so only this `00-63` set ships. (Both `/kubeflow` and `/aleph` exist
on the OneFS backend, so `nfs-models`/`/aleph` is valid once the stray is gone.)

## Cold-boot robustness (already baked in)

The serving-stack Jobs (60–63) clone `github.com/kubeflow/manifests` at run time. At a cold
boot the cluster DNS forwarder lags the Job start, so a bare `git clone` dies on
`Could not resolve host: github.com`, exhausts `backoffLimit`, and the Job stays Failed (this
is exactly what left KServe uninstalled on the first redeploy). The Jobs now **retry the clone
until egress is ready** (≈10 min) and **loop until each prerequisite namespace exists + pods
are Ready**, so the Istio→Knative→KServe→Profiles chain self-orders for real. `github.com` is
reachable from the node once networking settles, so the retries converge fast on a warm cluster.

## File list

| File | Installs | Source |
|---|---|---|
| `00-cert-manager.yaml` | cert-manager (CRDs on) | split from 230 `rancher.yaml`; **Rancher dropped** |
| `01-cluster-issuer.yaml` | Let's Encrypt `ClusterIssuer` (ACME HTTP-01 via traefik) | new |
| `10-hami.yaml` | HAMi vGPU scheduler + device plugin | 230 `hami.yaml` verbatim |
| `30-nfs.yaml` | nfs-subdir provisioner → **`nfs-models`** SC (default, OneFS-safe) | 230 `nfs.yaml` + `storage/nfs-models-storageclass.yaml` merged |
| `40-metallb.yaml` | MetalLB L2 install (speaker+frr **pinned to control-plane**; VIP/NIC are per-site → `../overlays/`) | new; **optional** |
| `50-tyk-redis.yaml` | Bitnami Redis (ns `tyk`) | `04-install-tyk-gateway.sh` |
| `51-tyk.yaml` | Tyk OSS gateway (ns `tyk`) | `configs/tyk-oss-values.yaml` |
| `60-istio.yaml` | Job: Istio + Kubeflow mesh scaffolding | kubeflow/manifests v1.11 slice |
| `61-knative.yaml` | Job: Knative Serving + `config-features` patch | kubeflow/manifests slice + post-install #1 |
| `62-kserve.yaml` | Job: KServe + `models` ns + config + Istio allow-all | kubeflow/manifests slice + post-install #2–4 |

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
| `../overlays/*` (metallb) | VIP, public NIC, subnet, gateway (per-site — NOT in the manifest) | `.55` / `enp6s19` / `129.128.190.48/28` / `129.128.190.49` |

## Post-deploy customization checklist

1. **Label GPU nodes:** `kubectl label node <gpu-node> gpu=on` (HAMi device-plugin needs it).
   On this cluster both workers are GPU nodes — `rack15-03` and `rack05-16` (4× L40S each,
   8 GPUs total, driver 595.71.05). Without the label, `hami-device-plugin` won't schedule and
   no GPUs are advertised (`allocatable.nvidia.com/gpu` stays `<none>`).
2. **Wait for charts:** `kubectl get helmchart -A -w` → all `Resolved`.
3. **NFS:** `kubectl get sc nfs-models` → default, mountOptions present.
4. **Serving stack (4 self-ordering Jobs):** `kubectl get jobs -n kube-system` → the
   `istio/knative/kserve/profiles-bootstrap` jobs all `Complete`; then
   `kubectl get pods -n istio-system,knative-serving,kubeflow` Running. They chain
   automatically; a failed one retries until its prerequisite is up.
5. **Public endpoint (MetalLB + node overlay, per-site → `../overlays/`):** bake the
   `netplan/` + `sysctl.d/` onto the head nodes, then apply `overlays/metallb-vip.example.yaml`
   filled with your VIP + NIC. A `type: LoadBalancer` Service then gets the VIP. `40-metallb.yaml`
   only *installs* MetalLB (speaker+frr pinned to control-plane); the VIP/NIC are per-site. The
   bundled `rke2-traefik` serves behind the VIP; also expose **port 80** for cert-manager HTTP-01.
6. **cert-manager:** set a real `acme.email`; once port 80 is reachable, add a `Certificate` CR
   per endpoint hostname → `kubectl get certificate` → `Ready`.
7. **Tyk:** inject the real admin secret from `.env` (`TYK_API_SECRET`) into
   `secrets-tyk-oss-tyk-gateway`, then load API definitions via `gateway/remote-deploy.sh`.
8. **Deploy the gateway + models** (`deploy.sh`, `kubectl apply -f models/<name>/`).

## What is NOT here (by design)

- **MetalLB VIP + public interface** — per-site; the node overlay (netplan + sysctl) and the
  VIP config (`IPAddressPool`/`L2Advertisement`) live in `../overlays/` (step 5). The
  `40-metallb.yaml` manifest only *installs* MetalLB — it carries no VIP or NIC.
- **Rancher** — dropped; cert-manager kept.
- **certbot** — cert-manager ACME replaces it (HTTP-01, port 80).
- **Full Kubeflow** (Dex/dashboard/pipelines/**Profiles**) — the serving Jobs install only
  Istio/Knative/KServe. Kubeflow Profiles was removed (`63-profiles.yaml` deleted) — no full
  Kubeflow by design.
- **Warewulf overlay** (OS image, NVIDIA driver/toolkit, containerd nvidia runtime, RKE2
  install, `gpu=on` label) — lives on the WW server `172.26.92.10`, separate effort. These
  manifests assume nodes are already provisioned.

## Follow-ups (the manifests "will get better")

- **Double-Traefik (resolved):** RKE2 bundles `rke2-traefik`, and a managed `40-traefik.yaml`
  collided with it (`IngressClass "traefik" ... current value is "rke2-traefik"` → stuck
  `helm-install-traefik`). Resolution: **dropped the managed manifest**; the bundled
  `rke2-traefik` is the only ingress controller and serves the endpoint. If a managed Traefik
  is ever wanted instead, disable the bundled one via RKE2 server config `disable: [rke2-traefik]`
  in the WW overlay and re-add a Traefik HelmChart.
- **Model PVC convention (resolved):** all model PVCs and `models/CLAUDE.md` now use
  `storageClassName: nfs-models`, which is the default/only SC (set up by `30-nfs.yaml` with the
  OneFS-safe mountOptions). There is intentionally no separate `nfs-client` SC.
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
kubectl get pods -n cert-manager,traefik,tyk,nfs-provisioner
kubectl get jobs -n kube-system                   # → istio/knative/kserve/profiles-bootstrap Complete
kubectl logs -n kube-system job/kserve-bootstrap  # → "KServe bootstrap complete"
kubectl get pods -n istio-system,knative-serving,kubeflow
```
