# Storage setup and recovery

Aleph uses NFS-backed persistent volumes for model weights, Tyk's Redis data, and
usage records. Persistence across pod or node replacement does not replace a backup.

Two manifests under
`ww-overlays/overlays/control-plane/etc/rancher/manifests/` contain explicit
bindings from an existing deployment:

| File | Purpose |
|---|---|
| `49-tyk-redis-data.yaml` | Redis PV/PVC binding |
| `80-model-pvcs.yaml` | Model-weight PV/PVC bindings |

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
