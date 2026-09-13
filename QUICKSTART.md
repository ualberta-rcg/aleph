# Aleph Quickstart

What you need to deploy Aleph, and the shortest path through it. For what Aleph is, see the
[README](./README.md); for the deep operational docs, see the pointers at the end.

## What you're deploying

One Kubernetes cluster that self-installs a complete inference platform when its nodes boot.
Nodes are **stateless** — Warewulf boots them over the network from a central image — and
the entire serving stack arrives as RKE2 auto-deploy manifests. You bring hardware, one
file share, a network plan, and a short list of values and secrets.

**The systems involved, and what each needs from you:**

| System | Role | What it needs from you |
|---|---|---|
| [Warewulf 4](https://warewulf.hpcng.org/) | Stateless node provisioning (PXE) | A WW server (assumed running — see their docs) on a network with DHCP/TFTP/PXE reachability to the nodes |
| [RKE2](https://docs.rke2.io/) | Kubernetes | TCP 6443 + 9345 open on control-plane; TCP 2379–2380 between control-plane nodes (etcd); UDP 8472 between **all** nodes (VXLAN) |
| [HAMi](https://github.com/Project-HAMi/HAMi) | GPU sharing/scheduling | NVIDIA driver on the host (baked in the base image); k8s version token must match the image exactly |
| NFS subdir provisioner | Model weights, key store, usage logs | **One NFS export**, ReadWriteMany, reachable (TCP 2049) from every node; a few TB for a real catalog |
| [MetalLB](https://metallb.universe.tf/) | Floating service IP (the edge VIP) | One spare IP on a subnet/L2 segment all control-plane nodes share |
| [Traefik](https://traefik.io/) | TLS edge | A DNS hostname pointing at the VIP; TCP 80/443 on the VIP |
| [cert-manager](https://cert-manager.io/) + Let's Encrypt | Certificates | Port 80 reachable by the ACME server (**public** deployments) — or an internal CA (**private** is fine) |
| [Tyk](https://tyk.io/) + Redis | API-key auth | A fresh admin secret from you; keys persist on the NFS share |
| [Istio](https://istio.io/) + [Knative](https://knative.dev/) + [KServe](https://kserve.github.io/) | Serving, scale-to-zero | Nothing — installed and wired automatically |
| model-gateway | The OpenAI/Anthropic-compatible API | Nothing — deployed from the manifests |

## Requirements

**Compute** (VMs are fine everywhere; they're a great fit for the control plane — physical
boxes work too):

| Role | Count | Minimum | Notes |
|---|---|---|---|
| Control plane | 1 (lab) or 3/5 (HA, odd) | 4 cores, 8–16 GB RAM, ~100 GB | No GPUs. etcd wants a low-latency disk |
| GPU workers | 1+ | NVIDIA GPU(s), ~8 cores, 32+ GB RAM | Stateless — capacity is added by booting more nodes with the GPU profile |
| Warewulf server | 1 | 2 cores, 8 GB RAM | Assumed to exist; runs the DHCP/TFTP/PXE provisioning side |
| NFS server | 1 | TB-scale | One export, RWX |

**Storage:** one NFS export. Roughly one PVC per model (10s of GB each) plus two platform
PVCs (API keys, usage ledger). Weights persist while idle models scale to zero — storage is
the catalog, not the running set.

**Networking to plan:**
- A **boot network** the WW server controls (DHCP/TFTP/PXE to the nodes)
- A **cluster network** connecting all nodes (RKE2 ports above; MTU 9000 if you have it)
- The **edge**: one VIP (MetalLB floats it across control-plane nodes in HA) + a DNS
  hostname → VIP. **Private is fine** (internal CA; clients reach it by hostname on your
  network). **Public works too** (real Let's Encrypt certificates; needs port 80 reachable
  from the internet for issuance)
- NTP on all nodes (chrony is baked in)

**Values and secrets** — the one config artifact is `ww-overlays/site.env.example`: copy it
to `site.env`, fill in your values (k8s version — **must match the base image exactly** —
NFS server/path, VIP, public NIC + per-control-plane IPs, hostname, ACME email), and
substitute the `__TOKENS__` into the control-plane overlay (the file contains the sed
loop). Secrets: a **fresh Tyk admin secret**, a HuggingFace token (weights), optionally an
NGC key (NIM models). Full token list: [docs/SITE-VALUES.md](./docs/SITE-VALUES.md).

**Site playbooks (required input):** first boot runs six Ansible playbooks that must exist
on your Warewulf server — `03-install-packages`, `09-register-dns`, `10-install-sssd`,
`11-create-users`, `33-install-zabbix`, `34-install-filebeat` (site packages, DNS
registration, directory auth, users, monitoring). Author or stub them (a stub must exit 0);
boot fails if one fails. Aleph's common overlay overrides the packages one.

## Minimal vs HA

- **Minimal (lab):** 1 control plane, private network, internal CA. Fine for evaluation —
  reboots of that node are scheduled outages; scale the gateway Deployment to 1.
- **HA (production):** 3 or 5 control planes (odd). Any single node can fail or be
  maintained without downtime: etcd keeps quorum, the VIP floats, gateway replicas spread
  across nodes. VMs or physical both fine.

## Steps

1. **Import the base image** on the WW server (Ubuntu + NVIDIA driver + RKE2, kernel
   included):
   ```bash
   wwctl image import --build --force docker://<image-tag> rke2-hami
   ```
   (Build your own from [warewulf-rke2-hami](https://github.com/ualberta-rcg/warewulf-rke2-hami) if you need different driver/kernel pins.)
2. **Install the Aleph overlays** into the WW overlay tree — `overlays/control-plane/` →
   control-plane nodes, `overlays/common/` → all nodes, `overlays/gpu-worker/` → GPU
   workers (mapping: [docs/WW-OVERLAYS.md](./docs/WW-OVERLAYS.md)). Check directory modes
   are 0755 — Git does not record them, and 0750 breaks APT at first boot.
3. **Fill site.env and substitute the tokens** into the control-plane overlay (per-node
   public IP for the netplan, if you use the HA/public edge).
4. **Define nodes** in wwctl: profiles for control-plane vs GPU roles, one IP per node, a
   shared cluster join token.
5. **Boot** the first control-plane node (it initializes the cluster and stages the
   manifests), then any other control-plane nodes, then the GPU workers.
   Verify as each comes up:
   ```bash
   kubectl get nodes                 # expect Ready, one at a time
   kubectl get node <gpu-node> -o jsonpath='{.status.allocatable.nvidia\.com/gpu}'   # HAMi slots
   ```
6. **Post-boot** essentials:
   ```bash
   kubectl create secret generic hf-token -n models --from-literal=token="$HF_TOKEN" --dry-run=client -o yaml | kubectl apply -f -
   # On a control-plane node:
   tyk-admin.sh add-user <identity>          # mint an API key
   bash ww-overlays/post-deploy/verify-test-model.sh cpu   # smoke test
   ```
   The certificate is issued automatically once DNS → VIP and port 80 work. Key/identity
   model: [docs/TYK-USERS.md](./docs/TYK-USERS.md).

**Boot acceptance:** firstboot playbooks all completed, every node `Ready`, GPU nodes
report `nvidia.com/gpu` allocatable, `kubectl get sc nfs-models -o jsonpath='{.mountOptions}'`
is non-empty, and `https://<hostname>/` serves the landing page.

## First model

```bash
kubectl apply -f models/<model>/pvc.yaml
kubectl apply -f models/<model>/inferenceservice.yaml
kubectl apply -f models/<model>/details.yaml     # the card — catalog entry appears live
GW_URL=https://<hostname> TYK_KEY=<key> MODEL=<model> python3 models/<model>/test.py
```

Apply each file separately. The model's `README.md` is its status record — keep it current
(works / quirks / in-progress). Directory contract and GPU rules:
[models/CLAUDE.md](./models/CLAUDE.md).

## Pointers

- [docs/WW-OVERLAYS.md](./docs/WW-OVERLAYS.md) — overlay structure + full manifest index
- [docs/SITE-VALUES.md](./docs/SITE-VALUES.md) — every token, where it lands
- [docs/ENDPOINTS.md](./docs/ENDPOINTS.md), [docs/TYK-USERS.md](./docs/TYK-USERS.md), [docs/LOGGING.md](./docs/LOGGING.md) — API surface, keys, usage ledger
- [warewulf-rke2-hami](https://github.com/ualberta-rcg/warewulf-rke2-hami) — base image build internals
- Upstream: [Warewulf docs](https://warewulf.hpcng.org/docs/) (server bring-up), [RKE2 requirements](https://docs.rke2.io/install/requirements) (full port matrix)
