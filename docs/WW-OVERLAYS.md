# Warewulf overlays

The trees under `ww-overlays/overlays/` supply the Aleph components of a
Warewulf/RKE2 deployment. Integrate them with your node image, profiles, firstboot
playbooks, and private site configuration.

## Role layout

| Repository path | Role |
|---|---|
| `ww-overlays/overlays/control-plane/` | Serving-stack manifests and control-plane configuration |
| `ww-overlays/overlays/common/` | Shared node configuration and shutdown integration |
| `ww-overlays/overlays/gpu-worker/` | GPU-worker services and RDMA module configuration |

These are boot overlays. A runtime refresh does not establish that a node has
received or successfully booted an updated system overlay. Preserve directory
permissions when installing them; Git tracks file executable bits, not directory
modes.

The bootstrap control-plane node stages files from `/etc/rancher/manifests/` into
RKE2's `/var/lib/rancher/rke2/server/manifests/` directory. RKE2 applies them to the
cluster. Joining control-plane nodes use the existing cluster.

## Manifest groups

The source is `ww-overlays/overlays/control-plane/etc/rancher/manifests/`.
Numbered filenames organize the components; verify readiness rather than assuming
that file order guarantees every dependency is ready.

| Group | Components |
|---|---|
| `00–11` | Certificates, GPU discovery, HAMi, hardware labels |
| `30` | NFS storage provisioner |
| `40–44` | MetalLB, Traefik, cluster network configuration |
| `49–56` | Redis, Tyk, authentication routes, TLS ingress |
| `60–63` | Istio, Knative, KServe, Aleph gateway |
| `70` | RDMA device plugin |
| `80` | Static model-storage bindings |

## Before building

1. Render site placeholders using [SITE-VALUES.md](SITE-VALUES.md), with separate
   node-specific networking values where required.
2. Review [storage bindings](STORAGE-RECOVERY.md) for a fresh install or recovery.
3. Integrate the shared firstboot tooling from the
   [node-image repository](https://github.com/ualberta-rcg/warewulf-rke2-hami)
   with your site's services. Aleph's common overlay includes a package-playbook
   override; review it for your environment.
4. Supply private credentials and trust configuration through your deployment
   process. Example files do not establish working access.

For an existing installation, review changes before merging them into its
operational overlays. Keep the repository, rendered boot sources, and deployed
configuration aligned so that a later reboot preserves the intended configuration.
Use [QUICKSTART.md](../QUICKSTART.md) for the deployment sequence.
