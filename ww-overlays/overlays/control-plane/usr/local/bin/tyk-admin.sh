#!/usr/bin/env bash
# Aleph Tyk key/user administration — run on a CONTROL-PLANE node.
# -----------------------------------------------------------------------------
# SOURCE OF TRUTH for this file. A deploy copy is baked onto control-plane nodes
# at /usr/local/bin/tyk-admin.sh via the Warewulf overlay
# (ww-overlays/overlays/control-plane/usr/local/bin/tyk-admin.sh) — keep both in
# sync. On a provisioned node you can just run `tyk-admin.sh ...` (it's on PATH).
# -----------------------------------------------------------------------------
# Manages model-gateway API keys via the Tyk admin API. Designed to run on any
# control plane: it reads the admin secret straight from the in-cluster Tyk
# Secret and talks to the Tyk gateway over its LoadBalancer/ClusterIP. Every
# mutating action is appended to an audit log.
#
# Identity model (no LDAP/PAM yet — we create keys by hand):
#   identity       service name (e.g. openwebui) OR an LDAP username
#   account        fairshare/billing bucket (defaults to identity)
#   identity_type  service | user   (default: service)
# These are stored as the key ALIAS (identity) and TAGS (account:<x>, type:<x>)
# and injected by Tyk (injectIdentity.js) as X-Aleph-* headers so the gateway can
# attribute every request for fairshare. NOTE: we deliberately do NOT rely on
# Tyk meta_data — Tyk OSS wipes it on the first request; alias + tags persist.
#
# Commands:
#   add-user <identity> [account] [type]   create a key, print the key string
#   validate-key <identity> <key>          true/false (and exit 0/1) if key is
#                                          valid AND belongs to <identity>
#   update-user <identity> [account] [type]   rotate: issue a NEW key for the
#                                          identity and invalidate its old keys
#   invalidate-key <key|hash>              revoke a single key
#   list-user <identity>                   show all keys for an identity
#   invalidate-user <identity>             revoke ALL keys for an identity
#   grant-api <api_id> [api_name]          add <api_id> to every key's access_rights
#                                          (mirrors the key's model-gateway limit)
#
# Env overrides:
#   TYK_URL      default: auto (LB IP of svc tyk/tyk-gateway-nodeport, else ClusterIP)
#   TYK_SECRET   default: auto (Secret tyk/secrets-tyk-oss-tyk-gateway key APISecret)
#   API_ID       default: model-gateway
#   AUDIT_LOG    default: /var/log/aleph/tyk-admin.log
#   KUBECTL      default: kubectl (falls back to rke2's bundled kubectl)
set -euo pipefail

API_ID="${API_ID:-model-gateway}"
AUDIT_LOG="${AUDIT_LOG:-/var/log/aleph/tyk-admin.log}"

# --- kubectl discovery (works inside a node shell or via rke2 bundle) ----------
KUBECTL="${KUBECTL:-kubectl}"
if ! command -v "$KUBECTL" >/dev/null 2>&1; then
  if [ -x /var/lib/rancher/rke2/bin/kubectl ]; then
    KUBECTL=/var/lib/rancher/rke2/bin/kubectl
    export KUBECONFIG="${KUBECONFIG:-/etc/rancher/rke2/rke2.yaml}"
  else
    echo "error: kubectl not found (set KUBECTL=...)" >&2; exit 1
  fi
fi
[ -z "${KUBECONFIG:-}" ] && [ -f /etc/rancher/rke2/rke2.yaml ] && export KUBECONFIG=/etc/rancher/rke2/rke2.yaml

# --- resolve admin secret + endpoint ------------------------------------------
if [ -z "${TYK_SECRET:-}" ]; then
  TYK_SECRET="$("$KUBECTL" get secret -n tyk secrets-tyk-oss-tyk-gateway \
    -o jsonpath='{.data.APISecret}' 2>/dev/null | base64 -d || true)"
