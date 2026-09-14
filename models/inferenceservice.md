# Running a model: inferenceservice.yaml

This file describes the serving process and the resources it needs. It can also
contain supporting ConfigMaps separated by `---`. Start from the closest working
pattern, then adapt it using the model's instructions and the selected runtime's
actual interface. Pair it with [storage](pvc.md), the [card](details.md), and
[tests](test.md).

## Basic prebuilt-runtime pattern

This illustrative service assumes weights have already been prepared on its PVC.
Add the initialization described below for a fresh deployment. Replace the model
name, budgets and runtime arguments with measured values for the intended model.

```yaml
apiVersion: serving.kserve.io/v1beta1
kind: InferenceService
metadata:
  name: example-model
  namespace: models
  annotations:
    autoscaling.knative.dev/scale-to-zero-pod-retention-period: "15m"
    serving.knative.dev/progress-deadline: "1200s"
spec:
  predictor:
    minReplicas: 0
    maxReplicas: 1
    scaleMetric: concurrency
    scaleTarget: 1
    timeout: 600
    nodeSelector:
      gpu: "on"
    affinity:
      nodeAffinity:
        requiredDuringSchedulingIgnoredDuringExecution:
          nodeSelectorTerms:
            - matchExpressions:
                - key: node-role.kubernetes.io/control-plane
                  operator: DoesNotExist
    containers:
      - name: kserve-container
        image: vllm/vllm-openai:v0.20.2
        args:
          - --model=/data/model
          - --served-model-name=example-model
          - --port=8080
          - --max-model-len=4096
        ports:
          - containerPort: 8080
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
        startupProbe:
          httpGet: {path: /health, port: 8080}
          periodSeconds: 10
          failureThreshold: 120
        readinessProbe:
          httpGet: {path: /health, port: 8080}
          periodSeconds: 10
        volumeMounts:
          - {name: model-data, mountPath: /data}
    volumes:
      - name: model-data
        persistentVolumeClaim:
          claimName: example-model-data
```

The vLLM image is the documented baseline reviewed on 2026-09-14, not a universal
architecture requirement. Prefer an explicit tested image version or digest.
Verify support before copying runtime arguments or updating a dependency.

## Choose the serving approach

| Approach | What changes in the service | What must agree in the card/test |
|---|---|---|
| Chat or multimodal runtime | Image, model path, served name, precision, context, parsers, template and batch settings | Chat API, supported tools/images/reasoning and tested limits |
| Embedding runtime | Model/task arguments, pooling, dtype, port and resource budget | Embedding endpoint, dimensions and meaningful similarity tests |
| Reranking runtime | Cross-encoder model and backend endpoint | The current `/v1/rerank` handler expects TEI-style `/rerank`; another contract needs integration work. |
| Packaged scientific server, including NIM | Vendor image, license/access requirements, caches, databases and native request path | Exact native payload and public route; no assumption of an OpenAI body |
| Custom server | Server code, full environment, model loading, health and request handlers | Real model computation, explicit validation and documented domain units |
| CPU server | Remove GPU resources and GPU-only placement; choose appropriate CPU placement | Same public contract, with measured latency/capacity |
| Another runtime | Research its container, startup, hardware and API requirements | Reuse a compatible handler or implement and validate an adapter where necessary. |

