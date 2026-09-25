# tmqmg-painn-3d — PaiNN Ensemble for Transition-Metal Excited States

`tmqmg-painn-3d` serves a five-member ensemble of equivariant PaiNN graph neural
networks (Elayan, Castro-Miyashiro, Blaskovits) that predicts excited-state
absorption properties of mononuclear transition-metal complexes from a single
XYZ geometry and formal charge — a fast ML surrogate for the TD-DFT workflow
used to generate its training targets (screening/ranking, not a replacement for
quantum-chemical validation).

- **Domain:** chemistry / spectroscopy, 3d–5d transition-metal complexes
- **Size:** 2,922,446 params/member, 14,612,230 total; FP32; ~59MB checkpoints total
- **License:** MIT (checkpoints + code); tmQMg* source dataset is CC BY 4.0
- **Upstream:** no reachable public host as of 2026-09-25 (the draft card's GitHub
  mirror 404s — verified with `git ls-remote`); the source of truth is the model
  author's package delivered directly to the ops team

## API

`POST /v1/science/predict`

```json
{
  "model": "tmqmg-painn-3d",
  "id": "YADPOK",
  "charge": 0,
  "xyz": "41\ncomment\nV -1.0997 1.1140 0.2421\n..."
}
```

- `charge` (required): formal molecular charge, one of `-1`, `0`, `1`.
- `xyz` (required): a complete XYZ document, 7–85 atoms, exactly one supported
  transition metal.
- `id` (optional): caller-defined identifier, echoed back.

Returns 30 vertical singlet excitation energies/wavelengths/oscillator
strengths per solvent (gas phase, acetone), regional UV/visible/nIR band
presence and peaks, and — gated on visible-band probability ≥ 0.5 — a
charge-transfer classification and NTO metal-fraction pair. Regional peaks are
serialized only when their band is predicted present. Full field-by-field
contract: `input_map`/`output_map` in `details.yaml`, and the upstream
`MODEL_CARD.md`/`README.md` shipped with the model source.

The model ships its own regression oracle: `example_request.json` (included
here) → the frozen reference values baked into `test.py` (from
`examples/example_prediction.json` and `scripts/smoke_test.py` upstream).

## Deployment

- **Pattern:** venv-on-PVC (caduceus/mace-mp pattern), but **no ConfigMap and no
  network fetch of the app itself** — unlike those two, this model's source and
  checkpoints have no reachable public host, so they are staged onto the PVC
  once, out of band (see "First-time staging" below). The initContainer only
  builds the Python venv (`numpy`, `torch` cu126, `torch_geometric`, `fastapi`,
  `pydantic`, `uvicorn` — all from public PyPI/pytorch.org) and `pip install -e`s
  the already-staged app; it fails fast with an instructive message if staging
  is missing.
- **Runtime:** `POST /v1/science/predict`, `GET /health` — served natively by
  the model's own FastAPI app (`tmqmg_es.api:app`); no gateway adapter needed.
- **GPU:** tiny model, CPU-capable (auto-detects CUDA else falls back). 1×
  L40S HAMi slice, `nvidia.com/gpumem: "4096"` — measured live usage is
  ~523–592MiB (`nvidia-smi` inside the pod), so this slice has comfortable
  headroom without being oversized.
- **Scaling:** `minReplicas: 1` / `maxReplicas: 2`, always-on (changed
  2026-09-25 from the initial scale-to-zero deploy, on request — no cold start
  for any request now; costs one persistent ~600MiB GPU slice at all times).
- **`serving.knative.dev/progress-deadline-seconds: "1800"`** — the first-ever
  boot builds the venv (torch/torch_geometric download+install) inside the
  Knative revision's startup window; Knative's default progress deadline
  (600s) could kill that mid-build under a slow PyPI pull. Matches the
  `caduceus` precedent, which carries the same 1800s for the same reason
  (there it's a much longer from-source compile, but the risk is identical in
  kind). Measured first-ever build here was ~4 min, comfortably under either
  deadline, but this isn't margin worth gambling on a slower run.

### First-time staging (required before first deploy)

The PVC starts empty; `/data/app` must contain the model's `pyproject.toml`,
`src/`, `artifacts/` and a `.staged` marker before the InferenceService's
initContainer will proceed:

