# pangu-weather — Huawei Pangu-Weather (Nature 2023)

Global medium-range weather forecasting at 0.25° (721×1440), 13 pressure levels (50–1000 hPa).
Served as ONNX (the 6-hour model, rolled forward for longer leads), initialized from **live ERA5**
via the public **WeatherBench2** Zarr on GCS.

- **Source:** https://github.com/SpuriousCorrelations/Pangu-Weather (weights: ECMWF CDN)
- **License:** BY-NC-SA-4.0
- **Initial conditions:** `gs://weatherbench2/datasets/era5/1959-2023_01_10-wb13-6h-1440x721_with_derived_variables.zarr`
  (public, anonymous GCS read; cached per-date on the PVC)
- **Framework:** `onnxruntime-gpu` (CUDA), 6h ONNX model rolled autoregressively

## API — `POST /v1/science/forecast`

**Real (researcher) mode** — send a date (and optional points), get a real forecast:

```json
{
  "model": "pangu-weather",
  "date": "2018-01-01T00:00:00",
  "lead_hours": 24,
  "coords": [{"lat": 53.5, "lon": -113.5}, {"lat": 0.0, "lon": -150.0}]
}
```

- `date` — ERA5 analysis time, snapped to the nearest 6h (range 1959-01-01 … 2023-01-10). Omit for demo.
- `lead_hours` — forecast lead, a multiple of 6 (6–72); the 6h model is rolled forward this many steps.
- `coords` — optional `{lat, lon}` points to return forecast values for.

Returns `init_time`, `valid_time`, `lead_hours`, `source: "weatherbench2-era5"`, a global `summary`
(mean/min/max of t2m, msl, t@850hPa, z@500hPa), and `points` with per-location forecast values.

**Demo mode** — no-network smoke test: `{"demo": true}` (synthetic ERA5-like input, single 6h step).

## How it works

1. `_load_era5(date)` opens the WeatherBench2 Zarr (`token: anon`), selects the nearest 6h analysis,
   stacks the 5 upper-air vars (Z,Q,T,U,V × 13 levels) + 4 surface vars (MSLP,U10,V10,T2M), reverses
   the level axis from WB2's ascending order to Pangu's descending order, and caches a `.npz` per date
   on the PVC (`/data/era5/<date>.npz`) — so repeat forecasts from the same date skip the fetch.
2. The 6h ONNX model is run `lead_hours/6` times, feeding each output back as the next input.
3. Global summary stats + nearest-grid values at each requested point are returned.

Units match WB2 directly (no conversion): geopotential m²/s², temperature K, wind m/s, pressure Pa.

## Deployment

- Custom FastAPI server (`server.py` in the `pangu-weather-server` ConfigMap, mounted at `/app`),
  run via a persisted venv on the PVC (caduceus pattern).
- initContainer builds `/data/venv-v5` (`onnxruntime-gpu` + `xarray zarr<3 fsspec gcsfs pandas`) and
  downloads the 6h ONNX (~1.1 GB). Gated by sentinel → fast cold starts. `progress-deadline: 1800s`.
- 1× L40S HAMi slice (`gpumem 30720`); nodeSelector `gpu=on`. Scale-to-zero (`minReplicas: 0`, 15m).
- RWX PVC `pangu-weather` (30Gi) — ONNX + ERA5 cache shared across cold starts.

## Test

```bash
GW_URL=https://inference.vulcan.alliancecan.ca TYK_KEY=<key> GW_INSECURE=1 MODEL=pangu-weather \
  python3 models/pangu-weather/test.py
```

DEMO leg asserts the ONNX runs and output is finite. REAL leg pulls ERA5 for 2018-01-01, checks
physically-plausible global temps/geopotential and that January Edmonton is colder than the equatorial
Pacific. REAL degrades to SKIP (not FAIL) if GCS egress is blocked on the node.

## Notes

- ONNX inputs/outputs are bound **by rank** (upper-air = 5-D, surface = 4-D) so the server is robust to
  the model's internal tensor-name drift across ONNX versions.
- Same ERA5 input contract as the other global weather models (`fengwu`, `climax`) — the fetch+cache
  pattern is reused there.
