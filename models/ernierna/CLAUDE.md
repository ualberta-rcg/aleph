# ERNIE-RNA Model Deployment

## What this model does
ERNIE-RNA from multimolecule/Baidu is a structure-aware RNA foundation model (~86M). Pre-trained on RNAcentral with structure objectives.

## Source
- **HF**: multimolecule/ernierna | **License**: AGPL-3.0 | **Params**: ~86M

## How the server works
- `POST /v1/science/embed` -- RNA sequence(s) to embeddings
- Uses BertTokenizer (WordPiece) + ErnieRnaModel from multimolecule
- Mean-pooled embeddings, max_length=1024

## Our config vs source
- venv-on-PVC with multimolecule + transformers + sentencepiece
- Downloads model to `/data/model` via snapshot_download
- GPU shared (L40S-SHARED), 5Gi PVC, minReplicas: 0

## Deploy/update/test
```bash
kubectl apply -k models/ernierna/
kubectl get inferenceservice ernierna -n models
```

## Gateway integration
- MODEL_TYPES: `"ernierna": "embedding"` | KServe custom | Not in MODEL_METADATA

## IMPORTANT
- Do NOT modify inferenceservice.yaml unless explicitly asked
