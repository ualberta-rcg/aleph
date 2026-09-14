# Working on Aleph

Aleph is an inference platform built around a FastAPI gateway, KServe/Knative,
Tyk, and Warewulf-provisioned RKE2 nodes with HAMi GPU scheduling.

Read and follow [AGENTS.md](AGENTS.md) for shared repository instructions, then
read the relevant component guide below. Check implementation and manifests
before trusting old notes. Site addresses, access commands, credentials, fleet
inventories, and rollout history belong in the operator's private working directory.

## Where to look

| Work | Guide |
|---|---|
| Overview and installation | [README](README.md), [Quickstart](QUICKSTART.md) |
| Add or update a model | [Model workflow](docs/ADD-A-MODEL.md), [card reference](models/details.md), and the model's own README/CLAUDE notes |
| Gateway implementation and tests | [Gateway reference](gateway/README.md), [gateway instructions](gateway/CLAUDE.md) |
| API behavior | [Endpoints](docs/ENDPOINTS.md) |
| Authentication and key administration | [Tyk](docs/TYK-USERS.md) |
| Usage records, retention, and metrics | [Logging and metrics](docs/LOGGING.md) |
| Overlays, site tokens, and storage bindings/recovery | [Warewulf](docs/WW-OVERLAYS.md) |
| Serving components, networking, scheduling, and lifecycle | [Kubernetes](docs/KUBERNETES.md) |
| Images, boot, systemd, GPU drivers, and RDMA | [System](docs/SYSTEM.md) |

Extend the owning guide when recording reusable findings. Keep model-specific
behavior with that model and date tested results. Keep the essential operator procedures here and detailed explanations in their
owning guides; do not add unrelated Slurm or CVMFS setup to this repo.

## Working rules

- Work within the authorized scope. Repository edits do not themselves authorize
  production deployment, fleet tests, or node maintenance.
- For InferenceService spec updates, delete the service, wait for old predictors
  and revisions to clear, then reapply its YAML. Never patch its spec or delete
  model PVCs. Hiding a catalog card and stopping execution are separate actions.
- Follow the model guide's test/recreate workflow. Do not claim capabilities or
  successful deployment without validation of the final configuration.
- Pin gateway releases to an explicit image version/digest. Authorized deployment
  changes must also reach the boot sources so reprovisioning preserves them.
- Preserve site tokens. Keep credentials and private records out of committed
  files, tool output, and examples; use synthetic examples for documentation.
- Validate documentation links and claims. Use the relevant component tests for
  behavior changes; documentation edits do not require deployment or inference.

## Environment and private configuration

The repository root's hidden `.env` is private and gitignored; `.env.example`
documents its interface. Do not print `.env`, dump the environment, or copy secret
values into commands or documentation. An authorized operator can load a trusted
shell-compatible `.env` in their private shell with tracing disabled:

```bash
set +x
set -a
source ./.env
set +a
```

Sourcing executes shell code: use only trusted configuration. This exports values
for that shell; it does not create Kubernetes Secrets or configure a remote shell.
Agents must follow the session's credential-access rules rather than opening the
file to discover values. Check required variables without displaying them, for
example `test -n "${TYK_KEY:-}"`.

| Purpose | Variables / configuration |
|---|---|
| RKE2 administration | `PATH` includes `/var/lib/rancher/rke2/bin`; `KUBECONFIG=/etc/rancher/rke2/rke2.yaml` in the control-plane admin shell. |
| API calls and model tests | `GW_URL` is the public origin, `TYK_KEY` is a client key, `MODEL` is the public model ID. These may need supplying separately from `.env`. Leave `GW_INSECURE` unset for normal TLS verification. |
| Model downloads | `HF_TOKEN`, and `NGC_API_KEY` where required by the runtime; provision the Kubernetes Secrets referenced by the selected manifests. Local exports alone do not reach pods. |
| Tyk administration | The installed helper discovers `TYK_SECRET` and `TYK_URL`. Optional overrides: `KUBECTL`, `AUDIT_LOG`. `TYK_API_SECRET` is a legacy helper variable, not a client key or the installed helper's automatic fallback. |
| Remote target | `HEAD` in `.env.example` is an operator convenience, not kubectl context selection. Get the actual target/access method from private site notes. |
| Overlay rendering | `ww-overlays/site.env.example` defines `K8S_VERSION`, NFS, public networking, inference hostname, ACME, and RoCE values. Use the Warewulf guide and private rendered configuration; do not put actual site values in Git. |
| Gateway accounting | Deployment variables `GATEWAY_USAGE_LOG`, `GATEWAY_USAGE_LOG_MAX_BYTES`, `GATEWAY_USAGE_LOG_BACKUPS`, and `SITE_NAME`; `POD_NAME` comes from the Downward API. These configure the server, not API clients. |

## Operator starting point