Aleph is not restricted to the runtimes already deployed. KServe manages the
container and Knative lifecycle; the runtime performs inference. A runtime with
a compatible interface can use existing gateway handling. Card descriptions do
not create a new API adapter or change a dedicated handler's backend contract.
See [card routing](details.md#endpoint-and-runtime-variations).

## Initialization and environments

Place initialization in `spec.predictor.initContainers`, mounting the same PVC
used by the serving container. Init containers run before serving and must exit
successfully. Their CPU/RAM requests also affect scheduling.

| Setup | Init container | Serving container |
|---|---|---|
| Download helper | Create a persistent helper venv, install pinned download dependencies once, fetch a specific model revision and verify artifacts | Use the prebuilt runtime to load cached weights |
| Full Python environment | Prepare a versioned venv with the tested PyTorch/CUDA/model-library combination and validate imports | Execute that venv's Python at the same PVC path |
| Packaged environment | Prepare only the files or databases not provided by the image | Use the packaged executable and expected cache paths |
| No preparation needed | Omit the init container | Load image-bundled or already prepared files |

Example mount and credential wiring inside an init container:

```yaml
name: setup
image: python:3.11-slim
env:
  - name: HF_TOKEN
    valueFrom:
      secretKeyRef: {name: hf-token, key: token}
volumeMounts:
  - {name: model-data, mountPath: /data}
```

This fragment needs a model-specific command and resource budget. Use Secrets
only where access is needed; registry authentication may instead require
`imagePullSecrets`. Never put token values in YAML or logs. Setup and serving
images must be compatible when they share a venv. Avoid reinstalling on every
wake; completion markers must represent verified files and dependency versions.
See [PVC initialization](pvc.md#initialization-and-updates) for concurrent writers
and safe replacement environments.

## Embedded server and configuration variants

Keep small server/configuration definitions in this file as additional ConfigMap
documents. A custom server ConfigMap has this structure; replace the deliberately
incomplete code with real model loading and handlers before deployment:

```yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: example-model-server
  namespace: models
data:
  server.py: |
    # Implement the model's real serving contract here.
    raise NotImplementedError("Supply model loading, health and inference handlers")
```

Add these entries to the predictor's existing volume and mount lists:

```yaml
# spec.predictor.volumes entry
name: server-code
configMap:
  name: example-model-server
```

```yaml
# serving container volumeMounts entry
name: server-code
mountPath: /app/model-server
readOnly: true
```

For a full PVC environment, a corresponding command is:

```yaml
command: ["/data/venv/bin/python", "/app/model-server/server.py"]
```

The same pattern can hold a runtime-specific parser, chat template, tokenizer
configuration or other small text file. Mount it at the path expected by the
runtime and explicitly enable it in startup arguments. Some configurations are
already bundled in the image or weights; omit the extra ConfigMap in that case.
Large dependencies and weights belong in an image/PVC, not a ConfigMap.

ConfigMap updates do not guarantee an already running process reloads its code or
configuration; `subPath` mounts also do not receive projected updates. Recreate
and test the service when its loaded code/configuration changes. A model's server
ConfigMap is distinct from its gateway card ConfigMap in `details.yaml`.

## Resources and placement

| Setting | How to choose |
|---|---|
| CPU/RAM requests and limits | Include model loading, tokenization/preprocessing, worker processes and peak inputs. Avoid copying another model's budget. |
| `nvidia.com/gpu` | Device count per replica; match requests and limits when both are provided. |
| `nvidia.com/gpumem` | HAMi shared memory allowance in MiB. Include weights, runtime overhead, KV cache/activations and concurrency. |
| Whole devices | Omit `gpumem`; request the number of devices required by the replica. |
| GPU compute share | Some HAMi configurations support `nvidia.com/gpucores`; use only after checking the installed scheduler/device-plugin behavior. It is not an observed utilization reading. |
| `nodeSelector` / affinity | Match actual node labels; GPU examples select `gpu: "on"` and exclude control-plane nodes. CPU deployments need a suitable alternative. |
| Tolerations | Add only for taints on the intended nodes. They allow placement; they do not select a node. |
| Shared memory | Use an `emptyDir` with `medium: Memory` mounted at `/dev/shm` if the runtime requires it. Size it deliberately and include its use in the memory budget. |

For multi-GPU replicas, set the runtime's tensor/pipeline parallelism to match the
allocation and verify topology, communication libraries and memory on every device.
Flags such as `--disable-custom-all-reduce` and attention-backend overrides are
runtime/hardware-specific findings, not requirements for every server. Do not
copy old HAMi workarounds without reproducing the issue on the current system.

## Ports, health, timeout and lifecycle

- Align the listening port, declared container port and probe port. Aleph's common
  serving pattern uses port 8080. Health paths differ by runtime.
- Readiness must represent ability to serve; a JSON body saying "loading" with
  HTTP 200 does not fail an HTTP probe. Startup probes should allow measured load
  time. Add liveness only with behavior that will not restart a busy healthy model.
- Distinguish initial downloads/environment builds from cached model loading.
  Coordinate startup/progress deadlines and request timeouts with
  [Kubernetes serving settings](../docs/KUBERNETES.md) and the gateway/ingress limits.
- `minReplicas: 0` permits idle scale-to-zero; a minimum of at least one retains
  loaded capacity. `maxReplicas` bounds replicas, not requests or GPUs fleet-wide.
- Knative `scaleTarget` and the runtime's batch/concurrency settings are different.
  Measure queueing, throughput and memory before adjusting them. The sample's
  target and maximum are illustrative, not a throughput recommendation.
- Idle retention and scale-down delay affect lifecycle timing. Keep the card's
  descriptions consistent. A card does not configure Knative's replica counts.
- Parking a card hides it; stopping execution is separate. Follow the
  [operator procedures](../CLAUDE.md#park-stop-scale-to-zero-or-keep-always-up).

For updates, edit source, delete the InferenceService, wait until its old predictor
pods and revisions clear, then recreate it. Preserve PVCs. Follow the guarded
[deployment procedure](../docs/ADD-A-MODEL.md#update-an-existing-service), rather
than patching its spec or scaling generated Deployments.
