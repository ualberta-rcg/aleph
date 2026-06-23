# Node + VIP overlay for MetalLB (per-site — NOT auto-deployed by RKE2)

These are **node-level and per-cluster configs**, NOT RKE2 auto-deploy manifests —
RKE2 does not apply them. They live outside `../rke2-manifests/` on purpose (so a
bulk-copy of the manifests dir to `/etc/rancher/manifests/` can't accidentally feed
netplan/sysctl YAML to the k8s API). Bake them into the Warewulf image overlay for
the head/edge nodes (Karim), or apply manually.

**Everything here is site-specific** — substitute your VIP, subnet, gateway, and
public NIC name. These files implement the proven MetalLB L2 recipe (cluster 230,
2026-06-22; see memory `metallb-public-vip-recipe`): a public VIP on an **unnumbered**
public NIC, using **destination routing** (not source-policy — kube-proxy rewrites the
reply's source to the VIP only in POSTROUTING, *after* the routing decision, so
`ip rule from <vip>` never fires) and `rp_filter=0`.

## Files

| File | Target | Purpose |
|---|---|---|
| `netplan/60-public-vip.yaml` | `/etc/netplan/60-public-vip.yaml` (node) | public NIC up, IP-free; VIP as a local address (dummy0); public subnet on-link via the NIC |
| `sysctl.d/99-public-vip.conf` | `/etc/sysctl.d/99-public-vip.conf` (node) | `rp_filter=0`, `arp_ignore=1`, `arp_announce=2` |
| `metallb-vip.example.yaml` | k8s (`kubectl apply`) | the `IPAddressPool` + `L2Advertisement` for your VIP/NIC — copy, fill in, apply per-cluster |

## Site values to substitute (230 examples shown in the files)
- `VIP` — the public IP MetalLB will own (230: `129.128.190.55`).
- `PUBLIC_SUBNET` — the on-link public subnet (230: `129.128.190.48/28`).
- `PUBLIC_GW` — the public gateway (230: `129.128.190.49`).
- `PUBLIC_NIC` — the head's NIC on the public VLAN (230: `enp6s19`).

## Why each piece
- **NIC up + IP-free, VIP on `dummy0`:** no node address on the public VLAN, yet a
  local source address for the VIP so replies egress correctly. (netplan can't
  address `lo`; `dummy0` is the equivalent — fall back to `ip addr add <VIP>/32 dev lo`
  if this netplan rejects `dummy`.)
- **Public subnet on-link via the NIC:** destination routing — replies to public hosts
  route out the NIC by *destination*, which is what actually works (see memory).
- **`rp_filter=0`:** the reverse path for public sources is asymmetric (in the public
  NIC, reverse via the cluster NIC), so any stricter value silently drops inbound.
- **`arp_ignore=1` / `arp_announce=2`:** on a multi-head cluster, only the MetalLB
  leader may answer ARP for the VIP (else every head answers → ARP conflict).

## External (Internet) clients
Same-subnet clients work with the above alone. For Internet clients, additionally
make the public NIC the default gateway (commented block in the netplan: `to: default,
via: <PUBLIC_GW>`). This is safe because the cluster subnet stays on the cluster NIC's
connected route. (Or use BGP for true active/active.)

## Resource caveat
MetalLB's frr is pinned to control-plane nodes by `../rke2-manifests/40-metallb.yaml`.
Size the heads (>=16 vCPU) or use dedicated edge nodes — on the 8-vCPU 230 POC head,
frr + the serving stack starved the control plane (CrashLoop).
