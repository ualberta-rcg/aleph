# Aleph — Site Values

Fill in these tokens before baking the Warewulf overlay. Every placeholder appears as
`__TOKEN__` in the files listed below. Replace each one with the real value for your site,
then bake the `ww-overlays/overlay/` tree into your Warewulf image.

A shell-var version for scripting: `ww-overlays/site.env.example`.

---

## Tokens and where they appear

| Token | Files | Aleph example | Notes |
|---|---|---|---|
| `__K8S_VERSION__` | `10-hami.yaml` | `v1.36.1` | Must match cluster Kubernetes version exactly. HAMi ships a patched kube-scheduler pinned to this version. |
| `__NFS_SERVER__` | `30-nfs.yaml` | `manage.storage.data.vulcan.local` | The NFS server hostname or IP for model weight storage. |
| `__NFS_PATH__` | `30-nfs.yaml` | `/aleph` | NFS export path. The provisioner creates subdirs here per PVC. |
| `__VIP__` | `41-metallb-vip.yaml`, `etc/netplan/60-public-vip.yaml` | `129.128.190.55` | The public IP MetalLB will own. Must be routable to the head nodes' public NIC. |
| `__PUBLIC_NIC__` | `41-metallb-vip.yaml`, `etc/netplan/60-public-vip.yaml` | `enp6s19` | The head node NIC on the public VLAN. Run `ip link` on the head node to confirm. |
| `__PUBLIC_SUBNET__` | `etc/netplan/60-public-vip.yaml` | `129.128.190.48/28` | The public subnet, on-link via `__PUBLIC_NIC__` for destination routing. |
| `__PUBLIC_GW__` | `etc/netplan/60-public-vip.yaml` | `129.128.190.49` | Public gateway IP (only needed for Internet clients, see commented block in netplan). |
| `__ACME_EMAIL__` | `01-cluster-issuer.yaml` | `admin@alliancecan.ca` | Email for Let's Encrypt ACME registration. Used for cert expiry notices. |
| `__TYK_API_SECRET__` | `51-tyk.yaml` | *(set from .env)* | Tyk gateway admin secret. Also used by `gateway/tyk/tyk-keys.sh`. **Never commit the real value.** See `.env` / `.env.example`. |

---

## Applicability by node role

| File | HEAD/edge nodes | GPU workers | Notes |
|---|---|---|---|
| `00-cert-manager.yaml` | ✓ | – | Cluster-wide; only meaningful on CP nodes |
| `01-cluster-issuer.yaml` | ✓ | – | Cluster-wide |
| `10-hami.yaml` | – | ✓ | Device-plugin DaemonSet only runs where `gpu=on` label exists (baked by WW GPU image) |
| `30-nfs.yaml` | ✓ | – | Cluster-wide StorageClass |
| `40-metallb.yaml` | ✓ | – | Speaker+controller pinned to control-plane nodes |
| `41-metallb-vip.yaml` | ✓ | – | HEAD/edge only — VIP L2-advertised out `__PUBLIC_NIC__` |
| `50-tyk-redis.yaml` | ✓ | – | Cluster-wide |
| `51-tyk.yaml` | ✓ | – | Cluster-wide |
| `52-tyk-loadbalancer.yaml` | ✓ | – | Gets VIP from MetalLB pool |
| `53-tyk-api-definitions.yaml` | ✓ | – | Cluster-wide |
| `60-istio.yaml` | ✓ | – | Cluster-wide serving stack |
| `61-knative.yaml` | ✓ | – | Cluster-wide serving stack |
| `62-kserve.yaml` | ✓ | – | Cluster-wide serving stack |
| `63-model-gateway.yaml` | ✓ | – | Runs on CP nodes (nodeSelector) |
| `etc/netplan/60-public-vip.yaml` | ✓ HEAD only | – | Node-level NIC plumbing; **not** applied to GPU workers |
| `etc/sysctl.d/99-public-vip.conf` | ✓ HEAD only | – | Node-level ARP/rp_filter; **not** applied to GPU workers |

> The manifests directory (`etc/rancher/manifests/`) is only read by `rke2-server` (control-plane nodes).
> GPU workers run `rke2-agent` which does not process this directory. All manifests are cluster-wide
> objects applied once by the first server node; the applicability column above describes which
> *workloads* land on which node type, not which node needs the file.

---

## Regression watch

**`40-metallb.yaml` nodeSelector:** the value MUST be the string `"true"` (not `""`).
RKE2 sets `node-role.kubernetes.io/control-plane="true"`; vanilla Kubernetes uses `""`.
A stale WW-overlay copy of this file once shipped `""`, so the MetalLB speaker and controller
never scheduled and no VIP came up. Always verify this after any overlay update.
