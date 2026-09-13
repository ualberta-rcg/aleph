# Deploy Aleph

This guide outlines a deployment on Warewulf-provisioned RKE2 nodes. It assumes
you administer the provisioning, networking, and storage infrastructure.
To use the existing Vulcan service, follow the
[Alliance Aleph guide](https://docs.alliancecan.ca/wiki/aleph).

## Requirements

| Requirement | What to prepare |
|---|---|
| Provisioning | A working Warewulf installation and a compatible RKE2 node image |
| Compute | Control-plane nodes and NVIDIA GPU workers sized for the models you intend to serve |
| Storage | Persistent NFS storage accessible from the nodes, with capacity for weights and platform data |
| Networking | Node connectivity, a service IP for MetalLB, and a DNS hostname for the API |
| TLS | Certificate configuration for that hostname; the supplied manifests use ACME HTTP-01 |
| Credentials | Cluster join credentials, a Tyk admin secret, and any model-download credentials |
| Site integration | Your node profiles, firstboot playbooks, and private access configuration |

The accompanying [node-image repository](https://github.com/ualberta-rcg/warewulf-rke2-hami)
covers the base image. Match the Kubernetes and driver requirements of the image
and overlays. A smaller evaluation deployment needs adjustments to replica counts
and placement; the supplied configuration is not a universal sizing recommendation.

## 1. Configure a deployment copy

Clone this repository and prepare a private copy of the overlays for your site.
Use `ww-overlays/site.env.example` as the starting point for site values, following
[the token reference](docs/SITE-VALUES.md). Render the placeholders before deployment
and configure node-specific networking separately.

Keep real credentials and rendered files out of Git. Preserve your site's private
SSH and cluster-join configuration when integrating the supplied overlays.

**Choose storage bindings before baking.** The included static PV/PVC manifests
record an existing deployment's storage layout. For a fresh installation, replace
those bindings with your own; changing the NFS address alone is insufficient.
See [storage setup and recovery](docs/STORAGE-RECOVERY.md).

## 2. Provision the nodes

Install the role overlays described in [the overlay guide](docs/WW-OVERLAYS.md),
configure your Warewulf node profiles and firstboot integration, and build the
node overlays. Boot the bootstrap control plane, then the joining control planes
and workers.

The bootstrap node stages the numbered manifests for RKE2 to apply. Provisioning
the platform does not deploy every model in `models/`; add selected models after
the serving components are available.

## 3. Check the platform

Run these commands from an administrative shell with `kubectl` configured for
the target cluster:

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

Confirm that firstboot completed, nodes are Ready, the serving controllers are
healthy, storage claims are Bound, and GPU workers advertise HAMi resources.
Verify DNS and TLS for your API hostname. Gateway readiness also requires at
least one model card and completed Kubernetes discovery, so an empty installation
is not yet a complete end-to-end check.

## 4. Add a model and test the API

Choose a model whose runtime and resource needs fit your deployment. Read its
`README.md` and the [add-model guide](docs/ADD-A-MODEL.md), then create any required
Kubernetes Secrets through your private credential workflow.

From the repository root, apply that model's files individually, including any
supporting ConfigMaps before the InferenceService:

```bash
kubectl apply -f models/<model>/pvc.yaml
# Apply supporting ConfigMaps here if the model requires them.
kubectl apply -f models/<model>/inferenceservice.yaml
kubectl apply -f models/<model>/details.yaml
kubectl get isvc <model> -n models
```

Issue a client key using [the Tyk guide](docs/TYK-USERS.md). With `TYK_KEY` exported
and `GW_URL` set to your HTTPS hostname, check discovery:

```bash
curl --silent --show-error --fail-with-body --max-time 120 \
  -H "Authorization: Bearer $TYK_KEY" "$GW_URL/v1/models?all=true"
```

Run the selected model's documented test through that same endpoint. Follow
cold-start retry guidance and inspect the actual response;
a catalog entry alone does not prove inference works.

The installation is ready for evaluation when an authenticated request reaches
your selected model and returns a valid result. Keep manifests and model notes
current as you make changes; retain storage when replacing model services.
