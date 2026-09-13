# Tyk Users & API Keys

How identity and API keys work for the Aleph model gateway: how to create, validate,
rotate, and revoke keys, what conventions clients can use to send them, and how
identity flows into usage accounting.

See also: [LOGGING.md](LOGGING.md) (usage/accounting), [docs/RUNBOOK.md](docs/RUNBOOK.md)
(operations), and `gateway/README.md`.

## The request path

```
client ──► https://<public-endpoint>
        ──► MetalLB VIP ──► Traefik (TLS, Let's Encrypt via cert-manager)
        ──► Tyk OSS (ClusterIP) ──► model-gateway ──► KServe/vLLM pod
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
| identity | key **alias** | `openwebui`, `jdoe` | service name OR cluster username |
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

## Managing keys — `tyk-admin.sh` (control plane)

Run on **any control-plane node** — `tyk-admin.sh` is baked onto the node at
`/usr/local/bin` (source: `ww-overlays/overlays/control-plane/usr/local/bin/tyk-admin.sh`).
It reads the Tyk admin secret from the in-cluster Secret
(`secrets-tyk-oss-tyk-gateway` / `APISecret`), auto-discovers the Tyk endpoint
(LB VIP, else ClusterIP), and appends every mutating action to an audit log
(`/var/log/aleph/tyk-admin.log`).

```bash
# On a control-plane node (tyk-admin.sh is already on PATH):

# Create a key (prints the key string — give it to the user/service):
KEY=$(tyk-admin.sh add-user <identity> [account] [type])
#   identity = service name or cluster username
#   account  = fairshare bucket   (default: identity)
#   type     = service | user     (default: service)

# Check a key is valid AND belongs to an identity (prints true/false, exit 0/1):
tyk-admin.sh validate-key <identity> <key>

# Rotate: issue a NEW key for the identity and revoke its old keys:
NEWKEY=$(tyk-admin.sh update-user <identity> [account] [type])

# Revoke a single key:
tyk-admin.sh invalidate-key <key|hash>

# List / revoke all keys for an identity:
tyk-admin.sh list-user <identity>
tyk-admin.sh invalidate-user <identity>

# Backfill a new api_id onto every existing key (used for model-anthropic):
tyk-admin.sh grant-api model-anthropic
```

New keys get `access_rights` on **both** `model-gateway` (`/v1/`) and
`model-anthropic` (`/anthropic/`). Existing keys need `grant-api` after the
Anthropic API definition is applied, or keyed `/anthropic/` calls 403.

### Examples

```bash
# A shared service (e.g. OpenWebUI) on a shared fairshare pool:
KEY=$(tyk-admin.sh add-user openwebui shared-pool service)

# A named person (cluster username), own account bucket:
KEY=$(tyk-admin.sh add-user jdoe def-pi-alloc user)

# Rotate a possibly-leaked key:
tyk-admin.sh update-user openwebui
```

### Env overrides

| Var | Default |
|---|---|
| `TYK_URL` | auto: Tyk service endpoint in-cluster (the admin API is NOT exposed through the public edge) |
| `TYK_SECRET` | auto: Secret `tyk/secrets-tyk-oss-tyk-gateway` key `APISecret` |
| `API_ID` | unused for minting — new keys always get `model-gateway` **and** `model-anthropic` |
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

Verified from source (both layers): Tyk's `normalizeAuth.js` normalizes any of
these to `Authorization: Bearer` **before** auth (and deletes any client-supplied
`X-Aleph-*` identity headers — identity can't be spoofed); the gateway
independently fingerprints whatever arrived (`sha256` last-8 + last-4, identical
lookup order) and logs it as `key_fp` on every usage record. The raw key is never
stored or logged anywhere past the mint response.

### Verify from a client (data path only)

The key works against the public endpoint from anywhere with network access —
no kubectl/secret needed (that's the whole point of an API key):

```bash
GW=https://inference.vulcan.alliancecan.ca

# no key -> 401, valid key -> 200
curl -s -o /dev/null -w '%{http_code}\n' $GW/v1/models
curl -s -o /dev/null -w '%{http_code}\n' $GW/v1/models -H "Authorization: Bearer $KEY"

# chat (any of the header styles above):
curl -s $GW/v1/chat/completions -H "Content-Type: application/json" \
  -H "x-api-key: $KEY" \
  -d '{"model":"command-r-7b","messages":[{"role":"user","content":"hi"}],"max_tokens":16}'
