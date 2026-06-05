# ProstT5 Model Deployment

## What this model does
ProstT5 from Rostlab translates between protein amino acid sequences and 3Di structure tokens. Enables fast structure prediction without MSA. ~800M parameters.

## Source
- **HF**: Rostlab/ProstT5 | **License**: MIT | **Params**: ~800M

## How the server works
- `POST /v1/translate` -- accepts `input` (sequences), `direction` (seq2struct|fold2AA)
- Uses T5ForConditionalGeneration with sentencepiece tokenizer
- Pinned transformers==4.40.2, tiktoken uninstalled
- fp16 on GPU, max_length=512

## Our config vs source
- venv-on-PVC, pinned transformers==4.40.2 + sentencepiece
- Deletes tokenizer.json from cache (needs sentencepiece not tiktoken)
- GPU shared (L40S-SHARED), 20Gi PVC, minReplicas: 0
- Init requests 8Gi/16Gi memory for download

## Deploy/update/test
```bash
kubectl apply -k models/prostt5/
kubectl get inferenceservice prostt5 -n models
```

## Gateway integration
- MODEL_TYPES: `"prostt5": "embedding"` | KServe custom | Not in MODEL_METADATA

## IMPORTANT
- Do NOT modify inferenceservice.yaml unless explicitly asked
