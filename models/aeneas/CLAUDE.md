# Aeneas Model Deployment

## What this model does
Aeneas is a generative neural network from DeepMind (Nature 2025) for contextualising Latin inscriptions. It restores missing text, dates inscriptions, and predicts geographic origin. Uses JAX/Flax with the predictingthepast framework.

## Source
- **Repo**: google-deepmind/predictingthepast (https://github.com/google-deepmind/predictingthepast)
- **Weights**: GCS ithaca-resources bucket (public)
- **License**: Apache-2.0
- **Parameters**: ~200M

## How the server works
- FastAPI server embedded as ConfigMap (`aeneas-server`)
- On startup: loads JAX model from pickle checkpoint at `/data/aeneas_117149994_2.pkl`
- Loads auxiliary data (LED dataset, retrieval embeddings)
- `POST /v1/science/predict` -- accepts `text` (Latin, 50-750 chars, # for gaps) or `demo: true`
- Returns restoration, attribution (dating), and contextualization (geography)
- JAX GPU runtime, 1x L40S

## Our config vs source
- Uses python:3.11 base (not slim) for pip install in main container
- Weights downloaded from GCS in init container to PVC
- Source code cloned from GitHub in init container
- GPU assigned via nodeSelector NVIDIA-L40S
- minReplicas: 0, timeout: 180s
- Demo mode returns hardcoded response for quick testing

## Deploy/update/test commands
```bash
kubectl apply -k models/aeneas/
kubectl get inferenceservice aeneas -n models
kubectl get pods -n models -l serving.kserve.io/inferenceservice=aeneas
```

## Gateway integration
- MODEL_TYPES: `"aeneas": "structure"`
- Not in MODEL_METADATA (needs adding)
- Not in CONTEXT_WINDOWS (needs adding: 750)
- ISVC name = API name: `aeneas`

## Known Issues
- pip installs at runtime in main container (slow cold start)
- No pip version pins
- Clone from GitHub can fail silently

## IMPORTANT
- Do NOT modify inferenceservice.yaml unless explicitly asked
