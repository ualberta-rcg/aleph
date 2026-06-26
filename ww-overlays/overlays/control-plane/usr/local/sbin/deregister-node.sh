#!/usr/bin/env bash
# deregister-node.sh — forced-command target for the node-deregister SSH key.
#
# Invoked by sshd (see /etc/ssh/deregister.authorized_keys). The ONLY thing that key can run.
# The node name to delete arrives as $SSH_ORIGINAL_COMMAND (whatever the worker passed as its
# remote command). We hard-validate it as a single DNS-1123 node name, then delete it. Runs as
# root, so the admin kubeconfig is readable — no sudoers rule required.
set -uo pipefail
export PATH="$PATH:/var/lib/rancher/rke2/bin"
export KUBECONFIG=/etc/rancher/rke2/rke2.yaml

node="${SSH_ORIGINAL_COMMAND:-}"
# strict allowlist: one DNS-1123 label/hostname, nothing else (blocks command injection)
if [[ ! "$node" =~ ^[a-z0-9]([a-z0-9.-]{0,61}[a-z0-9])?$ ]]; then
  echo "deregister-node: refused (invalid node name: '${node}')" >&2
  exit 1
fi

echo "deregister-node: deleting node '$node'"
exec timeout 20 kubectl delete node "$node" --wait=false --ignore-not-found
