# Aleph site values and redactions

The verified 24-manifest snapshot uses real deployed infrastructure values. It is not a generic placeholder template.

| Redacted value | File | Required handling |
|---|---|---|
| `__TYK_API_SECRET__` | `overlays/control-plane/etc/rancher/manifests/51-tyk.yaml` | Preserve the existing private Warewulf value. Never commit it or apply the redacted value. |
| `__ACME_EMAIL__` | `overlays/control-plane/etc/rancher/manifests/01-cluster-issuer.yaml` | Supply the existing authorized operations contact privately. |

Other manifests retain Kubernetes `v1.36.1`, NFS `manage.storage.data.vulcan.local:/aleph`, VIP `129.128.190.71`, public interface `enp6s20`, and RDMA/Canal interface `eth0`. Static PV paths and explicit volume bindings are preserved; changing these is not a harmless template substitution.

The older `site.env.example` and networking files remain examples for their separate provisioning workflow. Their public-address placeholders are not unresolved values in this manifest snapshot. Review per-node networking independently; never substitute one node's public address across the cluster.

SSH private keys, authorized keys and trust material were excluded from the export. Existing dummy/example files in the repository are not replacements for the live credentials. Do not copy the entire role tree blindly over an existing Warewulf overlay.
