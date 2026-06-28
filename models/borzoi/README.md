# borzoi — RNA-seq Prediction from Genomic DNA

`borzoi` serves **Borzoi** (Calico Research, Linder 2023, ~500M params) — predicts RNA-seq signal
from a **524,288 bp genomic DNA sequence** (gene expression at base-pair resolution, across bins).
An Enformer-variant architecture.

- **Source:** https://huggingface.co/johahi/borzoi-replicate-0
- **License:** CC-BY-4.0
- **Framework:** `borzoi-pytorch` + torch (CUDA 12.6); `transformers<4.51`

## API

`POST /v1/science/predict`

```json
{ "model": "borzoi", "sequence": "ACGT...(≤524kb)", "n_bins": 16 }
```

Shorter sequences are **padded with N** to 524,288 bp. Returns `predictions` (`[n_bins, n_tracks]`),
`bins_returned`, `num_tracks`. Lower `n_bins` to shrink the payload (track count is large).

## Deployment

- Custom FastAPI server (`server.py` embedded in the `borzoi-server` ConfigMap, mounted read-only at
  `/app`), run via a persisted venv on the PVC (caduceus pattern).
- initContainer builds `/data/venv` (torch cu126 + `borzoi-pytorch` + `transformers<4.51`) and caches
  the weights (`johahi/borzoi-replicate-0`) — both gated → fast cold starts.
- 1× L40S HAMi slice (`gpumem 10240`); fp32; nodeSelector `gpu=on`.
- Scale-to-zero (`minReplicas: 0`, 15m idle retention). Cold start ~3-6 min.

## Test

```bash
GW_URL=https://inference.vulcan.alliancecan.ca TYK_KEY=<key> GW_INSECURE=1 MODEL=borzoi \
  python3 models/borzoi/test.py
```
Sends 4kb ACGT (padded) with `n_bins=4`, asserts the `[4, n_tracks]` predictions grid.
