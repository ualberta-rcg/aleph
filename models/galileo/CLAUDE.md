# Galileo — NASA Harvest Agricultural Monitoring Model

## Source
- HuggingFace: https://huggingface.co/nasaharvest/galileo
- GitHub: https://github.com/nasaharvest/galileo
- License: MIT

## Deployment Summary
- **Model**: Galileo base encoder (~90M)
- **GPU**: CPU-only (no GPU request despite CUDA torch)
- **PVC**: galileo-data (10Gi, NFS ReadWriteMany)
- **Scale-to-zero**: Yes (minReplicas: 0)
- **Venv**: Yes (/data/venv on PVC)

## API
- `POST /v1/embeddings` — satellite time-series to embeddings
- `POST /v1/science/classify` — alias for same endpoint
- Input: pixels [batch, time, bands], months, latlons
- Output: per-pixel embeddings in OpenAI-compatible format

## Key Files
- `inferenceservice.yaml` — ConfigMap (server.py) + ISVC + init container
- `pvc.yaml` — galileo-data PVC (10Gi NFS)
- `details.yaml` — model metadata ConfigMap

## Dependencies
- torch (CUDA 12.6)
- einops, fastapi, uvicorn, huggingface_hub

## Audit Notes
- Model weights downloaded from HF + repo cloned from GitHub
- Loads encoder.pt via Galileo.load_pretrained() or raw torch.load
- Low resource: 2Gi CPU / no GPU (sufficient for CPU inference)
- Dual endpoint routing: /v1/embeddings and /v1/science/classify

## Update Reminder
- Monitor nasaharvest/galileo for updated checkpoints
- Consider adding crop type classification head
- Could add GPU for faster batch processing
