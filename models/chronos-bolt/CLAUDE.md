# chronos-bolt Notes

## Purpose
Chronos-Bolt (amazon/chronos-bolt-base): zero-shot time-series forecasting (T5
encoder-decoder). POST `values` + `horizon` to `/v1/forecast` → mean/median/quantiles.

## Runtime
- Custom FastAPI server (separate `server.py`, built via kustomize `configMapGenerator`
  `chronos-bolt-server`). Deploy with `kubectl apply -k models/chronos-bolt`.
- CPU, venv-on-PVC, `chronos-forecasting` (unpinned — idempotent venv check).
- HF token via `secretKeyRef`.

## Migration changes vs 232
- Inline HF token → secretKeyRef; v2 card (`routing.k8s_name: chronos-bolt`).
- Corrected parameter count to ~205M (base; old card said 710M).

## Deploy note
- Uses kustomize (server.py is a generated ConfigMap). Keep `kustomization.yaml`.

## Validation
See [TEST.md](TEST.md). horizon=6 forecast returned.
