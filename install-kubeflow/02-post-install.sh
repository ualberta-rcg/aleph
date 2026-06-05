#!/usr/bin/env bash
# =============================================================================
# Kubeflow Inference Stack — Post-Install Patches
# =============================================================================
# Applies critical config patches after the bootstrap install:
#   1. Knative config-features: enable PVCs, init containers, node selectors, etc.
#   2. KServe inferenceservice-config: ingress domain, resource defaults
#   3. Istio authorization: allow traffic in models namespace
#      (Kubeflow installs a global-deny-all policy that blocks everything)
#   4. Models namespace annotations
#
# Run from the RKE2 control plane node after 01-install.sh completes.
# Usage:
#   bash 02-post-install.sh
# =============================================================================

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# -------------------------------------------------------
# 1. Patch Knative config-features
# Required for KServe InferenceServices that use PVCs (model weights),
# init containers (model downloaders), node selectors (GPU placement),
# and runtime class (nvidia for GPU containers).
# -------------------------------------------------------
echo "=== Patching Knative config-features ==="
kubectl patch configmap config-features -n knative-serving --type merge -p '{
  "data": {
    "kubernetes.podspec-persistent-volume-claim": "enabled",
    "kubernetes.podspec-persistent-volume-write": "enabled",
    "kubernetes.podspec-securitycontext": "enabled",
    "kubernetes.podspec-init-containers": "enabled",
    "kubernetes.podspec-nodeselector": "enabled",
    "kubernetes.podspec-affinity": "enabled",
    "kubernetes.podspec-tolerations": "enabled",
    "kubernetes.podspec-runtimeclassname": "enabled"
  }
}'
echo "Knative config-features patched."

# -------------------------------------------------------
# 2. Patch KServe inferenceservice-config
# Sets ingress configuration and storage initializer defaults.
# -------------------------------------------------------
echo "=== Patching KServe inferenceservice-config ==="
if [ -f "$SCRIPT_DIR/configs/inferenceservice-config.yaml" ]; then
  kubectl apply -f "$SCRIPT_DIR/configs/inferenceservice-config.yaml" -n kubeflow
  echo "KServe inferenceservice-config patched."
else
  echo "WARNING: configs/inferenceservice-config.yaml not found, skipping."
fi

# -------------------------------------------------------
# 3. Istio authorization policy for models namespace
# Kubeflow installs a global-deny-all AuthorizationPolicy in istio-system.
# Without this, all traffic to pods with Istio sidecars is blocked.
# The models namespace needs an explicit ALLOW policy.
# -------------------------------------------------------
echo "=== Creating Istio allow policy for models namespace ==="
cat <<'EOF' | kubectl apply -f -
apiVersion: security.istio.io/v1
kind: AuthorizationPolicy
metadata:
  name: allow-all
  namespace: models
spec:
  action: ALLOW
  rules:
  - {}
EOF
echo "Istio authorization policy created."

# -------------------------------------------------------
# 4. Annotate models namespace for KServe tag routing
# -------------------------------------------------------
echo "=== Annotating models namespace ==="
kubectl label namespace models istio-injection=enabled --overwrite
kubectl annotate namespace models serving.kserve.io/enable-tag-routing=true --overwrite 2>/dev/null || true
echo "Models namespace labeled and annotated."

# -------------------------------------------------------
# 5. Verify critical pods are running
# -------------------------------------------------------
echo ""
echo "=== Verification ==="
echo "Istio pods:"
kubectl get pods -n istio-system -o wide 2>/dev/null || echo "  No pods found"
echo ""
echo "Knative pods:"
kubectl get pods -n knative-serving -o wide 2>/dev/null || echo "  No pods found"
echo ""
echo "KServe pods:"
kubectl get pods -n kubeflow -l app=kserve -o wide 2>/dev/null || echo "  No pods found"
echo ""
echo "Authorization policies:"
kubectl get authorizationpolicy -n models 2>/dev/null || echo "  None found"
echo ""
echo "=========================================="
echo " Post-install patches applied!"
echo "=========================================="
echo ""
echo "Next: Run 03-deploy-test-model.sh to verify everything works"
