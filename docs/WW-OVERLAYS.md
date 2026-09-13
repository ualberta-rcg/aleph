# Aleph Warewulf overlays

The manifests under `ww-overlays/overlays/` mirror the verified Aleph Warewulf sources,
**tokenized**: every site-specific value is a `__TOKEN__` placeholder (see
[SITE-VALUES.md](SITE-VALUES.md) and `ww-overlays/site.env.example`, which carries dummy
values — copy it to `site.env`, fill in your real ones, and substitute before baking).
SSH credentials are never exported from Warewulf into Git.

## Repository paths and deployed overlays

| Repository tree | Warewulf overlay root | Assigned nodes |
|---|---|---|
| `overlays/control-plane/` | `rke2-aleph/rootfs/` | control-plane nodes |
| `overlays/common/` | `rke2-aleph-common/rootfs/` | all nodes |
| `overlays/gpu-worker/` | `rke2-aleph-gpu/rootfs/` | GPU workers |

These are **system/boot overlays**. The runtime assignments contain `hosts` and `ssh_hostauth`
only, so starting `wwclient` does not install the manifests or Ansible playbooks. Do not change
that assignment, and never treat a successful runtime refresh as a boot-image validation.

The manifest source directory on control-plane nodes is `/etc/rancher/manifests/`. The first
control-plane node stages these into `/var/lib/rancher/rke2/server/manifests/` for cluster-wide
RKE2 auto-deploy; additional control-plane nodes join that cluster and need no extra staging
service. See [CONTROL-PLANE-REBOOT.md](CONTROL-PLANE-REBOOT.md) for the verified fresh-rejoin
setup and [RACK-BOOT.md](RACK-BOOT.md) for worker firstboot requirements.

## Complete manifest set

All 23 filenames from the live control-plane node are present, plus Warewulf's
`44-canal-config.yaml` (identical to the node's staged `rke2-canal-config.yaml`).

| Files | Purpose |
|---|---|
| `00-cert-manager`, `01-cluster-issuer` | Certificate controller and ACME issuer |
| `09-gpu-autolabel`, `10-hami`, `11-node-labeler` | GPU discovery, scheduling, and resource labels |
| `30-nfs` | NFS provisioner |
| `40-metallb`, `41-metallb-vip` | Load balancer and site VIP configuration |
| `42-traefik-loadbalancer`, `43-traefik-config`, `44-canal-config` | Ingress service, control-plane placement, and cluster network interface |
| `49-tyk-redis-data`, `50-tyk-redis`, `51-tyk`, `52-tyk-loadbalancer` | Tyk storage and services |
| `53-tyk-api-definitions`, `54-tyk-middleware`, `56-edge-routes` | Live API routes, middleware, TLS and ingress routes |
| `60-istio`, `61-knative`, `62-kserve`, `63-model-gateway` | Serving platform and pinned model gateway |
| `70-rdma-device-plugin`, `80-model-pvcs` | RDMA resources and static storage recovery bindings |

All filenames above have the `.yaml` suffix. See [STORAGE-RECOVERY.md](STORAGE-RECOVERY.md)
before restoring storage objects.

## Reconciliation provenance

The labeler, pinned gateway manifest, and Tyk admin script were captured directly from the
live control-plane node. The Tyk ConfigMap was exported from the live cluster so its three
existing routes, including `/anthropic/`, survive a rebuild. The appended storage binding with
its missing YAML document separator was repaired. The repository set matches the verified
operational sources modulo site-value tokens.

Existing networking examples and SSH/PAM scaffolding elsewhere in this tree were not refreshed
or certified by the manifest reconciliation; do not bulk-copy the entire repository tree over an
operational overlay.

## Ansible source

The shared `rke2-ansible` generator is maintained in
[warewulf-rke2-hami](https://github.com/ualberta-rcg/warewulf-rke2-hami/tree/main/overlays/rke2-ansible).
At the operator's direction, its `04-install-cvmfs` and `23-mount-nfs` entries were removed
(this shared overlay serves more than just Aleph).

Aleph's common overlay additionally overrides `03-install-packages.yaml` to remove the unused
CVMFS APT repository instead of re-adding it; the other five playbooks retain their verified
shared sources. No shared package playbook or base image was changed. See
[RACK-BOOT.md](RACK-BOOT.md), including the required 0755 directory permissions that Git
cannot record.

## Validation state

- Rendering of the corrected manifests and combined role overlays produced exactly the expected
  six Ansible files, without the two removed entries; the storage manifest and exported Tyk
  ConfigMap passed Kubernetes client dry-run.
- Full system and runtime overlay images were rebuilt and validated for every Aleph node.
- Control-plane reboot tests passed with the published overlays: firstboot completed, the nodes
  rejoined Ready, etcd endpoints passed health checks, and public IPs/routes were correct.
  Filebeat config/output checks reported acknowledged deliveries; Zabbix Agent 2 and SSSD were
  active. See [CONTROL-PLANE-REBOOT.md](CONTROL-PLANE-REBOOT.md).
- The worker canary passed its corrected reboot test: all six firstboot playbooks completed,
  the CVMFS repository was absent, directory permissions were 0755, and the node automatically
  regained `gpu=on`, hardware labels, HAMi sharing resources, and RDMA. See
  [RACK-BOOT.md](RACK-BOOT.md).
- Published boot overlays do not imply running files changed on nodes that were not rebooted.

## Secrets and site-specific files

See [SITE-VALUES.md](SITE-VALUES.md). Preserve the operational Tyk secret and SSH credential
files inside Warewulf. Restore the two redacted manifest values through the existing private
deployment process; never apply their redacted copies directly.
