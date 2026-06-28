# enformer — Gene-Expression Prediction from DNA

`enformer` serves **Enformer** (EleutherAI/enformer-official-rough, ~500M params) — predicts
gene-regulatory track values from a **196,608 bp DNA sequence** (5313 human + 1643 mouse tracks).
Convolutional trunk + transformer torso.

- **Source:** https://huggingface.co/EleutherAI/enformer-official-rough
- **License:** CC-BY-4.0
- **Framework:** `enformer-pytorch` + torch (CUDA 12.6); `transformers<4.52` (compat pin)

## API

`POST /v1/science/predict`

```json
{ "model": "enformer", "sequence": "ACGT...(~196kb)", "organism": "human" }
```

Shorter sequences are **padded with N** to 196,608 bp. Returns a **summary** (`human_shape`
`[896, 5313]`, `human_mean`, `human_sample`) — the full 896×5313 grid (~4.7M values) is too large to
return over HTTP. Pass `return_tracks: [int…]` to select specific tracks.

## Deployment

- Custom FastAPI server (`server.py` embedded in the `enformer-server` ConfigMap, mounted read-only
  at `/app`), run via a persisted venv on the PVC (caduceus pattern).
- initContainer builds `/data/venv` (Python 3.12, torch cu126, **`transformers<4.52`** +
  `enformer-pytorch`) and downloads the ~500M weights, both gated → fast cold starts.
- 1× L40S HAMi slice (`gpumem 20480`); fp32; nodeSelector `gpu=on`. Memory 16-32 Gi.
- Scale-to-zero (`minReplicas: 0`, 15m idle retention). Cold start ~4-8 min. Generous
  `progress-deadline: 1800s` + `timeout: 595`.

## Test

```bash
GW_URL=https://inference.vulcan.alliancecan.ca TYK_KEY=<key> GW_INSECURE=1 MODEL=enformer \
  python3 models/enformer/test.py
```
Sends 4kb of ACGT (padded), asserts `human_shape [896, 5313]` + finite mean.
