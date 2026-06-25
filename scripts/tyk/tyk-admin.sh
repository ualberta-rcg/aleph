#!/usr/bin/env bash
# Aleph Tyk key/user administration — run on a CONTROL-PLANE node.
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
# These land in the key's meta_data and are injected by Tyk (injectIdentity.js)
# as X-Aleph-* headers so the gateway can attribute every request for fairshare.
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

# Emit a key body with identity metadata.
key_body() {
  local identity="$1" account="$2" itype="$3"
  cat <<EOF
{
  "alias": "${identity}",
  "meta_data": {"identity": "${identity}", "account": "${account}", "identity_type": "${itype}", "source": "tyk-admin", "created": "$(date -u +%Y-%m-%dT%H:%M:%SZ)"},
  "tags": ["aleph", "${itype}"],
  "access_rights": {"${API_ID}": {"api_id": "${API_ID}", "api_name": "${API_ID}", "versions": ["Default"]}}
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
    md = d.get("meta_data") or {}
    if md.get("identity") == want or md.get("username") == want:
        print(f"{h}\t{md.get('identity', md.get('username',''))}\t{md.get('account','')}\t{md.get('identity_type','')}")
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
    ok="$(echo "$out" | python3 -c '
import sys, json, os
want = os.environ["WANT"]
try:
    d = json.load(sys.stdin)
except Exception:
    print("false"); sys.exit()
md = d.get("meta_data") or {}
ident = md.get("identity") or md.get("username")
# A valid lookup returns the session (has access_rights); identity must match.
print("true" if d.get("access_rights") and ident == want else "false")
' WANT="$identity" 2>/dev/null || echo false)"
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

  *)
    echo "usage: $0 {add-user <identity> [account] [type] | validate-key <identity> <key> | update-user <identity> [account] [type] | invalidate-key <key|hash> | list-user <identity> | invalidate-user <identity>}" >&2
    exit 1 ;;
esac