Use private site notes to select the target control plane and access method.
In its authorized administrative shell, configure RKE2 tools if necessary:

```bash
export PATH="$PATH:/var/lib/rancher/rke2/bin"
export KUBECONFIG=/etc/rancher/rke2/rke2.yaml
kubectl config current-context
kubectl get nodes
kubectl get isvc -n models
```

Confirm the target before mutations. Platform source lives in
`ww-overlays/overlays/control-plane/etc/rancher/manifests/`; rendered files stage
at `/etc/rancher/manifests/`, then the bootstrap node supplies RKE2's
`/var/lib/rancher/rke2/server/manifests/`. Model source is `models/<model>/`.
Use the Warewulf guide when changing boot sources; a live-only fix can disappear.

## Tyk keys

Use an existing client key provided through the private credential workflow.
With `GW_URL` set to the public origin (without `/v1`) and `TYK_KEY` supplied
privately, a catalog check is:

```bash
curl --silent --show-error --fail-with-body --max-time 120 \
  -H "Authorization: Bearer $TYK_KEY" "$GW_URL/v1/models"
```

Key administration uses `/usr/local/bin/tyk-admin.sh` on a control plane. It
obtains its admin secret and internal endpoint itself. For an authorized key
change, capture the result privately; do not print it or enable shell tracing.
These are separate operations, with fictitious identities:

```bash
# Create an additional key; this does not revoke existing keys.
KEY=$(tyk-admin.sh add-user example-user example-project user)
# Rotate: create a replacement, then attempt to revoke previous keys.
NEW_KEY=$(tyk-admin.sh update-user example-user example-project user)
```

Always supply account and type: omitted type defaults to `service`, even during
rotation. `validate-key <identity> <key-or-hash>` checks identity/access, not model
inference. `invalidate-key` revokes one; `invalidate-user` attempts all keys for
one identity. Verify revocation because the helper suppresses some delete failures.
`list-user` returns hashes, not recoverable raw keys. `grant-api` changes the key
store in bulk; it is not a routine single-user repair. Never PUT a fetched Tyk
session back unchanged. Read [Tyk](docs/TYK-USERS.md) before administering keys.

Redis holds sessions, identity, access and limits on PVC
`tyk/redis-data-tyk-redis-master-0`. It is separate from token usage history.
The helper's `/var/log/aleph/tyk-admin.log` is a separate administrative audit,
not the gateway ledger. Preserve Redis storage across rebuilds.

## Add or update a model

1. Research the upstream model/runtime and read the closest working model's
   manifests and notes. Work on one model at a time. Verify capabilities and
   resource requirements instead of copying another model's claims.
2. Prepare `pvc.yaml` where needed, `inferenceservice.yaml`, `details.yaml`,
   `test.py`, and a README. Add custom server/configuration files as required.
   Record runtime quirks in the model's own CLAUDE notes. Use the card reference;
   keep gateway capabilities in `behavior` and scaling consistent with the service.
3. Apply storage, then supporting ConfigMaps, then service, then card. Do not
   interrupt weight/environment staging with repeated redeployments or create
   competing writers to shared model storage.
4. Test the real model through the authenticated public API using its battery in
   an appropriate execution environment. Check output validity, errors, and each
   advertised feature. Fix source and retest; do not mark a failed test as passed.
5. Recreate from the final files, preserve weights, repeat tests, and verify the
   intended idle/always-up behavior. Date results and limitations in the model
   README and CHANGELOG before committing. Follow [Add a model](docs/ADD-A-MODEL.md).

## Park, stop, scale to zero, or keep always up

These are different operations. Use the service name from `inferenceservice.yaml`
and card ConfigMap name from `details.yaml`; do not assume they equal the public
model ID. Commands below use `MODEL_DIR`, `ISVC`, and `CARD_CM` set to those values.

| Intent | Required state |
|---|---|
| Park/hide | Remove only the details ConfigMap. Keep service, PVC, and source card. This does not stop compute. |
| Stop execution | Set `serving.kserve.io/stop=true` on the service. Card may remain listed; it cannot wake on demand. |
| Scale to zero when idle | Service `spec.predictor.minReplicas: 0`; card `scaling.scale_to_zero: true`, `scaling.min_replicas: 0`; no stop annotation. Requests can wake it. |
| Always up | Service minimum at least 1; card `scaling.scale_to_zero: false` and matching `scaling.min_replicas`; no stop annotation. Set `maxReplicas` at least as high as the minimum. |

```bash
# Park, or restore the catalog entry:
kubectl delete configmap "$CARD_CM" -n models
kubectl apply -f "$MODEL_DIR/details.yaml"

# Stop, or permit serving again:
kubectl annotate isvc "$ISVC" -n models serving.kserve.io/stop=true --overwrite
kubectl annotate isvc "$ISVC" -n models serving.kserve.io/stop-
```

