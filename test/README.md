# test/ — deployment & verification tests

Scripts for bringing up and verifying models through the gateway. Run from a
Vulcan login node with a Tyk key (see `docs/RUNBOOK.md`) unless noted.

| Script | What it does |
|---|---|
| `smoke.sh` | Copy-pasteable curls: catalogue, OpenAI chat, reasoning, streaming, Anthropic, vision, embeddings, telemetry, cold-start. |
| `test-model.sh` | Per-model deploy-from-repo + Knative-aware activation (pre-warm via gateway), `recreate` (delete+clear+reapply, keep PVC), curl with cold-start retry, scale-cycle. Usage: `test/test-model.sh <model> {apply\|recreate\|status\|curl <path> <body>}`. |
| `full_test.py` | Full OpenAI + Anthropic compatibility sweep across the chat fleet. |
| `metatask_test.py` | Meta-task (title/tags/followups) handling. |
| `thinking_test.py` | Thinking/reasoning param translation (effort/budget/toggle). |
| `retest.py` | Targeted re-run of a model's tests after a change. |
| `test-pending-batch2b.py` | Batch test of the pending (batch-2b) model set. |

Committed test fixtures live in `test/inputs/` (e.g. `1crn.pdb`). Ad-hoc scripts
and transient outputs go in `scratch/` — a local working dir (gitignored, not
part of the repo).
