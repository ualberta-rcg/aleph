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
    control-plane/     ← baked on CONTROL-PLANE nodes
      etc/rancher/manifests/        ← RKE2 auto-deploy set (00..63)
      etc/netplan/60-public-vip.yaml
      etc/sysctl.d/99-public-vip.conf
    gpu-worker/        ← baked on GPU WORKER nodes
      etc/systemd/system/nvidia-persistenced.service
      etc/systemd/system/multi-user.target.wants/nvidia-persistenced.service
  post-deploy/         ← applied after first boot (see post-deploy/README.md)
```

### Node assignment

| Overlay | Baked on | Contains |
|---|---|---|
| `common` | all nodes | inotify limit bump (dense-pod headroom) |
| `control-plane` | control-plane nodes | RKE2 auto-deploy manifests + public-VIP netplan/sysctl |
| `gpu-worker` | GPU workers | NVIDIA persistence-mode unit |

**About the manifests:** RKE2 reads `/etc/rancher/manifests/` only on server (control-plane)
nodes and applies each file cluster-wide. They only need to land on the **first / bootstrap**
server, but RKE2's helm-controller is idempotent, so it is safe if the `control-plane` overlay
is assigned to all control-plane nodes. Assign it to just the bootstrap node if you prefer.

---

## How it comes up

```
Warewulf bakes the overlays onto nodes at boot
  control-plane: etc/rancher/manifests/*  → RKE2 applies them
  control-plane: etc/netplan + etc/sysctl.d → public VIP plumbing
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
| `10-hami.yaml` | GPU nodes | `__K8S_VERSION__` |
| `30-nfs.yaml` | all | `__NFS_SERVER__`, `__NFS_PATH__` |
| `40-metallb.yaml` | control-plane | – |
| `41-metallb-vip.yaml` | control-plane | `__VIP__`, `__PUBLIC_NIC__` |
| `50-tyk-redis.yaml` | all | – |
| `51-tyk.yaml` | all | `__TYK_API_SECRET__` |
| `52-tyk-loadbalancer.yaml` | control-plane | – |
| `53-tyk-api-definitions.yaml` | all | – |
| `60-istio.yaml` | all (Job) | – |
| `61-knative.yaml` | all (Job) | – |
| `62-kserve.yaml` | all (Job) | – |
| `63-model-gateway.yaml` | all (runs on CP) | – |

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

## MetalLB L2 recipe (three layers)

| Layer | What | Where |
|---|---|---|
| `40-metallb.yaml` | Installs MetalLB (chart, frr sidecar, pinned to CP nodes) | control-plane manifest |
| `41-metallb-vip.yaml` | VIP pool + L2Advertisement on `__PUBLIC_NIC__` | control-plane manifest |
| `52-tyk-loadbalancer.yaml` | LoadBalancer svc → gets `__VIP__` from the pool | control-plane manifest |
| `etc/netplan/60-public-vip.yaml` | NIC up IP-free, VIP on dummy0, subnet on-link | control-plane node overlay |
| `etc/sysctl.d/99-public-vip.conf` | `rp_filter=0`, ARP suppress | control-plane node overlay |

The netplan + sysctl are the only non-manifest pieces — they configure the host network that
MetalLB L2 relies on, so they live in the `control-plane` overlay.

---

## See also

- `SITE-VALUES.md` — all tokens, file locations, example values, regression warnings
- `post-deploy/README.md` — steps after first boot (Tyk key, smoke test, adding models)
- `docs/RUNBOOK.md` — cluster ops, Tyk key management, troubleshooting
