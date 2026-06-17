#!/usr/bin/env bash
# =============================================================================
# Install Tyk OSS Gateway — Reverse Proxy in front of Istio/KServe
# =============================================================================
# Architecture:
#   user → LB/Traefik → Tyk Gateway (ns:tyk) → knative-local-gateway → KServe
#
# Tyk provides: API key auth, rate limiting, request routing, analytics
# Istio/Knative: service mesh routing to InferenceServices
#
# How routing works:
#   - Each KServe InferenceService creates an ExternalName service like
#     <model>.models.svc.cluster.local → knative-local-gateway.istio-system
#   - Tyk proxies to these ExternalName services directly
#   - The Host header matches the VirtualService, Istio routes to the right pod
#   - API definitions are loaded via Tyk's REST API (not file mount)
#
# Prerequisites:
#   - Helm 3 CLI on the control plane node
#   - Istio + Knative installed (01-install.sh)
#   - Post-install patches applied (02-post-install.sh)
#   - At least one InferenceService deployed (03-deploy-test-model.sh)
#
# Run from the control plane node:
#   bash 04-install-tyk-gateway.sh
# =============================================================================

set -euo pipefail

NAMESPACE="tyk"
APISecret="${TYK_API_SECRET:?set TYK_API_SECRET (Tyk gateway APISecret) — see .env / .env.example}"
TYK_SVC="gateway-svc-tyk-oss-tyk-gateway.${NAMESPACE}.svc.cluster.local:8080"

echo "=========================================="
echo " Tyk OSS Gateway Install"
echo "=========================================="
echo ""

# -------------------------------------------------------
# 1. Create namespace
# -------------------------------------------------------
echo "=== Creating namespace ${NAMESPACE} ==="
kubectl create namespace "${NAMESPACE}" 2>/dev/null || true

# -------------------------------------------------------
# 2. Install Redis (required by Tyk for rate limiting, sessions)
# -------------------------------------------------------
echo "=== Installing Redis ==="
helm repo add bitnami https://charts.bitnami.com/bitnami 2>/dev/null || true
helm repo update

helm upgrade tyk-redis bitnami/redis \
  -n "${NAMESPACE}" \
  --install \
  --set auth.enabled=true \
  --set architecture=standalone \
  --set master.persistence.enabled=false \
  --set replica.replicaCount=0 \
  --set resources.requests.cpu=50m \
  --set resources.requests.memory=64Mi \
  --set resources.limits.cpu=250m \
  --set resources.limits.memory=128Mi

echo "Waiting for Redis..."
kubectl wait --for=condition=ready pod -l app.kubernetes.io/name=redis -n "${NAMESPACE}" --timeout=120s || true

# -------------------------------------------------------
# 3. Install Tyk OSS Gateway
# -------------------------------------------------------
echo "=== Installing Tyk OSS Gateway ==="
helm repo add tyk-helm https://helm.tyk.io/public/helm/charts/ 2>/dev/null || true
helm repo update

helm upgrade tyk-oss tyk-helm/tyk-oss \
  -n "${NAMESPACE}" \
  --install \
  --set global.secrets.APISecret="${APISecret}" \
  --set global.redis.addrs="{tyk-redis-master.${NAMESPACE}.svc.cluster.local:6379}" \
  --set global.redis.passSecret.name=tyk-redis \
  --set global.redis.passSecret.keyName=redis-password \
  --set global.redis.enableCluster=false \
  --set global.components.pump=false \
  --set global.components.operator=false \
  --set global.tls.gateway=false \
  --set tyk-gateway.gateway.replicaCount=1 \
  --set tyk-gateway.service.type=ClusterIP \
  --set tyk-gateway.service.port=8080 \
  --set tyk-gateway.ingress.enabled=false

echo "Waiting for Tyk Gateway..."
kubectl wait --for=condition=ready pod -l app.kubernetes.io/name=tyk-gateway -n "${NAMESPACE}" --timeout=120s || true

# -------------------------------------------------------
# 4. Load API definitions via Tyk REST API
#    Tyk OSS doesn't auto-load from file mounts — use the Gateway API.
#    Each definition maps a listen path to an InferenceService.
# -------------------------------------------------------
echo "=== Loading API definitions via REST API ==="

