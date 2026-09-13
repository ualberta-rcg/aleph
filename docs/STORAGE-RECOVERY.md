# Persistent storage recovery manifests

`overlays/control-plane/etc/rancher/manifests/49-tyk-redis-data.yaml` mirrors the boot
manifest: it preserves the explicit Redis PV/PVC binding and its NFS directory. It contains
configuration only, not Redis data or API keys.

`overlays/control-plane/etc/rancher/manifests/80-model-pvcs.yaml` preserves the model
storage snapshot (100+ static PV/PVC pairs) including the Speaches pair (30Gi RWX; Bound
live to `pv-speaches`). These are recovery bindings for existing storage, not portable
examples or an inventory guarantee for every current model.

Both files are **tokenized** (`__NFS_SERVER__`, `__NFS_PATH__`) — the bake-time substitution
from `ww-overlays/site.env.example` → your `site.env` restores real values. UUID-bearing
directories, claim names, storage classes and explicit `volumeName` bindings are retained
verbatim; check them against your deployment's real volume UIDs before use.

Kubernetes client dry-run validated the corrected YAML. No PV/PVC or data is changed,
deleted, rebound, or recreated by committing these files. Before using them for disaster
recovery, independently confirm each surviving volume and claim mapping — a successful YAML
check does not establish data availability or reboot readiness.
