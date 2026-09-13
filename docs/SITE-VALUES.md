# Aleph site values and tokens

The control-plane overlay is **tokenized**: every site-specific value is a `__TOKEN__`
placeholder. Fill a copy of `ww-overlays/site.env.example` (dummy values) with your real
values as `site.env` (never committed), then substitute before baking — the example file
contains the ready-to-use sed loop. The `common` and `gpu-worker` overlays carry no tokens.

| Token | Meaning | Notes |
|---|---|---|
| `__K8S_VERSION__` | cluster Kubernetes version (e.g. `v1.36.1`) | Must match exactly — HAMi ships a patched kube-scheduler pinned to it (`10-hami.yaml`) |
| `__NFS_SERVER__` | NFS server for model weights | `30-nfs.yaml`, `49-tyk-redis-data.yaml`, `80-model-pvcs.yaml` |
| `__NFS_PATH__` | NFS export root (provisioner + static PV paths hang off it) | same files |
| `__VIP__` | public floating VIP (MetalLB L2) | `41-metallb-vip.yaml`; floats between control-plane nodes — never bound to a node or `lo` |
| `__PUBLIC_NIC__` | control-plane public NIC name | `41-metallb-vip.yaml` (L2 advertisement) + netplan |
| `__PUBLIC_NIC_IP__` | **per-node** own public IP | netplan `60-public-vip.yaml` — substitute once per control-plane node |
| `__PUBLIC_PREFIX__` / `__PUBLIC_GW__` | public subnet prefix + gateway | netplan; public gateway must be the PREFERRED default route (metric 50), cluster default at metric 100 |
| `__INFERENCE_HOST__` | public hostname (edge routing + cert CN) | `56-edge-routes.yaml`; DNS must point at the VIP |
| `__ACME_EMAIL__` | Let's Encrypt registration contact | `01-cluster-issuer.yaml` |
| `__TYK_API_SECRET__` | Tyk admin `APISecret` | `51-tyk.yaml`; load from the gitignored `.env`, never commit |
| `__ROCE_IFNAME__` | GPU-worker RoCE NIC | `70-rdma-device-plugin.yaml`; see [NCCL-ROCE.md](NCCL-ROCE.md) |

Networking model: each control-plane node carries three addresses — cluster IP, its own
public IP on the public NIC (in the VIP's prefix), and the floating VIP that MetalLB
advertises from the elected leader. Review per-node networking independently; never
substitute one node's public address across the cluster.

## Static storage bindings

`49-tyk-redis-data.yaml` and `80-model-pvcs.yaml` keep explicit PV/PVC bindings (UUID-bearing
NFS directories, `volumeName` refs) with only the server/path prefix tokenized. Changing
these is not a harmless template substitution — see [STORAGE-RECOVERY.md](STORAGE-RECOVERY.md).

## Credentials

SSH private keys, authorized keys and trust material are never exported into Git; the
repository ships dummy/example files only, which are not replacements for live credentials.
Do not copy the entire role tree blindly over an existing Warewulf overlay. The two secret
tokens (`__TYK_API_SECRET__`, `__ACME_EMAIL__`) must be restored through your private
deployment process — never apply their redacted/dummy values.
