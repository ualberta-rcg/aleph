# Deploy a model

A model deployment brings together three things: **how to run it**, **how Aleph
exposes it**, and **evidence that it works**.

[Part 1](#part-1-deploy-manually) explains the files and manual deployment steps.
[Part 2](#part-2-the-agentic-deployment-loop) is the process an AI coding agent uses
to research an unfamiliar model, tune it, test it, and prove the final deployment.
Both use the same repository files and public API.

## Part 1: Deploy manually

### 1. Start with an existing model

Read the upstream model's serving instructions, then inspect a similar directory
under `models/`. Read its manifests, card, test, README and implementation notes
before copying. Choose by runtime and task, not just model size.

| Pattern | Repository example | What to study |
|---|---|---|
| vLLM chat/reasoning | [models/gpt-oss-20b/](../models/gpt-oss-20b/) | Serving configuration, reasoning translation and a tailored chat test battery |
| Embeddings with TEI | [models/bge-m3/](../models/bge-m3/) | Shared GPU allocation, model mount, embeddings route and dimension/batch tests |
| Reranking with TEI | [models/bge-reranker-v2-m3/](../models/bge-reranker-v2-m3/) | Query/documents contract, top-N output and relevance-order tests |
| Custom science server | [models/esm2-650m/](../models/esm2-650m/) | Embedded server ConfigMap, persistent environment/weights and protein-embedding checks |
| NVIDIA NIM | [models/boltz-2/](../models/boltz-2/) | Registry/download credentials, NIM cache, port/health paths and prefix translation; inference not verified in this review |


| Model | Output checks that passed |
|---|---|
| `gpt-oss-20b` | Correct answer to 2 + 5, normal stop completion, no exposed reasoning when disabled |
| `bge-m3` | Three-input batch, 1,024-dimensional finite/nonzero vectors, consistent duplicate inputs and distinguishable different text |
| `bge-reranker-v2-m3` | Two results requested from three documents; relevant document first, finite descending scores |
| `esm2-650m` | Three short synthetic protein sequences, 1,280-dimensional finite/nonzero vectors, duplicate consistency and distinct-input differences |

These are basic functional checks, not the complete batteries. They did not test
public Tyk authentication, cold starts, redeployment, load, or scientific validity.
Boltz remains a configuration reference without inference verification in this
review. Do not transfer these results to a copied or modified deployment.

For additional implementation patterns, inspect
[models/gemma-4-26b-a4b/](../models/gemma-4-26b-a4b/) for multimodal setup and
[models/caduceus/](../models/caduceus/) for a custom compiled-dependency environment.

For an existing deployment, inspect its live configuration before proposing a
change; that is the evidence for how it currently runs. Compare it with source and
record differences. A running cluster, an installed service, or a Ready condition
is not evidence that every model or capability has been tested.

These are patterns, not universally correct defaults. Existing README text and
comments can lag behind manifests; some examples retain historical workarounds or
floating image tags. Verify the current implementation and select an explicit
compatible runtime version for your model. Do not inherit another model's test
results, capability claims, storage names or scaling limits.

### 2. Understand the model directory

All paths below are relative to the repository root. Replace `example-model`
with your chosen directory name throughout the files and commands.

| File | What goes in it |
|---|---|
| `models/example-model/pvc.yaml` | A PersistentVolumeClaim: namespace, unique claim name, storage class, access mode and requested capacity for reusable weights/caches. Aleph's shared NFS pattern uses `ReadWriteMany` with `nfs-models`. Omit only when the runtime genuinely needs no persistent files. |
| `models/example-model/inferenceservice.yaml` | The KServe InferenceService: runtime image/version, command and arguments, container port, resource requests/limits, placement, probes, timeouts, scaling, storage mounts and Secret references. Include init containers for any download or environment preparation. |
| `models/example-model/details.yaml` | The gateway model card, stored as JSON inside a ConfigMap. Describes the public model ID, task, endpoints, backend mapping, tested capabilities, input/output descriptions, limits, defaults and scaling behavior. This makes the deployment discoverable. |
| `models/example-model/test.py` | One test script for this model through Aleph: valid and invalid requests, expected outputs, supported features, limits, cold starts, load/stress and recovery. Customize it during deployment; running it executes all applicable checks. Accept `GW_URL`, `TYK_KEY` and `MODEL` through the environment. |
| `models/example-model/README.md` | What the model does and how to use/deploy it: runtime configuration, file list, complete commands, sample input/output, tested capabilities, dated results and known limitations. Distinguish upstream capability from what this deployment exposes. |
| `models/example-model/CLAUDE.md` | Implementation memory for the agent/operator: research links, why settings were chosen, dependency/parser quirks, failed approaches, measurements and remaining work. Start from [models/CLAUDE-TEMPLATE.md](../models/CLAUDE-TEMPLATE.md). |

Add files only when the model needs them:

| Additional file examples | Purpose |
|---|---|
| `models/example-model/server-configmap.yaml` and/or `models/example-model/server.py` | Custom HTTP server that loads the model and implements its request/response contract; mount or package the code as appropriate. |
| `models/example-model/parser-configmap.yaml` and/or `models/example-model/parser.py` | A runtime-specific parser, mounted and enabled by the serving command. |
| `models/example-model/chat_template.jinja` | A required chat format, supplied through the image, storage or a supporting ConfigMap. |
| `models/example-model/test-input.json` or domain fixture files | Small, redistributable test inputs with a documented expected result. Keep research data and credentials out. |

Prefer individual YAML applies; a new model does not need a kustomization layer.
Some existing files contain several YAML documents separated by `---`: for example,
Caduceus's service file also defines its server ConfigMap. Inspect the file before
assuming its basename tells you every resource it creates. Avoid defining the same
supporting ConfigMap in two places.

### 3. Connect storage, runtime and card

**Storage and startup.** The service's `persistentVolumeClaim.claimName` must match
`models/example-model/pvc.yaml`; its `volumeMounts[].name` must match its own volume
name. Names need not all be identical. Use a unique claim for a new deployment;
never rename or delete an existing model's claim just to match a naming convention.

Make setup idempotent. Cache downloaded weights and required prepared environments
so a restart does not repeat installation. A lightweight download-helper environment
is different from a custom server's full runtime environment. Mark setup complete
only after required artifacts are usable: one existing file or directory does not
prove a partial download/build finished. Prevent multiple initializers from writing
the same unfinished environment. Keep credentials in Kubernetes Secrets; an export
in your local shell does not supply them to a pod.

**Runtime and resources.** Match the actual serving port, health endpoint, model
path and API format. Budget startup probes for loading/initialization and use
readiness to exclude an unready server. Choose CPU, RAM, storage and GPU resources
from evidence. With HAMi, shared allocations request GPU count plus
`nvidia.com/gpumem` in MiB; whole-device allocations omit `gpumem`. Check topology
and runtime compatibility before copying tensor-parallel, attention or memory flags.
See [HAMi diagnostics](KUBERNETES.md#hami-diagnostics) for placement failures.

**Card.** Follow [models/DETAILS-TEMPLATE-LLM.md](../models/DETAILS-TEMPLATE-LLM.md):

- Set ConfigMap label `model-details: "true"` and put valid JSON in `data.details.json`.
- Set `id`, `type`, `schema_version`, and the appropriate public/health `endpoints`.
- Use `routing.k8s_name` for a differing InferenceService name and
  `routing.upstream_model_id` for a differing backend model name. Add only routing
  translations the gateway actually implements; Boltz's prefix handling is one example.
- Put capability flags in `behavior`, not `compatibility`. Describe input/output
  fields, types and units in `input_map`/`output_map`; descriptive maps alone do not
  implement a new backend adapter or input validator.
- Set tested `limits`, `defaults`, and any required `param_translation`. Put model
  provenance, license, upstream links and descriptions in `catalog`.

A custom server must return real results, not a demonstration response. Keep any
upstream `usage` object limited to accounting metadata because the gateway retains
it in [usage records](LOGGING.md).

**Scaling.** Configure the service and card together:

| Mode | `models/example-model/inferenceservice.yaml` | `models/example-model/details.yaml` |
|---|---|---|
| Idle scale-to-zero | `spec.predictor.minReplicas: 0`; no stop annotation | `scaling.scale_to_zero: true`, `scaling.min_replicas: 0` |
| Always up | Minimum at least 1; no stop annotation | `scaling.scale_to_zero: false`, matching `scaling.min_replicas` |

Set `maxReplicas` to a capacity-conscious bound, at least the minimum. Keep idle
retention settings consistent. `scaleTarget` is an autoscaling target, not the
runtime's batching limit; tune their interaction rather than assuming they must
be numerically equal. See [KServe's Knative autoscaling guide](https://kserve.github.io/website/docs/model-serving/predictive-inference/autoscaling/kpa-autoscaler).

### 4. Apply and call the model

Use a shell with administrative `kubectl` access to the intended cluster and a
checkout of the repository. Follow [Quickstart](../QUICKSTART.md) for platform
prerequisites and [environment setup](../CLAUDE.md#environment-and-private-configuration)
for access configuration. Check storage, available capacity and the required Secrets
without printing credentials.

For a **new** model, run from the repository root, applying each file separately:

```bash
kubectl apply -f models/example-model/pvc.yaml
# Apply required supporting files, if present, before the service:
kubectl apply -f models/example-model/server-configmap.yaml
kubectl apply -f models/example-model/inferenceservice.yaml
kubectl apply -f models/example-model/details.yaml
kubectl get isvc example-model -n models
kubectl get pods -n models -l serving.kserve.io/inferenceservice=example-model
```

Skip the supporting-file command when that file is absent or its ConfigMap is
already included in the service YAML. Add other required supporting files explicitly.
For an existing service whose spec changes, use the recreation steps in Part 2.

The gateway watches cards; adding one needs no gateway restart. A catalog entry
alone is not proof of a working model. With `GW_URL` set to the public origin
(without `/v1`) and `TYK_KEY` supplied privately, check the full catalog:

```bash
curl --silent --show-error --fail-with-body --max-time 120 \
  -H "Authorization: Bearer $TYK_KEY" "$GW_URL/v1/models?all=true"
```

Send the model's documented valid request or run its tailored test. An idle service
may need that request to activate. Honor cold-start retry guidance within a bounded
startup window; capacity refusal, loading and runtime failure are different outcomes.
Do not repeatedly reapply while weights or environments are being prepared.

In your prepared test environment, with dependencies installed and the endpoint/key
exported, run:

```bash
MODEL=example-model python3 models/example-model/test.py
```

Use an appropriate allocated environment for tests/builds, not a shared login node.
Keep TLS verification enabled. Public API tests exercise authentication and routing;
an internal backend call is a diagnostic, not a substitute. Check the reported
results as well as the process exit code—some existing batteries only print failures.

## Part 2: The agentic deployment loop

This is the workflow for an AI coding agent developing or repairing a deployment.
A human specifies the model, intended capability, allowed environment and resource
budget. The agent works one model at a time, records evidence in its directory,
and stays within that scope. Existing unrelated deployments are left alone.

```text
Research → adapt files → deploy → inspect → tune settings
                            ▲                  │
                            └──────────────────┘
       → functional battery → pressure and recovery tests
       → clean redeployment → repeat verification → record → commit/push
```

### 1. Research and adapt

Read the upstream model card, architecture/configuration, license and access terms,
then the serving runtime's documentation for the version you intend to deploy.
Confirm task, real I/O, context/input limits, quantization, hardware fit, parsers,
sampling recommendations and dependency compatibility. Use upstream issues and
recipes to investigate failures; verify suggestions against the selected version.
Useful starting points are [vLLM serving](https://docs.vllm.ai/en/latest/serving/online_serving/)
and [TEI's quick tour](https://huggingface.co/docs/text-embeddings-inference/quick_tour).
A science/NIM model needs its own runtime's API and domain documentation.

Adapt the closest example from Part 1. Record source links, chosen settings and
reasons in `models/example-model/CLAUDE.md`. Do not copy historical fleet version
ladders, memory thresholds, replica counts or model-specific workarounds as defaults.

### 2. Iterate settings until the model works

Deploy, inspect startup and a small valid request, identify the cause of a failure,
change the owning source file, recreate, and try again. This settings iteration is
a separate phase from running the full battery. Record each useful finding so the
next agent session continues from evidence.

Distinguish image pull/download failures, incomplete setup, scheduler capacity,
GPU-memory exhaustion, wrong ports/probes, parser failures and wrong output shape.
For a runtime issue, inspect its relevant diagnostic output and research the exact
version. Change a small, explainable set of settings, then check its effect.
Do not expose credentials, private prompts or other users' records in reports.

**Every InferenceService spec update uses delete and recreate, never patch.**
Edit `models/example-model/inferenceservice.yaml` first, then:

```bash
kubectl delete isvc example-model -n models
kubectl wait --for=delete pod -n models \
  -l serving.kserve.io/inferenceservice=example-model --timeout=300s
kubectl get revisions.serving.knative.dev -n models \
  -l serving.kserve.io/inferenceservice=example-model
# Continue only after old predictor pods AND revisions have cleared.
# Apply changed supporting ConfigMaps before recreating the service.
kubectl apply -f models/example-model/inferenceservice.yaml
kubectl apply -f models/example-model/details.yaml
```

Use the actual service name when it differs from the directory name. Stop on a
failed wait and investigate remaining resources; never fall through to recreate.
Preserve the PVC and shared data. Do not manually scale controller-owned predictor
Deployments. Do not interrupt staging or delete a cached environment without a
separately justified recovery plan. Keep intentionally parked cards absent.

### 3. Prove the advertised features

Keep one test script per model: `models/example-model/test.py`. Start from the
appropriate template:

- [models/test.template.py](../models/test.template.py): chat, reasoning, tools,
  vision, Anthropic, embeddings and reranking sections to select from.
- [models/test.science-template.py](../models/test.science-template.py): custom
  science requests, output shape and domain sanity checks.
- [models/test.science-openapi-template.py](../models/test.science-openapi-template.py):
  models with a documented/OpenAPI-described science API.

Customize this file as you deploy and learn about the model. The operator or AI
agent should update its requests, fixtures, expected outputs, boundary cases and
load sizes to match the model and available resources. Keep those checks in the
same file and rerun the complete battery against the final deployment.

Templates are menus, not automatic proof of support. Replace placeholder inputs
and expected results, remove irrelevant positive tests, and retain useful checks
that unsupported requests fail cleanly. Verify results, not just HTTP 200:

| Capability | Evidence |
|---|---|
| Chat/completions | Correct simple answer, model identity, stop/truncation behavior, streaming completion |
| Tools/reasoning | Correct tool and arguments, follow-up result handling, supported thinking on/off behavior and token budgets |
| Images/audio | Known inline fixture, correct interpretation/output and explicit size/format limits |
| Embeddings/reranking | Dimension, finite values, ordering or similarity expectations, batches and input limits |
| Science | Real domain input, output schema/units and comparison to a suitable reference; a plausible shape alone is not scientific validation |
| Alternate APIs and guards | Supported Anthropic behavior, invalid model/input handling and endpoint/type rejection |

Resolve failures and errors. `EXP` must mean a documented expected outcome, not a
failure relabeled to pass. A missing fixture or skipped capability remains unverified;
remove the claim or report the limitation. Preserve the detailed result summary.

### 4. Pressure-test and harden

Keep functional, limit and pressure checks together in `models/example-model/test.py`.
Running that file runs the whole battery, with no separate stress command or test-selection
flags. Follow the existing simple style: small test functions, API calls, assertions
and one results summary. Keep the workload within the authorized resource budget.
Start small, then exercise representative long inputs, concurrency,
bursts and a sustained mix; include multimodal inputs where advertised.

Measure request latency/throughput, queueing, GPU memory and runtime health. Check
for OOM/engine death and finish with a valid request proving the server still works.
Exercise scale-up when capacity permits and scale-down after traffic stops; record
capacity-blocked checks as unverified. Scope recovery tests so they cannot disrupt
other models. [Logging and metrics](LOGGING.md) explains physical GPU measurements,
runtime load and the limits of accounting estimates.

Tune memory headroom, context, batching/concurrency, probes and scaling from those
measurements. Do not infer that a queue always means too few replicas or that free
KV cache alone justifies increasing concurrency. After a fix, recreate and repeat
the affected functional and pressure checks. One successful long request does not
prove that the same input size works under concurrent load.

### 5. Prove reproducibility, then finish

Once the settings, battery and pressure checks pass, recreate the service from the
final repository files while preserving its weights. Reapply all required supporting
resources and the intended card. Repeat functional verification and the relevant
load/recovery checks against that final deployment. A live-only patch or a cached
manual dependency is not a reproducible result.

For idle scale-to-zero, confirm pods disappear after the idle window and a later
valid request wakes the service. For always-up, confirm the intended minimum stays
ready. Parking hides a card; stopping execution is different—see the
[operator scaling procedures](../CLAUDE.md#park-stop-scale-to-zero-or-keep-always-up).

Update `models/example-model/README.md` with the final runtime/image, resources,
scaling, complete deployment/test commands, dated measurements and limitations.
Keep the research and tuning record in `models/example-model/CLAUDE.md`. Remove
stray test resources, preserve intended services/storage, and record unfinished
work honestly if blocked.

