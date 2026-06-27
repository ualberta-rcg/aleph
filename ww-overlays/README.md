# ww-overlays — Aleph Warewulf + RKE2 overlays

This directory is the canonical source for the files Warewulf bakes onto Aleph cluster nodes.
It is split into per-node-type overlays, each a filesystem-rooted tree (the overlay root maps
to `/` on the node), so a directory can be dropped straight into a Warewulf overlay.

The Warewulf image already provides the OS, NVIDIA drivers, HAMi runtime, RKE2, and node
labels. These overlays add the per-role customizations on top of that image.

---

## The three overlays

```
ww-overlays/
  README.md            ← you are here
  SITE-VALUES.md       ← every placeholder: token, files, example value, how to fill
  site.env.example     ← the same values as shell vars for scripted substitution
  overlays/
    common/            ← baked on ALL nodes
      etc/sysctl.d/90-inotify.conf
      etc/rke2-deregister/id_ed25519             ← private SSH key (DUMMY committed; real swapped at bake)
      etc/default/rke2-deregister                ← HEAD_NODES list, key path, server toggle
      etc/systemd/system/rke2-deregister.service ← on-shutdown hook (SSHes head, deletes own Node)
      usr/local/bin/rke2-deregister.sh           ← the deregister script (time-boxed, server-guarded)
    control-plane/     ← baked on CONTROL-PLANE nodes
      etc/rancher/manifests/        ← RKE2 auto-deploy set (00..70)
      etc/ssh/deregister.authorized_keys         ← forced-command pubkey (DUMMY committed)
      etc/ssh/sshd_config.d/10-deregister.conf   ← adds the extra AuthorizedKeysFile path
      usr/local/sbin/deregister-node.sh          ← forced-command target (validates + kubectl delete)
      etc/netplan/60-public-vip.yaml             ← numbers the public NIC + preferred default route (VIP floats)
      usr/local/bin/tyk-admin.sh    ← Tyk key admin CLI (on PATH; see docs/TYK-USERS.md)
    gpu-worker/        ← baked on GPU WORKER nodes
      etc/systemd/system/nvidia-persistenced.service
      etc/systemd/system/multi-user.target.wants/nvidia-persistenced.service
      etc/modules-load.d/rdma.conf   ← RoCE kernel modules (see NCCL-ROCE.md)
  post-deploy/         ← applied after first boot (see post-deploy/README.md)
  NCCL-ROCE.md         ← making NCCL run over RoCE (provider injection recipe)
```

### Node assignment

| Overlay | Baked on | Contains |
|---|---|---|
| `common` | all nodes | inotify limit bump (dense-pod headroom) + on-shutdown node-deregister client (SSH key + unit + script + config) |
| `control-plane` | control-plane nodes | RKE2 auto-deploy manifests + public-VIP netplan + `tyk-admin.sh` + node-deregister SSH target (forced-command key + wrapper) |
| `gpu-worker` | GPU workers | NVIDIA persistence-mode unit + RoCE kernel modules |

**About the manifests:** RKE2 reads `/etc/rancher/manifests/` only on server (control-plane)
nodes and applies each file cluster-wide. They only need to land on the **first / bootstrap**
server, but RKE2's helm-controller is idempotent, so it is safe if the `control-plane` overlay
is assigned to all control-plane nodes. Assign it to just the bootstrap node if you prefer.

---

## How it comes up

```
Warewulf bakes the overlays onto nodes at boot
  control-plane: etc/rancher/manifests/*  → RKE2 applies them
  control-plane: etc/netplan → public NIC numbered + preferred default (VIP floats via MetalLB)
  common:        etc/sysctl.d → tuning on every node
  gpu-worker:    etc/systemd → NVIDIA persistence mode

RKE2 applies the manifests automatically at cluster boot
  HelmCharts: cert-manager, HAMi, NFS, MetalLB(+VIP), Tyk(+Redis, LB, api-defs)
  Jobs:       Istio → Knative → KServe → model-gateway

post-deploy/ — a handful of steps after first boot (Tyk key, smoke test, model cards)
```

No deploy script, no SSH push. Provision the node → everything comes up.

---

## Auto-deploy manifest set (control-plane overlay)

