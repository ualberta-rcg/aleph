# tmqmg-painn-3d Notes

## Research (2026-09-25)

- Source: `/project/def-amii-compute-team/aleph/tmqmg-painn-3d/` (delivered directly
  by the model authors — Elayan, Castro-Miyashiro, Blaskovits — as a complete
  package: `README.md`, `MODEL_CARD.md`, `pyproject.toml`, `src/tmqmg_es/`,
  `src/manifests/final_ensemble_manifest.json`, `artifacts/runs/<5 seeds>/best.pt`,
  `examples/`, `tests/`, plus a draft `deployment/vulcan/details.yaml` (marked
  "Drafted by OpenAI Codex from the ualberta-rcg/aleph mace-mp template").
- **The draft card's `catalog.source_url`
  (`https://github.com/jdiego-miyashiro/tmqmg-painn-3d`) does not exist** —
  `git ls-remote https://github.com/jdiego-miyashiro/tmqmg-painn-3d.git` returns
  "Repository not found." Dropped `source_url` from `details.yaml` rather than
  publish a dead link. This also rules out the mace-mp pattern of fetching the
  app from a public host at pod-init time — see "Deployment deviation" below.
- App already implements exactly what Aleph needs, no adapter required:
  `GET /health` → `{"status":"ok","model_loaded":bool}`; `POST /v1/science/predict`
  (Pydantic-validated `PredictionRequest`/`PredictionResponse` in `api_schemas.py`,
  strict — rejects undocumented fields). Verified in `src/tmqmg_es/api.py`.
- Device: `inference.py:151-152` auto-detects `cuda` if available else falls back
  to `cpu` — no device env var needed.
- Artifact/manifest paths are overridable via `TMQMG_ARTIFACT_ROOT` /
  `TMQMG_ENSEMBLE_MANIFEST` env vars (`api.py:53-64`), defaulting to paths
  relative to `config.py`'s own file location (`REPO_ROOT = parents[1]` = the
  `src/` dir; artifact root = `REPO_ROOT.parent/artifacts`; manifest =
  `REPO_ROOT/manifests/final_ensemble_manifest.json`). With an **editable**
  install (`pip install -e /data/app --no-deps`) these defaults resolve
  correctly against the staged tree without needing the env vars at all — set
  explicitly anyway in `inferenceservice.yaml` for clarity/robustness.

## Deployment deviation: staged, not fetched

Every other custom-server model in this fleet (`mace-mp`, `caduceus`, …)
downloads its code/weights from a public host (HF, PyPI) inside the
initContainer. **This model has no such host** for its code or its five
checkpoints (~59MB total) — the draft card's GitHub link is dead. Options
considered:

1. Embed the whole `tmqmg_es` package as ConfigMap keys (like mace-mp's single
   `server.py`) — source alone is only ~64KB across ~13 files, would fit, but
   the 5 checkpoints (~59MB, binary `.pt`) can't (ConfigMap/etcd object limits).
   Would also need per-file `items`/`path` mapping for the package's
   subdirectories (`data/`, `models/`, `web/`) — workable but verbose, and still
   leaves the checkpoint problem unsolved.
2. **Chosen: stage the full app (source + `artifacts/` + `src/manifests/`) onto
   the PVC once, out of band, via a temporary pod + `kubectl cp` + `tar`**
   (documented in `README.md` "First-time staging"). The InferenceService's
   initContainer then only builds the venv (all deps ARE on public PyPI/
   pytorch.org) and does an editable install of the already-staged app; it
   checks for a `/data/app/.staged` marker and fails fast with an instructive
   message if it's missing, rather than silently trying to fetch anything.

This is the one deliberate deviation from the standard pattern in this
deployment. Revisit if a real public mirror ever appears — see "Known issues"
in `README.md`.

## Deployed + verified live (2026-09-25)

Full loop completed on the real cluster (aleph1 control plane, worker
`rack09-06`). See `README.md` "Deployed + verified" for the dated results
(6 PASS/4 EXP/0 FAIL, twice — first deploy and after a clean delete+recreate
proof). Resolved items from the original "not yet done" list:

- `torch==2.12.1 --index-url https://download.pytorch.org/whl/cu126` resolved
  and installed without issue on `python:3.11-slim`; `torch.cuda.is_available()`
  is `True` on the L40S workers.
- GPU memory measured via `nvidia-smi` inside the running pod: **~523–592MiB**
  used of the requested 4096MiB HAMi slice. Left as-is (comfortable headroom,
  not oversized relative to a 1/10 L40S share).
