# RNA-BERT Model Deployment

## What this model does
RNA-BERT from multimolecule is pre-trained on Rfam structured RNA alignments. ~86M params. Embeddings for RNA secondary structure and functional element prediction.

## Source
- **HF**: multimolecule/rnabert | **License**: AGPL-3.0 | **Params**: ~86M

## How the server works
- `POST /v1/science/embed` -- RNA sequence(s) to mean-pooled embeddings
- Uses RnaTokenizer + RnaBertModel from multimolecule
- max_length=440

## Our config vs source
- venv-on-PVC with multimolecule + transformers
- GPU shared (L40S-SHARED), 5Gi PVC, minReplicas: 0
- HF_HUB_OFFLINE=1 in main container

## Deploy/update/test
```bash
kubectl apply -k models/rnabert/
kubectl get inferenceservice rnabert -n models
```

## Gateway integration
- MODEL_TYPES: `"rnabert": "embedding"` | KServe custom | Not in MODEL_METADATA

## IMPORTANT
- Do NOT modify inferenceservice.yaml unless explicitly asked
