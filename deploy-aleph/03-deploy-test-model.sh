#!/usr/bin/env bash
# =============================================================================
# Deploy test InferenceServices to verify the full stack
# =============================================================================
# Verifies the full routing path works:
#   curl → Istio local gateway → Knative → KServe → model container
#
# Two test models:
#   cpu — BAAI/bge-small-en-v1.5 via TEI (embeddings, no GPU)
#   gpu — TinyLLaMA 1.1B via vLLM (chat, tests HAMi vGPU)
#
# Run from the control plane node after 01-install.sh + 02-post-install.sh.
# Usage:
#   bash 03-deploy-test-model.sh [cpu|gpu|all]
# =============================================================================

set -euo pipefail

MODE="${1:-cpu}"

deploy_cpu() {
  echo "=== Deploying CPU test model: BAAI/bge-small-en-v1.5 (embeddings via TEI) ==="
  echo "    Tiny model (~130MB), fast tokenizer, no GPU needed"
  echo ""

  cat <<'EOF' | kubectl apply -f -
apiVersion: serving.kserve.io/v1beta1
kind: InferenceService
metadata:
  name: bge-small
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
          limits: { cpu: "4", memory: 8Gi }
        readinessProbe:
          httpGet: { path: /health, port: 8080 }
          initialDelaySeconds: 30
          periodSeconds: 10
          failureThreshold: 30
EOF

  echo ""
  echo "Waiting for bge-small to become Ready..."
  echo "Watch:  kubectl get isvc bge-small -n models -w"
  echo ""
  echo "Test once Ready:"
  echo "  kubectl run curl-test --rm -it --restart=Never --image=curlimages/curl --labels='sidecar.istio.io/inject=false' --command -- sleep 300"
  echo "  kubectl exec curl-test -- curl -s http://bge-small.models.svc.cluster.local/embed -X POST -H 'Content-Type: application/json' -d '{\"inputs\":\"What is deep learning?\"}'"
}

deploy_gpu() {
  echo "=== Deploying GPU test model: TinyLLaMA 1.1B via vLLM (HAMi vGPU) ==="
  echo "    Tests: HAMi GPU scheduling, nvidia runtime, vLLM with GPU"
  echo "    Requests: nvidia.com/gpu: 1, nvidia.com/gpumem: 4096 (4 GiB vGPU slice)"
  echo ""

  cat <<'EOF' | kubectl apply -f -
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
            set -e
            pip install -q huggingface_hub
            python3 -u <<'PY'
            import os
            from pathlib import Path
            if Path("/data/config.json").is_file():
                print("TinyLlama already on PVC, skipping.", flush=True)
            else:
                from huggingface_hub import snapshot_download
                Path("/data").mkdir(parents=True, exist_ok=True)
                print("Downloading TinyLlama/TinyLlama-1.1B-Chat-v1.0 ...", flush=True)
                snapshot_download(
                    repo_id="TinyLlama/TinyLlama-1.1B-Chat-v1.0",
                    local_dir="/data",
                    local_dir_use_symlinks=False,
                )
                print("Done.", flush=True)
            PY
        resources:
          requests: { cpu: "1", memory: 2Gi }
          limits: { cpu: "2", memory: 4Gi }
        volumeMounts:
          - name: model-data
            mountPath: /data
    containers:
      - name: kserve-container
        image: vllm/vllm-openai:v0.8.4
        args:
          - --model=/data
          - --served-model-name=tinyllama-1.1b
          - --port=8080
          - --max-model-len=4096
          - --dtype=float16
          - --gpu-memory-utilization=0.85
          - --trust-remote-code
        env:
          - name: HF_HUB_CACHE
            value: /tmp/hf-cache
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
---
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
EOF

  echo ""
  echo "Waiting for test-tinyllama to become Ready..."
  echo "Watch:  kubectl get isvc test-tinyllama -n models -w"
  echo ""
  echo "NOTE: Requests nvidia.com/gpumem: 4096 (4 GiB VRAM via HAMi)"
  echo "      This uses 1 vGPU slice out of 10 per physical GPU"
  echo ""
  echo "Test once Ready:"
  echo "  kubectl exec curl-test -- curl -s http://test-tinyllama.models.svc.cluster.local/v1/chat/completions -X POST -H 'Content-Type: application/json' -d '{\"model\":\"tinyllama-1.1b\",\"messages\":[{\"role\":\"user\",\"content\":\"Say hello\"}],\"max_tokens\":50}'"
}

case "$MODE" in
  cpu)
    deploy_cpu
    ;;
  gpu)
    deploy_gpu
    ;;
  all)
    deploy_cpu
    echo ""
    deploy_gpu
    ;;
  *)
    echo "Usage: $0 [cpu|gpu|all]"
    echo "  cpu  — Deploy bge-small-en-v1.5 embeddings (no GPU, fast verify)"
    echo "  gpu  — Deploy TinyLLaMA with HAMi vGPU (tests full GPU stack)"
    echo "  all  — Deploy both"
    exit 1
    ;;
esac