- All four invalid-input checks (`charge=7`, <7 atoms, zero transition metals,
  missing `xyz`) return `422` exactly as `api.py`'s exception handling implied
  from reading the source — confirmed live, not just by inspection.
- First-ever cold start (fresh venv build) measured at ~4 minutes; warm
  cold start (cached venv, pod recreated) at ~15–30s — the latter is what's
  recorded in `details.yaml`'s `cold_start_estimate`, per the "measure cached
  wake, not first-ever install" convention in `models/details.md`.

**One test-tooling deviation, not a model issue**: this session's Vulcan login
node had no `httpx` on the default `python3` (the fleet's usual `test.py`
convention assumes it's preinstalled) and installing it there directly isn't
appropriate (no `pip install` on the login node per org policy). Rewrote
`test.py`'s HTTP calls on top of `urllib` (stdlib only, same approach as the
model's own `scripts/smoke_test.py`) instead of `httpx` — functionally
identical, same PASS/EXP/FAIL accounting. Worth revisiting if the fleet
convention changes or a suitable module/venv with `httpx` becomes the norm.

## Reviewer fix: progress-deadline (2026-09-25)

A colleague reviewing the deploy flagged that the ISVC was missing
`serving.knative.dev/progress-deadline-seconds: "1800"` — the first-ever boot
builds the venv inside the Knative revision's startup window, and Knative's
default progress deadline (600s) could kill the revision mid-build on a slow
PyPI pull. Cited the `caduceus` precedent, which carries the same 1800s for
its (much longer, from-source) mamba-ssm compile — same class of risk. Added
the annotation, then re-did the standard update procedure (edit → delete isvc
→ wait for pod/revision clear → re-apply) and re-ran the full battery: still
**6 PASS/4 EXP/0 FAIL**, cached-venv wake ~15s, no regression. Our measured
first-ever build was ~4 min (well under even the 600s default), so this
wasn't an observed failure — it's margin against a slower run, not a fix for
something broken live.

## Access note (2026-09-25, resolved)

`/project/def-amii-compute-team/repos/aleph` was `rwxr-s---` (owned by
`rahimk:amii-engineering`, group read/execute only) — this session runs as
`iqapple`, a group member but blocked by the missing group-write bit. Per
`docs/SHARED-ACCESS.md` this is the known open item for additional shared
operators. Resolved this session with the user's explicit approval:
`sudo chmod -R g+w /project/def-amii-compute-team/repos/aleph` (group-write
only; did not touch `rahimk`'s private deploy key or any file contents). The
six deployment files were then copied in from the ops-dir staging path
(`tmqmg-painn-3d/deployment/vulcan/models/tmqmg-painn-3d/`, kept in sync as a
historical draft) to `models/tmqmg-painn-3d/` in the real checkout.

## Scaling change: always-on (2026-09-25)

User requested at least 1 pod always up (not scale-to-zero). Changed
`inferenceservice.yaml` (`minReplicas: 1`, added `maxReplicas: 2`) and
`details.yaml` (`scale_to_zero: false`, `min_replicas: 1`,
`idle_retention: "always-on"`, `cold_start_estimate: "Always on"`) — matches
the fleet convention for small always-on services (e.g. `bge-m3`,
`esm2-650m`). Applied via delete+recreate, not patch. Verified stable (3+ min
`3/3 Running`, 0 restarts) and functionally unchanged (`test.py` still
6 PASS/4 EXP/0 FAIL, now with `attempts=1` — no cold start at all). Cost:
one persistent ~600MiB GPU slice held continuously instead of only on demand.

## Deploy / update steps

See `README.md` "First-time staging" and "Deploy / update / test".

## Validation checklist

- [x] `test.py` battery: 0 FAIL/ERR (6 PASS, 4 EXP)
- [x] Live response matches `example_prediction.json` oracle within the
      `smoke_test.py` tolerance (`abs_tol=5e-4` eV on S1 energies, exact CT labels)
- [x] Scale-to-zero → cold-start → 200 cycle observed
- [x] `kubectl delete isvc` + re-apply from these files reproduces a passing
      result (proves it isn't dependent on an unrecorded live edit)
- [x] `/v1/models?all=true` lists `tmqmg-painn-3d`
- [x] Measured GPU memory recorded here, `nvidia.com/gpumem` left at 4096 (headroom, not oversized)
- [x] Dated results + final resource numbers added to `README.md`
- [ ] Load/stress ("pressure") testing — not run; low-traffic single-molecule
      screening tool, but genuinely unverified under concurrency/burst
- [ ] Dated `CHANGELOG.md` entry added before commit/push — not yet committed,
      pending separate go-ahead (repo-write and live-deploy were already two
      separate authorizations; commit/push is a third)
