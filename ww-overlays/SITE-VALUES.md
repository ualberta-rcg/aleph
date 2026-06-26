# Aleph — Site Values

Fill in these tokens before baking the overlays. Every placeholder appears as `__TOKEN__`
in the files listed below. Replace each with the real value for your site, then bake each
overlay (`ww-overlays/overlays/<role>/`) into the Warewulf image for that node role.

A shell-var version for scripting: `ww-overlays/site.env.example`.

All paths below are relative to `ww-overlays/overlays/control-plane/` unless noted (that is
the only overlay carrying tokens; `common` and `gpu-worker` have none).

---

## Tokens and where they appear

| Token | Files (under overlays/control-plane/) | Example value | Notes |
|---|---|---|---|
| `__K8S_VERSION__` | `etc/rancher/manifests/10-hami.yaml` | `v1.36.1` | Must match cluster Kubernetes version exactly. HAMi ships a patched kube-scheduler pinned to this version. |
| `__NFS_SERVER__` | `etc/rancher/manifests/30-nfs.yaml` | *(your NFS host)* | The NFS server hostname or IP for model-weight storage. |
| `__NFS_PATH__` | `etc/rancher/manifests/30-nfs.yaml` | *(your export path)* | NFS export path. The provisioner creates subdirs here per PVC. |
| `__VIP__` | `etc/rancher/manifests/41-metallb-vip.yaml`, `etc/netplan/60-public-vip.yaml`, `etc/systemd/system/metallb-vip-lo.service` | *(your public IP)* | The public IP MetalLB will own. Must be routable to the control-plane public NIC. The `metallb-vip-lo.service` binds it to `lo` so node replies source from it. |
| `__PUBLIC_NIC__` | `etc/rancher/manifests/41-metallb-vip.yaml`, `etc/netplan/60-public-vip.yaml` | *(your public NIC)* | The control-plane NIC on the public VLAN. Run `ip link` on the node to confirm. |
| `__PUBLIC_SUBNET__` | `etc/netplan/60-public-vip.yaml` | *(e.g. a.b.c.0/28)* | The public subnet, on-link via `__PUBLIC_NIC__` for destination routing. |
| `__PUBLIC_GW__` | `etc/netplan/60-public-vip.yaml` | *(your public gw)* | Public gateway IP (only needed for Internet clients, see commented block in netplan). |
| `__ACME_EMAIL__` | `etc/rancher/manifests/01-cluster-issuer.yaml` | *(your ops email)* | Email for Let's Encrypt ACME registration. Used for cert expiry notices. |
| `__TYK_API_SECRET__` | `etc/rancher/manifests/51-tyk.yaml` | *(set from .env)* | Tyk gateway admin secret. Also used by `gateway/tyk/tyk-keys.sh`. **Never commit the real value.** See `.env` / `.env.example`. |
| `__ROCE_IFNAME__` | `etc/rancher/manifests/70-rdma-device-plugin.yaml` | `eth0` | The GPU worker's active RoCE NIC (the one that is `PORT_ACTIVE` under `/sys/class/infiniband`). The device plugin selects it to advertise `rdma/roce`. Confirm with `ibv_devinfo` / `ip link` on a GPU node. |

> Fill in the example column with your own values in `site.env` — keep concrete site values
> out of the committed manifests (they stay tokenized).

---

## Which overlay goes on which node

| Overlay | Baked on | Tokens to fill |
|---|---|---|
| `overlays/common/` | all nodes | none |
| `overlays/control-plane/` | control-plane nodes | all of the tokens above |
| `overlays/gpu-worker/` | GPU workers | none |

### What each overlay contains

| Overlay / file | Applies to | Purpose |
|---|---|---|
| `common/etc/sysctl.d/90-inotify.conf` | all nodes | Raise `fs.inotify.max_user_instances` for dense-pod nodes (optional polish) |
| `common/etc/systemd/system/rke2-deregister.service` + `usr/local/bin/rke2-deregister.sh` + `etc/default/rke2-deregister` | all nodes | On-shutdown hook: SSHes a head node to delete this node's own stale `Node` object so stateless reboots rejoin clean (servers guarded off by default) |
| `common/etc/rke2-deregister/id_ed25519` | all nodes | Private SSH key for the deregister hook. **Not a `__TOKEN__`** — DUMMY committed; swap in the real key (from the local secrets dir) at bake. |
| `control-plane/etc/ssh/deregister.authorized_keys` + `sshd_config.d/10-deregister.conf` + `usr/local/sbin/deregister-node.sh` | control-plane | Forced-command SSH target that performs the `kubectl delete node`. DUMMY pubkey committed; swap in the real public key at bake. |
| `control-plane/etc/rancher/manifests/*` | control-plane (RKE2 applies cluster-wide) | The full auto-deploy set (see README table) |
| `control-plane/etc/netplan/60-public-vip.yaml` | control-plane only | Public NIC plumbing for MetalLB L2 (IP-free NIC + on-link route) |
| `control-plane/etc/systemd/system/metallb-vip-lo.service` | control-plane only | Bind the VIP to `lo` at boot (`ip addr add __VIP__/32 dev lo`) — netplan can't address `lo` |
| `control-plane/etc/sysctl.d/99-public-vip.conf` | control-plane only | `rp_filter=0`, ARP suppress for the VIP |
| `gpu-worker/etc/systemd/system/nvidia-persistenced.service` | GPU workers | Enable NVIDIA persistence mode at boot (optional polish) |
| `gpu-worker/etc/modules-load.d/rdma.conf` | GPU workers | Load RDMA/RoCE kernel modules at boot so `rdma/roce` is advertised (see NCCL-ROCE.md) |
| `control-plane/etc/rancher/manifests/70-rdma-device-plugin.yaml` | control-plane (advertises on `gpu=on`) | RDMA shared device plugin → `rdma/roce` resource for NCCL over RoCE |

> `etc/rancher/manifests/` is read only by `rke2-server` (control-plane) nodes; `rke2-agent`
> (GPU workers) ignores it. The manifests are cluster-wide objects applied once by a server
> node — "applies to" in the README describes which *workloads* land where, not which node
> needs the file. HAMi's device-plugin DaemonSet, for example, is declared in the
> control-plane overlay but only schedules pods on `gpu=on` GPU workers.

---

## Regression watch

**`40-metallb.yaml` nodeSelector:** the value MUST be the string `"true"` (not `""`).
RKE2 sets `node-role.kubernetes.io/control-plane="true"`; vanilla Kubernetes uses `""`.
A stale overlay copy of this file once shipped `""`, so the MetalLB speaker and controller
never scheduled and no VIP came up. Always verify this after any overlay update.
