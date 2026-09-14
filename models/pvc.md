# Model storage: pvc.yaml

Use this reference when preparing `models/<model>/pvc.yaml`. Start with the
[deployment workflow](../docs/ADD-A-MODEL.md); connect this claim to the mounts in
[inferenceservice.yaml](inferenceservice.md). The examples are patterns to adapt,
not commands to apply to an existing model's storage.

## A shared model claim

```yaml
apiVersion: v1
kind: PersistentVolumeClaim
metadata:
  name: example-model-data
  namespace: models
spec:
  accessModes: [ReadWriteMany]
  storageClassName: nfs-models
  resources:
    requests:
      storage: 60Gi
```

`60Gi` is illustrative. Include weights, tokenizer/configuration files, auxiliary
checkpoints, caches and any environment or database required by the runtime.
The claim name must match `persistentVolumeClaim.claimName` in the service.
The volume's local name must match each container's `volumeMounts[].name`.

| Field | Choice and effect |
|---|---|
| `metadata.name` | Unique claim name for a new model. Preserve the actual name for an existing model. |
| `metadata.namespace` | Must match the pods using the claim; examples use `models`. |
| `storageClassName` | `nfs-models` is the established shared-storage class. Use the class installed at the target site. |
| `accessModes` | `ReadWriteMany` supports mounts across workers/replicas. Access mode is not a substitute for coordinating concurrent writes. |
| `resources.requests.storage` | Requested capacity; actual enforcement and expansion depend on the provisioner. |
| `volumeName` / selectors | Only for a deliberately pre-provisioned volume. Do not copy another model's binding or a site-specific PV name. |

Site storage definitions belong in [Site values](../docs/SITE-VALUES.md) and
[Warewulf/storage guidance](../docs/WW-OVERLAYS.md). This file requests storage;
it does not create or recover the site's NFS server.

**Sizing and classes in practice** (fleet survey 2026-09-14): model claims run from
2 Gi to 200 Gi — small science models 5–10 Gi, chat LLMs 30–100 Gi, the largest
multi-GPU weights ~200 Gi — plus a few Gi where a venv is persisted. Request what
the model's weights + caches + environment actually need plus headroom; a claim is
cheap to create and disruptive to replace. Most existing claims at the reference
site are bound to pre-provisioned volumes (`storageClassName: ""` with a `volumeName`)
as part of its storage-recovery snapshot — **new models should use the dynamic
`nfs-models` class** as shown above; static bindings are recovery state, not the
pattern to copy. Two platform claims are not model storage: the gateway usage ledger
(10 Gi RWX, dynamic) and the Tyk Redis key store (2 Gi RWO) — preserve both across
rebuilds (Redis holds every API key).

## What persists and where

| Pattern | PVC contents | Serving behavior |
|---|---|---|
| Prebuilt runtime | Weights at `/data/model`; optional download helper at `/data/venv` | Runtime comes from the container image and loads the cached model. |
| Custom Python runtime | Weights plus the full `/data/venv` | Container runs `/data/venv/bin/python`; setup and serving images need compatible Python, system libraries and CUDA. |
| Packaged model server | Vendor-specific weights, databases and cache directories | Mount where that image expects its persistent files; `/data` is a convention, not a requirement. |
| Multiple checkpoints or auxiliary models | Separate directories under the claim | Record exact revisions, paths and required auxiliary artifacts. |
| Prepared environment on shared storage | Versioned environment directory and completion marker | Init validates the environment before the serving container uses it. |

Set runtime cache variables such as `HF_HOME` or `TORCH_HOME` to the intended PVC
paths when those caches should survive pod replacement. Some servers write even
when weights are read-only; provide a separate writable cache mount or directory.
Use `emptyDir` for disposable request scratch space or shared memory, not the only
copy of weights or environments.

A single claim can appear at different container paths, but the setup destination
must refer to the same underlying files the runtime reads. A `subPath` can select
a directory; create that directory before mounting it and document the layout.

## Initialization and updates

Run preparation in the service's init container. Persist download dependencies
as well as weights so a cached wake does not reinstall software. A small download
helper and a full serving environment are different uses of a venv; both belong
on the PVC when needed.

Validate expected files and imports before recording successful setup. A lone
`config.json` or existing `venv/bin` directory is not proof that a previous download
or install finished. Record model revisions and dependency versions with the
completion condition. Coordinate writers when replicas can initialize together;
for example, prepare once before increasing replicas, or use an appropriate
exclusive initialization mechanism for the shared filesystem.

When changing dependencies, build and verify a replacement environment rather
than overwriting one in use. Keep old working data until the replacement has been
validated. Do not apply migration snippets from another model's history without
checking the existing directory layout.

## Other storage arrangements

- **Already populated claim:** reuse its existing name and layout. Do not create a
  replacement PVC just because the directory or public model name changed.
- **Multiple claims:** use separate claims where large databases, weights or
  writable results have different lifetimes/access needs. Each mount must be
  represented explicitly in the service YAML.
- **Read-only serving mounts:** useful when initialization does all writes; keep
  caches writable if required. `ReadOnlyMany` is another access mode where the
  provisioner supports it, but cannot support the write phase of the normal setup.
- **ReadWriteOnce:** can constrain placement across nodes; verify replica and
  rescheduling requirements before substituting it for shared storage.
- **No PVC:** appropriate when the image contains everything needed and no files
  must persist. Document the image size and startup tradeoff. Runtime support for
  alternative storage mechanisms must be verified rather than assumed.

Scaling to zero stops processes and releases their resources; PVC data remains.
Service recreation must preserve the claim. Reusing a populated PVC tests cached
startup, not installation from empty storage. Storage backups and retention remain
site responsibilities.
