"""
Chronos-Bolt: zero-shot time series forecasting (amazon/chronos-bolt-base).
Weights downloaded at startup, cached on PVC. CPU inference.
API: POST /v1/forecast — returns probabilistic forecasts.
"""
import os, json, asyncio
from pathlib import Path
from fastapi import FastAPI
from fastapi.responses import JSONResponse
import uvicorn

MODEL_DIR = os.environ.get("MODEL_DIR", "/data")

app = FastAPI()
pipeline = None

def load():
    global pipeline
    import torch
    from chronos import BaseChronosPipeline
    print("Loading chronos-bolt-base...", flush=True)
    pipeline = BaseChronosPipeline.from_pretrained(
        MODEL_DIR,
        device_map="cpu",
        torch_dtype=torch.float32,
    )
    print(f"[ok] chronos-bolt-base loaded", flush=True)

@app.on_event("startup")
async def startup():
    await asyncio.get_event_loop().run_in_executor(None, load)

@app.get("/health")
async def health():
    return {"status": "ok" if pipeline else "loading", "model": "chronos-bolt"}

@app.get("/v1/models")
async def list_models():
    return {"object": "list", "data": [
        {"id": "chronos-bolt", "object": "model", "created": 1700000000,
         "owned_by": "amazon", "type": "forecast"}
    ]}

@app.post("/v1/forecast")
async def forecast(request: dict):
    if pipeline is None:
        return JSONResponse({"error": "model loading"}, 503)

    values = request.get("values") or request.get("time_series") or request.get("series")
    if not values or not isinstance(values, list):
        return JSONResponse({"error": "'values' field required — list of numeric time series observations"}, 400)

    horizon = request.get("horizon", 12)
    num_samples = request.get("num_samples", 20)
    quantile_levels = request.get("quantile_levels", [0.1, 0.5, 0.9])

    loop = asyncio.get_event_loop()
    try:
        result = await loop.run_in_executor(None, _predict, values, horizon, num_samples, quantile_levels)
        return result
    except Exception as e:
        return JSONResponse({"error": str(e)}, 500)

def _predict(values, horizon, num_samples, quantile_levels):
    import torch
    ctx = torch.tensor([values], dtype=torch.float32)
    forecasts = pipeline.predict(ctx, prediction_length=horizon)
    import numpy as np
    s = forecasts.numpy().squeeze()
    if s.ndim == 1:
        s = s.reshape(1, -1)

    result = {"model": "chronos-bolt", "horizon": horizon, "samples": s.shape[0]}

    result["quantiles"] = {}
    for q in quantile_levels:
        qval = np.quantile(s, q, axis=0).tolist()
        result["quantiles"][str(q)] = qval

    result["median"] = np.median(s, axis=0).tolist()
    result["mean"] = np.mean(s, axis=0).tolist()
    return result

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8080)
