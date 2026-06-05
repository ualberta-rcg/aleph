# aion — Test Report (BLOCKED)

## Result: FAILED to load — deferred, removed from cluster.

Deployed to 230 (CPU, Knative+PVC). Pod reached Running but the model never loaded:
- `transformers` path: `Unrecognized model in /data/model. Should have a model_type key`.
- `polymathic_aion` path: `No module named 'polymathic_aion'` (real import is `aion`,
  and the package wasn't installed; the old server's API guesses are wrong anyway).
- `POST /v1/science/embed` → 503 "Model not loaded yet".

## Conclusion
The 232 generic server is a non-functional stub. AION requires its own `aion` package
(`CodecManager` + modality dataclasses) and structured astronomical inputs. Removed the
broken deployment. See CLAUDE.md for the correct integration path. Re-do in a later pass.
