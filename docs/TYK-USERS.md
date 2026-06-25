# Tyk Users & API Keys

How identity and API keys work for the Aleph model gateway: how to create, validate,
rotate, and revoke keys, what conventions clients can use to send them, and how
identity flows into usage accounting.

See also: [LOGGING.md](LOGGING.md) (usage/accounting), [RUNBOOK.md](RUNBOOK.md)
(operations), and `gateway/README.md`.

## The request path

```
client ──► MetalLB VIP :80 ──► Tyk OSS ──► model-gateway :8080 ──► KServe/vLLM pod
                                 │
                                 ├─ normalizeAuth (pre):  accept key in any form → Bearer
                                 ├─ standard token auth:  validate the key (Redis)
                                 └─ injectIdentity (post): X-Aleph-* headers from key alias/tags
```

Tyk is the only authenticated entrypoint. The gateway itself is a ClusterIP with
no auth — it trusts the `X-Aleph-*` headers Tyk injects (and Tyk strips any
client-supplied `X-Aleph-*` first, so they cannot be spoofed).

## Identity model

Tyk OSS has no "user" object — identity lives **on the key**:

| Field | Stored as | Example | Notes |
|---|---|---|---|
| identity | key **alias** | `openwebui`, `jdoe` | service name OR LDAP username |
| account | tag `account:<x>` | `account:shared-pool` | fairshare/billing bucket; defaults to identity |
| identity_type | tag `type:<x>` | `type:service` / `type:user` | `service` for shared apps, `user` for a person |

> We deliberately do **not** use Tyk `meta_data` for identity: Tyk OSS wipes
> `meta_data` on a key's first request (it re-saves a thin session after
> rate-limiting). The `alias` and `tags` persist, so identity injection reads those.

`injectIdentity.js` (a JSVM post-auth hook) maps these onto the upstream request:

```
X-Aleph-Identity:      <alias>
X-Aleph-Account:       <account tag, or alias>
X-Aleph-Identity-Type: <type tag, or "service">
```

The gateway reads them and stamps every usage record (see [LOGGING.md](LOGGING.md)).
A request that bypasses Tyk is logged as `anonymous`.

## Managing keys — `scripts/tyk/tyk-admin.sh` (control plane)

Run on **any control-plane node**. It reads the Tyk admin secret from the
in-cluster Secret (`secrets-tyk-oss-tyk-gateway` / `APISecret`), auto-discovers the
Tyk endpoint (LB VIP, else ClusterIP), and appends every mutating action to an
audit log (`/var/log/aleph/tyk-admin.log`).

```bash
# On a control-plane node (kubectl works without setup inside the node shell):
cd /path/to/aleph   # or copy scripts/tyk/tyk-admin.sh over

# Create a key (prints the key string — give it to the user/service):
KEY=$(scripts/tyk/tyk-admin.sh add-user <identity> [account] [type])
#   identity = service name or LDAP username
#   account  = fairshare bucket   (default: identity)
#   type     = service | user     (default: service)

# Check a key is valid AND belongs to an identity (prints true/false, exit 0/1):
scripts/tyk/tyk-admin.sh validate-key <identity> <key>

# Rotate: issue a NEW key for the identity and revoke its old keys:
NEWKEY=$(scripts/tyk/tyk-admin.sh update-user <identity> [account] [type])

# Revoke a single key:
scripts/tyk/tyk-admin.sh invalidate-key <key|hash>

# List / revoke all keys for an identity:
scripts/tyk/tyk-admin.sh list-user <identity>
scripts/tyk/tyk-admin.sh invalidate-user <identity>
```

### Examples

```bash
# A shared service (e.g. OpenWebUI) on a shared fairshare pool:
KEY=$(scripts/tyk/tyk-admin.sh add-user openwebui shared-pool service)

# A named person (future LDAP username), own account bucket:
KEY=$(scripts/tyk/tyk-admin.sh add-user jdoe def-pi-alloc user)

# Rotate a possibly-leaked key:
scripts/tyk/tyk-admin.sh update-user openwebui
```

### Env overrides

| Var | Default |
|---|---|
| `TYK_URL` | auto: LB IP of `tyk/tyk-gateway-nodeport`, else ClusterIP |
| `TYK_SECRET` | auto: Secret `tyk/secrets-tyk-oss-tyk-gateway` key `APISecret` |
| `API_ID` | `model-gateway` |
| `AUDIT_LOG` | `/var/log/aleph/tyk-admin.log` |
| `KUBECTL` | `kubectl` (falls back to the RKE2 bundle + KUBECONFIG) |

## How clients send the key (catch-all)

