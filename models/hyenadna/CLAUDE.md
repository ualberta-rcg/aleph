# HyenaDNA — Model Context

## What This Model Does

HyenaDNA by LongSafari. 6.5M params (medium variant). State-space model using Hyena operators instead of attention, enabling sequence lengths up to 1 million base pairs with sub-quadratic scaling. This deployment uses the 160K-seqlen variant with max deployed context of 8192 bp. Produces 256-dimensional DNA embeddings for long-range regulatory genomics, promoter prediction, and chromatin accessibility prediction.

## Source Repo

**HuggingFace**: [LongSafari/hyenadna-medium-160k-seqlen-hf](https://huggingface.co/LongSafari/hyenadna-medium-160k-seqlen-hf)
**Paper**: [HyenaDNA: Long-Range Genomic Sequence Modeling at Single Nucleotide Resolution](https://arxiv.org/abs/2306.15794)

Key info from source:
- **Tokenizer**: Character-level (ACGT), trust_remote_code required
- **Max deployed tokens**: 8192 (model supports up to 160K)
- **Model max tokens**: 160,000 (theoretical up to 1M)
- **License**: MIT
- **Embedding dim**: 256
- **Architecture**: Hyena state-space (not attention-based)

## How The Server Works

- **Pattern**: Custom FastAPI embedding server with HuggingFace Transformers
- **Container**: `python:3.11-slim` running `/data/venv/bin/python /app/server.py`
- **Init container**: Creates venv, installs torch+transformers+einops (CPU), downloads model from HF
- **ConfigMap**: `hyenadna-server` — server code embedded in inferenceservice.yaml
- **PVC**: `hyenadna-data` — stores venv + model weights (5Gi, NFS ReadWriteMany)
- **Health**: Custom `/health` endpoint
- **CPU only**: No GPU allocation. PyTorch CPU with float32.
- **Env vars**: `MODEL_DIR=/data/model`, `MODEL_NAME=hyenadna-160k`
- **Extra deps**: `einops` (required by HyenaDNA model code)
- **Pooling**: Mean pooling with attention mask; falls back to simple mean if no mask
- **Output**: OpenAI-compatible `/v1/embeddings` response format

## Gateway Integration

- **k8s ISVC name**: `hyenadna`
- **API model ID**: `hyenadna-6.5m` (mapped via ISVC_NAME_MAP)
- **MODEL_TYPE**: embedding
- **KSERVE_CUSTOM_MODELS**: yes — uses `/v1/` prefix
- **CONTEXT_WINDOWS**: 32768 (gateway-level cap; server uses 8192)
- **Scale-to-zero**: minReplicas=0, scaleTarget=2, 900s retention

## Deploy / Update / Test

```bash
# Deploy
kubectl apply -f models/hyenadna/pvc.yaml
kubectl apply -f models/hyenadna/inferenceservice.yaml
kubectl apply -f models/hyenadna/details.yaml

# Check status
kubectl get pods -n models -l serving.kserve.io/inferenceservice=hyenadna

# Logs
kubectl logs -n models -l serving.kserve.io/inferenceservice=hyenadna -c kserve-container -f

# Test externally via gateway VIP + Tyk auth
GW_URL=http://<GATEWAY_VIP> TYK_KEY=<key> python3 models/hyenadna/test.py
```

## Known Issues / Optimization Opportunities

1. **CPU only**: Model runs on CPU with PyTorch. HyenaDNA is designed for long sequences which are computationally expensive on CPU.

2. **Deployed context vs model capacity**: Server uses MAX_LEN=8192 but model supports up to 160K. Could increase for longer-range regulatory analysis, at the cost of memory and latency.

3. **trust_remote_code required**: Model uses custom Hyena operator code from the HF repo.

4. **Token count uses char count**: Usage reports `prompt_tokens` as character count (`sum(len(s))`), appropriate for DNA sequences.

5. **HF_TOKEN plaintext**: Token stored as plaintext env var in init container (intentional per docs).

6. **Gateway context mismatch**: CONTEXT_WINDOWS in gateway says 32768 but server MAX_LEN is 8192. Gateway limit is looser than actual server limit.

## Files

| File | Purpose |
|------|---------|
| `details.yaml` | ConfigMap with model metadata |
| `inferenceservice.yaml` | ConfigMap + ISVC spec: init container + FastAPI container |
| `kustomization.yaml` | Kustomize resources |
| `pvc.yaml` | Dedicated PVC (hyenadna-data) |

**IMPORTANT: When changing this model's deployment config (inferenceservice.yaml), update details.yaml to match.**
