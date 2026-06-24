# Caduceus Model Deployment

## What this model does
Caduceus from Kuleshov Lab (Cornell) is a bidirectional Mamba DNA foundation model supporting up to 131k bp context. Uses reverse complement equivariance. ~45M parameters.

## Source
- **HF**: kuleshov-group/caduceus-ps_seqlen-131k_d_model-256_n_layer-16 | **License**: Apache-2.0

## How the server works
- `POST /v1/embeddings` -- DNA sequence(s) to embeddings
- Uses AutoModelForMaskedLM with trust_remote_code, output_hidden_states
- Mean-pooled last hidden state, **fp32** on GPU (SSMs are precision-sensitive)
- RCPS: forward + reverse-complement averaged → 256-dim (RC-invariant)
- Server truncates at max_length=8192 (model supports 131k)

## Our config vs source
- Uses pytorch/pytorch CUDA devel image (needs compilation)
- mamba-ssm and causal-conv1d compiled from source (15-20 min init)
- venv-on-PVC; 1x L40S HAMi slice (`nvidia.com/gpumem: 10240`), 10Gi PVC, minReplicas: 0

## Deploy/update/test
```bash
kubectl apply -f models/caduceus/pvc.yaml
kubectl apply -f models/caduceus/inferenceservice.yaml
kubectl apply -f models/caduceus/details.yaml
kubectl get inferenceservice caduceus -n models

# Test (external via gateway VIP + Tyk auth)
GW_URL=http://<GATEWAY_VIP> TYK_KEY=<key> python3 models/caduceus/test.py
# Or in-pod (no auth):
cat models/caduceus/test.py | kubectl exec -i -n models deploy/model-gateway -c gateway -- python3 -
```

## Gateway integration
- type `embedding` (details.yaml schema v2); KServe custom model.

## Known Issues / Gotchas
- **Pinned build**: `torch==2.2.0` + `mamba-ssm==1.2.0`, `numpy<2`. Newer combos break the
  custom mamba kernels. Mamba/causal-conv1d compile from source ~20 min on first deploy; the
  PVC venv is cached so warm restarts are ~5s.
- **fp32 only**: SSM precision is sensitive — do not switch to fp16.
- Last run (2026-06-19): **7 PASS / 2 EXP / 0 FAIL**.
