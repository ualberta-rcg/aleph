#!/usr/bin/env bash
# =============================================================================
# verify-test-model.sh — smoke-test the serving stack after first boot.
# =============================================================================
# Deploys a minimal CPU model (bge-small embeddings, no GPU) and optionally a
# GPU model (TinyLLaMA via HAMi vGPU) to confirm end-to-end routing works:
#   Tyk (VIP:80) → model-gateway → KServe → model container
#
# Usage (from any node with kubectl access):
#   bash verify-test-model.sh cpu          # fast: CPU embeddings only (~2 min)
#   bash verify-test-model.sh gpu          # GPU path via HAMi (~5 min)
#   bash verify-test-model.sh all          # both
#   bash verify-test-model.sh cleanup      # delete test resources
#
# Requires: TYK_KEY env var set to a valid Tyk Bearer token.
#   export TYK_KEY=$(bash ww-overlays/post-deploy/create-tyk-key.sh)
# =============================================================================
set -euo pipefail

MODE="${1:-cpu}"
GW="${GW_URL:-http://$(kubectl get svc tyk-gateway-nodeport -n tyk -o jsonpath='{.status.loadBalancer.ingress[0].ip}' 2>/dev/null)}"
TYK_KEY="${TYK_KEY:-}"

if [ -z "$TYK_KEY" ]; then
  echo "ERROR: set TYK_KEY to a valid Tyk Bearer token." >&2
  echo "  Create one: POST $GW/tyk/keys/create (x-tyk-authorization: <APISecret>)" >&2
  exit 1
fi

deploy_cpu() {
  echo "=== Deploying CPU test model: BAAI/bge-small-en-v1.5 (embeddings via TEI) ==="
  cat <<'EOF' | kubectl apply -f -
apiVersion: serving.kserve.io/v1beta1
kind: InferenceService
metadata:
  name: test-bge-small
  namespace: models
spec:
  predictor:
    minReplicas: 1
    timeout: 600
    containers:
      - name: kserve-container
        image: ghcr.io/huggingface/text-embeddings-inference:cpu-latest
        args:
          - --model-id=BAAI/bge-small-en-v1.5
          - --port=8080
          - --dtype=float32
        ports:
          - containerPort: 8080
            protocol: TCP
        resources:
          requests: { cpu: "2", memory: 4Gi }
          limits:   { cpu: "4", memory: 8Gi }
        readinessProbe:
          httpGet: { path: /health, port: 8080 }
          initialDelaySeconds: 30
          periodSeconds: 10
          failureThreshold: 30
EOF
  echo "Waiting for test-bge-small (up to 3 min)..."
  kubectl wait isvc test-bge-small -n models --for=condition=Ready --timeout=180s || true

  echo "Testing via gateway..."
  HTTP=$(curl -sw '%{http_code}' -o /dev/null -X POST "$GW/v1/embeddings" \
    -H "Authorization: Bearer $TYK_KEY" -H "Content-Type: application/json" \
    -d '{"model":"test-bge-small","input":"hello world"}' 2>/dev/null || echo "000")
  [ "$HTTP" = "200" ] && echo "  PASS (embeddings 200 OK)" || echo "  FAIL HTTP $HTTP"
}

deploy_gpu() {
  echo "=== Deploying GPU test model: TinyLLaMA 1.1B via vLLM + HAMi ==="
  cat <<'EOF' | kubectl apply -f -
apiVersion: v1
kind: PersistentVolumeClaim
metadata:
  name: test-tinyllama-data
  namespace: models
spec:
  accessModes: [ReadWriteOnce]
  resources:
    requests:
      storage: 5Gi
  storageClassName: nfs-models
---
apiVersion: serving.kserve.io/v1beta1
kind: InferenceService
metadata:
  name: test-tinyllama
  namespace: models
spec:
  predictor:
    minReplicas: 1
    timeout: 300
    nodeSelector:
      gpu: "on"
    initContainers:
      - name: hf-fetch
        image: python:3.11-slim
        command: ["bash", "-c"]
        args:
          - |
            pip install -q huggingface_hub
            python3 -c "
            from pathlib import Path
            if Path('/data/config.json').is_file():
                print('already downloaded')
            else:
                from huggingface_hub import snapshot_download
                snapshot_download('TinyLlama/TinyLlama-1.1B-Chat-v1.0', local_dir='/data', local_dir_use_symlinks=False)
            "
        resources:
          requests: { cpu: "1", memory: 2Gi }
          limits:   { cpu: "2", memory: 4Gi }
        volumeMounts:
          - name: model-data
            mountPath: /data
    containers:
      - name: kserve-container
        image: vllm/vllm-openai:v0.8.4
        args:
          - --model=/data
          - --served-model-name=test-tinyllama
          - --port=8080
          - --max-model-len=4096
          - --dtype=float16
          - --gpu-memory-utilization=0.85
        ports:
          - containerPort: 8080
            protocol: TCP
        resources:
          requests:
            cpu: "2"
            memory: 4Gi
            nvidia.com/gpu: "1"
            nvidia.com/gpumem: "4096"
          limits:
            cpu: "4"
            memory: 8Gi
            nvidia.com/gpu: "1"
            nvidia.com/gpumem: "4096"
        readinessProbe:
          httpGet: { path: /v1/models, port: 8080 }
          initialDelaySeconds: 60
          periodSeconds: 15
          failureThreshold: 30
        volumeMounts:
          - name: model-data
            mountPath: /data
            readOnly: true
          - name: shm
            mountPath: /dev/shm
    volumes:
      - name: model-data
        persistentVolumeClaim:
          claimName: test-tinyllama-data
      - name: shm
        emptyDir:
          medium: Memory
          sizeLimit: 2Gi
EOF
  echo "Waiting for test-tinyllama (up to 8 min — first run pulls vLLM image ~9 GB)..."
  kubectl wait isvc test-tinyllama -n models --for=condition=Ready --timeout=480s || true

  echo "Testing via gateway..."
  HTTP=$(curl -sw '%{http_code}' -o /dev/null -X POST "$GW/v1/chat/completions" \
    -H "Authorization: Bearer $TYK_KEY" -H "Content-Type: application/json" \
    -d '{"model":"test-tinyllama","messages":[{"role":"user","content":"hi"}],"max_tokens":10}' 2>/dev/null || echo "000")
  [ "$HTTP" = "200" ] && echo "  PASS (chat completions 200 OK)" || echo "  FAIL HTTP $HTTP"
  echo "  HAMi VRAM check (should show ~4096 MiB, not physical 46068):"
  kubectl exec -n models -l serving.kserve.io/inferenceservice=test-tinyllama \
    -c kserve-container -- nvidia-smi --query-gpu=memory.total --format=csv,noheader 2>/dev/null || echo "  (pod not running)"
}

cleanup() {
  echo "=== Cleaning up test resources ==="
  kubectl delete isvc test-bge-small test-tinyllama -n models --ignore-not-found
  kubectl delete pvc test-tinyllama-data -n models --ignore-not-found
}

case "$MODE" in
  cpu)     deploy_cpu ;;
  gpu)     deploy_gpu ;;
  all)     deploy_cpu; echo; deploy_gpu ;;
  cleanup) cleanup ;;
  *)
    echo "Usage: $0 [cpu|gpu|all|cleanup]"
    exit 1
    ;;
esac
