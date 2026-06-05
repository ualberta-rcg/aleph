
## Verified 2026-06-05 (verification loop) — DEEP-FIXED
Two bugs fixed:
1. Input shape: server added an extra trailing dim ([1,seq,1]); Sundial wants 2D
   [batch, lookback]. Removed `.unsqueeze(-1)`. Also use `num_samples=` (not
   num_return_sequences) and treat output as forecast-only [batch, num_samples, horizon].
2. transformers incompat: remote code uses DynamicCache.seen_tokens (removed >=4.44).
   Pinned transformers==4.40.2.
Test: series 1..32, horizon 6 -> forecast [33.0,33.7,34.3,34.9,35.4,35.9] + std + quantiles. PASS.