| File | Applies to | Site values |
|---|---|---|
| `00-cert-manager.yaml` | all | – |
| `01-cluster-issuer.yaml` | all | `__ACME_EMAIL__` |
| `09-gpu-autolabel.yaml` | workers (autodetected) | – |
| `10-hami.yaml` | GPU nodes | `__K8S_VERSION__` |
| `11-node-labeler.yaml` | GPU nodes (`gpu=on`) | – |
| `30-nfs.yaml` | all | `__NFS_SERVER__`, `__NFS_PATH__` |
| `40-metallb.yaml` | control-plane | – |
| `41-metallb-vip.yaml` | control-plane | `__VIP__`, `__PUBLIC_NIC__` |
| `50-tyk-redis.yaml` | all | – |
| `51-tyk.yaml` | all | `__TYK_API_SECRET__` |
| `52-tyk-loadbalancer.yaml` | control-plane | – |
| `53-tyk-api-definitions.yaml` | all | – |
| `54-tyk-middleware.yaml` | all | – |
| `60-istio.yaml` | all (Job) | – |
| `61-knative.yaml` | all (Job) | – |
| `62-kserve.yaml` | all (Job) | – |
| `63-model-gateway.yaml` | all (runs on CP) | – |
| `70-rdma-device-plugin.yaml` | GPU nodes (`gpu=on`) | `__ROCE_IFNAME__` |

`09-gpu-autolabel` detects an NVIDIA GPU on each worker (runtime nsenter) and stamps
`gpu=on` — the gate that `10-hami`, `11-node-labeler`, and `70-rdma-device-plugin` all
select on; `11-node-labeler` then stamps `aleph.gpu/product` etc onto GPU nodes (usage
accounting); `54-tyk-middleware` carries the JSVM catch-all-auth + identity-injection hooks.

"Applies to" is which workloads land where; all manifests are cluster-wide objects applied
once by a server node.

---

## Before baking: fill in site values

1. Read `SITE-VALUES.md` — one table of every `__TOKEN__`, which files use it, and the value
   to put there. Each overlay file also has a header listing its own tokens.
2. Copy `site.env.example` → `site.env`, fill in real values.
3. Substitute tokens (sed loop in `site.env.example`) or edit the files directly.
4. **Never commit real secrets** — `__TYK_API_SECRET__` is loaded from `.env` (gitignored).
5. Bake each overlay into the Warewulf image for its node role (table above).

---

## Manifest boot order and self-ordering

File-number prefixes are for humans; RKE2's helm-controller reconciles HelmCharts
independently. The serving-stack Jobs (60–63) self-order via internal wait loops:

```
00 cert-manager ──► 60-istio ──► 61-knative ──► 62-kserve ──► 63-model-gateway
09 gpu-autolabel──► gpu=on on GPU workers ──► unblocks 10-hami / 11-node-labeler / 70-rdma
10 hami         ──► device-plugin on gpu=on nodes (independent)
30 nfs          ──► StorageClass (independent)
40 metallb      ──► 41-metallb-vip (CRD-race: retries until MetalLB CRDs land — benign)
50 tyk-redis    ──► 51-tyk → mounts 53-tyk-api-definitions
                         └──► 52-tyk-loadbalancer (waits for VIP from 41)
```

Re-running a bootstrap Job: `kubectl delete job <name>-bootstrap -n kube-system`

---

## Gateway updates (CI → cluster)

The model-gateway image is published to Docker Hub on every push to `main` touching
`gateway/**`. The Deployment in `63-model-gateway.yaml` uses `imagePullPolicy: Always`, so:

```bash
kubectl rollout restart deploy/model-gateway -n models
```

No file-copy, no SSH push, no deploy script.

---

## Public endpoint

```
Clients → __VIP__:80 → Tyk (auth, rate-limit) → model-gateway → KServe pods
```

- OpenAI SDK:    `base_url="http://__VIP__/v1"`, `api_key=<TYK_KEY>`
- Anthropic SDK: `base_url="http://__VIP__"`, `api_key=<TYK_KEY>`

---

## MetalLB L2 recipe

| Layer | What | Where |
|---|---|---|
| `40-metallb.yaml` | Installs MetalLB (chart, frr sidecar, pinned to CP nodes) | control-plane manifest |
| `41-metallb-vip.yaml` | VIP pool + L2Advertisement on `__PUBLIC_NIC__` (VIP floats, no nodeSelector) | control-plane manifest |
| `52-tyk-loadbalancer.yaml` | LoadBalancer svc → gets `__VIP__` from the pool | control-plane manifest |
| `etc/netplan/60-public-vip.yaml` | Numbers the public NIC with this head's OWN IP + public gateway as the PREFERRED default route | control-plane node overlay |

