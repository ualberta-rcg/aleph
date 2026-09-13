# Aleph rack boot setup

Aleph GPU racks use the `rke2-aleph-common` and `rke2-aleph-gpu` Warewulf profiles.
Control-plane nodes also use the separate `rke2-aleph` manifest overlay. The common
overlay's directory permissions must allow normal unprivileged system execution:

```sh
chmod 0755 /var/lib/warewulf/overlays/rke2-aleph-common/rootfs/usr \
  /var/lib/warewulf/overlays/rke2-aleph-common/rootfs/usr/local \
  /var/lib/warewulf/overlays/rke2-aleph-common/rootfs/usr/local/bin
```

Git records file executable bits, but does not record directory modes. Preserve these modes
when copying the files into Warewulf. A mode of 0750 on `/usr` prevents APT's unprivileged
signature checker from executing `apt-key`, even when that executable itself is 0755. Check
the built system archive's directory entries before rebooting.

The common overlay's `etc/ansible/playbooks/03-install-packages.yaml` overrides the shared
package playbook for Aleph. It removes the unused CVMFS repository file `cernvm.list`, then
performs the existing package setup. The other five generated playbooks remain unchanged.
This does not edit the shared non-Aleph playbook or the base image.

At rejoin, `gpu-autolabel` detects NVIDIA hardware and applies `gpu=on`. That label enables
HAMi, the hardware labeler and RDMA. Check the actual GPU devices, the `aleph.gpu/count`
label, HAMi availability, and RDMA resources. HAMi's advertised `nvidia.com/gpu` count is
its configured sharing-slot count (slices per card × cards), not the number of physical GPUs.

Require successful completion of all six firstboot playbooks as well as Kubernetes Ready.
Verify Filebeat config/output and acknowledged deliveries, Zabbix Agent 2, SSSD, and
wwclient. Preserve PVC data and use normal graceful pod evacuation for reboot tests.

Reboot a **canary worker first** (a physical server — allow its POST and network boot to
finish). Warewulf's `wwctl node status <worker>` reports the most recent provisioning stage.
A successful node rejoin does not imply that the separate firstboot playbooks succeeded.

## Verified result (from the canary rollout, 2026-09-10)

After correcting the directory modes and package playbook, the worker canary passed a fresh
reboot: all six playbooks completed, the CVMFS repository was absent, the node rejoined
Ready, and `gpu=on` plus hardware labels appeared automatically. HAMi and RDMA were ready.
Filebeat connected to Logstash and reported acknowledged deliveries; Zabbix Agent 2, SSSD,
and wwclient were active. All six playbook hashes and six checked non-secret common/GPU file
hashes matched their operational sources.

The corrected package playbook SHA256 is
`1510db0d53490dc7170f7d0975b760abfb8fed67f8e795e8a930265756e2caef` (verify it after copying
into Warewulf). After the canary passed, every Aleph node's published system/runtime
overlays were rebuilt and validated; only the authorized control-plane canaries and the
worker canary were actually rebooted.
