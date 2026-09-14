# Tyk users and API keys

Tyk authenticates Aleph API requests, applies key rate limits, and passes caller
identity to the model gateway. Operators manage keys with the control-plane
`tyk-admin.sh` command. Researchers use the resulting key; they do not need
Kubernetes or Tyk administration access.

## Current configuration

Verified on the control plane on **2026-09-13**: the installed
`/usr/local/bin/tyk-admin.sh` matches the
[repository overlay source](../ww-overlays/overlays/control-plane/usr/local/bin/tyk-admin.sh)
byte for byte. The route flags below were checked against the live API definitions.
No user sessions, key values, or Redis contents were inspected.

| API | Listen path | Authentication | Rate limits | Cumulative quotas |
|---|---|---|---|---|
| `model-gateway` | `/v1/` | Key required | Enabled | Disabled |
| `model-anthropic` | `/anthropic/` | Key required; prefix stripped | Enabled | Disabled |
| `model-web` | `/` | Keyless | Disabled | Disabled |

The edge path is MetalLB → Traefik/TLS → Tyk → model-gateway. Tyk's services are
ClusterIP, including the legacy-named `tyk-gateway-nodeport`. Do not infer public
exposure from that name. The keyless root definition is a catch-all, not a
proof that every route except the landing page requires authentication.

## Identity belongs to the key

| Value | Durable session field |
|---|---|
| Researcher or service identity | `alias` |
| Account/group for accounting | `account:<value>` tag |
| Caller type | `type:user` or `type:service` tag |

The helper also fills `meta_data`, but identity handling relies on alias and tags:
the recorded Tyk behavior can discard metadata when a session is updated.
Middleware normalizes authentication and injects `X-Aleph-Identity`,
`X-Aleph-Account`, and `X-Aleph-Identity-Type` for usage attribution.

A shared application's key identifies the application, not each person using it.
The model gateway trusts this authentication layer; do not expose a bypass path
as though it provided the same identity checks.

## Use a key

