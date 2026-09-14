# Deploy a model

A deployment defines how to run a model, how Aleph exposes it, and how to check
its results. The manual steps and agentic loop below use the same files and tests.

1. Research the model and inspect templates and similar deployments in `models/`.
2. Prepare `pvc.yaml`, `inferenceservice.yaml`, `details.yaml` and one `test.py`.
3. Apply storage, then the service, then the card; recreate an existing service when updating its spec.
4. Run `test.py`, fix problems and repeat against the final deployment.
5. Record configuration, findings and dated results in the model's README and CLAUDE notes.
6. Review the final diff, add a dated changelog entry, then commit and push.

**Updating an existing InferenceService: edit its source, delete the service,
wait for old predictor pods and revisions to clear, then recreate it. Never patch
its spec or delete its PVC.** The [update procedure](#update-an-existing-service)
applies to both human operators and agents.

## Research once, then adapt

Read the model's upstream instructions and the documentation for the intended
runtime version. Establish the task, real inputs and outputs, license/access
requirements, model files, dependencies, hardware needs and input limits.
For language or multimodal models, check quantization, parsers, chat formatting,
sampling and supported tools/reasoning. For science models, check domain units,
output interpretation and a suitable reference result.

Look at templates and examples in `models/`. Choose by runtime and task, read
the deployment YAML, card, test and notes, and adapt them together. The templates
include chat, custom science, and embedding/reranking/audio patterns. File names
and examples can change; inspect their contents rather than assuming a template
is limited to the task in its name.

For an existing deployment, compare its live configuration with source before
editing. Check what it actually runs and preserve the working settings you are
not changing. Readiness and old test results are starting evidence, not proof of
a modified deployment. Keep dated measurements with the model rather than adding
fleet snapshots to this guide.

Record research, chosen versions, reasons and deviations in
`models/example-model/CLAUDE.md`. An operator or AI agent may deviate from the
usual layout when research establishes a need; explain the reason and make the
result reproducible. Work within the authorized environment and resource budget.

## Part 1: Deploy manually

### 1. Prepare the model directory

Paths below are relative to the repository root. Replace `example-model` with
your directory name. The normal layout has four implementation files plus notes:

| File | Contents |
|---|---|
| `models/example-model/pvc.yaml` | PersistentVolumeClaim: name, namespace, storage class, access mode and capacity for weights, caches and any required virtual environment. |
| `models/example-model/inferenceservice.yaml` | Runtime image/version, startup commands, init containers, ports, probes, resource requests/limits, scaling, mounts and Secret references. Keep model-specific setup and small server/configuration definitions here. |
| `models/example-model/details.yaml` | Gateway card ConfigMap: model ID, task, API paths, routing, inputs/outputs, capabilities, limits, defaults, scaling and provenance. |
| `models/example-model/test.py` | One basic script covering valid/invalid requests, expected results, supported features, limits, cold starts, load/stress and recovery. Customize it during deployment; a normal run executes all applicable checks. |
| `models/example-model/README.md` | What the model does, sample requests/results, complete deployment/test commands, final configuration, dated results and limitations. |
| `models/example-model/CLAUDE.md` | Research sources, configuration decisions, runtime quirks, failed approaches and findings for the next operator or agent session. |

Most deployments should fit this layout. A custom server can be a ConfigMap
document inside `models/example-model/inferenceservice.yaml`, followed by the
InferenceService document, separated with `---`. Mount the ConfigMap into the
serving container. Initialization scripts belong in that file's init containers.
This keeps setup, server configuration and deployment together in one apply.

### 2. Connect storage, runtime and card

**Persistent storage and environments.** Match the service's
`persistentVolumeClaim.claimName` to `models/example-model/pvc.yaml`, and each
mount name to its volume. Use a unique claim for a new model and preserve an
existing model's claim and data. Omit a PVC only when no persistent files are
needed. Deployment-specific storage values belong in [Site values](SITE-VALUES.md).

When a model needs a Python virtual environment, **create it on the model's PVC**.
For example, mount the claim at `/data`, prepare `/data/venv` in an init container,
then start the server with `/data/venv/bin/python`. Mount that same claim and path
in both containers. Use compatible Python, system libraries and CUDA dependencies
between setup and serving. A runtime image that already provides the required
environment does not need another venv.

Persist downloaded weights and prepared dependencies so restarts and scale-from-zero
reuse them. Make setup idempotent: verify required files and imports before marking
it complete, and coordinate initialization so replicas do not build the same
unfinished environment concurrently. Prepare a replacement environment deliberately
when dependencies change; preserve the working one until replacement is validated.
Supply credentials through Kubernetes Secrets referenced in the YAML.

**Runtime and resources.** Select an explicit compatible image version or digest.
Match its serving port, health endpoint, model path and API format. Allow startup
probes enough time for preparation/loading, and use readiness to exclude an unready
server. Set CPU, RAM, GPU and storage budgets from measured needs.

For HAMi sharing, request a GPU count and a memory allowance in MiB. For example,
this container resource block requests one shared device with 20 GiB of GPU memory:

```yaml
# Inside a serving container in models/example-model/inferenceservice.yaml
resources:
  requests:
    cpu: "2"
    memory: 8Gi
    nvidia.com/gpu: "1"
    nvidia.com/gpumem: "20480"
  limits:
    cpu: "4"
    memory: 16Gi
    nvidia.com/gpu: "1"
    nvidia.com/gpumem: "20480"
```

These are illustrative budgets. GPU memory must cover weights, runtime overhead
and the intended input/concurrency, not just the model file size. Whole-device
allocations omit `nvidia.com/gpumem`; set GPU count to the number of devices needed
per replica. Verify topology and runtime compatibility for multi-GPU operation.
Use [HAMi diagnostics](KUBERNETES.md#hami-diagnostics) to distinguish placement
problems from runtime memory exhaustion.

**Model card.** Inspect the relevant card templates and examples in `models/`:

- Label the ConfigMap `model-details: "true"` and store valid JSON in `data.details.json`.
- Set the public `id`, task `type`, schema version and documented API/health paths.
- Set `routing.k8s_name` if the service name differs and `routing.upstream_model_id`
  if the backend model name differs. Use only translations the gateway implements;
  [Endpoints](ENDPOINTS.md) explains dedicated handlers and custom-path forwarding.
- Put capability flags in `behavior`. Describe input/output types and domain units
  in `input_map`/`output_map`; these descriptions do not implement validation or adapters.
- Keep tested limits, defaults and parameter translations consistent with the
  runtime. Put provenance, license and upstream links in `catalog`.

Science cards need their actual input/output contract, not copied chat capabilities.
A custom server must produce real model results. Limit any upstream `usage` object
to accounting metadata because it is retained in [usage records](LOGGING.md).

**Scaling and visibility.** Keep service and card settings consistent:

| State | Service | Card |
|---|---|---|
| Idle scale-to-zero | `spec.predictor.minReplicas: 0`; no stop annotation | `scaling.scale_to_zero: true`, `scaling.min_replicas: 0` |
| Always up | Minimum at least 1; no stop annotation | `scaling.scale_to_zero: false`, matching minimum |
| Park/hide | Service unchanged; this alone does not stop compute | Remove the deployed details ConfigMap; retain source |
| Stop execution | `serving.kserve.io/stop: "true"` annotation | May remain visible, or also be hidden |

Parking and stopping are separate actions. Preserve an intentionally hidden card
when updating its service. See the [operator procedures](../CLAUDE.md#park-stop-scale-to-zero-or-keep-always-up)
for commands. Set `maxReplicas` at least as high as the minimum and within capacity.
Tune the Knative concurrency target against the runtime's batching behavior; they
are different settings. Keep idle-retention settings consistent too.

### 3. Apply a new deployment or update an existing one

Use an administrative shell for the intended cluster and the repository checkout.
[Quickstart](../QUICKSTART.md) covers prerequisites; [Site values](SITE-VALUES.md)
owns site configuration. Check available capacity, storage and required Secrets
without displaying credentials. Commands below use `example-model` as both the
directory and service name; substitute the actual service name where they differ.

#### New deployment

Apply each file in order, from the repository root:

```bash
kubectl apply -f models/example-model/pvc.yaml
kubectl apply -f models/example-model/inferenceservice.yaml
kubectl apply -f models/example-model/details.yaml
```

#### Update an existing service

Edit `models/example-model/inferenceservice.yaml` first. For a spec change,
delete only the InferenceService, leaving its PVC and data intact:

```bash
kubectl delete isvc example-model -n models
kubectl wait --for=delete pod -n models \
  -l serving.kserve.io/inferenceservice=example-model --timeout=300s
kubectl get revisions.serving.knative.dev -n models \
  -l serving.kserve.io/inferenceservice=example-model
```

Continue only when the wait succeeds **and** no old predictor pods or revisions
remain. If either check fails, inspect the remaining resources before proceeding.
Then recreate from source:

```bash
kubectl apply -f models/example-model/inferenceservice.yaml
# Apply the card only when the model should be listed:
kubectl apply -f models/example-model/details.yaml
```

Applying the service file also applies its embedded ConfigMaps. Set desired replica
behavior in the InferenceService rather than scaling controller-owned Deployments.

### 4. Call and test the model

Inspect startup before sending a small valid request:

```bash
kubectl get isvc example-model -n models
kubectl get pods -n models -l serving.kserve.io/inferenceservice=example-model
```

Allow weight and environment preparation to finish. If a request returns a
cold-start response, follow its retry guidance within a bounded startup window.
Distinguish loading from insufficient capacity or runtime failure before changing
settings. The gateway discovers the card without a gateway restart.

In a prepared test environment with `GW_URL` set to the public origin, `TYK_KEY`
supplied privately and `MODEL` set to the public model ID, run:

```bash
MODEL=example-model python3 models/example-model/test.py
```

Use an appropriate allocated environment for tests/builds, not a shared login node.
Keep TLS verification enabled. A public API run checks authentication and routing;
internal calls help diagnose failures but do not replace that check. Review both
the result summary and exit status. Use the validation and completion steps below
for manual work as well as agent-assisted deployment.

## Part 2: The agentic deployment loop

A human supplies the model, intended capability, environment and resource budget.
The agent works one model at a time, using the research and deployment steps above:

```text
Research → adapt files → deploy → inspect a small request → tune and recreate
                       → run test.py → fix failures and repeat
                       → clean redeployment → run test.py → record → commit/push
```

### 1. Diagnose and tune

Identify the cause before changing settings. Image/download errors need registry,
access or file checks; setup failures need dependency/import checks; pending pods
need scheduler events and capacity checks; runtime OOM needs measured memory
headroom and input/batch limits. Wrong ports, probes, parsers and output formats
need a direct comparison with the selected runtime's contract.

Change a small, explainable set of settings in the owning source file, follow the
update procedure, and check the effect. Use the existing research section when
new evidence requires a different runtime or approach. Record useful findings in
`models/example-model/CLAUDE.md` so another session can continue the work.

### 2. Customize and run one test script

Build `models/example-model/test.py` from templates and examples in `models/`.
Keep it basic: small functions, ordinary API requests, meaningful assertions and
one result summary. The operator or AI agent should customize requests, fixtures,
expected results, boundaries and workload sizes as deployment proceeds.

**Running `test.py` runs all applicable checks**, including functional behavior,
limits, stress/load and recovery. There are no separate stress scripts or
test-selection flags. Choose workloads within the authorized budget and preserve
these checks in the final file for the next deployment.

| Capability | What to check |
|---|---|
| Chat | Known answer, model identity, stop/truncation, output limits and streaming completion |
| Tools/reasoning | Tool name/arguments and result handling; supported thinking behavior and budgets |
| Images/audio | Known fixture, meaningful interpretation/output, supported formats and size limits |
| Embeddings/reranking | Dimensions, finite values, expected similarity/order, batches and input limits |
| Science | Real domain input, schema/units and comparison with a suitable reference result |
| Errors and alternate APIs | Expected rejection of invalid requests and unsupported features; supported Anthropic behavior |
| Load and recovery | Representative long inputs, concurrency, sustained requests and a valid final request |

The templates report `PASS` for a successful check, `EXP` for a documented expected
outcome such as rejecting unsupported tools, `FAIL`/`ERR` for failures or exceptions,
and `SKIP` for an untested case. Define expected outcomes before checking them;
fix failures rather than relabeling them. Missing fixtures and skipped checks
remain unverified. A successful HTTP status or plausible output shape alone is
not scientific validation.

Observe request latency/throughput, queueing, GPU memory and runtime errors during
load checks. A growing queue calls for comparing arrival rate, per-replica throughput,
batching and placement capacity before increasing replicas. Free KV cache alone
does not establish safe concurrency; measure peak memory under representative
input sizes. After tuning, recreate and rerun the battery. See
[Logging and metrics](LOGGING.md) for runtime and physical GPU measurements.

### 3. Prove reproducibility and finish

Recreate the service from the final repository files while preserving its PVC.
Run the complete `models/example-model/test.py` again. This checks that the result
survives pod replacement and does not depend on an unrecorded live edit.

Verify the intended lifecycle: idle models stop after their idle window and wake
on a later valid request; always-up models retain their minimum; hidden cards stay
hidden. Check scale-up when capacity permits and record capacity-blocked checks
as unverified. Scope recovery checks to this model.

Update `models/example-model/README.md` with final versions, resources, scaling,
commands, dated results and limitations. Keep research and tuning history in
`models/example-model/CLAUDE.md`. Review the diff, remove temporary test resources,
preserve service data, and add a dated repository changelog entry before committing
and pushing. Report incomplete work explicitly instead of claiming a deployment
or capability that has not been verified.
