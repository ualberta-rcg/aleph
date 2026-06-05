#!/usr/bin/env bash
# Runs ON the head node (172.26.92.230), from the dir this repo was unpacked into
# (default /root/gateway-build). Builds the gateway image, imports it into RKE2's
# containerd, and applies all manifests + Tyk config. Idempotent — safe to re-run.
#
# Invoked by ../deploy.sh; you normally don't run this by hand.
set -euo pipefail

export PATH="$PATH:/var/lib/rancher/rke2/bin"
export KUBECONFIG=/etc/rancher/rke2/rke2.yaml

TAG="${TAG:-0.3}"
# IMPORTANT: import into RKE2's containerd, not the host/Docker one, or the pod
# gets ErrImageNeverPull (imagePullPolicy: Never).
CTR="ctr --address /run/k3s/containerd/containerd.sock -n k8s.io"

echo "[1/6] build + import image model-gateway:${TAG}"
docker build -t "model-gateway:${TAG}" gateway/
docker save "model-gateway:${TAG}" | ${CTR} images import -

echo "[2/6] namespace + RBAC + service"
kubectl create namespace models --dry-run=client -o yaml | kubectl apply -f -
kubectl apply -f gateway/k8s/rbac.yaml -f gateway/k8s/service.yaml

echo "[3/6] gateway deployment (tag ${TAG})"
sed "s#image: model-gateway:.*#image: model-gateway:${TAG}#" \
    gateway/k8s/deployment.yaml | kubectl apply -f -

echo "[4/6] model cards + InferenceService"
kubectl apply -f gateway/cards/
kubectl apply -f models/command-r-7b/details.yaml
kubectl apply -f models/command-r-7b/inferenceservice.yaml

echo "[5/6] Tyk: API def + required env overrides + NodePort"
kubectl create configmap tyk-api-definitions -n tyk \
    --from-file=model-gateway.json=gateway/tyk/model-gateway-api.json \
    --dry-run=client -o yaml | kubectl apply -f -
# APPPATH: read API defs from the ConfigMap mount (Helm default points at an empty scratch dir).
# ENABLEHASHEDKEYSLISTING: allow GET /tyk/keys (off by default).
kubectl set env deploy/gateway-tyk-oss-tyk-gateway -n tyk \
    TYK_GW_APPPATH=/opt/tyk-gateway/apps \
    TYK_GW_ENABLEHASHEDKEYSLISTING=true
kubectl apply -f gateway/tyk/nodeport.yaml

echo "[6/6] roll + wait"
kubectl rollout restart deploy/gateway-tyk-oss-tyk-gateway -n tyk
kubectl rollout restart deploy/model-gateway -n models 2>/dev/null || true
kubectl rollout status  deploy/model-gateway -n models --timeout=120s || true
echo
echo "DONE. Endpoint: http://172.26.92.230:30808  (NodePort)"
echo "Wait for the model to be Ready:  kubectl get isvc command-r-7b -n models -w"
