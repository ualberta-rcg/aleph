# LaBraM (braindecode/labram-pretrained)

LaBraM — Large Brain Model (Jiang/Zhao/Lu, SJTU, ICLR 2024 spotlight). An EEG foundation model
pretrained on ~2500h of EEG from ~20 datasets. Segments multi-channel EEG into 200-sample
(1s @ 200Hz) channel patches, vector-quantizes them via a neural spectrum tokenizer (VQ-NSP),
and encodes them with a BEiTv2-style 12-layer / 200-dim / 10-head windowed-attention transformer
to produce a **200-dim [CLS] embedding** per window. Robust to channel subsets (graceful
degradation to ~11 channels). Use cases: BCI, abnormal/pathology detection, event classification,
emotion recognition, sleep staging.

Custom FastAPI/braindecode server on CPU, scale-to-zero, venv-on-PVC.

**Non-text domain model**: EEG-array input only — does **not** expose OpenAI `/v1/embeddings`.
Serves its domain endpoint `POST /v1/science/embed`.

## Deployment

```bash
kubectl apply -f pvc.yaml              # RWX venv + HF snapshot (nfs-client) — cp-migrated from old RWO
kubectl apply -f inferenceservice.yaml # ConfigMap (server.py) + ISVC, CPU
kubectl apply -f details.yaml          # Template-C card (type: embedding)
```

## Testing

```bash
cat models/labram/test.py | kubectl exec -i -n models deploy/model-gateway -c gateway -- python3 -
```

Last run (2026-06-19): **8 PASS / 0 FAIL** — dim 200, non-zero real, distinctness (cos 0.90),
deterministic (cos 1.0), channel subset, short-input padding (→3000), ch_names mismatch, malformed.

## Key Configuration

| Setting | Value |
|---------|-------|
| Backend | custom FastAPI + `braindecode` 1.5.2 `Labram.from_pretrained` (CPU) |
| Endpoint | `POST /v1/science/embed` (domain; EEG array, not OpenAI text) |
| Embedding dim | **200** ([CLS] token via `return_features`) |
| Input | `eeg` (2D `[n_chans][n_times]`, padded/truncated to 3000) + `ch_names` (10-20 subset) |
| Parameters | 5.8M (12-layer, hidden 200, MLP 800, 10-head) |
| GPU | none (CPU) |
| Scale | scale-to-zero (`minReplicas: 0`, 15m retention) |
| PVC | `labram-data-rwx` (RWX, nfs-client, 5Gi) — venv + weights |

## Cold start

~2-4 min on first boot (venv + braindecode install once; HF snapshot pre-downloaded by init).
Subsequent boots skip the venv (guarded). Loads fully offline (`HF_HUB_OFFLINE=1`) via
`from_pretrained(/data/model)`.

## Notes
- The braindecode checkpoint expects `n_times=3000` (vs the original 935963004 LaBraM-Base's 1600).
- Recommended input preprocessing: bandpass 0.1-75 Hz, notch 50 Hz, resample 200 Hz, unit µV.
