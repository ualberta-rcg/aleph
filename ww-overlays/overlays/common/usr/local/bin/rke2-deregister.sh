#!/usr/bin/env bash
# rke2-deregister.sh — on shutdown, SSH to a head node and delete this node's own Node object.
#
# These are stateless Warewulf nodes: a reboot comes up "fresh", RKE2 auto-rejoins, but the stale
# Node object left behind dirties/blocks the rejoin. We SSH to a control-plane (head) node with a
# dedicated, forced-command-restricted key; the head runs `kubectl delete node <self>` for us
# (the head already has the admin kubeconfig — workers have no credential that can delete nodes).
#
# Everything is time-boxed so an unreachable head can NEVER hang a shutdown.
#
# Config in /etc/default/rke2-deregister:
#   HEAD_NODES="ip1 ip2 ip3"   # tried in order until one succeeds
#   SSH_KEY=/etc/rke2-deregister/id_ed25519
#   SSH_USER=root
#   DEREGISTER_SERVERS=true    # also deregister control-plane/etcd nodes (default: false)
set -uo pipefail

DEREGISTER_SERVERS="${DEREGISTER_SERVERS:-false}"
HEAD_NODES="${HEAD_NODES:-}"
SSH_KEY="${SSH_KEY:-/etc/rke2-deregister/id_ed25519}"
SSH_USER="${SSH_USER:-root}"
NODE="$(hostname -s | tr '[:upper:]' '[:lower:]')"

log() { echo "rke2-deregister: $*"; }

# --- server/etcd guard: don't let a control-plane node self-delete on reboot by default ----
IS_SERVER=false
if systemctl is-enabled rke2-server.service >/dev/null 2>&1 || [ -d /var/lib/rancher/rke2/server/db ]; then
  IS_SERVER=true
fi
if [ "$IS_SERVER" = "true" ] && [ "$DEREGISTER_SERVERS" != "true" ]; then
  log "server/etcd node ($NODE); self-deregister disabled (DEREGISTER_SERVERS=true to enable). skipping."
  exit 0
fi

# --- detect head (control-plane) nodes ----------------------------------------------------
# Nothing is hardcoded. RKE2 agents keep the live list of all control-plane addresses in their
# load-balancer config, which tracks topology changes automatically. Fall back to the join
# endpoint in config.yaml if that's missing. HEAD_NODES in /etc/default/rke2-deregister is an
# optional manual override only.
detect_heads() {
  local lb f addrs=""
  for lb in /var/lib/rancher/rke2/agent/etc/rke2-agent-load-balancer.json \
            /var/lib/rancher/rke2/agent/etc/rke2-api-server-agent-load-balancer.json; do
    if [ -r "$lb" ]; then
      addrs="$(grep -oE '"[0-9A-Za-z._-]+:[0-9]+"' "$lb" | tr -d '"' | sed 's/:[0-9]*$//')"
      [ -n "$addrs" ] && { echo "$addrs" | sort -u; return; }
    fi
  done
  # fallback: server: https://host:port in config.yaml (registration endpoint)
  for f in /etc/rancher/rke2/config.yaml /etc/rancher/rke2/config2.yaml; do
    [ -r "$f" ] || continue
    grep -E '^[[:space:]]*server:' "$f" 2>/dev/null | sed -E 's#.*//([^:/]+).*#\1#'
  done | sort -u
}

if [ -z "$HEAD_NODES" ]; then
  HEAD_NODES="$(detect_heads)"
fi
[ -n "$HEAD_NODES" ] || { log "could not detect any head nodes; skipping"; exit 0; }
log "head node(s): $(echo $HEAD_NODES | tr '\n' ' ')"

[ -r "$SSH_KEY" ] || { log "no ssh key at $SSH_KEY; skipping"; exit 0; }

# ssh refuses keys with group/other-readable perms; stage a private copy (overlay can't keep 0600).
KEY=/run/rke2-deregister.key
if ! install -m 600 "$SSH_KEY" "$KEY" 2>/dev/null; then
  cp "$SSH_KEY" "$KEY" && chmod 600 "$KEY"
fi
trap 'rm -f "$KEY"' EXIT

for h in $HEAD_NODES; do
  log "deregistering $NODE via $SSH_USER@$h"
  if timeout 25 ssh -i "$KEY" \
       -o BatchMode=yes \
       -o StrictHostKeyChecking=no \
       -o UserKnownHostsFile=/dev/null \
       -o ConnectTimeout=6 \
       -o LogLevel=ERROR \
       "$SSH_USER@$h" "$NODE" 2>&1 | sed 's/^/rke2-deregister: /'; then
    log "deregistered via $h"
    exit 0
  fi
  log "head $h unreachable/failed; trying next"
done

log "all heads failed; giving up (not blocking shutdown)"
exit 0
