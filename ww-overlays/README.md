# Aleph Warewulf overlays

The manifests in this directory mirror the verified Aleph Warewulf sources as of 2026-09-09. They contain the deployed site values. The Tyk admin secret and ACME contact are redacted; SSH credentials are not exported from Warewulf into Git.

## Repository paths and deployed overlays

| Repository tree | Warewulf overlay root | Assigned nodes |
|---|---|---|
| `overlays/control-plane/` | `rke2-aleph/rootfs/` | `aleph1`, `aleph2`, `aleph3` |
| `overlays/common/` | `rke2-aleph-common/rootfs/` | `aleph1–3`, `rack09-01–07` |
| `overlays/gpu-worker/` | `rke2-aleph-gpu/rootfs/` | `rack09-01–07` |

These are **system/boot overlays**. The current runtime assignments contain `hosts` and `ssh_hostauth`, so starting `wwclient` does not install the manifests or Ansible playbooks. Do not change that assignment or reboot based only on a successful runtime refresh.

The manifest source directory on control-plane nodes is `/etc/rancher/manifests/`. Aleph1's existing `rke2-head2` manifest service stages these into `/var/lib/rancher/rke2/server/manifests/` for cluster-wide application. Aleph2/3 join that cluster and need no additional staging service. See [CONTROL-PLANE-REBOOT.md](CONTROL-PLANE-REBOOT.md) for their verified fresh-rejoin setup.

## Complete manifest set

All 23 filenames from live `.43` are present, plus Warewulf's `44-canal-config.yaml` (identical to `.43`'s staged `rke2-canal-config.yaml`).

| Files | Purpose |
|---|---|
| `00-cert-manager`, `01-cluster-issuer` | Certificate controller and ACME issuer |
| `09-gpu-autolabel`, `10-hami`, `11-node-labeler` | GPU discovery, scheduling, and resource labels |
| `30-nfs` | NFS provisioner |
| `40-metallb`, `41-metallb-vip` | Load balancer and actual site VIP configuration |
| `42-traefik-loadbalancer`, `43-traefik-config`, `44-canal-config` | Ingress service, control-plane placement, and cluster network interface |
| `49-tyk-redis-data`, `50-tyk-redis`, `51-tyk`, `52-tyk-loadbalancer` | Tyk storage and services |
| `53-tyk-api-definitions`, `54-tyk-middleware`, `56-edge-routes` | Live API routes, middleware, TLS and ingress routes |
| `60-istio`, `61-knative`, `62-kserve`, `63-model-gateway` | Serving platform and pinned model gateway |
| `70-rdma-device-plugin`, `80-model-pvcs` | RDMA resources and static storage recovery bindings |

All filenames above have the `.yaml` suffix. See [STORAGE-RECOVERY.md](STORAGE-RECOVERY.md) before restoring storage objects.

## What was reconciled

The labeler, pinned gateway manifest, and Tyk admin script were copied directly from `.43`. The Tyk ConfigMap was exported from the live cluster so its three existing routes, including `/anthropic/`, survive a rebuild. The Speaches PV/PVC binding already appended to the Warewulf storage snapshot was preserved, with its missing YAML document separator repaired.

All 24 repository manifests match the sanitized Warewulf export byte-for-byte. Non-secret site values are retained. Common/GPU support files included in the export match the live files checked. Existing networking examples and SSH/PAM scaffolding elsewhere in this tree were not refreshed or certified by this manifest reconciliation; do not bulk-copy the entire repository tree over an operational overlay.

## Ansible source

The shared `rke2-ansible` generator is maintained in [warewulf-rke2-hami](https://github.com/ualberta-rcg/warewulf-rke2-hami/tree/main/overlays/rke2-ansible). At the operator's direction, its `04-install-cvmfs` and `23-mount-nfs` entries were removed. The remaining six rendered playbooks match live `.43`. This shared overlay serves 12 nodes; changes are not exclusive to Aleph.

## Validation and rollout state

- Private rendering passed for the corrected manifests and for the combined role overlays of `aleph3` and `rack09-01`. Both produced exactly the expected six Ansible files, without the two removed entries.
- The corrected storage manifest and exported Tyk ConfigMap passed Kubernetes client dry-run. No storage objects or live API policies were applied by this reconciliation.
- Full system and runtime overlay images were rebuilt for `aleph2`, `aleph3`, and `rack09-01`.
- At 23:16 UTC, `wwclient` was started on `aleph3` and refreshed on the already-running `rack09-01`. Both applied runtime overlays without inspected errors. Both nodes stayed Ready; gateway remained 3/3 Ready and public health returned 200.
- That initial runtime refresh did not change boot manifest/Ansible/GPU checksums; runtime refresh does not replace or remove boot files.
- On 2026-09-10, `aleph3` and then `aleph2` passed reboot tests with their published overlays. All 24 delivered manifests and six playbooks matched the operational sources. Firstboot completed successfully, both nodes rejoined Ready, all three etcd endpoints passed health checks, and public IPs/routes were correct.
- Filebeat passed config/output checks on both rebooted nodes and reported acknowledged deliveries. Zabbix Agent 2 and SSSD were active. Gateway replicas were moved gracefully before each reboot, with 3/3 available before reboot and at recovery checks.
- Joining control-plane nodes use a node-specific Ignition Rancher filesystem wipe to avoid retaining a removed etcd member's database. Aleph1 and the shutdown scripts were not changed. No image changes were made.

The rack reboot canary remains pending. Other nodes' distributed overlays must be rebuilt and validated before their rollout; the completed control-plane tests do not certify untested nodes.

## Secrets and site-specific files

See [SITE-VALUES.md](SITE-VALUES.md). Preserve the operational Tyk secret and SSH credential files inside Warewulf. Restore the two redacted manifest values through the existing private deployment process; never apply their redacted copies directly.
