# Deploy Aleph

This guide walks a deployment on Warewulf-provisioned RKE2 nodes. It assumes you
administer the provisioning, networking, and storage infrastructure. To use the
existing Vulcan service instead, follow the
[Alliance Aleph guide](https://docs.alliancecan.ca/wiki/aleph).

## What you need

| Requirement | What to prepare |
|---|---|
| Provisioning | A working [Warewulf 4](https://warewulf.hpcng.org/docs/) server (DHCP/TFTP/PXE to the nodes) and a compatible RKE2 node image — use the published image from the [node-image repository](https://github.com/ualberta-rcg/warewulf-rke2-hami) or build your own there |
| Compute | Control-plane nodes: **one is enough to evaluate**; **three (odd)** for HA — reboots and node failures then happen without downtime, and the VIP floats between them. No GPUs on the control plane. GPU workers: at least one NVIDIA node, sized for the models you intend to serve (the catalog grows by adding worker nodes) |
| Storage | One NFS export, mounted **ReadWriteMany** from every node. Roughly one PVC per model (small science models a few Gi, large LLMs up to ~200 Gi) plus two platform PVCs (API keys, usage ledger) — a few TB for a real catalog |
| Networking | Node-to-node connectivity (RKE2 ports, VXLAN), a spare **service IP** for the MetalLB VIP, a **DNS hostname** pointing at that VIP, and ports 80/443 reachable by your users (80 also by the ACME server for public TLS) |
| Time | NTP on all nodes (chrony is baked into the image) |

## Accounts and keys

Before deploying, prepare:

- **A HuggingFace account and access token** — required; model init containers
  download weights with it.
- **An NVIDIA NGC account and API key** — only if you will serve NIM-container models;
  NIM images also need an image-pull secret.
- **A fresh Tyk admin secret** — generate a new strong value; never reuse a secret from
  another deployment or from documentation.
- **A DNS record** for your API hostname pointing at the VIP you reserved
  (this hostname is the `INFERENCE_HOST` site value; the TLS certificate is issued for it).

## Gather your values

Two small sets of values drive the whole deployment; both stay **out of Git**:

- **Site values** (in a copy of `ww-overlays/site.env.example`): the Kubernetes version —
  must match the node image **exactly** — NFS server and export path, the VIP, the
  public NIC name, subnet prefix and gateway, each control-plane node's own public IP,
  the API hostname, an ACME contact email, and the GPU workers' RoCE NIC.
  Full token reference: [docs/SITE-VALUES.md](docs/SITE-VALUES.md).
- **Credentials** (in a gitignored `.env` at the repo root): the HuggingFace token,
  the NGC key if used, and the Tyk admin secret — see
  [environment values](docs/SITE-VALUES.md#environment-values-env) for what each is
  for and where it lands.

## 1. Import the node image

On the Warewulf server, import the RKE2 node image (Ubuntu + NVIDIA driver + RKE2; the
node kernel comes from this image):

```bash
wwctl image import --build --force docker://<node-image-tag> rke2-hami
```

To build your own with different driver or kernel pins, use the
[node-image repository](https://github.com/ualberta-rcg/warewulf-rke2-hami).

## 2. Install the Aleph overlays

Install this repository's overlay trees into your Warewulf overlay tree per the
[role layout](docs/WW-OVERLAYS.md#role-layout) (control-plane / all nodes / GPU
workers), and review [the overlay files](docs/WW-OVERLAYS.md#the-overlay-files).
Check directory permissions when copying — Git does not record them, and restrictive
modes on `/usr` break package setup at first boot.

Render the site values into the control-plane overlay (placeholders are documented in
[docs/SITE-VALUES.md](docs/SITE-VALUES.md)); per-node public IPs go into the netplan
file once per control-plane node.

**Choose storage bindings before baking.** The included static PV/PVC manifests record
an existing deployment's storage layout. For a fresh installation, replace those
bindings with your own; changing the NFS address alone is insufficient. See
[storage setup and recovery](docs/WW-OVERLAYS.md#storage-setup-and-recovery).

## 3. Define nodes and boot

In Warewulf, give every node its IP and role:

- **Bootstrap control plane (the head)** — initializes the cluster and stages the
  numbered manifests for RKE2 to apply. Boot this node first and wait for it to be Ready.
- **Joining control planes** — join the head via a shared cluster token. Configure the
  joining-node filesystem wipe described in
  [WW-OVERLAYS](docs/WW-OVERLAYS.md#joining-control-plane-filesystem-configuration)
  so a rejoining node does not keep a removed etcd member's database. Add and boot
  them one at a time.
- **GPU workers** — boot with the GPU role overlay; they self-label `gpu=on`, which
  brings up HAMi GPU scheduling, hardware labeling, and RDMA automatically.

Boot order: head → remaining control planes → workers. Provisioning the platform does
not deploy every model in `models/`; add selected models after the serving components
are available.

## 4. Check the platform

Run these commands from an administrative shell with `kubectl` configured for the
target cluster:

```bash
kubectl get nodes
kubectl get pods -n kube-system
kubectl get pods -n tyk
kubectl get pods -n knative-serving
kubectl get pods -n kubeflow
kubectl get sc nfs-models
kubectl get pvc -n tyk
kubectl get pvc -n models
kubectl get certificates -n tyk
```

Confirm that firstboot completed, nodes are Ready, the serving controllers are healthy,
storage claims are Bound, GPU workers advertise HAMi resources, and DNS/TLS resolve for
your hostname. Gateway readiness also requires at least one model card, so an empty
installation is not yet a complete end-to-end check.

## 5. Post-boot secrets and first key

```bash
# HuggingFace token (required by model init containers):
kubectl create secret generic hf-token -n models \
  --from-literal=token="$HF_TOKEN" --dry-run=client -o yaml | kubectl apply -f -

# NGC (NIM models only) — API key secret plus the image-pull secret:
kubectl create secret generic ngc-api-key -n models \
  --from-literal=NGC_API_KEY="$NGC_API_KEY" --dry-run=client -o yaml | kubectl apply -f -
kubectl create secret docker-registry ngc-registry-secret -n models \
  --docker-server=nvcr.io --docker-username='$oauthtoken' \
  --docker-password="$NGC_API_KEY" --docker-email=you@example.com
```

On a control-plane node, mint the first API key (see
[the Tyk guide](docs/TYK-USERS.md)):

```bash
tyk-admin.sh add-user <identity> [account] [type]
```

## 6. Add a model and test the API

Choose a model whose runtime and resource needs fit your deployment. Read its
`README.md` and the [add-model guide](docs/ADD-A-MODEL.md). From the repository root,
apply that model's files individually, including any supporting ConfigMaps before the
InferenceService:

```bash
kubectl apply -f models/<model>/pvc.yaml
# Apply supporting ConfigMaps here if the model requires them.
kubectl apply -f models/<model>/inferenceservice.yaml
kubectl apply -f models/<model>/details.yaml
kubectl get isvc <model> -n models
```

With `TYK_KEY` exported and `GW_URL` set to your HTTPS hostname, check discovery and
then run the model's documented test through the same endpoint:

```bash
curl --silent --show-error --fail-with-body --max-time 120 \
  -H "Authorization: Bearer $TYK_KEY" "$GW_URL/v1/models?all=true"
```

Follow cold-start retry guidance and inspect the actual response; a catalog entry alone
does not prove inference works. The installation is ready for evaluation when an
authenticated request reaches your selected model and returns a valid result. Keep
manifests and model notes current as you make changes; retain storage when replacing
model services.
