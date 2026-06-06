#!/usr/bin/env bash
# Convenience wrapper for THIS cluster (230) only: ships the repo to the head node
# and runs gateway/remote-deploy.sh. Run from the repo root on a Vulcan login node.
#
#   ./deploy.sh                                    # deploy with rkhoja/aleph:latest
#   GATEWAY_IMAGE=rkhoja/aleph:gateway-68f01ba ./deploy.sh   # pin a CI tag
#   HEAD=172.26.92.230 ./deploy.sh
#
# For a DIFFERENT cluster, don't use this as-is — follow RUNBOOK.md and substitute
# the per-cluster values (node labels, Tyk release name/secret, StorageClass, IPs).
# Assumes the platform is already up (RKE2, HAMi, KServe/Knative, Istio, Tyk OSS, NFS).
set -euo pipefail

HEAD="${HEAD:-172.26.92.230}"
GATEWAY_IMAGE="${GATEWAY_IMAGE:-rkhoja/aleph:latest}"
DIR=/root/gateway-build
SSH=(sudo ssh -o StrictHostKeyChecking=no "root@${HEAD}")

cd "$(dirname "$0")"

echo ">> shipping source to ${HEAD}:${DIR}"
tar czf - gateway models | "${SSH[@]}" "rm -rf ${DIR} && mkdir -p ${DIR} && tar xzf - -C ${DIR}"

echo ">> running remote deploy (GATEWAY_IMAGE=${GATEWAY_IMAGE})"
"${SSH[@]}" "cd ${DIR} && GATEWAY_IMAGE=${GATEWAY_IMAGE} bash gateway/remote-deploy.sh"