```

Lifecycle: no key → `401`; valid key → `200`; bad key → `403`. Tyk has a ~10s
in-memory session cache, so a freshly revoked key may keep working for a few
seconds — expected.

## Cold starts (scale-to-zero)

Most models scale to zero when idle. The first request wakes the model and returns
a friendly 503 telling the client to retry — it is **not** an error:

```json
{"error":{"message":"Model 'gemma-3-4b-it' is starting up (scaled to zero for efficiency). Please retry in 1-2 minutes.","type":"model_starting","code":"model_scaled_to_zero"}}
```

The response also carries `Retry-After`. Clients should retry until they get a
`200` (typically 1-3 min for a small model, longer for large ones). A model whose
ISVC is genuinely not healthy returns a different 503 (`code: model_not_ready`),
and a wake that cannot fit in remaining GPU capacity returns
`code: insufficient_capacity`.

Each scale-up (503) is itself recorded in the usage log with `cold_start: true`,
because spinning a model up has real GPU cost — see [LOGGING.md](LOGGING.md).

## Per-user keys: PAM auto-provisioning

Every SSH login to a cluster login node fires a PAM session hook
(`/etc/pam.d/sshd` → `pam_exec.so /usr/local/sbin/aleph-tyk-key`, `optional` so
login never breaks). It mints/rotates that user's personal Tyk key via a
control-plane node (hostbased SSH → `tyk-admin.sh add-user|update-user`, or the
`tyk-pam-cmd` forced-command wrapper in hardening mode) and writes
**`~/.aleph_tyk.env`** (mode 600) into the user's home. Users
`source ~/.aleph_tyk.env` and call the endpoint with
`Authorization: Bearer $TYK_KEY`. So `identity` = the cluster username and
`type` = `user` — exactly as the alias/tags model above describes. Manual
`tyk-admin.sh` minting remains for services and admins.

The login-node hook script and the hostbased trust files are installed as manual
overlays on the login nodes (not tracked in this repo).

## Under the hood — Tyk configuration

**Config (Tyk pod env):** `TYK_GW_HASHKEYS=true`, `TYK_GW_HASHKEYFUNCTION=murmur128`
(raw keys never stored — Redis is keyed by `apikey-<murmur128-hex>`), single-node
Redis DB0 (`STORAGE_ENABLECLUSTER=false`), `ENABLENONTRANSACTIONALRATELIMITER=true`,
APPS/MIDDLEWARE mounted from ConfigMaps at `/mnt/tyk-gateway/{apps,middleware}`.

**Session blob anatomy** (at `apikey-<hash>`): `allowance`/`rate` + `per` window
at top level · `quota_max: -1` = quota disabled, rate-limit only · `expires: 0` =
never expires · `access_rights` for **both** APIs (`model-gateway` +
`model-anthropic`), each carrying its own limit copy · identity = `alias` +
`tags: ["aleph","account:<x>","type:<user|service>"]` (injection reads these;
historically Tyk wipes `meta_data` on first request, so alias/tags are the
durable source) · `apply_policies: null` — no policy layer, plain access_rights.

**Rate counters are ephemeral**: the non-transactional limiter creates per-window
counters with short TTLs that vanish seconds later, so a SCAN for them usually
finds nothing unless traffic is flowing that instant. The persistent keys ≈ the
key blobs themselves. **Keys live only in Redis (hash-only) — back that
datastore up; keys cannot be re-derived.**

## Under the hood (raw Tyk admin API)

`tyk-admin.sh` wraps the Tyk gateway admin API (`x-tyk-authorization: <APISecret>`):

```bash
# Run from a control-plane node (the admin API is in-cluster only):
TYK=http://<tyk-svc-clusterip>:8080
SECRET=$(kubectl get secret secrets-tyk-oss-tyk-gateway -n tyk -o jsonpath='{.data.APISecret}' | base64 -d)

# create
curl -s -X POST $TYK/tyk/keys/create -H "x-tyk-authorization: $SECRET" -H "Content-Type: application/json" -d '{
  "alias": "openwebui",
  "tags": ["aleph", "account:shared-pool", "type:service"],
  "access_rights": {
    "model-gateway": {"api_id": "model-gateway", "api_name": "model-gateway", "versions": ["Default"], "limit": {"rate": 300, "per": 60}},
    "model-anthropic": {"api_id": "model-anthropic", "api_name": "model-anthropic", "versions": ["Default"], "limit": {"rate": 300, "per": 60}}
  }
}'
# list (hashes only) / inspect / delete
curl -s $TYK/tyk/keys -H "x-tyk-authorization: $SECRET"
curl -s $TYK/tyk/keys/<key>           -H "x-tyk-authorization: $SECRET"   # by raw key
curl -s $TYK/tyk/keys/<hash>?hashed=true -H "x-tyk-authorization: $SECRET"
curl -s -X DELETE $TYK/tyk/keys/<key> -H "x-tyk-authorization: $SECRET"
```

Tyk OSS has no identity index, so `list-user`/`invalidate-user` scan all key hashes
and filter on `alias`. Fine for modest key counts.

## API definitions & manifests

| Tyk API | listen_path | strip | auth | notes |
|---|---|---|---|---|
| `model-gateway` | `/v1/` | no | **authed** (standard token) | rate-limit on, quota off; pre normalizeAuth + post injectIdentity |
| `model-anthropic` | `/anthropic/` | yes | **authed** | injects `X-Aleph-Api: anthropic`; `/api/hello` (GET/HEAD) is a **pre-auth Tyk mock** `{"message":"hello"}` (agent warm probe — never proxied) |
| `model-web` | `/` | no | **keyless** | the public landing page; also forwards `/healthz` and `/metrics` |

| Manifest | Role |
|---|---|
| `51-tyk.yaml` | Tyk OSS (JSVM enabled, api-defs + middleware volume mounts) |
| `52-tyk-loadbalancer.yaml` | Tyk Service (ClusterIP; legacy name kept for scripts) |
| `53-tyk-api-definitions.yaml` | The three API definitions above |
| `54-tyk-middleware.yaml` | JSVM: `normalizeAuth` + `injectIdentity` |

Source of truth for the JS + API defs: `gateway/tyk/`.
