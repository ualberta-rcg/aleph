# Aleph joining control-plane reboot

A verified procedure for rebooting a **joining** (non-bootstrap) control-plane node on this
platform. Node names below are placeholders — substitute your own.

## Existing design

The first (bootstrap) control-plane node applies manifests cluster-wide using its manifest
staging service. The other control-plane nodes receive the same YAML through their overlay
but do not require an additional copy service. No image or manifest-staging service changes
are needed.

The common shutdown hook deletes the node. For joining control-plane nodes, RKE2 also removes
its etcd membership. Keeping that removed member's local database prevents a fresh rejoin.
GPU agents do not have that database, so their existing shutdown behavior is unchanged.

## Verified Warewulf setting

The built-in ignition overlay already provisions the local filesystems. Enable filesystem
recreation on the **joining node's** rancher partition, not on the bootstrap node:

```sh
wwctl node set <cp-node> --fsname /dev/disk/by-partlabel/rancher --fswipe --yes
wwctl overlay build --workers 1 <cp-node>
```

Inspect the published system overlay's `warewulf/ignition.json` before rebooting. It must
contain `wipeFilesystem: true` only for `/var/lib/rancher`; `/var/lib/kubelet` remains false.
This recreates the entire selected local filesystem on EVERY boot, including etcd, local RKE2
certificates and cached container images. Cluster join inputs remain in the private
operational overlays. NFS storage is not part of this filesystem.

Only the joining control-plane nodes get this setting (their system/runtime overlays are then
rebuilt). Do NOT apply it to the bootstrap control-plane node or a shared all-node profile.

This is a Warewulf node setting consumed by the existing ignition overlay; it is not a
Kubernetes manifest or an image modification. The active node configuration remains on the
Warewulf server. The sanitized record below documents only the relevant setting and is not a
full node import file.

```yaml
<cp-node>:
  filesystems:
    /dev/disk/by-partlabel/rancher:
      format: ext4
      path: /var/lib/rancher
      wipe_filesystem: true
    /dev/disk/by-partlabel/kubelet:
      format: ext4
      path: /var/lib/kubelet
```

## Canary evidence (from the verified rollout)

- The initial reboot delivered all 24 manifests and completed all six Ansible playbooks, but
  rejoin failed because the old etcd member database survived. No shutdown script was changed.
- After enabling filesystem wiping and rebuilding the overlay, the second reboot changed both
  boot ID and filesystem UUID. RKE2 rejoined successfully; the node was Ready and all etcd
  endpoints passed health checks. All 24 manifests and six playbooks matched the operational
  sources. The gateway replicas remaining on the other control-plane nodes stayed Ready
  throughout.
- A second joining node subsequently passed the same test after sequential graceful
  evacuation of its gateway replicas: filesystem UUID changed, re-registered Ready, etcd
  healthy, manifests + playbooks matched, firstboot completed. Filebeat configuration/output
  checks passed with acknowledged delivery counters; Zabbix Agent 2 and SSSD were active.
  Public addresses and routes remained correct (per-node public IP in the VIP's prefix,
  public gateway at route metric 50 with the private fallback at metric 100).

## Before rebooting a control-plane node

1. Gracefully evacuate serving pods from the node (the gateway replicas tolerate this — keep
   the quorum of replicas available on the remaining nodes).
2. Verify the remaining etcd members are healthy.
3. Reboot one node at a time; require explicit firstboot success and full node/network
   recovery before moving to the next.
