# Science-Embed — Shared Embedding Backend Service

## Status: Standalone Deployment (NOT an InferenceService)

## Overview
Science-embed is a shared Kubernetes Deployment that serves multiple science
embedding models from a single pod. It is NOT managed by KServe/Knative.

## Models Served
- **esm2-650m** — protein embeddings (CPU)
- **nucleotide-transformer-500m** — DNA embeddings (CPU)
- **esm2-3b** — protein embeddings (GPU)

## Source
- ESM2: https://huggingface.co/facebook/esm2_t33_3B_UR50D
- Nucleotide Transformer: https://huggingface.co/InstaDeepAI/nucleotide-transformer-v2-500m-multi-species

## Deployment Summary
- **Type**: Standard Deployment (apps/v1)
- **Replicas**: 1 (fixed, no autoscaling)
- **Image**: python:3.11-slim
- **PVC**: small-models (readOnly, shared across models)
- **Dependencies**: pip install --target=/pkgs (emptyDir, rebuilt each restart)

## API
- `POST /v1/embeddings` — OpenAI-compatible embeddings
- `GET /health` — returns loaded model list
- `GET /v1/models` — lists available models

## Gateway Integration
- Registered in EXTRA_MODELS as `nucleotide-transformer-500m` backend
- Backend URL: http://science-embed.models.svc.cluster.local:8080
- Users access it via `model: nucleotide-transformer-500m`
- Also backs esm2-650m and esm2-3b

## Audit Notes
- Dependencies are installed to emptyDir (/pkgs), rebuilt every pod restart
- Cold start is slow (~3-5 minutes for dependency install)
- Should migrate to PVC-based venv pattern for faster restarts
- esm2-3b uses GPU when available
- Fixed 1 replica — no scale-to-zero

## Files
- `deployment.yaml` — ConfigMap (server.py) + Service + Deployment
- `details.yaml` — model metadata ConfigMap

## Update Reminder
- Consider migrating to PVC venv pattern for faster cold starts
- Add kustomization.yaml for consistent deploy workflow
- Monitor if esm2-3b should have its own ISVC
