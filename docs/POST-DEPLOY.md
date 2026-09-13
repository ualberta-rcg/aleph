# Aleph post-deploy steps

These are the few steps that can't be auto-deployed by RKE2 — either because they are
site-specific fill-ins that need external prereqs (DNS, port 80) or because they are
one-time verifications.

**Everything else is fully automated.** Once the Warewulf image is baked with the tokens
filled in `ww-overlays/overlays/` and nodes are provisioned, the entire platform comes up:
MetalLB, Traefik edge, Tyk, NFS, cert-manager, Istio, Knative, KServe, and the model-gateway.

## 1. Issue a Tyk API key (required to use the gateway)

`tyk-admin.sh` is baked onto every control-plane node at `/usr/local/bin`. On any
control-plane node:

```bash
# Mint a key (prints the key string once — save it; Tyk stores hashes only):
KEY=$(tyk-admin.sh add-user <identity> [account] [type])
#   identity = service name or cluster username
#   account  = fairshare bucket   (default: identity)
#   type     = service | user     (default: service)

tyk-admin.sh validate-key <identity> "$KEY"   # sanity check
```

Identity lives on the key as `alias` + tags (`account:<x>`, `type:<service|user>`) — NOT
`meta_data` (Tyk OSS wipes it on first request). For day-2 key management see
[`../TYK-USERS.md`](../TYK-USERS.md).

If your site runs the login-node PAM hook, personal keys are minted automatically into
`~/.aleph_tyk.env` on every SSH login — manual minting is then only for services and admins.

## 2. Smoke-test the stack

```bash
export TYK_KEY=<from above>
bash ww-overlays/post-deploy/verify-test-model.sh cpu    # CPU path (~2 min)
bash ww-overlays/post-deploy/verify-test-model.sh gpu    # GPU + HAMi path (~5 min)
bash ww-overlays/post-deploy/verify-test-model.sh cleanup
```

## 3. Add models

For each model, apply its files (each in its own `kubectl apply`; the gateway picks the card
up via K8s watch within seconds — no gateway restart needed):

```bash
kubectl apply -f models/<model>/pvc.yaml
kubectl apply -f models/<model>/inferenceservice.yaml
kubectl apply -f models/<model>/details.yaml
kubectl get isvc <model> -n models -w    # wait for Ready
```

## 4. Bake the node-deregister SSH keys (stateless rejoin cleanup)

On shutdown each node SSHes a control-plane node to delete its own stale `Node` object so it
rejoins clean. The repo ships a **DUMMY** key pair; swap in a real one at bake (real keys
live outside the repo).

```bash
# Generate a real key pair once (keep it OUT of the repo, e.g. in your secure key dir):
ssh-keygen -t ed25519 -N '' -C aleph-node-deregister \
  -f <your-secure-key-dir>/deregister/id_ed25519

# Private half -> common overlay (all nodes):
cp <your-secure-key-dir>/deregister/id_ed25519 \
   ww-overlays/overlays/common/etc/rke2-deregister/id_ed25519
chmod 600 ww-overlays/overlays/common/etc/rke2-deregister/id_ed25519

# Public half -> control-plane overlay, kept restricted to the delete wrapper:
printf 'command="/usr/local/sbin/deregister-node.sh",restrict %s\n' \
  "$(cat <your-secure-key-dir>/deregister/id_ed25519.pub)" \
  > ww-overlays/overlays/control-plane/etc/ssh/deregister.authorized_keys
```

Then re-bake. Head nodes are auto-detected at runtime from the RKE2 agent load-balancer
config, so nothing needs an IP. Verify the path from a worker WITHOUT deleting a real node
(bogus name + the wrapper's `--ignore-not-found` makes it a no-op):

```bash
HEAD=$(ssh <worker-node> "grep -oE '\"[0-9.]+:[0-9]+\"' \
  /var/lib/rancher/rke2/agent/etc/rke2-agent-load-balancer.json | tr -d '\"' | sed 's/:.*//' | head -1")
ssh <worker-node> "ssh -i /etc/rke2-deregister/id_ed25519 \
  -o BatchMode=yes -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null \
  root@$HEAD 'zzz-fake-node'"            # -> deregister-node: deleting node 'zzz-fake-node'
```

The server-guard toggle and an optional manual `HEAD_NODES` override live in
`ww-overlays/overlays/common/etc/default/rke2-deregister` (detection is the default).

## 5. TLS certificate

With DNS pointing the public hostname at the VIP and Traefik exposing port 80, cert-manager
issues the real certificate automatically from the shipped ClusterIssuer (ACME HTTP-01) —
verify with `kubectl get certificate -n tyk` (Ready=True). To serve **additional** hostnames,
fill in and apply the example:

```bash
kubectl apply -f ww-overlays/post-deploy/certificate.example.yaml
```

## Nothing else needed

The following are fully managed by the WW-overlay manifests — no manual kubectl required:
- MetalLB install + VIP pool + L2 advertisement, Traefik public service + edge routes
- Tyk OSS + Redis install, env config, API-def ConfigMap mount
- model-gateway Deployment + RBAC + Service
- cert-manager + ClusterIssuer
- NFS StorageClass
- HAMi vGPU scheduler + device plugin
- Istio + Knative + KServe bootstrap