fi
[ -z "${TYK_SECRET:-}" ] && { echo "error: could not read Tyk APISecret (set TYK_SECRET=...)" >&2; exit 1; }

if [ -z "${TYK_URL:-}" ]; then
  lb_ip="$("$KUBECTL" get svc -n tyk tyk-gateway-nodeport \
    -o jsonpath='{.status.loadBalancer.ingress[0].ip}' 2>/dev/null || true)"
  if [ -n "$lb_ip" ]; then
    TYK_URL="http://${lb_ip}:80"
  else
    cip="$("$KUBECTL" get svc -n tyk gateway-svc-tyk-oss-tyk-gateway \
      -o jsonpath='{.spec.clusterIP}' 2>/dev/null || true)"
    [ -n "$cip" ] && TYK_URL="http://${cip}:8080"
  fi
fi
[ -z "${TYK_URL:-}" ] && { echo "error: could not resolve Tyk URL (set TYK_URL=...)" >&2; exit 1; }

AUTH=(-H "x-tyk-authorization: ${TYK_SECRET}")
JSON=(-H "Content-Type: application/json")

hashed_flag() { [ "${#1}" -le 40 ] && echo "?hashed=true" || echo ""; }

audit() {
  # audit "<action>" "<identity>" "<detail>"
  local line
  line=$(printf '{"ts":"%s","actor":"%s","action":"%s","identity":"%s","detail":"%s"}' \
    "$(date -u +%Y-%m-%dT%H:%M:%SZ)" "${SUDO_USER:-${USER:-root}}@$(hostname -s)" "$1" "$2" "$3")
  mkdir -p "$(dirname "$AUDIT_LOG")" 2>/dev/null || true
  echo "$line" >> "$AUDIT_LOG" 2>/dev/null || true
}

# Emit a key body. Identity lives in alias + tags (durable); meta_data is also
# set for human inspection right after creation but is NOT relied upon (Tyk OSS
# wipes meta_data on first request).
key_body() {
  local identity="$1" account="$2" itype="$3"
  cat <<EOF
{
  "alias": "${identity}",
  "tags": ["aleph", "account:${account}", "type:${itype}"],
  "meta_data": {"identity": "${identity}", "account": "${account}", "identity_type": "${itype}", "source": "tyk-admin", "created": "$(date -u +%Y-%m-%dT%H:%M:%SZ)"},
  "rate": 60,
  "per": 60,
  "allowance": 60,
  "expires": 0,
  "quota_max": -1,
  "quota_renews": 0,
  "quota_remaining": -1,
  "quota_renewal_rate": 0,
  "access_rights": {
    "model-gateway": {"api_id": "model-gateway", "api_name": "model-gateway", "versions": ["Default"], "limit": {"rate": 60, "per": 60}},
    "model-anthropic": {"api_id": "model-anthropic", "api_name": "model-anthropic", "versions": ["Default"], "limit": {"rate": 60, "per": 60}}
  }
}
EOF
}

create_key() {
  local identity="$1" account="$2" itype="$3"
  curl -s -X POST "${AUTH[@]}" "${JSON[@]}" \
    "${TYK_URL}/tyk/keys/create" -d "$(key_body "$identity" "$account" "$itype")"
}

# Scan all keys, print "hash<TAB>identity" lines for a given identity.
scan_identity() {
  local want="$1"
  TYK_URL="$TYK_URL" TYK_SECRET="$TYK_SECRET" WANT="$want" python3 <<'PY'
import json, os, urllib.request
base, secret, want = os.environ["TYK_URL"], os.environ["TYK_SECRET"], os.environ["WANT"]
hdr = {"x-tyk-authorization": secret}
def req(path):
    r = urllib.request.Request(base + path, headers=hdr)
    with urllib.request.urlopen(r, timeout=15) as resp:
        return json.load(resp)
for h in req("/tyk/keys").get("keys", []):
    try:
        d = req(f"/tyk/keys/{h}?hashed=true")
    except Exception:
        continue
    # Identity = durable alias; account/type parsed from tags (meta_data unreliable).
    ident = d.get("alias") or (d.get("meta_data") or {}).get("identity", "")
    if ident != want:
        continue
    account, itype = ident, "service"
    for t in (d.get("tags") or []):
        if t.startswith("account:"):
            account = t[len("account:"):]
        elif t.startswith("type:"):
            itype = t[len("type:"):]
    print(f"{h}\t{ident}\t{account}\t{itype}")
PY
}