**Networking model (see SITE-VALUES.md for the full write-up):** each control-plane node carries
its 172 cluster IP (eth0), its own public IP (`__PUBLIC_NIC_IP__`, in the VIP's `/28`), and the
floating VIP (`__VIP__`). MetalLB advertises the VIP at L2 from the elected head — it is **not**
bound to any node and is **not** on `lo`. The one trick is the route metric: the public gateway is
the head's **preferred** default (metric 50) so off-subnet/Internet replies leave the public NIC
symmetrically; the cluster default must be a higher metric (100). This replaced the old IP-free +
`lo`-bind + `rp_filter=0` recipe (those files were deleted — symmetric routing alone suffices).

---

## Stateless-node deregistration on shutdown (SSH to head)

These nodes are stateless: a reboot brings the box up "fresh" and RKE2 auto-rejoins, but the
**old `Node` object lingers in the API and dirties/blocks the rejoin**. On shutdown each node SSHes
to a control-plane (head) node — which already has the admin kubeconfig — and asks it to delete the
node's own `Node` object, so it re-registers clean on the next boot.

Why SSH and not "just kubectl on the worker": agent nodes have **no** credential that can delete
nodes — `kubelet`, `kubeproxy`, and `rke2controller` kubeconfigs are all forbidden by the Node
authorizer + NodeRestriction (verified: `kubectl auth can-i delete nodes` → `no`). The head node
does have the rights, so we let it do the delete.

| Piece | Overlay / where | Does |
|---|---|---|
| `usr/local/bin/rke2-deregister.sh` | common (all nodes) | On shutdown, SSHes each `HEAD_NODES` in turn with the deregister key, passing its own hostname. Time-boxed (`timeout` + `ConnectTimeout`) so a dead head can't hang shutdown. **Skips control-plane/etcd nodes by default.** |
| `etc/default/rke2-deregister` | common | `HEAD_NODES`, `SSH_KEY`, `SSH_USER`, `DEREGISTER_SERVERS` |
| `etc/rke2-deregister/id_ed25519` | common | Private SSH key. **DUMMY committed**; real key swapped in at bake (real one lives in the local secrets dir, not the repo). |
| `etc/systemd/system/rke2-deregister.service` | common | oneshot, `RemainAfterExit=yes`; work in `ExecStop`, ordered `After=` network so networking is still up when it fires |
| `etc/ssh/deregister.authorized_keys` | control-plane | The key's matching entry, `command="…",restrict` — the key can ONLY run the delete wrapper (this is the "permission to delete", so no sudoers needed). **DUMMY pubkey committed.** |
| `etc/ssh/sshd_config.d/10-deregister.conf` | control-plane | Adds that file as an extra `AuthorizedKeysFile` so the admin/WW keys in `~/.ssh/authorized_keys` are never clobbered |
| `usr/local/sbin/deregister-node.sh` | control-plane | Forced-command target: validates `$SSH_ORIGINAL_COMMAND` as a single DNS-1123 node name (blocks injection), then `kubectl delete node <name> --ignore-not-found` as root |

**Servers are guarded off by default.** Deleting a control-plane/etcd node's `Node` object on every
reboot is a quorum footgun, so the script no-ops on server nodes unless `DEREGISTER_SERVERS=true` is
set in `/etc/default/rke2-deregister`. Workers (the ones that actually churn) deregister automatically.

**Keys: dummy in the repo, real at bake.** Per project convention the committed key pair is a clearly
labelled DUMMY; the real pair lives outside the repo (e.g. `~/hami-cluster-test/deregister-keys/`).
At bake time, drop the real private key into `common/etc/rke2-deregister/id_ed25519` and the real
public key into the `command="…" <pubkey>` line of `control-plane/etc/ssh/deregister.authorized_keys`.

> **Backstop for hard resets:** this hook only fires on *clean* shutdown. Power loss / hard reset
> leaves a ghost `NotReady` node — delete it by hand, or run a small cron/timer on a head node that
> deletes non-control-plane nodes that have been `NotReady` for >15 min.

## See also

- `SITE-VALUES.md` — all tokens, file locations, example values, regression warnings
- `NCCL-ROCE.md` — making NCCL collectives run over RoCE (root cause + per-pod recipe)
- `post-deploy/README.md` — steps after first boot (Tyk key, smoke test, adding models)
- `docs/RUNBOOK.md` — cluster ops, Tyk key management, troubleshooting
