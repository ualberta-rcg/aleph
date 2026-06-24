#!/usr/bin/env bash
# Runs ON the head node (control plane), from the dir this repo was unpacked into
# (default /root/gateway-build). Applies gateway manifests + Tyk config. Idempotent.
#
# Invoked by ../deploy-aleph/deploy.sh; you normally don't run this by hand.
set -euo pipefail

export PATH="$PATH:/var/lib/rancher/rke2/bin"
export KUBECONFIG=/etc/rancher/rke2/rke2.yaml

GATEWAY_IMAGE="${GATEWAY_IMAGE:-rkhoja/aleph:latest}"

echo "[1/5] namespace + RBAC + service"
kubectl create namespace models --dry-run=client -o yaml | kubectl apply -f -
kubectl apply -f gateway/k8s/rbac.yaml -f gateway/k8s/service.yaml

echo "[2/5] gateway deployment (image ${GATEWAY_IMAGE})"
sed -e "s#image: rkhoja/aleph:.*#image: ${GATEWAY_IMAGE}#" \
    -e "s#image: model-gateway:.*#image: ${GATEWAY_IMAGE}#" \
    gateway/k8s/deployment.yaml | kubectl apply -f -

echo "[3/5] model cards + InferenceService"
kubectl apply -f gateway/cards/
kubectl apply -f models/command-r-7b/details.yaml
kubectl apply -f models/command-r-7b/inferenceservice.yaml

echo "[4/5] Tyk: API def + required env overrides + NodePort"
kubectl create configmap tyk-api-definitions -n tyk \
    --from-file=model-gateway.json=gateway/tyk/model-gateway-api.json \
    --dry-run=client -o yaml | kubectl apply -f -
# APPPATH: read API defs from the ConfigMap mount (Helm default points at an empty scratch dir).
# ENABLEHASHEDKEYSLISTING: allow GET /tyk/keys (off by default).
kubectl set env deploy/gateway-tyk-oss-tyk-gateway -n tyk \
    TYK_GW_APPPATH=/opt/tyk-gateway/apps \
    TYK_GW_ENABLEHASHEDKEYSLISTING=true
kubectl apply -f gateway/tyk/nodeport.yaml

echo "[5/5] roll + wait"
kubectl rollout restart deploy/gateway-tyk-oss-tyk-gateway -n tyk
kubectl rollout restart deploy/model-gateway -n models 2>/dev/null || true
kubectl rollout status  deploy/model-gateway -n models --timeout=180s || true
echo
echo "DONE. Gateway image: ${GATEWAY_IMAGE}"
echo "Endpoint: http://172.26.92.43:30808  (NodePort)"
echo "Wait for the model to be Ready:  kubectl get isvc command-r-7b -n models -w"
