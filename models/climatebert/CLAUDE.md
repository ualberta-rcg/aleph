# ClimateBERT — Model Context

## What This Model Does

ClimateBERT by climatebert.org. DistilRoBERTa-based models for climate-focused NLP. Includes climate text detection (is this climate-related?), net-zero/reduction commitment detection, and climate text embeddings. Domain-adapted on climate and sustainability text. Max sequence length 512 tokens.

## Source Repo

**HuggingFace**: [climatebert/distilroberta-base-climate-f](https://huggingface.co/climatebert/distilroberta-base-climate-f)

Key info from source:
- **Input format**: Text strings for climate analysis
- **Max tokens**: 512
- **License**: MIT
- **Architecture**: DistilRoBERTa (82M params)
- **Sub-models**: base (embeddings), detect (climate detector), netzero (commitment detector)

## How The Server Works

- **Pattern**: Custom FastAPI classification server with HuggingFace Transformers
- **Container**: `python:3.11-slim` — installs deps at every startup (no venv/PVC pattern)
- **No PVC**: Uses RawDeployment, installs pip deps every restart (~3-5 min cold start)
- **ConfigMap**: `climatebert-server` — server code embedded in inferenceservice.yaml
- **Health**: Custom `/health` endpoint + startupProbe
- **CPU only**: No GPU allocation
- **Deployment mode**: RawDeployment (not Serverless)
- **Output**: Custom `/v1/science/classify` and `/v1/embeddings` response formats

## Gateway Integration

- **k8s ISVC name**: `climatebert`
- **API model ID**: `climatebert` (no mapping in ISVC_NAME_MAP)
- **MODEL_TYPE**: defaults to "chat" — needs update to "classify"
- **KSERVE_CUSTOM_MODELS**: not listed — needs addition
- **Scale-to-zero**: minReplicas=0, maxReplicas=1 (RawDeployment)

## Deploy / Update / Test

```bash
# Deploy
kubectl apply -k models/climatebert/

# Check status
kubectl get pods -n models -l serving.kserve.io/inferenceservice=climatebert

# Logs
kubectl logs -n models -l serving.kserve.io/inferenceservice=climatebert -c kserve-container -f

# Test (public)
curl -X POST https://inference.kubeflow.vulcan.alliancecan.ca/serving/api/v1/science/classify \
  -H "Content-Type: application/json" \
  -d '{"model":"climatebert","text":"The company committed to reducing carbon emissions by 50% by 2030.","task":"netzero"}'
```

## Known Issues / Optimization Opportunities

1. **No venv/PVC pattern**: Installs pip deps every restart (~3-5 min cold start). Should use venv-on-PVC.

2. **RawDeployment mode**: Does not use Knative scaling. Consider Serverless for scale-to-zero.

3. **Loads 3 models**: Loads base, detect, and netzero models simultaneously. Higher memory usage.

4. **No model caching**: All 3 models downloaded from HF at runtime each restart.

5. **Gateway registration incomplete**: Model not in MODEL_TYPES, MODEL_METADATA, KSERVE_CUSTOM_MODELS, or CONTEXT_WINDOWS in gateway.py.

## Files

| File | Purpose |
|------|---------|
| `details.yaml` | ConfigMap with model metadata |
| `inferenceservice.yaml` | ConfigMap + ISVC spec (no PVC) |

**IMPORTANT: When changing this model's deployment config (inferenceservice.yaml), update details.yaml to match.**
