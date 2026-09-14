# Model documentation: README.md and CLAUDE.md

Every model directory should explain what users can do and what the next operator
needs to know. Keep deployment definitions in their owning YAML files; notes
explain choices and evidence rather than becoming another configuration source.

## README.md: current state and use

The README answers whether the model works and how to use it. Include:

- Purpose, supported tasks, upstream model/runtime sources and license/access needs.
- Public model ID, API path, example input/output and interpretation with domain units.
- Deployment/test commands using complete repository-relative paths and private
  environment variables for access, with no credentials or local addresses.
- Final tested image/dependency/model revisions, resources, storage and lifecycle.
- Dated validation scope: useful checks, failures, skipped cases and known limitations.
- Whether work is complete, in progress or blocked, and what remains to establish.

A reusable outline:

```markdown
# Model name

## Purpose and supported API
Describe the task, inputs, output interpretation, license and upstream sources.

## Deploy and use
List the owning manifests, follow the shared deployment/update workflow,
and give a small supported request and expected result.

## Tested configuration
Record runtime/model revisions, resources, storage and scaling.

## Validation and limitations
YYYY-MM-DD: record the exact configuration and checks performed, including
untested cases and the command used to run test.py.
```

## CLAUDE.md: research and continuity

The model's CLAUDE notes preserve what another human or agent needs to continue.
The starter checklist below provides the skeleton. Include:

| Topic | Useful record |
|---|---|
| Research | Model/runtime instructions consulted, architecture support, access requirements and reference fixtures |
| Runtime | Image/version, entry command, parser/template choices, precision, dependencies and why they fit |
| Resources | CPU/RAM/GPU allocation, shared-memory needs, concurrency findings and evidence |
| Storage | Claim and mount paths, helper or serving venv, revision markers and cached-start checks |
| API and card | Public/native paths, payload differences, thinking/tool behavior, limits and required adapter work |
| Failed approaches | What failed, observed symptoms, diagnosis and the working replacement |
| Deviations | Why the standard pattern did not fit, what changed and how it was validated |
| Continuation | Current blocker, next useful check and scope of any unfinished work |

Keep dates on observations; a past successful result is evidence for that tested
configuration, not a permanent guarantee. Keep the README's current status concise
and use these notes for relevant history. Neither file should copy private account,
key or raw usage records. Site access details belong in private local notes and
[Site values](../docs/SITE-VALUES.md), as appropriate.

Starter checklist for a new model's CLAUDE.md:

```markdown
# <model-name> Notes

## Purpose
Short description of model use in this cluster.

## Runtime
- Image:
- Entry command/args:
- API path(s):

## Resources
- CPU request/limit:
- Memory request/limit:
- GPU request:
- HAMi gpumem:

## Storage
- PVC name:
- Mount path:
- Warm-cache condition:

## Known quirks
- Tool calling:
- Reasoning behavior:
- Context limits:
- Cold-start profile:

## Deploy / update steps
1.
2.
3.

## Validation checks
- [ ] basic request
- [ ] streaming (if applicable)
- [ ] tool call behavior (if applicable)
- [ ] anthropic translation (if applicable)
- [ ] no secret values in manifest
```

Replace the checklist with prose as findings accumulate; the headings that matter
are the research/runtime/resources/storage/API/failed-approaches rows above.

## Keep the files consistent

After tuning, update the service, card, test and notes together. Preserve the model's
PVC and intentionally hidden status. Refer to the shared
[deployment workflow](../docs/ADD-A-MODEL.md) for commands instead of maintaining a
second, potentially stale recreate/scaling procedure. Every repository change
needs a dated changelog entry when committed.
