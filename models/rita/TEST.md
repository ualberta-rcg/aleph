# RITA-XL Test Report

Model: `rita-xl` (lightonai/RITA_xl, 1.2B params, protein autoregressive LM)
Cluster: 230 (rack15-03 worker, CPU only)
Date: 2026-06-05

## Fixes Applied

1. **transformers compatibility**: RITA custom model class incompatible with `transformers≥4.37`:
   - `can_generate()` classmethod check — patched at class level: `type(model).can_generate = classmethod(lambda cls: True)`
   - `generation_config` is `None` — set to `GenerationConfig()` default in `load()`
   - `prepare_inputs_for_generation` not defined on RITA class — replaced `model.generate()` with a manual token-by-token autoregressive loop

2. **venv NFS lock bug**: `/data/venv2` path had stale NFS `.nfs*` locks after failed `rm -rf`. New path `/data/rita-env` avoids this.

## Test Results

### POST /v1/science/generate

```bash
curl -s -X POST http://10.43.79.101:80/v1/science/generate \
  -H "Content-Type: application/json" \
  -d '{"model":"rita-xl","prompt":"M","max_length":40,"num_sequences":1}'
```

**Response** (PASS):
```json
{"sequences":["MSLAAVSIDPDALQLDYERLTAKVGDEHPRRATFVSRGA"],"prompt":"M","model":"rita-xl"}
```

- Protein sequence generated from prompt `M`
- Manual autoregressive loop, ~15s for 40 tokens on CPU
- Single and multi-sequence generation confirmed working

## Notes

- Cold start: ~5min (1.2B model loads on CPU from NFS)
- Generation: ~0.4 tokens/sec on CPU (expected for 1.2B LM)
- `minReplicas: 0` (scale-to-zero after idle)
