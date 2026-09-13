# Add or update a model

Our workflow is: research the model, adapt a suitable existing deployment, test it,
iterate, and prove the final files can reproduce the result. Work on one model at
a time and record incomplete work honestly.

## 1. Choose the runtime and configuration

Read the upstream model card and serving instructions. Confirm the license,
required access, supported tasks, input format, and runtime compatibility. Choose
the engine that supports the model; do not assume every model belongs on vLLM.

Find the closest example under `models/` and read its manifests and notes before
copying it. Verify the image version, resource requirements, startup behavior,
and any custom server code for the new model. Copy the pattern, not another
model's capability claims or test results.

## 2. Prepare the model directory

| File | Purpose |
|---|---|
| `models/<model>/pvc.yaml` | Persistent weights/cache storage, when needed |
| `inferenceservice.yaml` | Runtime image, startup, resources, probes, and scaling |
| `details.yaml` | Gateway card: identity, routes, capabilities, limits, and defaults |
| `test.py` | Checks for the endpoints and behavior this model supports |
| `README.md` | How to deploy/use it, current test status, and known limitations |
| `CLAUDE.md` | Optional model-specific implementation notes |

Add supporting ConfigMaps, download jobs, parsers, or server files only as needed.
Keep names and references consistent. If the public model ID differs from the
InferenceService or upstream model name, declare that mapping in the card.

Use [the card templates](../models/DETAILS-TEMPLATE-LLM.md) for the gateway schema.
Gateway capabilities belong in `behavior`, not a `compatibility` block. Keep
upstream `usage` responses limited to accounting metadata, since they are retained
in [usage records](LOGGING.md).

For GPU models, use the deployment's HAMi conventions: fractional allocations
request GPU count plus `nvidia.com/gpumem` in MiB; multi-GPU whole-device allocations
omit `gpumem`. Size CPU, RAM, storage, and GPU requests deliberately. Check the
existing tensor-parallel examples for topology-specific runtime flags; they are
not universal hardware defaults.

Use persistent storage for reusable weights and make download/setup steps
idempotent. Reference Kubernetes Secrets for credentials. Keep the card's scaling
settings consistent with the InferenceService: scale-to-zero for idle models,
always-on only when the deployment requires it.

## 3. Deploy and exercise it

Use an administrative shell with `kubectl` configured for the target cluster.
From the repository root, apply each file separately:

```bash
kubectl apply -f models/<model>/pvc.yaml
# Apply any required supporting ConfigMaps before the service.
kubectl apply -f models/<model>/inferenceservice.yaml
kubectl apply -f models/<model>/details.yaml
kubectl get isvc <model> -n models
```

The gateway discovers the card without a restart. Send a valid model-specific
request through the authenticated public endpoint, follow cold-start guidance,
and check predictor readiness and startup logs. For science models, validate the
result against an appropriate reference, including units and preprocessing.

Start `test.py` from the appropriate existing battery:

- [Chat](../models/test.template.py)
- [Custom science server](../models/test.science-template.py)
- [Science server with an OpenAPI schema](../models/test.science-openapi-template.py)

With your endpoint and client key exported as `GW_URL` and `TYK_KEY`, run the
model's documented tests. Check valid inputs, invalid inputs, limits, and any
advertised streaming, reasoning, tool, vision, or alternate-API behavior. A
successful HTTP status alone is insufficient: inspect the returned result.

## 4. Iterate and prove the final deployment

When changing an existing InferenceService spec, **delete the service and reapply
its YAML; never patch its spec or delete its PVC**. Wait for the old predictor
pods and revisions to clear before recreating it, so they do not compete for the
same GPUs. Reapply supporting files when they change.

Retest after each adjustment. Exercise bounded concurrency and representative
large inputs, inspect failures and memory use, and verify scaling up and back
down. Keep the load appropriate for the shared deployment.

Finally, recreate the service from the final repository files while preserving
its weights, and repeat the relevant tests. Record the date, tested configuration,
results, expected failures, and remaining gaps in the model's `README.md`. Do not
mark an untested or blocked deployment as working. Update [CHANGELOG.md](../CHANGELOG.md)
with the change and validation before committing.

## Hide versus stop

Removing the model's details ConfigMap hides its catalog entry; it does not stop
its InferenceService or remove weights. Reapplying `details.yaml` restores the
entry. Stopping execution is a separate action using
`serving.kserve.io/stop=true`; clear that annotation to allow serving again.