For Vulcan access and automatic key provisioning, follow the
[Alliance Aleph guide](https://docs.alliancecan.ca/wiki/aleph). In a shell where
your client key is exported as `TYK_KEY`, check the catalog:

```bash
curl --silent --show-error --fail-with-body --max-time 120 \
  -H "Authorization: Bearer $TYK_KEY" \
  https://inference.vulcan.alliancecan.ca/v1/models
```

The authentication middleware also accepts raw `Authorization`, `x-api-key`,
`api-key`, `x-goog-api-key`, and the legacy query parameters `api_key`, `api-key`,
or `key`. Prefer a header. API authentication compatibility does not mean every
client feature or model capability is supported; see [Endpoints](ENDPOINTS.md).

## The operator command

Run `tyk-admin.sh` on a control-plane node with administrative Kubernetes access.
It discovers `kubectl`, obtains the Tyk admin secret from the configured Kubernetes
Secret, and resolves the internal service endpoint. The current installation
uses its ClusterIP fallback; the helper still contains a legacy LoadBalancer lookup.
There is no need to print the secret or paste it into a raw admin-API command.

| Command | Behavior |
|---|---|
| `add-user <identity> [account] [type]` | Creates an additional key and prints it. It does not rotate an existing key. |
| `validate-key <identity> <key-or-hash>` | Checks that a session with access rights belongs to the identity; prints true/false and returns success/failure. It does not test model inference. |
| `update-user <identity> [account] [type]` | Creates a new key first, then attempts to revoke other keys for that identity. |
| `list-user <identity>` | Prints matching hashes, identity, account, and type; does not recover raw key strings. |
| `invalidate-key <key-or-hash>` | Attempts to revoke one key. |
| `invalidate-user <identity>` | Attempts to revoke all keys for the identity. |
| `grant-api <api-id> [api-name]` | Adds missing API access to existing keys across the key store; this is a bulk operation. |

Account defaults to the identity; type defaults to **service**, including during
rotation. Supply both explicitly to preserve a user's intended account and type.
Examples use fictitious identities and capture the returned key without printing it:

```bash
KEY=$(tyk-admin.sh add-user example-user example-project user)
NEW_KEY=$(tyk-admin.sh update-user example-user example-project user)
SERVICE_KEY=$(tyk-admin.sh add-user example-service example-project service)
```

Deliver keys through your private credential workflow. Creation and rotation return
raw keys because clients need them; personal provisioning can store a key in the
user's private environment file. Do not claim that raw keys never exist outside
the mint response.

The script classifies arguments of 40 characters or fewer as hashes when looking
up or revoking one key. Some revoke paths suppress request failures; the reported
count is not an independently verified revocation result. Verify an authorized
rotation/revocation before relying on it to remove access.

## New-key limits and access

These are defaults in the verified helper, not an audit of all existing keys:

| Setting | New user key | New service key |
|---|---|---|
| Rate | 300 requests per 60 seconds | 100000 requests per 60 seconds |
| Expiry | No expiry (`expires: 0`) | No expiry (`expires: 0`) |
| Cumulative quota | Disabled (`quota_max: -1`) | Disabled (`quota_max: -1`) |
| API access | `model-gateway` and `model-anthropic` | Both APIs |

The service limit is high, not literally unlimited. Rate/per are included at the
session level and in both API access blocks. Setting the helper's `API_ID`
variable does not change which APIs `key_body()` grants.

The August 26 changelog supersedes the older 60/minute policy. The August 25
entry explains another important behavior: **do not GET a Tyk session and PUT
that response back unchanged**. Runtime allowance/quota fields can be hydrated
with values unsuitable for writing back. `grant-api` builds a reduced session,
cleans nested limits, uses `suppress_reset=1`, and skips keys that already have
the requested API. It is not a general rate-limit repair command.

## Provisioning integration

The login-node provisioning hook is separate from the key store and is not
included in this repository. The optional overlay
[`tyk-pam-cmd`](../ww-overlays/overlays/control-plane/usr/local/sbin/tyk-pam-cmd)
is a restricted SSH command wrapper: it permits add, update, and validation,
forces `account=identity` and `type=user`, and calls `tyk-admin.sh`. Deploying the
wrapper alone does not install or prove a working PAM hook.

The admin script's old comment saying keys are created only by hand does not
describe this integration. Read the implementation and the deployment's access
configuration rather than treating that comment as current system state.

## State, audit, and configuration ownership

Tyk stores hashed key sessions in Redis; the checked deployment has
`TYK_GW_HASHKEYS=true` and `TYK_GW_HASHKEYFUNCTION=murmur128`. Preserve Redis data
and its private recovery process. The Redis pod uses PVC
`redis-data-tyk-redis-master-0` in namespace `tyk`, bound to
`pv-tyk-redis-data` with reclaim policy `Retain` (verified 2026-09-13).
This is an explicit existing-volume binding, rather than a newly provisioned
`nfs-models` volume. Sessions include identity, API access, and configured limits;
Redis also supports rate-limit counters. This is separate from the gateway usage
ledger and the admin audit file below. See
[Warewulf storage](WW-OVERLAYS.md#storage-setup-and-recovery) for binding and recovery.
An overlay reconstructs configuration, not the
sessions or the client-side raw key files.

`tyk-admin.sh` writes a separate administrative audit file, defaulting to
`/var/log/aleph/tyk-admin.log`. Records contain timestamp, operator/host, action,
identity, and action details. Validation calls are logged too. Single-key
invalidation includes the first eight characters of the supplied key or hash.
Writes are best-effort; the script does not implement rotation or guaranteed
delivery. This is not the gateway's persistent per-request usage ledger; see
[Logging and metrics](LOGGING.md).

Configuration overrides are `TYK_URL`, `TYK_SECRET`, `AUDIT_LOG`, and `KUBECTL`.
Keep real values in private configuration. The owning overlay manifests are
`51-tyk.yaml` (deployment/mounts), `53-tyk-api-definitions.yaml` (routes), and
`54-tyk-middleware.yaml` (middleware). The API definitions and middleware mount at
`/opt/tyk-gateway/apps` and `/opt/tyk-gateway/middleware`; the chart also supplies a
scratch mount under `/mnt/tyk-gateway`. Review the effective override when debugging
an empty API catalog. See [Kubernetes](KUBERNETES.md#bootstrap-and-request-path-diagnostics)
and [Warewulf](WW-OVERLAYS.md) for platform and overlay concerns.
