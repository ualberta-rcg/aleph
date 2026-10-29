# Kev 9B (decision model)

**jaredpalmer/kev-9b** — a *decision model*, not a chat model: it reads one
document (the "state") plus typed questions (`choice` / `score` / `noul`) and
returns **calibrated probabilities in a single prefill pass — no generation**.
Built for classification, routing, triage, eligibility checks, and
confidence-gated automation. Implements TypeSafe's **System One API** — the
TypeSafe SDK works unchanged against this endpoint.

Architecture: Qwen3.5-9B-Base (frozen) + LoRA (173 MB) + pointer head
(`head.pt`, T=2.19). ~21.9 GB resident on CUDA, author-validated **on L40S**
(66 ms/decision, ~33 req/s at 64 clients). Apache-2.0.

## Serving config

- **Engine**: Kev's own FastAPI server (`python -m kev.serve` from
  github.com/jaredpalmer/kev @ main) — **NOT vLLM** (the pointer head +
  calibration are custom). venv + weights persist on the PVC (caduceus pattern).
  `flash-linear-attention` installed explicitly (fused DeltaNet kernels — not a
  kev dependency). `--device cuda` (skips the child-process probe).
- **GPU**: single HAMi slice — `gpu: 1` + `gpumem 26624`.
- **Endpoints**: `POST /v1/systemone` (primary), `/v1/systemone/permute`,
  `/v1/systemone/separate`; server health on `GET /v1/models` (pod-local).
  All routed through the gateway's `/v1/{path}` catch-all via `body.model`.
- **Context**: serves states to 65,536 tokens (**validated at 8,192** — longer
  degrades); >65,536 → 422 with token counts.
- **Scaling**: scale-to-zero, min 0 / max 2.
- kev-27b does NOT fit this fleet (51.3 GB bf16, >80 GB peaks, no TP in the
  server). kev-9b trails it by 11 pts on breadth-v1 — the L40S ceiling.

## Files

| File | Purpose |
|---|---|
| `pvc.yaml` | 60Gi RWX PVC (venv ~10 GB + base+adapter weights in HF cache) |
| `inferenceservice.yaml` | ISVC: venv-on-PVC init + kev.serve main container |
| `details.yaml` | v2 card — type `decision`, primary `/v1/systemone` |
| `test.py` | Full decision-API battery incl. workload + limit guards |
| `example.py` | **Operator-authorized extra** — runnable System One examples |
| `README.md` / `CLAUDE.md` | This record / research + quirks |

## Deploy

```bash
K='export PATH=$PATH:/var/lib/rancher/rke2/bin; export KUBECONFIG=/etc/rancher/rke2/rke2.yaml; kubectl apply -f -'
cat models/kev-9b/pvc.yaml              | sudo ssh root@172.26.92.43 "$K"
cat models/kev-9b/inferenceservice.yaml | sudo ssh root@172.26.92.43 "$K"
cat models/kev-9b/details.yaml          | sudo ssh root@172.26.92.43 "$K"
```

First staging builds the venv (torch + transformers + kev + fla — ~10 GB of
wheels) and stages Qwen3.5-9B-Base (~18 GB) + the adapter. Test:

```bash
source ~/.aleph_tyk.env
GW_URL=https://inference.vulcan.alliancecan.ca TYK_KEY=$TYK_KEY \
  python3 models/kev-9b/test.py > /tmp/kev-9b-test.log 2>&1 &
```

## Verify at startup (pod logs)

- `venv ready` / `weights staged` in init; server binds 0.0.0.0:8080
- `GET /v1/models` probes go 200; decisions ~40–70 ms once warm

## Quirks

- `body.model` **must** be `kev-9b` (gateway routing); the server itself ignores it.
- Every question type in one request shares the cached state prefill — cheap.
- `no_stream: true` in the card (prefill-only; nothing to stream).
- Probabilities sum to 1; `confidence` is the model's own calibration, not max-prob.
- KEV_TEMPERATURE=1.0 would disable calibration (we keep calibration on).

## Status

- **2026-10-28: DEPLOYED + PROVEN** — the fleet's first `decision`-type model.
  Solid battery **24 PASS / 3 EXP / 0 FAIL (27 checks)**: mechanics (all 3
  question types, permute/separate, 422 over-length, boundaries 1/50 options,
  10-level score, multi-axis batch), semantics (author-fixture parity; ground
  truth 3/3 exact; moderation hostile 0.88 vs benign 0.08), stability
  (deterministic, 100% permutation agreement, phrasing-stable), workload
  (8-way burst, 20-mix @135 ms median). Proof delete+redeploy battery green.
  Two crashloop iterations taught: main container needs full python:3.12
  (Triton JIT needs gcc); permute body wraps in `request` + top-level `model`
  for gateway routing.
