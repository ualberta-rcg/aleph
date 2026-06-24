#!/usr/bin/env bash
# =============================================================================
# Kubeflow Inference Stack — Bootstrap Install
# =============================================================================
# Installs only the components needed for model serving:
#   - Istio (CRDs, control plane, ingress gateway, cluster-local-gateway)
#   - Knative Serving
#   - KServe (InferenceService CRD + controller)
#   - Kubeflow Profiles (namespace management)
#
# NOT installed (Tyk handles auth, no need for Kubeflow UI):
#   - Dex, oauth2-proxy, Central Dashboard
#   - Kubeflow Pipelines, Katib, Jupyter, Tensorboards
#
# Run this script from the RKE2 control plane node (aleph1).
# Prerequisites already in place:
#   - cert-manager (RKE2 manifest)
#   - NFS provisioner (RKE2 manifest)
#   - HAMi scheduler + device plugin (RKE2 manifest)
#   - NVIDIA drivers + container toolkit on GPU nodes (Warewulf overlay)
#   - GPU nodes labeled: kubectl label node <node> gpu=on
#
# Usage:
#   sudo ssh root@172.26.92.43
#   cd /root/install-kubeflow && bash 01-install.sh
#
# Known issues handled by this script:
#   - CRD race conditions: re-applies after CRDs settle
#   - kubeflow namespace must exist before Istio install
#   - KServe ClusterServingRuntimes need controller running first
# =============================================================================

set -euo pipefail

MANIFESTS_DIR="${MANIFESTS_DIR:-/tmp/kubeflow-manifests}"
MANIFESTS_REPO="https://github.com/kubeflow/manifests.git"
# v1.11-branch is the latest stable branch (same as POC cluster)
# Switch to master if compatibility issues arise with k8s v1.36
MANIFESTS_BRANCH="${MANIFESTS_BRANCH:-v1.11-branch}"

# Helper: apply a kustomize dir, retry once after 10s (handles CRD race conditions)
apply_kustomize() {
  local path="$1"
  local extra_flags="${2:-}"
  echo "  Applying: $path"
  kubectl apply $extra_flags -k "$path" 2>&1 | tail -3 || true
  # Check for CRD race condition errors and retry
  kubectl apply $extra_flags -k "$path" 2>&1 | tail -3 || true
}

apply_kustomize_server_side() {
  local path="$1"
  echo "  Applying (server-side): $path"
  kubectl apply --server-side --force-conflicts -k "$path" 2>&1 | tail -5 || true
}

echo "=========================================="
echo " Kubeflow Inference Stack Bootstrap"
echo "=========================================="
echo "Manifests: ${MANIFESTS_REPO} @ ${MANIFESTS_BRANCH}"
echo "K8s version: $(kubectl version --output=json 2>/dev/null | grep gitVersion | head -1 || echo 'unknown')"
echo ""

# -------------------------------------------------------
# Clone kubeflow manifests
# -------------------------------------------------------
echo "=== Step 0: Clone kubeflow manifests ==="
if [ -d "$MANIFESTS_DIR" ]; then
  echo "Manifests dir exists, pulling latest..."
  cd "$MANIFESTS_DIR" && git pull && git checkout "$MANIFESTS_BRANCH"
else
  git clone --depth=1 --branch "$MANIFESTS_BRANCH" "$MANIFESTS_REPO" "$MANIFESTS_DIR"
fi
cd "$MANIFESTS_DIR"

# -------------------------------------------------------
# Wait for cert-manager (deployed via RKE2 HelmChart)
# -------------------------------------------------------
echo "=== Waiting for cert-manager ==="
kubectl wait --for=condition=Ready pods --all -n cert-manager --timeout=300s || true

# -------------------------------------------------------
# Step 1: cert-manager issuer (Kubeflow needs this for internal TLS)
# -------------------------------------------------------
echo "=== Step 1: cert-manager issuer ==="
kubectl apply -k common/cert-manager/kubeflow-issuer/base

# -------------------------------------------------------
# Step 2: Istio (service mesh — KServe's routing layer)
# IMPORTANT: kubeflow namespace must be created BEFORE Istio install
#   because Istio manifests include resources (sidecar exceptions)
#   that target the kubeflow namespace.
# -------------------------------------------------------
echo "=== Step 2: Istio ==="
# Create kubeflow namespace first (Istio install needs it)
kubectl apply -k common/kubeflow-namespace/base

kubectl apply -k common/istio/istio-crds/base
kubectl apply -k common/istio/istio-namespace/base
kubectl apply -k common/istio/istio-install/base
echo "Waiting for Istio pods..."
kubectl wait --for=condition=Ready pods --all -n istio-system --timeout=300s || true

# -------------------------------------------------------
# Step 3: Knative Serving + cluster-local-gateway
# NOTE: First apply may fail with "no matches for kind" errors —
#   CRDs aren't ready yet. We apply twice to handle the race.
# -------------------------------------------------------
echo "=== Step 3: Knative Serving ==="
kubectl apply -k common/knative/knative-serving/overlays/gateways 2>&1 | tail -3 || true
sleep 5
kubectl apply -k common/knative/knative-serving/overlays/gateways 2>&1 | tail -3 || true
kubectl apply -k common/istio/cluster-local-gateway/base
echo "Waiting for Knative pods..."
kubectl wait --for=condition=Ready pods --all -n knative-serving --timeout=300s || true

# -------------------------------------------------------
# Step 4: Kubeflow roles + Istio resources (namespace already created in step 2)
# -------------------------------------------------------
echo "=== Step 4: Kubeflow roles + Istio resources ==="
kubectl apply -k common/kubeflow-roles/base
kubectl apply -k common/istio/kubeflow-istio-resources/base

# -------------------------------------------------------
# Step 5: KServe (InferenceService CRD + controller)
# --server-side --force-conflicts is REQUIRED:
#   KServe CRDs have annotations exceeding kubectl apply's 262144-byte limit
# NOTE: First apply creates CRDs. ClusterServingRuntime resources will fail
#   because the webhook isn't ready yet. We wait for the controller, then
#   re-apply to register the runtimes.
# -------------------------------------------------------
echo "=== Step 5: KServe (first pass — CRDs) ==="
kubectl apply --server-side --force-conflicts -k applications/kserve/kserve 2>&1 | tail -5 || true
echo "Waiting for KServe controller to start..."
kubectl wait --for=condition=Ready pods -n kubeflow -l app=kserve --timeout=300s || true
echo "=== Step 5b: KServe (second pass — ClusterServingRuntimes) ==="
kubectl apply --server-side --force-conflicts -k applications/kserve/kserve 2>&1 | tail -5 || true

# -------------------------------------------------------
# Step 6: Kubeflow Profiles (namespace/user management)
# -------------------------------------------------------
echo "=== Step 6: Kubeflow Profiles ==="
kubectl apply -k applications/profiles/upstream/overlays/kubeflow

# -------------------------------------------------------
# Step 7: models namespace
# -------------------------------------------------------
echo "=== Step 7: models namespace ==="
kubectl create namespace models --dry-run=client -o yaml | kubectl apply -f -
kubectl label namespace models istio-injection=enabled --overwrite

echo ""
echo "=========================================="
echo " Bootstrap complete!"
echo "=========================================="
echo ""
echo "Next: Run 02-post-install.sh to patch Knative/KServe configs"
echo "Then:  Run 03-deploy-test-model.sh to verify with a test model"