cmd="${1:-}"; shift || true
case "$cmd" in
  add-user)
    identity="${1:?identity required}"; account="${2:-$identity}"; itype="${3:-service}"
    resp="$(create_key "$identity" "$account" "$itype")"
    key="$(echo "$resp" | python3 -c 'import sys,json;print(json.load(sys.stdin).get("key",""))' 2>/dev/null || true)"
    if [ -z "$key" ]; then
      echo "error: key creation failed: $resp" >&2; exit 1
    fi
    audit "add-user" "$identity" "account=$account type=$itype"
    echo "$key"
    ;;

  validate-key)
    identity="${1:?identity required}"; key="${2:?key required}"
    out="$(curl -s "${AUTH[@]}" "${TYK_URL}/tyk/keys/${key}$(hashed_flag "$key")")"
    ok="$(echo "$out" | WANT="$identity" python3 -c '
import sys, json, os
want = os.environ["WANT"]
try:
    d = json.load(sys.stdin)
except Exception:
    print("false"); sys.exit()
# Identity is the durable alias (meta_data is unreliable in Tyk OSS).
ident = d.get("alias") or (d.get("meta_data") or {}).get("identity")
# A valid lookup returns the session (has access_rights); identity must match.
print("true" if d.get("access_rights") and ident == want else "false")
' 2>/dev/null || echo false)"
    audit "validate-key" "$identity" "result=$ok"
    echo "$ok"
    [ "$ok" = "true" ]
    ;;

  update-user)
    identity="${1:?identity required}"; account="${2:-$identity}"; itype="${3:-service}"
    # Issue the new key first so a failure never leaves the user with none.
    resp="$(create_key "$identity" "$account" "$itype")"
    key="$(echo "$resp" | python3 -c 'import sys,json;print(json.load(sys.stdin).get("key",""))' 2>/dev/null || true)"
    [ -z "$key" ] && { echo "error: key creation failed: $resp" >&2; exit 1; }
    new_hash="$(echo "$resp" | python3 -c 'import sys,json;print(json.load(sys.stdin).get("key_hash",""))' 2>/dev/null || true)"
    revoked=0
    while IFS=$'\t' read -r h _ _ _; do
      [ -z "$h" ] && continue
      [ "$h" = "$new_hash" ] && continue
      curl -s -X DELETE "${AUTH[@]}" "${TYK_URL}/tyk/keys/${h}?hashed=true" >/dev/null || true
      revoked=$((revoked+1))
    done < <(scan_identity "$identity")
    audit "update-user" "$identity" "rotated; revoked_old=$revoked"
    echo "$key"
    ;;

  invalidate-key)
    key="${1:?key-or-hash required}"
    curl -s -X DELETE "${AUTH[@]}" "${TYK_URL}/tyk/keys/${key}$(hashed_flag "$key")"
    echo
    audit "invalidate-key" "-" "key=${key:0:8}…"
    ;;

  list-user)
    identity="${1:?identity required}"
    printf 'hash\tidentity\taccount\ttype\n'
    scan_identity "$identity"
    ;;

  invalidate-user)
    identity="${1:?identity required}"
    n=0
    while IFS=$'\t' read -r h _ _ _; do
      [ -z "$h" ] && continue
      curl -s -X DELETE "${AUTH[@]}" "${TYK_URL}/tyk/keys/${h}?hashed=true" >/dev/null || true
      n=$((n+1))
    done < <(scan_identity "$identity")
    audit "invalidate-user" "$identity" "revoked=$n"
    echo "revoked $n key(s) for '$identity'"
    ;;

  grant-api)
    api="${1:?api_id required}"; name="${2:-$api}"
    # Backfill access_rights[api] on every existing key. Copy only rate/per from
    # that key's model-gateway block — NEVER PUT the raw GET session (Tyk hydrates
    # allowance/quota_remaining to 0; writing that back zeros the live limit).
    out="$(TYK_URL="$TYK_URL" TYK_SECRET="$TYK_SECRET" GRANT_API="$api" GRANT_NAME="$name" python3 <<'PY'
