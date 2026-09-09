# Persistent storage recovery manifests

`49-tyk-redis-data.yaml` is an exact copy of the existing Warewulf/live boot manifest. It preserves the explicit Redis PV/PVC binding and existing NFS directory. It contains configuration only, not Redis data or API keys.

`80-model-pvcs.yaml` preserves the prior 105-pair model storage snapshot and the existing Speaches PV/PVC pair (106 pairs total). The missing newline and YAML document separator before Speaches were repaired. Speaches is Bound live to `pv-speaches`, with 30Gi RWX storage and the same existing NFS directory.

NFS server names, UUID-bearing directories, claim names, storage classes and explicit `volumeName` bindings are retained. These are recovery bindings for existing storage, not portable examples or an inventory guarantee for every current model.

Kubernetes client dry-run validated the corrected YAML. No PV/PVC or data was changed, deleted, rebound, or recreated. Before using these files for disaster recovery, independently confirm each surviving volume and claim mapping. A successful YAML check does not establish data availability or reboot readiness.
