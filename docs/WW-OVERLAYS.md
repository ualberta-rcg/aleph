# Warewulf and overlay configuration

The trees under `ww-overlays/overlays/` supply the Aleph components of a
Warewulf/RKE2 deployment. Integrate them with your node image, profiles, firstboot
playbooks, and private site configuration. This guide owns overlay settings,
site-value tokens, and storage setup. See [Kubernetes](KUBERNETES.md) for serving
behavior and [System](SYSTEM.md) for node services and drivers.

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

1. Render site placeholders using [site values](#site-values-and-tokens), with separate
   node-specific networking values where required.
2. Review [storage bindings](#storage-setup-and-recovery) for a fresh install or recovery.
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

## Overlay settings to review

Not every deployment choice is a `__TOKEN__`. Review these files before baking;
paths are relative to `ww-overlays/overlays/`.

| Setting | Source | What to check |
|---|---|---|
| Cluster NIC | `control-plane/etc/rancher/manifests/44-canal-config.yaml` | `flannel.iface` is currently `eth0`. Select the cluster interface explicitly on hosts whose preferred default route uses a different NIC. |
| Public ingress placement | `control-plane/etc/rancher/manifests/43-traefik-config.yaml` | Traefik's selector must agree with the nodes able to serve the MetalLB VIP. |
| Per-node public networking | `control-plane/etc/netplan/60-public-vip.yaml` | Render each node's own address and routes; do not configure the floating VIP as its static address. |
| NFS mount options | `control-plane/etc/rancher/manifests/30-nfs.yaml` | Options belong under `spec.valuesContent` → `nfs.mountOptions`. The supplied chart does not use `storageClass.mountOptions` for this purpose. Verify the resulting StorageClass and PVs. |
| Gateway image and placement | `control-plane/etc/rancher/manifests/63-model-gateway.yaml` | Review the image pin, replicas, node placement, timeouts, and termination settings together; see [Kubernetes](KUBERNETES.md). |
| Shutdown behavior | `common/etc/default/rke2-deregister` | Review server deregistration and target discovery against the site's rejoin procedure; see [System](SYSTEM.md#shutdown-and-rejoin). |
| Node services and kernel settings | `common/` and `gpu-worker/` | Review inotify limits, persistence mode, RDMA modules, and unit enablement; see [System](SYSTEM.md). |

The NFS manifest sets NFS 4.2, 128 KiB read/write sizes, and a `Delete` reclaim
policy for the dynamic storage class. These are the supplied configuration, not
universal storage defaults. Review them for the target backend; changing a class
does not establish that existing volumes or mounts adopted the new settings.

## Storage setup and recovery

Aleph uses NFS-backed persistent volumes for model weights, Tyk's Redis data, and
usage records. Persistence across pod or node replacement does not replace a backup.

Two manifests under
`ww-overlays/overlays/control-plane/etc/rancher/manifests/` contain explicit
bindings from an existing deployment:

| File | Purpose |
|---|---|
| `49-tyk-redis-data.yaml` | Redis PV/PVC binding |
| `80-model-pvcs.yaml` | Model-weight PV/PVC bindings |

The Redis chart in `50-tyk-redis.yaml` enables persistence. The preceding
`49-tyk-redis-data.yaml` supplies the exact claim expected by its StatefulSet:
`tyk/redis-data-tyk-redis-master-0`, explicitly bound to `pv-tyk-redis-data`.
A read-only check on 2026-09-13 confirmed that the Redis pod mounts this Bound
claim and the PV uses `Retain`. During recovery, preserve the binding to the
surviving data; a newly provisioned empty volume will not restore key sessions.
`Retain` preserves the PV's data on claim release; it is not a backup.

**For a fresh installation**, replace these bindings with storage definitions for
your site. Use the selected models' `pvc.yaml` files with the configured storage
class, and provide persistent Redis storage compatible with the Tyk deployment.
Do not install the old model-volume bindings merely to populate a new catalog.

**For recovery**, verify each claim name, explicit `volumeName`, and NFS directory
against the surviving data before applying a binding. Rendering `__NFS_SERVER__`
and `__NFS_PATH__` changes the storage location prefix; it does not recreate the
original directories or their contents.

These YAML files contain configuration, not a backup of weights or API keys.
Redis contains authentication state that cannot be regenerated from manifests.
Maintain private backups and recovery procedures for that state and the other
data your deployment needs. Preserve PVCs when replacing model services.

## Joining control-plane filesystem configuration

The September 2026 reboot work identified an important boundary between stateless
boot configuration and persistent local RKE2 state. In that deployment's
shutdown/rejoin design, a joining control-plane node lost its etcd membership but
retained the removed member's database. Delivering the correct manifests was not
enough to make it rejoin.

The verified correction used Warewulf's ignition filesystem configuration to
recreate `/var/lib/rancher` on the **joining** control-plane node. It was a
per-node filesystem setting, not a Kubernetes manifest or a base-image change.
The relevant partial configuration was:

```yaml
filesystems:
  /dev/disk/by-partlabel/rancher:
    format: ext4
    path: /var/lib/rancher
    wipe_filesystem: true
```

This destroys and recreates the selected local filesystem on **every boot**,
including its RKE2 database, local certificates, and cached images. It is specific
to that fresh-rejoin design, not a default for an arbitrary RKE2 installation.
Do not apply it to the bootstrap control plane or a shared all-node profile.
The recorded setup left `/var/lib/kubelet` unwiped and NFS storage unaffected.

For a deployment using this design, inspect the built system archive's
`warewulf/ignition.json`: the intended rancher filesystem should render
`wipeFilesystem: true`, without changing other filesystems. Rebuild the affected
node's overlays after changing its definition. Follow the
[system rejoin checks](SYSTEM.md#shutdown-and-rejoin); a successful overlay build
is not proof of a successful reboot.

Historical evidence: [control-plane reboot record](https://github.com/ualberta-rcg/aleph/blob/e8e6777/ww-overlays/CONTROL-PLANE-REBOOT.md)
from the rollout completed in September 2026. This records the tested mechanism;
it does not certify the current node inventory or authorize filesystem changes.

### Diagnosing storage writes

The 128 KiB NFS transfer sizes in `30-nfs.yaml` came from a backend-specific
failure: small writes succeeded while large model files failed with an I/O error
at flush/close. Keep that distinction in mind when testing a new storage backend;
creating a small file does not validate a complete weight download.

Check the rendered StorageClass's `mountOptions`, the affected PV, and the actual
mount. Setting options in the wrong chart section can leave the intended fix
unapplied. The configuration is already described under
[overlay settings](#overlay-settings-to-review); avoid creating another recovery
manifest or deleting model claims to work around a mount-option problem.
