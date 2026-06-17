# Timer-S1 — Large MoE Time-Series Forecasting

## Source
- HuggingFace: https://huggingface.co/thuml/Timer-S1
- License: Apache 2.0
- **Note**: Replaces timer-xl-1b (gated Timer-XL-1B no longer publicly available)

## What this model does
Timer-S1 from Tsinghua THUML (2026) is a decoder-only MoE transformer:
- 8.3B total parameters, 0.75B activated per token (32 experts, top-2 routing)
- 24 layers, hidden_size 1024, 16 attention heads
- Up to 11,520 context length (we use 2,880 for single-L40S fit)
- Zero-shot quantile forecasting (9 quantiles: 0.1–0.9)
- SOTA on GIFT-Eval benchmark

## Our config vs source
- **transformers~=4.57.1** (required by Timer-S1 custom code)
- **use_cache=False** at runtime to fit L40S 48GB (no efficiency loss for forecast_length ≤ 256)
- **bf16** on GPU
- **gpumem: 40960** (40GB slice — nearly whole L40S, needed for 16.6GB model + activations)
- **revin=True** in model.generate() — Reversible Instance Normalization built-in
- Context limited to 2,880 steps (multiple of patch_size 16, within L40S memory)
- Prediction length capped at 256

## API
- `POST /v1/forecast` — time-series forecasting with quantile output
- Input: `{"time_series": [...], "prediction_length": 96}`
- Output: `{"forecast": {"mean": [...], "quantiles": {"0.1": [...], ..., "0.9": [...]}}, ...}`

## Deploy/update/test
```bash
test/test-model.sh timer-s1 recreate
test/test-model.sh timer-s1 status
test/test-model.sh timer-s1 curl /v1/forecast '{"model":"timer-s1","time_series":[1.0,2.0,3.0,4.0,5.0],"prediction_length":10}'
```

## Gateway Integration
- ISVC name: `timer-s1`
- MODEL_TYPE: forecast
- KSERVE_CUSTOM_MODELS: yes

## Known Issues
- Large model (~16.6GB download, ~5 min cold start after cache)
- Requires nearly whole L40S (40GB gpumem slice) — only 1 replica fits per GPU
