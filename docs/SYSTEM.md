# System configuration

This guide records Aleph's node-level requirements and adjustments: boot
integration, systemd services, kernel settings, and GPU/RDMA support. For how
these files reach nodes, see [Warewulf](WW-OVERLAYS.md). For serving resources,
see [Kubernetes](KUBERNETES.md).

The paths below are relative to `ww-overlays/overlays/`. Settings describe the
committed files; check the running node before diagnosing deployment drift.

## Boot integration and permissions

The node image and site firstboot tooling are maintained alongside the
[node-image repository](https://github.com/ualberta-rcg/warewulf-rke2-hami).
Aleph adds its role overlays and a common package-playbook override. Inspect the
rendered playbooks and their completion status when validating a boot; Kubernetes
Ready alone does not establish that every firstboot task succeeded.

Preserve normal executable-directory permissions when importing overlays. Git
tracks file executable bits, not directory modes. Restrictive permissions on
system paths such as `/usr` can prevent unprivileged package helpers from running
even if the executable itself has the correct mode.

## Supplied adjustments

| Source | Behavior and reason to review it |
|---|---|
| `common/etc/sysctl.d/90-inotify.conf` | Raises `fs.inotify.max_user_instances` to 1024 for nodes running many pod watches. Inspect effective limits when diagnosing failed watches. |
| `gpu-worker/etc/systemd/system/nvidia-persistenced.service` | Enables NVIDIA persistence mode with `nvidia-smi -pm 1`. Coordinate it with any persistence service supplied by the image. |
| `gpu-worker/etc/modules-load.d/rdma.conf` | Loads RDMA core, userspace verbs, and connection-management modules for the GPU-worker device stack. |
| `common/etc/systemd/system/rke2-deregister.service` | Runs node deregistration during shutdown while networking is still available. |
| `common/etc/default/rke2-deregister` | Controls target discovery, SSH configuration, and whether control-plane nodes deregister. |

When changing a systemd service, review its enablement symlink and unit ordering
as well as the unit file. Removing or replacing only one of those may leave an
unintended boot configuration.

## GPU and RDMA checks

GPU drivers come from the node image; HAMi provides Kubernetes GPU scheduling.
Validate host device visibility before investigating the device plugin or model
runtime. HAMi's advertised GPU resource count represents sharing slots, not a
physical-card inventory.

RDMA requires more than a declared Kubernetes resource: host modules and devices,
the selected interface, and a container userspace provider compatible with the
host driver must agree. Confirm the model uses the intended transport before
attributing a performance result to RDMA. Keep hardware-specific provider recipes
and measured results with their relevant source and test scope.

## Shutdown and rejoin

The deregistration hook attempts to delete the node's Kubernetes object using
restricted SSH access. Target control planes are discovered from RKE2's local
configuration unless `HEAD_NODES` overrides them. The script defaults to skipping
servers, but the supplied environment file enables `DEREGISTER_SERVERS`.

That setting is significant for control-plane maintenance. Node deletion is not
a complete etcd recovery procedure: local state and the site's rejoin design
must also agree. Preserve quorum and validate one node's rejoin before proceeding
to another. Keep site-specific recovery commands and credentials in private
operating notes.
