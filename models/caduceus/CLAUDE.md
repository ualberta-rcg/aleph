# Caduceus Model Deployment

## What this model does
Caduceus from Kuleshov Lab (Cornell) is a bidirectional Mamba DNA foundation model supporting up to 131k bp context. Uses reverse complement equivariance. ~45M parameters.

## Source
- **HF**: kuleshov-group/caduceus-ps_seqlen-131k_d_model-256_n_layer-16 | **License**: Apache-2.0

## How the server works
- `POST /v1/embeddings` -- DNA sequence(s) to embeddings
- Uses AutoModelForMaskedLM with trust_remote_code, output_hidden_states
- Mean-pooled last hidden state, fp16 on GPU
- Server truncates at max_length=8192 (model supports 131k)

## Our config vs source
- Uses pytorch/pytorch:2.6.0-cuda12.6-cudnn9-devel image (needs compilation)
- mamba-ssm and causal-conv1d compiled from source (15-20 min init)
- Conda-based venv at `/data/caduceus_env`
- 1x L40S (full GPU, not shared), 10Gi PVC, minReplicas: 0

## Deploy/update/test
```bash
kubectl apply -k models/caduceus/
kubectl get inferenceservice caduceus -n models
```

## Gateway integration
- MODEL_TYPES: `"caduceus": "embedding"` | KServe custom | Not in MODEL_METADATA

## IMPORTANT
- Do NOT modify inferenceservice.yaml unless explicitly asked