The `normalizeAuth` pre-hook accepts the key under any common convention and
normalizes it to `Authorization: Bearer` before auth, so OpenAI, Anthropic, Azure,
Google, and Cohere SDKs all work unchanged:

| Convention | Header / param |
|---|---|
| OpenAI / Cohere | `Authorization: Bearer <key>` |
| (also) raw | `Authorization: <key>` |
| Anthropic | `x-api-key: <key>` |
| Azure OpenAI | `api-key: <key>` |
| Google | `x-goog-api-key: <key>` |
| query string | `?api_key=<key>` / `?api-key=<key>` / `?key=<key>` |

### Verify from a login node (data path only)

The key works against the public MetalLB VIP from anywhere with network access —
no kubectl/secret needed (that's the whole point of an API key):

```bash
VIP=<metallb-vip>          # e.g. the public LoadBalancer IP for Tyk

# no key -> 401, valid key -> 200
curl -s -o /dev/null -w '%{http_code}\n' http://$VIP/v1/models
curl -s -o /dev/null -w '%{http_code}\n' http://$VIP/v1/models -H "Authorization: Bearer $KEY"

# chat (any of the header styles above):
curl -s http://$VIP/v1/chat/completions -H "Content-Type: application/json" \
  -H "x-api-key: $KEY" \
  -d '{"model":"command-r-7b","messages":[{"role":"user","content":"hi"}],"max_tokens":16}'
```

Lifecycle (verified): no key → `401`; valid key → `200`; bad key → `403`. Tyk has a
~10s in-memory session cache, so a freshly revoked key may keep working for a few
seconds — expected.

## Cold starts (scale-to-zero)

Most models scale to zero when idle. The first request wakes the model and returns
a friendly 503 telling the client to retry — it is **not** an error:

```json
{"error":{"message":"Model 'gemma-3-4b-it' is starting up (scaled to zero for efficiency). Please retry in 1-2 minutes.","type":"model_starting","code":"model_scaled_to_zero"}}
```

The response also carries `Retry-After: 30`. Clients should retry until they get a
`200` (typically 1-3 min for a small model, longer for large ones). A model whose
ISVC is genuinely not healthy returns a different 503 (`code: model_not_ready`).

Each scale-up (503) is itself recorded in the usage log with `cold_start: true`,
because spinning a model up has real GPU cost — see [LOGGING.md](LOGGING.md).

## Future: LDAP / PAM

Not wired yet. For now keys are created by hand on the control plane with
`tyk-admin.sh`. When LDAP/PAM is integrated, `identity` becomes the LDAP username
and `type` becomes `user`; the alias/tags model and everything downstream
(injection, accounting) stays the same.

## Under the hood (raw Tyk admin API)

`tyk-admin.sh` wraps the Tyk gateway admin API (`x-tyk-authorization: <APISecret>`):

```bash
TYK=http://<VIP>
SECRET=$(kubectl get secret secrets-tyk-oss-tyk-gateway -n tyk -o jsonpath='{.data.APISecret}' | base64 -d)

# create
curl -s -X POST $TYK/tyk/keys/create -H "x-tyk-authorization: $SECRET" -H "Content-Type: application/json" -d '{
  "alias": "openwebui",
  "tags": ["aleph", "account:shared-pool", "type:service"],
  "access_rights": {"model-gateway": {"api_id": "model-gateway", "api_name": "model-gateway", "versions": ["Default"]}}
}'
# list (hashes only) / inspect / delete
curl -s $TYK/tyk/keys -H "x-tyk-authorization: $SECRET"
curl -s $TYK/tyk/keys/<key>           -H "x-tyk-authorization: $SECRET"   # by raw key
curl -s $TYK/tyk/keys/<hash>?hashed=true -H "x-tyk-authorization: $SECRET"
curl -s -X DELETE $TYK/tyk/keys/<key> -H "x-tyk-authorization: $SECRET"
```

Tyk OSS has no identity index, so `list-user`/`invalidate-user` scan all key hashes
and filter on `alias`. Fine for modest key counts.

## Manifests involved

| Manifest | Role |
|---|---|
| `51-tyk.yaml` | Tyk OSS (JSVM enabled, api-defs + middleware volume mounts) |
| `52-tyk-loadbalancer.yaml` | MetalLB LoadBalancer for the public VIP |
| `53-tyk-api-definitions.yaml` | API def (token auth, custom_middleware pre/post) |
| `54-tyk-middleware.yaml` | JSVM: `normalizeAuth` + `injectIdentity` |

Source of truth for the JS + API def: `gateway/tyk/`.