```bash
kubectl apply -f models/tmqmg-painn-3d/pvc.yaml
# One-off staging pod mounting the same PVC:
kubectl run tmqmg-stage -n models --image=busybox --restart=Never --overrides='
{"spec":{"containers":[{"name":"stage","image":"busybox","command":["sleep","3600"],
"volumeMounts":[{"name":"data","mountPath":"/data"}]}],
"volumes":[{"name":"data","persistentVolumeClaim":{"claimName":"tmqmg-painn-3d"}}]}}'
kubectl wait --for=condition=Ready pod/tmqmg-stage -n models --timeout=120s
# tar the model source (pyproject.toml, src/, artifacts/, src/manifests/) on the
# machine that has it, then:
kubectl cp tmqmg-painn-3d.tar.gz models/tmqmg-stage:/tmp/
kubectl exec -n models tmqmg-stage -- sh -c \
  'mkdir -p /data/app && tar xzf /tmp/tmqmg-painn-3d.tar.gz -C /data/app && touch /data/app/.staged'
kubectl delete pod tmqmg-stage -n models
```

### Deploy / update / test

```bash
kubectl apply -f models/tmqmg-painn-3d/pvc.yaml
kubectl apply -f models/tmqmg-painn-3d/inferenceservice.yaml
kubectl apply -f models/tmqmg-painn-3d/details.yaml
kubectl get isvc tmqmg-painn-3d -n models
kubectl get pods -n models -l serving.kserve.io/inferenceservice=tmqmg-painn-3d

# Test (external, via gateway + Tyk auth):
GW_URL=https://inference.vulcan.alliancecan.ca TYK_KEY=<key> MODEL=tmqmg-painn-3d \
  python3 models/tmqmg-painn-3d/test.py
# Or in-pod (no auth):
cat models/tmqmg-painn-3d/test.py | kubectl exec -i -n models deploy/model-gateway -c gateway -- python3 -
```

Updating the spec: delete the InferenceService (PVC/staged data survive), wait
for old predictor pods/revisions to clear, then re-apply — never patch.

## Gateway integration

`type: spectroscopy` (v2 card, Template-B style typed `input_map`/`output_map`);
KServe custom model via the gateway's generic passthrough handler
(`custom_params.passthrough: true` strips `model`/`stream` before forwarding —
harmless here since the app's own schema already tolerates `model` being
present).

## Deployed + verified (2026-09-25)

Deployed live on cluster (aleph1–3 control plane, worker `rack09-06`). Full
battery: **6 PASS / 4 EXP / 0 FAIL** — regression check matches the model's own
`example_prediction.json` oracle (S1 energies within `abs_tol=5e-4` eV, CT
labels exact); invalid-input checks (bad charge, <7 atoms, zero transition
metals, missing `xyz`) all return the expected `422`. Proved reproducible: the
InferenceService was deleted and recreated from these repo files (PVC/staged
data preserved) and the full battery re-run clean.

- First-ever cold start (fresh venv build: torch/torch_geometric/fastapi
  install from PyPI/pytorch.org): ~4 minutes.
- Warm cold start (cached venv on PVC, pod recreated): **~15–30s** to first
  `200` — this is the number in `details.yaml`'s `cold_start_estimate`, per the
  "measure cached wake, not first-ever install" convention.
- Measured GPU memory: **~523–592MiB** used of the requested 4096MiB HAMi
  slice (`nvidia-smi` inside the running pod).
- `torch==2.12.1 --index-url https://download.pytorch.org/whl/cu126` resolved
  and installed cleanly; `cuda available: True`, device `NVIDIA L40S`.

## Scaling change (2026-09-25, after initial deploy)

Switched from scale-to-zero to always-on at the user's request:
`inferenceservice.yaml` `minReplicas: 0` → `1`, added `maxReplicas: 2`;
`details.yaml` `scale_to_zero` true→false, `min_replicas` 0→1,
`idle_retention` "15m"→"always-on", `cold_start_estimate` "15-30 s"→"Always
on". Applied via the standard update procedure (delete isvc → wait for old
pod/revision to clear → re-apply — never patch). Verified: pod `3/3 Running`
continuously for 3+ minutes with 0 restarts, then a full battery run showed
`WAKE + predict: attempts=1` (immediate response, no cold start) — 6 PASS/4
EXP/0 FAIL, unchanged from the scale-to-zero results.

## Known issues / gotchas

- **No public upstream host** (2026-09-25 finding): the draft card's
  `github.com/jdiego-miyashiro/tmqmg-painn-3d` returns 404. Re-check before
  assuming this is permanent — if a real mirror appears, switching to a
  download-at-init pattern (like `mace-mp`) removes the manual staging step.
- `test.py` uses only the Python standard library (`urllib`), not `httpx` —
  the fleet's usual test convention assumes `httpx` is available on the Vulcan
  login node's default `python3`, but it wasn't in this session's environment
  and installing it there directly isn't appropriate (no `pip install` on the
  login node). Functionally equivalent; flagging the deviation from convention.
- Load/stress ("pressure") testing per the standard deploy loop has not been
  run yet — this is a low-traffic, scale-to-zero screening tool (one molecule
  per request, no batching), so the risk profile is low, but it's unverified.