# Helper: create or update a Tyk API definition
# Usage: add_tyk_api <api_id> <listen_path> <target_url>
add_tyk_api() {
  local api_id="$1"
  local listen_path="$2"
  local target_url="$3"

  echo "  ${api_id}: ${listen_path} → ${target_url}"

  # Use a temporary pod to hit Tyk's REST API
  # (Tyk gateway is only reachable inside the cluster)
  kubectl run "tyk-api-${api_id}" --restart=Never --image=curlimages/curl \
    --labels='sidecar.istio.io/inject=false' \
    --command -- sleep 30 2>/dev/null || true
  kubectl wait --for=condition=Ready pod "tyk-api-${api_id}" --timeout=30s 2>/dev/null || sleep 3

  # Create/update the API definition
  kubectl exec "tyk-api-${api_id}" -- curl -s --max-time 10 \
    "http://${TYK_SVC}/tyk/apis" \
    -H "x-tyk-authorization: ${APISecret}" \
    -H "Content-Type: application/json" \
    -d "{
      \"name\": \"${api_id}\",
      \"slug\": \"${api_id}\",
      \"api_id\": \"${api_id}\",
      \"org_id\": \"orgid\",
      \"use_keyless\": true,
      \"version_data\": {
        \"not_versioned\": true,
        \"versions\": {
          \"Default\": {
            \"name\": \"Default\",
            \"use_extended_paths\": true
          }
        }
      },
      \"proxy\": {
        \"listen_path\": \"${listen_path}\",
        \"target_url\": \"${target_url}\",
        \"strip_listen_path\": true,
        \"enable_load_balancing\": false
      },
      \"active\": true,
      \"domain\": \"\",
      \"do_not_track\": true
    }" 2>/dev/null

  kubectl delete pod "tyk-api-${api_id}" --force --grace-period=0 2>/dev/null || true
}

# --- Add API definitions for deployed InferenceServices ---
# Each maps a Tyk listen path to the InferenceService's ExternalName service.
# The ExternalName points to knative-local-gateway, which routes via Host header.

# Check which InferenceServices exist and create API definitions for them
ISVC_LIST=$(kubectl get isvc -n models -o jsonpath='{range .items[*]}{.metadata.name}{"\n"}{end}' 2>/dev/null || true)

if [ -z "$ISVC_LIST" ]; then
  echo "  No InferenceServices found in models namespace."
  echo "  Deploy models with 03-deploy-test-model.sh, then re-run this script"
  echo "  or add API definitions manually with add_tyk_api()."
else
  for isvc in $ISVC_LIST; do
    add_tyk_api "${isvc}" "/serving/${isvc}/" "http://${isvc}.models.svc.cluster.local"
  done
fi

# -------------------------------------------------------
# 5. Hot-reload Tyk to pick up new API definitions
# -------------------------------------------------------
echo "=== Hot-reloading Tyk Gateway ==="
kubectl run tyk-reload --restart=Never --image=curlimages/curl \
  --labels='sidecar.istio.io/inject=false' \
  --command -- sleep 10 2>/dev/null || true
sleep 3

kubectl exec tyk-reload -- curl -s --max-time 10 \
  "http://${TYK_SVC}/tyk/reload/group" \
  -H "x-tyk-authorization: ${APISecret}" \
  -X GET 2>/dev/null || true

kubectl delete pod tyk-reload --force --grace-period=0 2>/dev/null || true

# -------------------------------------------------------
# 6. Verify
# -------------------------------------------------------
echo ""
echo "=== Verification ==="
kubectl get pods -n "${NAMESPACE}" -o wide
echo ""
kubectl get svc -n "${NAMESPACE}"
echo ""

# Quick test: if bge-small exists, hit it through Tyk
if echo "$ISVC_LIST" | grep -q "bge-small" 2>/dev/null; then
  echo "=== End-to-end test: Tyk → bge-small ==="
  kubectl run tyk-test --restart=Never --image=curlimages/curl \
    --labels='sidecar.istio.io/inject=false' \
    --command -- sleep 30 2>/dev/null || true
  sleep 3

  HTTP_CODE=$(kubectl exec tyk-test -- curl -sw '%{http_code}' -o /dev/null --max-time 15 \
    "http://${TYK_SVC}/serving/bge-small/embed" \
    -X POST -H 'Content-Type: application/json' \
    -d '{"inputs":"What is deep learning?"}' 2>/dev/null || echo "000")

  kubectl delete pod tyk-test --force --grace-period=0 2>/dev/null || true

  if [ "$HTTP_CODE" = "200" ]; then
    echo "  ✅ Tyk → bge-small → 200 OK (embeddings working)"
  else
    echo "  ❌ Got HTTP ${HTTP_CODE} — check Tyk logs and Istio VirtualService"
  fi
fi

echo ""
echo "=========================================="
echo " Tyk OSS Gateway installed!"
echo "=========================================="
echo ""
echo "Gateway:  ${TYK_SVC}"
echo "Secret:   ${APISecret}"
echo ""
echo "API definitions loaded (per InferenceService):"
for isvc in $ISVC_LIST; do
  echo "  /serving/${isvc}/* → ${isvc}.models → KServe"
done
echo ""
echo "Test from cluster:"
echo "  kubectl run curl-test --rm -it --restart=Never --image=curlimages/curl \\"
echo "    --labels='sidecar.istio.io/inject=false' --command -- sleep 300"
echo "  kubectl exec curl-test -- curl -s http://${TYK_SVC}/serving/bge-small/embed \\"
echo "    -X POST -H 'Content-Type: application/json' -d '{\"inputs\":\"hello\"}'"
echo ""
echo "Adding new models:"
echo "  After deploying an InferenceService, add it to Tyk with:"
echo "  bash 04-install-tyk-gateway.sh  # re-runs and picks up new ISVCs"
echo "  Or manually via the Tyk REST API:"
echo "  POST http://${TYK_SVC}/tyk/apis"
echo "  GET  http://${TYK_SVC}/tyk/reload/group  (hot reload)"
