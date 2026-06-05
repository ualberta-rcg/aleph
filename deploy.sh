#!/usr/bin/env bash
# Convenience wrapper for THIS cluster (230) only: ships the repo to the head node
# and runs gateway/remote-deploy.sh. Run from the repo root on a Vulcan login node.
#
#   ./deploy.sh                # build+deploy with default image tag
#   TAG=0.4 ./deploy.sh        # bump the image tag (also edit gateway/k8s/deployment.yaml)
#   HEAD=172.26.92.230 ./deploy.sh
#
# For a DIFFERENT cluster, don't use this as-is — follow RUNBOOK.md and substitute
# the per-cluster values (node labels, Tyk release name/secret, StorageClass, IPs).
# Assumes the platform is already up (RKE2, HAMi, KServe/Knative, Istio, Tyk OSS, NFS).
set -euo pipefail

HEAD="${HEAD:-172.26.92.230}"
TAG="${TAG:-0.3}"
DIR=/root/gateway-build
SSH=(sudo ssh -o StrictHostKeyChecking=no "root@${HEAD}")

cd "$(dirname "$0")"

echo ">> shipping source to ${HEAD}:${DIR}"
tar czf - gateway models | "${SSH[@]}" "rm -rf ${DIR} && mkdir -p ${DIR} && tar xzf - -C ${DIR}"

echo ">> running remote deploy (TAG=${TAG})"
"${SSH[@]}" "cd ${DIR} && TAG=${TAG} bash gateway/remote-deploy.sh"
