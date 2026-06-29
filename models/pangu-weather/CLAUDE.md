# pangu-weather — research notes

## Source
- GitHub: https://github.com/SpuriousCorrelations/Pangu-Weather
- Weights: ECMWF CDN — `https://get.ecmwf.int/repository/test-data/ai-models/pangu-weather/pangu_weather_6.onnx` (~1.1 GB, 6h model)
- Initial conditions: WeatherBench2 ERA5 — `gs://weatherbench2/datasets/era5/1959-2023_01_10-wb13-6h-1440x721_with_derived_variables.zarr`
  (public, anonymous; 13 levels, 6-hourly, 0.25°, 1959-01-01 … 2023-01-10)
- License: BY-NC-SA-4.0

## Install settings (verified)
- `onnxruntime-gpu>=1.18` (CUDAExecutionProvider on L40S)
- ERA5 zarr stack: `xarray>=2024.1`, `zarr<3` (v2 consolidated metadata reader — safest for WB2), `fsspec>=2024.1`, `gcsfs>=2024.1`, `pandas`
- Read WB2 with `xr.open_zarr(url, storage_options={"token": "anon"}, consolidated=True)` (fall back to `consolidated=False`)

## Model I/O (verified from repo + ONNX introspection)
- **Inputs** (bound by rank, not name — robust): upper-air 5-D `(1,5,13,721,1440)` = Z,Q,T,U,V; surface 4-D `(1,4,721,1440)` = MSLP,U10,V10,T2M
- **Outputs**: same shapes — the 6h-ahead state
- **Pressure levels (Pangu, DESCENDING)**: [1000,925,850,700,600,500,400,300,250,200,150,100,50]
- **WB2 stores levels ASCENDING** [50…1000] → reverse the level axis after load. Lat (90→-90) and lon (0→359.75) already match.
- **Units** match WB2 directly — geopotential m²/s², T in K, wind m/s, pressure Pa. No conversion.
- **Lead time**: the 6h model is rolled autoregressively `lead_hours/6` times for longer forecasts (6–72h).

## API contract
- `POST /v1/science/forecast`
- Real: `{"date","lead_hours","coords"}` → pulls ERA5 (cached per date on PVC), rolls forward, returns `summary` (global mean/min/max of t2m, msl, t@850, z@500) + `points` (per-coord t2m/msl/u10/v10/t@850hPa/t@500hPa/z@500hPa).
- Demo: `{"demo": true}` — synthetic input, single step, no network.

## Deployment
- Caduceus pattern: ConfigMap `server.py` at `/app`, venv `/data/venv-v5` + ONNX + ERA5 cache on RWX PVC `pangu-weather` (30Gi).
- initContainer gated by `/data/pangu-weather-ready-v5` + NFS-safe mkdir lock. `progress-deadline: 1800s`.
- 1× L40S slice (`gpumem 30720`); scale-to-zero, 15m retention.

## Files
- `inferenceservice.yaml` — ConfigMap (`server.py`) + ISVC + init container
- `pvc.yaml` — `pangu-weather` PVC (30Gi RWX)
- `details.yaml` — v2 Template B science card
- `test.py` — DEMO leg (finite) + REAL leg (ERA5 2018-01-01, Edmonton-vs-tropics sanity); REAL→SKIP if GCS blocked
- `README.md`

## Reuse
- The ERA5 fetch+cache+level-reverse pattern is reused by the other global weather models (`fengwu`, `climax`).