Each pair shows alternative actions, not a sequence to run together. Persist the
intended stop annotation in the source if it must survive reapplication.

For minimum/maximum replicas, resource requests, image or arguments, edit source
first. **Never patch an InferenceService spec or scale its generated Deployment.**
For an authorized service recreation:

```bash
kubectl delete isvc "$ISVC" -n models
kubectl wait --for=delete pod -n models \
  -l "serving.kserve.io/inferenceservice=$ISVC" --timeout=300s
kubectl get revisions.serving.knative.dev -n models \
  -l "serving.kserve.io/inferenceservice=$ISVC"
# Proceed only after old predictor pods AND revisions have cleared.
kubectl apply -f "$MODEL_DIR/inferenceservice.yaml"
# Apply the card only if the model should be listed.
kubectl apply -f "$MODEL_DIR/details.yaml"
```

Stop on a failed wait; inspect remaining resources before reapplying. Preserve
PVCs. Do not take the entire gateway down for a routine single-model change.
For a separately authorized fleet operation requiring gateway suspension, record
and restore its actual desired replica count; never assume a fixed count.

Verify an always-up model becomes Ready and completes a request. For scale-to-zero,
allow the configured idle window, confirm predictor pods disappear, then verify
wake-up and eventual success. `minReplicas: 0` does not force an immediate stop.
Cold-start `503`/retry guidance and unavailable capacity are distinct from runtime
failure. Check the Knative initial-scale finding in [Kubernetes](docs/KUBERNETES.md)
when validating a new deployment.

The local workspace's older scaling one-offs and the removed `test-model.sh`
helper are historical, not the current procedure: the helper's `zero` action
scaled a generated Deployment directly, `up`/`curl` used an internal gateway
path, and its recreation could continue after its wait loop.

## HAMi troubleshooting and GPU usage

Start with [HAMi diagnostics](docs/KUBERNETES.md#hami-diagnostics). Check physical
GPU visibility on the worker, `gpu=on` labeling, NVIDIA runtime and device-plugin
health, then scheduler events and the model's resource requests. Sharing slots
are not physical GPUs. Whole-device models omit `nvidia.com/gpumem`; shared models
request it in MiB alongside GPU count. Do not restore obsolete near-full-memory
values as a workaround for whole-device allocation.

Old revisions can retain capacity; multiple free sharing slots do not establish
that enough whole GPUs are available on a suitable node. Runtime OOM, image pulls,
NFS staging, and RDMA provider failures need different fixes from scheduling.

For physical utilization and VRAM, use the bounded worker-side measurement in
[Logging and metrics](docs/LOGGING.md#measure-physical-gpu-usage). For allocation,
inspect model/pod resource requests and HAMi assignment. For estimated per-request
GPU time, use `derived.gpu_seconds` in the ledger. Do not equate these quantities.

## Token usage history

Historical token consumption comes from the JSONL usage ledger, not Redis,
`kubectl logs`, or current Prometheus counters. The supplied deployment mounts
PVC `models/model-gateway-usage-logs` at `/var/log/aleph` with a per-pod subdirectory;
the file is `usage.log`, with rotated `usage.log.1` through `.5` by default.
A running pod sees only its own subdirectory. Retired pod directories also matter.

For an authorized report, follow [operator reporting](docs/LOGGING.md#operator-token-history):
select identity/account and UTC time range, access a read-only view of the full
retained ledger, include all relevant replica directories and rotations once,
and aggregate on the cluster. Return the scoped summary, not raw records or key
fingerprints. State retention gaps and missing backend token counts. Shared keys
attribute usage to the service, not individual people behind it. Conversation
text is not recoverable from this ledger.

## Changelog before every commit

Every repository change—including documentation, comments, and typos—requires a
**dated entry in CHANGELOG.md before committing**, staged in the same commit.
There are no exceptions for small edits. Group related edits into one logical
change and keep entries newest first. Record what changed, why, operational
impact, validation performed, and any incomplete or unverified work. Distinguish
committed changes from deployed changes and historical tests from live checks.

## Preserve README customizations

Keep the README's original header and branding: logos, title, badges, tagline,
institutional attribution, and maintainer names/links. Preserve the Markdown/Mermaid
architecture diagrams and the closing References, Support, License, and About
University of Alberta Research Computing sections, including their exact wording
and links. Update technical sections around these customizations; do not replace
the README wholesale. Change a protected part only when the user explicitly
requests that particular change. The historical baseline is commit e8e6777
(2026-09-10) for the branding and closing sections; retain the subsequently added
Aleph logo. The user approved centered logos and Mermaid architecture diagrams
on 2026-09-13. Keep the request-flow and provisioning/placement diagrams, including
GPU workers and shared NFS storage, as editable markup. Do not replace them with
images unless the user explicitly requests that format.