import json, os, urllib.error, urllib.request
base = os.environ["TYK_URL"].rstrip("/")
secret = os.environ["TYK_SECRET"]
api = os.environ["GRANT_API"]
name = os.environ["GRANT_NAME"]
hdr = {"x-tyk-authorization": secret, "Content-Type": "application/json"}

def req(path, method="GET", data=None):
    body = None if data is None else json.dumps(data).encode()
    r = urllib.request.Request(base + path, headers=hdr, method=method, data=body)
    with urllib.request.urlopen(r, timeout=20) as resp:
        raw = resp.read()
        return json.loads(raw) if raw else {}

def clean_block(block):
    if not isinstance(block, dict):
        return block
    out = {k: v for k, v in block.items() if v is not None}
    if isinstance(out.get("limit"), dict):
        lim = {k: v for k, v in out["limit"].items()
               if v is not None and k not in ("quota_remaining", "quota_renews")}
        out["limit"] = lim
    return out

hashes = req("/tyk/keys").get("keys", [])
updated = skipped = failed = 0
for h in hashes:
    try:
        d = req(f"/tyk/keys/{h}?hashed=true")
    except Exception:
        failed += 1
        continue
    ar = {k: clean_block(v) for k, v in (d.get("access_rights") or {}).items()}
    if api in ar:
        skipped += 1
        continue
    src = ar.get("model-gateway") or (next(iter(ar.values())) if ar else {})
    src_lim = src.get("limit") if isinstance(src, dict) else {}
    rate = (src_lim or {}).get("rate") or d.get("rate") or 60
    per = (src_lim or {}).get("per") or d.get("per") or 60
    ar[api] = {
        "api_id": api,
        "api_name": name,
        "versions": list((src or {}).get("versions") or ["Default"]),
        "limit": {"rate": rate, "per": per},
    }
    # Re-PUT a *minimal* session: identity + rate + cleaned access_rights.
    # Drop GET-hydrated zeros (allowance remaining, quota remaining).
    body = {
        "alias": d.get("alias") or "",
        "tags": d.get("tags") or [],
        "rate": d.get("rate") or rate,
        "per": d.get("per") or per,
        "allowance": d.get("rate") or rate,
        "expires": d.get("expires") or 0,
        "quota_max": d.get("quota_max") if d.get("quota_max") not in (None, 0) else -1,
        "access_rights": ar,
    }
    if d.get("meta_data"):
        body["meta_data"] = d["meta_data"]
    try:
        req(f"/tyk/keys/{h}?hashed=true&suppress_reset=1", method="PUT", data=body)
        updated += 1
    except urllib.error.HTTPError as e:
        failed += 1
        print(f"fail {h}: HTTP {e.code}", flush=True)
    except Exception as e:
        failed += 1
        print(f"fail {h}: {e}", flush=True)
print(f"grant-api {api}: updated={updated} skipped={skipped} failed={failed} scanned={len(hashes)}")
PY
)"
    echo "$out"
    audit "grant-api" "-" "api=$api $out"
    ;;

  *)
    echo "usage: $0 {add-user <identity> [account] [type] | validate-key <identity> <key> | update-user <identity> [account] [type] | invalidate-key <key|hash> | list-user <identity> | invalidate-user <identity> | grant-api <api_id> [api_name]}" >&2
    exit 1 ;;
esac
