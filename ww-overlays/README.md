# ww-overlays — Aleph Warewulf + RKE2 overlay

This directory is the canonical source for the files the Warewulf image bakes onto Aleph
cluster nodes. It is organized to mirror the actual on-node filesystem so the contents
can be dropped directly into a Warewulf overlay tree.

The running reference is cluster **aleph** (aleph1 `172.26.92.43`, aleph2 `.44`, aleph3 `.45`
+ GPU workers `rack15-03`, `rack05-16`). What is here matches what runs there, improved and
tokenized for reuse on other clusters.

---

## How it works (three layers)

```
Layer 1: Warewulf bakes overlay/ onto nodes at boot
  └─ etc/rancher/manifests/*.yaml  →  RKE2 auto-deploy manifests
     (RKE2 server watches this dir and applies every file as a HelmChart or raw manifest)
  └─ etc/netplan/   + etc/sysctl.d/  →  head-node NIC / ARP / VIP plumbing

Layer 2: RKE2 applies manifests automatically at cluster boot
  └─ HelmCharts install: cert-manager, HAMi, NFS, MetalLB, Tyk+Redis
  └─ Jobs bootstrap:     Istio → Knative → KServe → model-gateway

Layer 3: post-deploy/ — a handful of steps after the first boot
  └─ Issue a Tyk API key
  └─ Smoke-test with verify-test-model.sh
  └─ Apply model cards + InferenceServices as you add models
  └─ (Optional) TLS certificate once DNS + port 80 are live
```

There is no deploy script, no SSH push step, no remote-deploy. Provision the node → everything
comes up.

---

## Directory layout

```
ww-overlays/
  README.md              ← you are here
  SITE-VALUES.md         ← every placeholder: token, files, Aleph example value
  site.env.example       ← same values as shell vars for scripted substitution
  overlay/               ← baked by Warewulf (filesystem rooted at /)
    etc/rancher/manifests/           ← RKE2 auto-deploy set
      00-cert-manager.yaml           ← all nodes
      01-cluster-issuer.yaml         ← all nodes           __ACME_EMAIL__
      10-hami.yaml                   ← GPU nodes           __K8S_VERSION__
      30-nfs.yaml                    ← all nodes           __NFS_SERVER__ __NFS_PATH__
      40-metallb.yaml                ← head/edge nodes
      41-metallb-vip.yaml            ← head/edge nodes     __VIP__ __PUBLIC_NIC__
      50-tyk-redis.yaml              ← all nodes
      51-tyk.yaml                    ← all nodes           __TYK_API_SECRET__
      52-tyk-loadbalancer.yaml       ← head/edge nodes
      53-tyk-api-definitions.yaml    ← all nodes
      60-istio.yaml                  ← all nodes  (Job)
      61-knative.yaml                ← all nodes  (Job)
      62-kserve.yaml                 ← all nodes  (Job)
      63-model-gateway.yaml          ← all nodes  (runs on CP via nodeSelector)
    etc/netplan/
      60-public-vip.yaml             ← head/edge nodes ONLY   __VIP__ __PUBLIC_NIC__ __PUBLIC_SUBNET__ __PUBLIC_GW__
    etc/sysctl.d/
      99-public-vip.conf             ← head/edge nodes ONLY
  post-deploy/           ← applied after first boot (see post-deploy/README.md)
    README.md
    certificate.example.yaml
    verify-test-model.sh
```

---

## Before baking: fill in site values

1. Read `SITE-VALUES.md` — one table of every `__TOKEN__` and which files use it.
2. Copy `site.env.example` → `site.env`, fill in real values.
3. Substitute tokens (sed loop shown in `site.env.example`) or edit files directly.
4. **Never commit real secrets** — `__TYK_API_SECRET__` is loaded from `.env` (gitignored).
5. Bake `overlay/` into the Warewulf image for the appropriate node role:
   - **Control-plane nodes**: all of `overlay/`
   - **GPU workers**: `overlay/etc/rancher/manifests/10-hami.yaml` is the only manifest that
     matters there (HAMi device-plugin, runs where `gpu=on`). The worker runs `rke2-agent`,
     not `rke2-server`, so it does not process the manifests directory — but the NVIDIA
     driver/runtime/label setup must be baked into the GPU worker image separately.

---

## Manifest boot order and self-ordering

File-number prefixes are for humans. RKE2's helm-controller reconciles HelmCharts
independently; the serving-stack Jobs (60–63) self-order via internal wait loops:

```
00 cert-manager ──► 60-istio (waits for cert-manager)
                        └──► 61-knative (waits for istio-system)
                                 └──► 62-kserve (waits for knative-serving)
                                          └──► 63-model-gateway (needs models ns from 62)
10 hami         ──► device-plugin on gpu=on nodes (independent)
30 nfs          ──► StorageClass (independent)
40 metallb      ──► 41-metallb-vip (CRD-race: retries until MetalLB CRDs land — benign)
50 tyk-redis    ──► 51-tyk → mounts 53-tyk-api-definitions (optional: true, no race)
                         └──► 52-tyk-loadbalancer (waits for VIP from 41)
```

Re-running a bootstrap Job: `kubectl delete job <name>-bootstrap -n kube-system`

---

## Gateway updates (CI → cluster)

The model-gateway image (`rkhoja/aleph:latest`) is published to Docker Hub automatically
on every push to `main` that touches `gateway/**` (~4 min build). The Deployment in
`63-model-gateway.yaml` uses `imagePullPolicy: Always`, so:

```bash
kubectl rollout restart deploy/model-gateway -n models
kubectl rollout status  deploy/model-gateway -n models
```

No file-copy, no SSH push, no deploy script needed.

---

## Public endpoint

```
Clients → __VIP__:80 → Tyk (auth, rate-limit) → model-gateway → KServe pods
```

- OpenAI SDK:    `base_url="http://__VIP__/v1"`, `api_key=<TYK_KEY>`
- Anthropic SDK: `base_url="http://__VIP__"`, `api_key=<TYK_KEY>`
- NodePort fallback (internal): `http://<any-node-ip>:30808`

---

## MetalLB L2 recipe (three layers)

| Layer | What | Where |
|---|---|---|
| `40-metallb.yaml` | Installs MetalLB (chart, frr sidecar, pinned to CP nodes) | manifest |
| `41-metallb-vip.yaml` | VIP pool + L2Advertisement on `__PUBLIC_NIC__` | manifest |
| `52-tyk-loadbalancer.yaml` | LoadBalancer svc → gets `__VIP__` from the pool | manifest |
| `etc/netplan/60-public-vip.yaml` | NIC up IP-free, VIP on dummy0, public subnet on-link | node overlay |
| `etc/sysctl.d/99-public-vip.conf` | `rp_filter=0`, ARP suppress | node overlay |

The netplan + sysctl are the only pieces that aren't k8s manifests — they configure the
host network that MetalLB L2 relies on. They are HEAD/edge node only.

---

## See also

- `SITE-VALUES.md` — all tokens, applicability table, regression warnings
- `post-deploy/README.md` — steps after first boot (Tyk key, smoke test, adding models)
- `docs/RUNBOOK.md` — cluster ops, Tyk key management, troubleshooting
- `gateway/tyk/tyk-keys.sh` — key create/list/revoke helper
