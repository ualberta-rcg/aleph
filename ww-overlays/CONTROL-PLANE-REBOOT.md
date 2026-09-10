# Aleph joining control-plane reboot

## Existing design

Aleph1 applies manifests cluster-wide using the existing rke2-head2 manifest-copy service. Aleph2/3 receive the same YAML through rke2-aleph but do not require an additional copy service. No image or manifest-staging service changes were made.

The common shutdown hook deletes the node. For joining control-plane nodes, RKE2 also removes its etcd membership. Keeping that removed member's local database prevents a fresh rejoin. GPU agents do not have that database, so their existing shutdown behavior is unchanged.

## Verified Warewulf setting

The built-in ignition overlay already provisions the local filesystems. Enable filesystem recreation on the joining node's rancher partition, not on the bootstrap node:

```sh
wwctl node set aleph3 --fsname /dev/disk/by-partlabel/rancher --fswipe --yes
wwctl overlay build --workers 1 aleph3
```

Inspect the published system overlay's `warewulf/ignition.json` before rebooting. It must contain `wipeFilesystem: true` only for `/var/lib/rancher`; `/var/lib/kubelet` remains false. This recreates the entire selected local filesystem on EVERY boot, including etcd, local RKE2 certificates and cached container images. Cluster join inputs remain in the private operational overlays. NFS storage is not part of this filesystem.

As verified on 2026-09-10, this setting is enabled on aleph2 and aleph3, and their system/runtime overlays have been rebuilt. Both passed their reboot tests. Aleph1 is unchanged. Do not apply it to aleph1 or a shared all-node profile.

This is a Warewulf node setting consumed by the existing ignition overlay; it is not a Kubernetes manifest or an image modification. The active node configuration remains on the Warewulf server. The sanitized record below documents only the relevant setting and is not a full node import file.

```yaml
aleph3:
  filesystems:
    /dev/disk/by-partlabel/rancher:
      format: ext4
      path: /var/lib/rancher
      wipe_filesystem: true
    /dev/disk/by-partlabel/kubelet:
      format: ext4
      path: /var/lib/kubelet
```

## Canary evidence

The initial reboot delivered all 24 manifests and completed all six Ansible playbooks, but rejoin failed because the old etcd member database survived. No shutdown script was changed.

After enabling filesystem wiping and rebuilding the overlay, the second reboot changed both boot ID and filesystem UUID. RKE2 rejoined successfully; aleph3 was Ready and all three etcd endpoints passed health checks. All 24 manifests and six playbooks matched the operational sources. The three gateway replicas remained Ready on the other control-plane nodes during this recovery.

Before any further control-plane reboot, gracefully evacuate serving pods and verify the remaining etcd members are healthy. Reboot one node at a time. Require explicit firstboot success and full node/network recovery before moving to another canary.

Aleph2 subsequently passed the same test after sequential graceful evacuation of its two gateway replicas. Its Rancher filesystem UUID changed, it re-registered Ready, all three etcd endpoints were healthy, and all 24 manifests plus six playbooks matched Warewulf. Firstboot completed successfully on both nodes. Filebeat configuration/output checks passed on both, with acknowledged delivery counters; Zabbix Agent 2 and SSSD were active. Their public addresses remained 129.128.190.68/28 and 129.128.190.69/28, respectively, using gateway 129.128.190.65 with metric 50 and private fallback metric 100.
