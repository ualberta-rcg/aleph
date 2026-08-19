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
| `__NFS_SERVER__` | `etc/rancher/manifests/30-nfs.yaml` | `manage.storage.data.vulcan.local` | The NFS server hostname or IP for model-weight storage. |
| `__NFS_PATH__` | `etc/rancher/manifests/30-nfs.yaml` | `/aleph` | NFS export path. The provisioner creates subdirs here per PVC. |
| `__VIP__` | `etc/rancher/manifests/41-metallb-vip.yaml` | `129.128.190.71` | The public IP MetalLB owns and advertises (L2) from the elected head. It **floats** — NOT bound to any node, NOT on `lo`. A separate address from each head's own `__PUBLIC_NIC_IP__`; lives in the same `/28`. |
| `__PUBLIC_NIC__` | `etc/rancher/manifests/41-metallb-vip.yaml`, `etc/netplan/60-public-vip.yaml` | `enp6s20` (live Vulcan) | The control-plane NIC on the public VLAN (same name on every head). Run `ip link` on the node to confirm. Repo token stays `__PUBLIC_NIC__`; live on-node copy is filled. |
| `__PUBLIC_NIC_IP__` | `etc/netplan/60-public-vip.yaml` | *(PER-NODE, e.g. a.b.c.55 / .57 / .58)* | **Per control-plane node**: that head's OWN real IP on the public NIC (in the `__VIP__` /28, distinct from the VIP and from every other head). Fill with this node's value at bake — see `HEADn_PUBLIC_IP` in `site.env`. |
| `__PUBLIC_PREFIX__` | `etc/netplan/60-public-vip.yaml` | *(e.g. 28)* | Prefix length of the public subnet (the `/NN` for `__PUBLIC_NIC_IP__`). |
| `__PUBLIC_GW__` | `etc/netplan/60-public-vip.yaml` | *(your public gw, e.g. a.b.c.49)* | Public gateway IP. **Required**: it is the head's PREFERRED default route (metric 50) so off-subnet/Internet replies leave the public NIC symmetrically. The cluster NIC's default must be a higher metric (100). |
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
| `control-plane/etc/netplan/60-public-vip.yaml` | control-plane only | Numbers the public NIC with this head's own public IP + makes the public gateway the PREFERRED default route (metric 50). MetalLB floats the VIP on top. No `lo` bind, no rp_filter/ARP sysctl — symmetric routing alone is enough. |
| `gpu-worker/etc/systemd/system/nvidia-persistenced.service` | GPU workers | Enable NVIDIA persistence mode at boot (optional polish) |
| `gpu-worker/etc/modules-load.d/rdma.conf` | GPU workers | Load RDMA/RoCE kernel modules at boot so `rdma/roce` is advertised (see NCCL-ROCE.md) |
| `control-plane/etc/rancher/manifests/70-rdma-device-plugin.yaml` | control-plane (advertises on `gpu=on`) | RDMA shared device plugin → `rdma/roce` resource for NCCL over RoCE |

> `etc/rancher/manifests/` is read only by `rke2-server` (control-plane) nodes; `rke2-agent`
> (GPU workers) ignores it. The manifests are cluster-wide objects applied once by a server
> node — "applies to" in the README describes which *workloads* land where, not which node
> needs the file. HAMi's device-plugin DaemonSet, for example, is declared in the
> control-plane overlay but only schedules pods on `gpu=on` GPU workers.

---

## Public VIP networking model (read before baking)

- **Each control-plane node** ends up with three addresses: its **172 cluster IP** (eth0), its
  **own public IP** (`__PUBLIC_NIC_IP__`, in the VIP's `/28`), and the **floating VIP** (`__VIP__`).
- The **VIP is not pinned to any node** — MetalLB L2-advertises it from the elected head and moves
  it on failover. No nodeSelector in `41-metallb-vip.yaml`, no VIP-on-`lo`.
- The **public gateway is the PREFERRED default route** (metric 50) on each head, so replies to
  off-subnet/Internet clients leave the public NIC symmetrically. Proven: reverse the metrics
  (cluster preferred) and external clients (e.g. via a squid proxy) time out.

### One required change OUTSIDE this overlay — the cluster (warewulf-generated) netplan
netplan **appends** routes across files; it cannot demote another file's default. So the
warewulf-generated cluster netplan MUST ship its default at **`metric: 100`** so the public
overlay's `metric: 50` wins. (GPU workers have no public NIC and only one default — they need no
metric and do **not** get `60-public-vip.yaml`.) Example cluster netplan for a control-plane node:

```yaml
network:
  version: 2
  renderer: networkd
  ethernets:
    eth0:                       # cluster NIC
      addresses: [ 172.x.y.z/23 ]
      mtu: 9000
      routes:
        - to: default
          via: 172.x.y.1
          metric: 100           # BACKUP — must be higher than the public overlay's 50
```

### Temporary single-edge state
Until every head has a spare public IP, only one head is numbered. Live, that is done by hand
(number one head's `__PUBLIC_NIC__`, set its `metric 50` default, and pin MetalLB with a
nodeSelector to that head). That pin is **not** committed — the overlay above is the end state
where every head is numbered and the VIP floats freely.

---

## Regression watch

**`40-metallb.yaml` nodeSelector:** the value MUST be the string `"true"` (not `""`).
RKE2 sets `node-role.kubernetes.io/control-plane="true"`; vanilla Kubernetes uses `""`.
A stale overlay copy of this file once shipped `""`, so the MetalLB speaker and controller
never scheduled and no VIP came up. Always verify this after any overlay update.

**Public default-route metric:** if external clients can reach the VIP but same-subnet works,
check `ip route show default` on the leader — the public gateway must be the **lower** metric
(50). A stray `metric 0` cluster default (un-demoted warewulf netplan) silently wins and breaks
off-subnet replies.
