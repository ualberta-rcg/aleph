# Validating a model: test.py

Each deployed model has one basic `models/<model>/test.py`. Start from the existing
examples, adapt the requests and expected results during deployment, and keep all
applicable checks in its normal run. This reference explains the existing files;
it does not replace them with a framework or change their assertions.

## Choose existing material

| Existing example | Use and adaptation |
|---|---|
| [Chat and API battery](test.template.py) | Chat, system prompts, sampling, tools, vision, reasoning, meta-tasks, OpenAI/Anthropic and accounting. Also contains embedding/reranking sections to select when relevant. |
| [Custom science battery](test.science-template.py) | Explicit scientific request, output shape, domain checks, limits, concurrency and recovery. Supply the model's real fixture and assertions. |
| [OpenAPI science battery](test.science-openapi-template.py) | Native scientific/NIM schema exploration, required fields, enums/ranges and gateway checks. Understand its direct-backend calls and endpoint discovery before using it. |

Read the whole selected file and comparable model tests. A name does not limit
which useful checks can be adapted from it. Templates contain illustrative values
and incomplete assertions; copying one unchanged does not validate a model.

## What to customize

| Item | What to establish |
|---|---|
| Model and endpoint | Public card ID and actual supported API, not necessarily the directory or runtime name |
| Fixture | Small reproducible input with a known answer, reference output or meaningful domain properties |
| Expected output | Required keys/types, units, dimensions, finite values, correctness and interpretation |
| Features | Supported tools, image/audio formats, reasoning controls, streaming and alternate APIs |
| Limits | Measured context/input/payload/batch/output boundaries and documented rejection or truncation |
| Workload | Representative long inputs, concurrency and sustained requests within the authorized resource budget |
| Startup | Bounded retries appropriate to cached load time; distinguish loading, capacity refusal and runtime errors |
| Regression checks | Reproduce issues discovered while deploying and retain the checks after fixing them |

The manifest, [card](details.md) and tests describe the same contract. Adjust them
together as research establishes what works. Start with standard patterns; explain
a justified deviation in model notes. Do not remove applicable coverage merely
because it exposes a deployment problem.

## Capability variations

**Chat and completions.** Check known answers, system instructions, sampling,
stop/output limits, complete streams and accounting. A completions-only API uses
`prompt` and text completions rather than messages; adapt requests and assertions
to it instead of assuming the chat handler applies defaults.

**Reasoning.** Retain reasoning tests for reasoning models, using supported effort,
toggle or budget controls. Check enabled/disabled behavior where applicable,
reasoning versus final content, a verifiable final answer and streaming in each
supported API. Some models always reason internally; hidden output is not proof
that computation stopped. Use [the gateway's thinking behavior](details.md#capabilities-and-reasoning)
to choose expectations. Template budgets are examples, not model-independent limits.

**Tools.** Check function names, argument structure and tool-result continuation.
Test interaction with thinking where supported. A tools capability flag does not
install a runtime parser. Check documented rejection for unsupported features.

**Vision, video and audio.** Supply known fixtures and check useful interpretation
or output, not only an HTTP success. Match the dedicated handler's JSON/multipart
format. Include size/format limits. Missing fixtures remain untested. Use synthetic
or appropriately shareable fixtures and avoid putting private research in output.

**Embeddings and reranking.** Check vector dimension and finite values, ordering,
semantic similarity/ranking, batch behavior and input boundaries. Adapt load and
recovery requests to their endpoints rather than leaving chat calls in the runner.
For protein embeddings, document whether accounting counts residues or tokens.

**Science.** Specify real domain inputs and meaningful expected outputs: structures,
forces/energies, sequences, forecasts or classifications as appropriate. Schema and
sanity checks alone are not a scientific accuracy assessment. Distinguish API
integration, domain sanity and comparison to a trusted reference.

**OpenAPI-backed servers.** The existing example can probe native POST operations
and generate requests from schema values. These calls can run expensive inference;
inspect the selected operations and bound the workload before running it. Native
checks diagnose the backend but do not establish public gateway compatibility.
Schemas can use references/compositions the example does not fully validate; read
the actual contract and add explicit checks. A missing schema is not a successful
validation. Do not assume every packaged runtime is a NIM or has the same health,
model-list and OpenAPI paths.

## One run, complete results

A normal run executes all applicable checks, including limits, stress/load and
recovery. Keep the simple function list and summary. Separate stress scripts and
test-selection switches are not needed. Set workload sizes deliberately in the
model's test, and retain a valid final request after invalid inputs and load.

For exact chat boundaries, account for tokenized input, chat formatting and output
allowance. Other models need appropriate sequence lengths, image dimensions,
audio duration or batch sizes. Observe latency, queueing, GPU memory and runtime
errors during authorized load tests; four small concurrent requests alone do not
measure production capacity.

| Result | Meaning |
|---|---|
| `PASS` | The defined assertion passed |
| `EXP` | A documented expected result, such as rejection of an unsupported feature |
| `FAIL` / `ERR` | Failed assertion or exception; resolve and rerun |
| `SKIP` | Not checked; record why and keep the limitation visible |

Some template sections deliberately require stronger model-specific assertions.
For example, an HTTP 200 or a nonempty reasoning field alone cannot establish
scientific correctness or a correct final answer. Inspect the checks before claiming
coverage. Expected results must be defined in advance, not relabeled after failure.
Review both exit status and skips; a zero exit does not prove complete coverage.

## Running and recording

Prepare dependencies in an allocated test environment or suitable container.
Do not run inference/load tests on a shared login node. Set `GW_URL` to the public
origin, provide `TYK_KEY` privately, and keep TLS verification enabled. Then run:

```bash
MODEL=example-model python3 models/example-model/test.py
```

The existing examples also allow direct gateway-container execution for diagnosis.
That bypasses public ingress/authentication and cannot replace an authenticated
end-to-end check. Do not copy old hostnames, insecure-TLS examples or local access
settings into a model's public documentation. See [Endpoints](../docs/ENDPOINTS.md).

Recreate from final source while retaining the PVC, then rerun the model battery.
Verify intended scale-to-zero/wake or always-up behavior separately under the
[deployment workflow](../docs/ADD-A-MODEL.md). Record dated versions, resources,
results and unverified cases in the [model notes](model-notes.md). Do not delete
persistent data to manufacture a cold installation test.
