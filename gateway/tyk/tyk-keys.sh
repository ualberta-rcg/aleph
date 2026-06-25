#!/usr/bin/env bash
# Manage Tyk API keys for the model-gateway from a login node.
#
# NOTE: For day-to-day identity/key management prefer the control-plane tool
#   scripts/tyk/tyk-admin.sh  (add-user / validate-key / update-user / invalidate-key).
# It stores identity in the key ALIAS + TAGS (durable) and reads the APISecret
# from the in-cluster Secret. This script keeps identity in meta_data.username,
# which Tyk OSS WIPES on the first request — so its find/revoke-user scans become
# unreliable after a key is used. Kept here for quick list/inspect/test from a
# login node. Auth is catch-all now: the key works under Authorization Bearer,
# x-api-key, api-key, x-goog-api-key, or ?api_key=.
#
# Usage:
#   ./tyk-keys.sh list
#   ./tyk-keys.sh create <username> [uid] [account]   # prints the new key string
#   ./tyk-keys.sh inspect <key-or-hash>               # hash needs no special flag here
#   ./tyk-keys.sh revoke  <key-or-hash>
#   ./tyk-keys.sh test    <key>                       # send a chat request with the key
#   ./tyk-keys.sh find    <username>                  # scan all keys, show ones for that user
#   ./tyk-keys.sh revoke-user <username>              # revoke ALL keys for that username
#
# NOTE: Tyk OSS has no username index — find/revoke-user scan every key
#       (list hashes -> inspect each -> filter on meta_data.username). Fine for
#       modest key counts; for large fleets use a Dashboard or your own index.
#
# Env overrides:
#   TYK_URL     (default http://172.26.92.43:30808)
#   TYK_SECRET  (required; see .env / .env.example)    -- the admin APISecret
#   API_ID      (default model-gateway)
set -euo pipefail

TYK_URL="${TYK_URL:-http://172.26.92.43:30808}"
TYK_SECRET="${TYK_SECRET:?set TYK_SECRET (Tyk gateway APISecret) — see .env / .env.example}"
API_ID="${API_ID:-model-gateway}"
AUTH=(-H "x-tyk-authorization: ${TYK_SECRET}")
JSON=(-H "Content-Type: application/json")

# Detect whether an id looks like a raw key (long base64) or a short hash.
hashed_flag() { [ "${#1}" -le 40 ] && echo "?hashed=true" || echo ""; }

cmd="${1:-}"; shift || true
case "$cmd" in
  list)
    curl -s "${AUTH[@]}" "${TYK_URL}/tyk/keys" ;;
  create)
    user="${1:?username required}"; uid="${2:-}"; account="${3:-}"
    body=$(cat <<EOF
{
  "alias": "${user}",
  "meta_data": {"username": "${user}", "uid": "${uid}", "account": "${account}", "source": "pam"},
  "tags": ["pam"],
  "access_rights": {"${API_ID}": {"api_id": "${API_ID}", "api_name": "${API_ID}", "versions": ["Default"]}}
}
EOF
)
    curl -s -X POST "${AUTH[@]}" "${JSON[@]}" "${TYK_URL}/tyk/keys/create" -d "${body}" ;;
  inspect)
    id="${1:?key-or-hash required}"
    curl -s "${AUTH[@]}" "${TYK_URL}/tyk/keys/${id}$(hashed_flag "$id")" ;;
  revoke)
    id="${1:?key-or-hash required}"
    curl -s -X DELETE "${AUTH[@]}" "${TYK_URL}/tyk/keys/${id}$(hashed_flag "$id")" ;;
  test)
    key="${1:?key required}"
    curl -s "${TYK_URL}/v1/chat/completions" \
      -H "Authorization: Bearer ${key}" "${JSON[@]}" \
      -d '{"model":"command-r-7b","messages":[{"role":"user","content":"say ok"}],"max_tokens":10}' ;;
  find|revoke-user)
    user="${1:?username required}"
    TYK_URL="$TYK_URL" TYK_SECRET="$TYK_SECRET" MODE="$cmd" USER_Q="$user" python3 <<'PY'
import json, os, urllib.request

base, secret = os.environ["TYK_URL"], os.environ["TYK_SECRET"]
mode, want = os.environ["MODE"], os.environ["USER_Q"]
hdr = {"x-tyk-authorization": secret}

def req(path, method="GET"):
    r = urllib.request.Request(base + path, headers=hdr, method=method)
    with urllib.request.urlopen(r, timeout=15) as resp:
        return json.load(resp)

hashes = req("/tyk/keys").get("keys", [])
matches = []
for h in hashes:
    try:
        d = req(f"/tyk/keys/{h}?hashed=true")
    except Exception:
        continue
    md = d.get("meta_data") or {}
    if md.get("username") == want:
        matches.append((h, d.get("alias", ""), md))

if not matches:
    print(f"no keys for username '{want}' (scanned {len(hashes)})")
else:
    for h, alias, md in matches:
        print(f"hash={h} alias={alias} meta={json.dumps(md)}")
    if mode == "revoke-user":
        for h, _, _ in matches:
            res = req(f"/tyk/keys/{h}?hashed=true", method="DELETE")
            print(f"revoked {h}: {res.get('action', res)}")
PY
    ;;
  *)
    echo "usage: $0 {list|create <user> [uid] [account]|inspect <key|hash>|revoke <key|hash>|test <key>|find <user>|revoke-user <user>}" >&2
    exit 1 ;;
esac
echo
