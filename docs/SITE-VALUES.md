# Site values

## Site values and tokens

The control-plane overlay is **tokenized**: every site-specific value is a `__TOKEN__`
placeholder. Fill a copy of `ww-overlays/site.env.example` (dummy values) with your real
values as `site.env` (never committed), then substitute before baking — the example file
contains the ready-to-use sed loop. The `common` and `gpu-worker` overlays carry no tokens.

| Token | Meaning | Notes |
|---|---|---|
| `__K8S_VERSION__` | cluster Kubernetes version | Must match exactly — HAMi ships a patched kube-scheduler pinned to it (`10-hami.yaml`) |
| `__NFS_SERVER__` | NFS server for model weights | `30-nfs.yaml`, `49-tyk-redis-data.yaml`, `80-model-pvcs.yaml` |
| `__NFS_PATH__` | NFS export root (provisioner + static PV paths hang off it) | same files |
| `__VIP__` | public floating VIP (MetalLB L2) | `41-metallb-vip.yaml`; floats between control-plane nodes — never bound to a node or `lo` |
| `__PUBLIC_NIC__` | control-plane public NIC name | `41-metallb-vip.yaml` (L2 advertisement) + netplan |
| `__PUBLIC_NIC_IP__` | **per-node** own public IP | netplan `60-public-vip.yaml` — substitute once per control-plane node |
| `__PUBLIC_PREFIX__` / `__PUBLIC_GW__` | public subnet prefix + gateway | netplan; public gateway must be the PREFERRED default route (metric 50), cluster default at metric 100 |
| `__INFERENCE_HOST__` | public hostname (edge routing + cert CN) | `56-edge-routes.yaml`; DNS must point at the VIP |
| `__ACME_EMAIL__` | Let's Encrypt registration contact | `01-cluster-issuer.yaml` |
| `__TYK_API_SECRET__` | Tyk admin `APISecret` | `51-tyk.yaml`; load from the gitignored `.env`, never commit |
| `__ROCE_IFNAME__` | GPU-worker RoCE NIC | `70-rdma-device-plugin.yaml`; verify the interface and provider for your hardware |

Networking model: each control-plane node carries three addresses — cluster IP, its own
public IP on the public NIC (in the VIP's prefix), and the floating VIP that MetalLB
advertises from the elected leader. Review per-node networking independently; never
substitute one node's public address across the cluster.

### Credentials

SSH private keys, authorized keys and trust material are never exported into Git; the
repository ships dummy/example files only, which are not replacements for live credentials.
Do not copy the entire role tree blindly over an existing Warewulf overlay.
Supply the Tyk admin secret and site contact values through your private deployment
process; example values are not a working site configuration.

## Environment values (`.env`)

The repository root's `.env` (copy of [`.env.example`](../.env.example), gitignored)
holds the deployment **credentials** — the other half of your site values. Source it
into a private shell with `set -a; source .env; set +a`; never commit, print, or paste
it. For an authorized operator's variable-by-variable reference, see the environment
section of [CLAUDE.md](../CLAUDE.md).

| Variable | Why you need it / where it is used |
|---|---|
| `HF_TOKEN` | Model init containers download weights from HuggingFace with it. Create the `hf-token` Secret (key `token`, `models` namespace) from it; InferenceService init containers reference that Secret. A local export alone does not reach pods. |
| `NGC_API_KEY` | Only for NIM-container models: creates the `ngc-api-key` Secret and the `ngc-registry-secret` docker-registry pull secret for `nvcr.io`. Skip entirely if you deploy no NIMs. |
| `TYK_SECRET` / `TYK_API_SECRET` | The Tyk admin `APISecret` (same value in both). **At deploy time this is the value of the `__TYK_API_SECRET__` token** — it is rendered into `51-tyk.yaml`, becomes the in-cluster Secret `secrets-tyk-oss-tyk-gateway`, and is what authenticates Tyk administration (`tyk-admin.sh` discovers it automatically). Generate it fresh per deployment. |
| `HEAD` | Operator convenience for SSH one-liners to a control-plane node; it is not kubectl context selection. Optional. |

Test-time variables (`GW_URL`, `TYK_KEY`, `MODEL`) are supplied in the shell running a
model's `test.py`, not stored in `.env` — see [Add a model](ADD-A-MODEL.md).
