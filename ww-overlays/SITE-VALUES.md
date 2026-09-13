# Aleph site values and redactions

The verified 24-manifest snapshot uses real deployed infrastructure values — it is **not** a
generic placeholder template. Real values live only in the operational deployment and the
private site store (`site.env` / your secrets directory); this file documents *which* values
are site-specific and how to handle them.

| Redacted value | File | Required handling |
|---|---|---|
| `__TYK_API_SECRET__` | `overlays/control-plane/etc/rancher/manifests/51-tyk.yaml` | Preserve the existing private Warewulf value. Never commit it or apply the redacted value. |
| `__ACME_EMAIL__` | `overlays/control-plane/etc/rancher/manifests/01-cluster-issuer.yaml` | Supply the existing authorized operations contact privately. |

Other site values retained in the snapshot (verify against your deployment before use):

| Value kind | Where | Notes |
|---|---|---|
| Kubernetes version | `10-hami.yaml` (`__K8S_VERSION__` concept) | Must match the cluster exactly — HAMi ships a scheduler pinned to it |
| NFS server + export path | `30-nfs.yaml`, `80-model-pvcs.yaml` | The storage backend all model weights live on |
| Public VIP | `41-metallb-vip.yaml` | MetalLB L2 pool; hostname routes to it |
| Public NIC + per-node public IP / prefix / gateway | `41` + netplan | Each control-plane node has 3 addresses (cluster, own public, floating VIP) |
| RDMA / Canal interface names | `70-rdma-device-plugin.yaml`, `44-canal-config.yaml` | Typically `eth0` |
| Public hostname | `56-edge-routes.yaml` | Traefik Host routing + Let's Encrypt cert |

Static PV paths and explicit volume bindings are preserved; changing these is not a harmless
template substitution.

The older `site.env.example` and networking files remain examples for their separate
provisioning workflow. Review per-node networking independently; never substitute one node's
public address across the cluster.

SSH private keys, authorized keys and trust material were excluded from the export. Existing
dummy/example files in the repository are not replacements for the live credentials. Do not
copy the entire role tree blindly over an existing Warewulf overlay.
