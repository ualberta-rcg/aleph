# Describing a model: details.yaml

The model card connects the public API and catalog to a deployed model. Prepare
`models/<model>/details.yaml` alongside the [InferenceService](inferenceservice.md)
and [tests](test.md). This reference describes repository gateway behavior reviewed
on 2026-09-14 against the gateway source and the live card fleet; it does not claim a
live inference test of every configuration.

Implementation: [gateway source](../gateway/app/gateway.py), especially
`_parse_card`, `resolve`, `prepare_chat`, `_model_entry` and the endpoint handlers.
[Endpoints](../docs/ENDPOINTS.md) explains client URLs and access. Use those sources
when extending an integration; a field appearing in an old card does not prove
that the gateway implements it.

## Exemplars (deployed cards to study, verified 2026-09-14)

| Pattern | Example `models/<dir>/details.yaml` |
|---|---|
| Chat, effort thinking + tools (max features) | `gpt-oss-120b` |
| Chat, effort thinking with build-quirk effort aliases | `qwen38-27b` |
| Chat, toggle thinking, whole-device multi-GPU | `qwen35-122b` |
| Vision chat, no tools | `qwen25-vl-72b-awq` |
| Vision chat, medical | `medgemma-27b-it` |
| Embedding (TEI) | `bge-m3` |
| Reranker (TEI via /v1/rerank) | `bge-reranker-v2-m3` |
| Custom science server | `esmfold` |
| NIM with `strip_v1_prefix` | `boltz-2` |
| Native path via `upstream_path` | `genmol`, `molmim` |
| Completions-only | `progen2` |
| Multi-endpoint audio (clone/voices) | `xtts-v2` |

Read the matching `inferenceservice.yaml` and `test.py` beside each card.

## Card structure and discovery

Create a ConfigMap in the model namespace, normally named `<model>-details`, with
label `model-details: "true"` and JSON in `data.details.json`. The gateway watches
these ConfigMaps and discovers updates without restarting. The parser requires
valid JSON and a nonempty `id`; it is not a complete card validator. Include the
fields needed by the selected handler and validate them with the model's tests.

**The card body is always parsed as JSON.** The parser accepts the ConfigMap key
`details.json` or `details.yaml`, but either way runs `json.loads` on it — a YAML
body stored under `details.yaml` is rejected as invalid JSON. Store JSON regardless
of the key name.

Cards with invalid JSON or a missing `id` are silently dropped (a log line only) —
the model simply never appears. Renaming a card's `id` evicts the old id on update.

A public model ID, directory name, InferenceService name and runtime's served
model name may differ. Use them consistently:

| Name | Where it is used |
|---|---|
| Card `id` | Client requests and catalog identity |
| `routing.k8s_name` | InferenceService lookup; defaults to `id` |
| Service name | Internal host `<service>-predictor.<namespace>.svc.cluster.local` |
| `routing.upstream_model_id` | Backend model rewrite in handlers that support it |
| ConfigMap name | Kubernetes object identity; normally `<model>-details` |

Use a unique public ID. Hiding a deployed card is separate from stopping its
service. Preserve intentionally hidden cards during updates.

## Core fields

Types below describe the expected configuration, not a promise of schema
validation. Omitted settings can yield permissive or misleading defaults; declare
what is known and tested.

| Field | Type / omission behavior | Gateway use |
|---|---|---|
| `id` | Nonempty string required by parser | Public identity and default service lookup |
| `type` | String, defaults to `chat` in most routing/catalog paths | Anthropic handlers require `chat`; ordinary catalog lists chat by default. Use an explicit task for non-chat models. |
| `endpoints.primary` | String; catalog default is empty | Public endpoint shown in generated examples. Does not register a new handler or redirect a dedicated handler. |
| `endpoints.health` | String | Describe the runtime's health path. This does not configure the Kubernetes probe or the gateway's wake probe. |
| `endpoints.clone` | String | Voice-cloning card (`type: tts`): adds the clone example block to the public catalog web page |
| `endpoints.voices` | String | Adds the "list voices" example next to the clone block on the web page |
| `endpoints` (whole dict) | Object; echoed verbatim | The full `endpoints`, `input_map` and `custom_params` objects are copied into each `/v1/models` entry |
| `routing.k8s_name` | String; absent/empty uses `id` | Selects service state and internal host |
| `routing.upstream_model_id` | String or null; omitted means no rewrite | Used by chat (incl. Anthropic), `count_tokens`, embeddings and the dedicated audio handlers; not by rerank or the custom catch-all. Also serves as an **alias** mechanism: one public id can point at another model's served name |
| `routing.no_stream` | Boolean, default false | Suppresses upstream streaming where the handler supports streaming. It does not add streaming to a server. |
| `routing.upstream_path` | String; absent means no override | Custom forwarding only; takes precedence over prefix stripping |
| `routing.strip_v1_prefix` | Boolean, default false | Custom forwarding only: `/v1/task` becomes `/task` |
| `limits.context_window` | Integer, display default 0 | Catalog/documentation; not a general gateway tokenizer-based input-length check. Also stamped into every usage record |
| `limits.max_completion_tokens` | Positive integer enables chat preparation cap | Caps prepared chat `max_tokens`; also exposed in catalog and stamped into every usage record. It does not enforce every custom endpoint's output size. |
| `scaling.scale_to_zero` | Boolean, catalog default false | Catalog and Anthropic listing eligibility; actual cold-start admission checks observed service state |
| `scaling.min_replicas` | Integer | Catalog/Anthropic listing metadata; set the matching InferenceService minimum separately |
| `scaling.cold_start_estimate` | String; cold guard fallback `2-5 minutes` | Startup message and derived retry delay: `Retry-After` is the largest integer in the string × 60 seconds (`"3-6 min"` → 360; no digits → 30). Measure cached 0→1 wake, not first-ever installation. |
| `scaling.idle_retention` | String | Operating documentation; set actual retention in the service annotations |
| `defaults.chat` | Object, default empty | Fill missing/null chat request values; `thinking` is handled separately |
| `defaults.meta_tasks` | Object keyed by `title`, `tags`, `followups` | Controls detected chat-UI tasks, token settings and thinking behavior |
| `input_map` | Object, default empty | Public parameter descriptions and generated examples; does not implement validation |
| `output_map` | Object | Documents the response contract; does not transform or validate responses |
| `custom_params.schema` | Object of parameter descriptions | Parameter table/example generation; not a general runtime schema validator |
| `custom_params.passthrough` | Boolean, default false | Removes `model` and `stream` in custom forwarding; affects the `no_stream` fallback. Does not select a new runtime adapter. |
| `catalog` | Object, default empty | Public catalog metadata, input descriptions and generated documentation |

Keep the conventional `schema_version` field in copied cards. The current parser
does not dispatch between versions. Fields such as `routing.serialize`,
`param_translation.max_tokens`, `thinking.budget_support`, and arbitrary custom
limit fields are not implemented as controls by this gateway. Do not rely on them
to serialize calls, rename output-limit parameters or enforce input validation.
`status: production` is also not a deployment-readiness check.

Fields present on live cards but **never read** by this gateway: `behavior.supports_streaming`
(streaming is controlled by `routing.no_stream` and the runtime), `endpoints.secondary`,
`endpoints.edit`, `limits.max_input_tokens` (document it in `catalog.input_format` or
`input_map` descriptions instead), `catalog.pooling`, `catalog.max_input_tokens`. They are
inert metadata; harmless to keep, wrong to rely on.

## Endpoint and runtime variations

Dedicated routes run before the catch-all. Their paths and translation are
implemented in code; changing `endpoints.primary` or adding an upstream override
does not replace that code.

| Public API | Backend contract / card effect |
|---|---|
| `/v1/chat/completions` | Prepares defaults/thinking, gates tools and image content, rewrites backend model ID and calls `/v1/chat/completions`. Use `type: chat` for catalog discovery; this handler itself does not reject other types by name. |
| `/v1/messages` | Requires `type: chat`; translates Anthropic messages/tools/thinking to the chat backend and translates results/events back. |
| `/v1/messages/count_tokens` | Requires `type: chat`; forwards to backend `/v1/messages/count_tokens` with model-ID rewrite. It does not translate to `/tokenize` or apply chat generation defaults. |
| `/v1/embeddings` | Calls backend `/v1/embeddings`, optionally rewriting model ID. Backend must support that contract. A protein embedding model can use this path too. |
| `/v1/rerank` | Builds TEI `{query, texts}` for `/rerank` and maps `{index, score}` results to `relevance_score`; applies `top_n` and optional documents. Other request fields are not a generic passthrough. |
| `/v1/audio/transcriptions` | Dedicated multipart/JSON handling and backend model rewrite; preserve the native transcription response format. |
| `/v1/audio/speech` | JSON text-to-speech, backend model rewrite, raw audio response; uses the dedicated backend path. |
| `/v1/audio/clone`, `/v1/audio/voices` | Dedicated cloning/voice handling; cloning supports multipart/JSON, voices selects model via query. Check handler-specific defaults; they are not universal model-card options. |
| Other `/v1/...` paths | Custom handler resolves `model` from a JSON body, applies optional path changes, removes routing fields when passthrough is enabled, and forwards a buffered upstream POST. |

The custom handler accepts public GET and POST registrations but still needs a
JSON body containing `model` and forwards POST upstream. It is not a generic GET,
query-string-model or multipart proxy. It does not apply the dedicated handlers'
backend model rewrite, chat defaults or arbitrary request-field mapping. A custom
server must accept the resulting payload, or an adapter must be added and tested.

Examples of custom routing objects:

```json
{"k8s_name": "example-model", "upstream_path": "/generate", "no_stream": true}
```

```json
{"k8s_name": "example-model", "strip_v1_prefix": true, "no_stream": true}
```

For a native server that rejects `model` and `stream`, add:

```json
{"custom_params": {"passthrough": true}}
```

A public id can alias a differently-named deployment or served model (a live pattern —
an unquantized public id pointing at its quantized deployment):

```json
{"k8s_name": "example-model-awq", "upstream_model_id": "example-model-awq"}
```

The rewrite applies on chat (both APIs), `count_tokens`, embeddings and the dedicated
audio handlers; the custom catch-all does not rewrite the model field.

If the public request is `{ "model": "example-model", "sequence": "MKT" }`, the
first routing example plus passthrough sends `{ "sequence": "MKT" }` to `/generate`.
Other fields remain as supplied. `input_map` should describe the public input and
explain any transformation. Runtime health/probe paths remain separately configured.

Completions-only models use `type: completions` and a public `/v1/completions`
endpoint through custom forwarding. They do not inherit chat-default or thinking
translation simply because their runtime is vLLM. Likewise, custom image,
classification, weather and scientific APIs need their actual native contracts.
New runtimes are welcome: select compatible handlers or implement the needed
adapter rather than claiming support through card metadata alone.

## Capabilities and reasoning

| `behavior` field | Default and effect |
|---|---|
| `supports_tools` | False; chat/Anthropic reject supplied tools when unsupported |
| `supports_vision` | False; chat/Anthropic gate recognized image content; also affects generated input descriptions |
| `supports_video` | False in catalog; a reported capability, not a general video adapter or validator |
| `supports_system_prompt` | True in catalog; describe tested support, not an automatic runtime conversion switch |
| `reasoning_model` | False; affects catalog, chat meta-task budgets and small-budget handling |
| `strips_thinking` | False; fallback response-stripping behavior for models without managed thinking |

`param_translation.thinking.mode` selects the implemented thinking behavior:

| Mode | Behavior |
|---|---|
| `none` (default) | No thinking-parameter injection; fallback stripping can still apply |
| `budget` | Effort maps to `thinking_token_budget`; explicit budget can override the map; reserve room for the answer within the card cap |
| `effort` | Inject `on` defaults without replacing caller values, or `off` values when disabled; accepted effort names come from aliases/map/default |
| `toggle` | Merge the `on` or `off` object, such as runtime-specific chat-template kwargs |
| `always_on` | No native off injection; gateway can hide reasoning and cap output when the caller asks for off |

All five modes are implemented in the gateway. Live-fleet usage (census 2026-09-14): `none`
dominates, `effort` and `toggle` are each proven on multiple deployed chat models, while
`budget` and `always_on` have no deployed example yet — test them end-to-end before relying
on them for a new model.

Managed modes expose reasoning when enabled and hide it when disabled. Hiding
reasoning does not mean the model stopped computing it. Parser configuration in
the runtime must make reasoning available in the expected response fields.

| Thinking option | Type / behavior |
|---|---|
| `effort_aliases` | Object mapping client names to configured effort names; consulted before `effort_map` |
| `effort_map` | Object; entries may be integer budgets or objects with `thinking_token_budget`. Also identifies accepted effort names. |
| `default_effort` | String; fallback for unrecognized efforts. Configure explicitly when using effort controls. |
| `disabled_effort` | String, default `none`; budget-mode off selection |
| `answer_reserve` | Integer, default 512; budget preparation reserves final-answer space within the completion cap |
| `on` / `off` | Objects injected in effort/toggle modes; use only parameters supported by the runtime |
| `off_max_tokens` | Integer, default 2048; caps managed-thinking requests when thinking is off |

Budget lookup falls back to the `medium` entry if the requested entry is absent.
A null budget does not inject a limit. Effort/toggle modes simulate a supplied
thinking budget through an output-token cap; this is not a measured separate
reasoning-token allowance. Test the model's real behavior, including a final answer.

Example native-budget configuration, to adapt to a runtime that supports it:

```json
{
  "mode": "budget",
  "answer_reserve": 512,
  "default_effort": "medium",
  "disabled_effort": "none",
  "effort_aliases": {"med": "medium", "disabled": "none"},
  "effort_map": {
    "none": {"thinking_token_budget": 0},
    "low": {"thinking_token_budget": 1024},
    "medium": {"thinking_token_budget": 4096},
    "high": {"thinking_token_budget": 12288},
    "max": {"thinking_token_budget": null}
  }
}
```

Example toggle configuration:

```json
{
  "mode": "toggle",
  "on": {"chat_template_kwargs": {"enable_thinking": true}},
  "off": {"chat_template_kwargs": {"enable_thinking": false}}
}
```

For direct effort support, use `mode: effort` with appropriate `on`, `off`,
`default_effort`, aliases and accepted map keys. An always-reasoning model may
need low native effort when output reasoning is hidden; do not blindly copy a
`none` value unsupported by its runtime.

`defaults.chat.thinking.enabled` defaults to true in preparation;
`defaults.chat.thinking.effort` supplies budget-mode effort (fallback `medium`).
Explicit client controls and Anthropic translation also affect preparation. For
managed chat, completion caps, off caps, and reasoning budget/answer reserve
interact; validate both APIs with the actual runtime.

Meta-task defaults apply to detected title/tags/followup prompts. Their thinking
default is off. Their `max_tokens` is a cap for ordinary models but a floor for
models marked `reasoning_model`, so an internal reasoning phase has space before
the short final answer. General chat preparation still applies the completion cap.
This is why copying tiny meta-task budgets between different models can fail.

## Catalog, descriptions and lifecycle

`catalog` is consumed by the gateway; it is not an ignored bag of metadata.

| Fields | Use / omission behavior |
|---|---|
| `description`, `description_short` | Public description; full description falls back to short |
| `display_name` | Anthropic display name, falling back to short description then ID |
| `owned_by` | Public owner; gateway has a site default, so supply the actual model publisher |
| `source`, `source_url` | Model provenance; a source containing `/` supplies a default Hugging Face link if no URL is given |
| `license`, `parameters`, `precision`, `framework`, `domain`, `subdomain`, `tags` | Public catalog metadata; generally empty when omitted |
| `embedding_dimensions` | Public dimension, default 0; use measured/model-defined value |
| `input_format` | Explicit input description; otherwise the gateway derives a basic type-dependent description |
| `gpu` | Fallback when service resources are unavailable; live service allocation takes precedence |

`input_map` and `custom_params.schema` drive parameter descriptions and best-effort
example bodies. Provide concrete types, defaults, required flags, descriptions,
units and useful example values where supported. These descriptions are not
JSON Schema validation and do not rename fields. Preserve model-specific output
contracts in `output_map` and the model README even if every field is not exposed
by the current catalog renderer.

Ordinary `GET /v1/models` lists chat cards; `?all=true` includes non-chat cards.
Each entry also carries live state (readiness, replica counts, resource allocation)
plus verbatim copies of the card's `endpoints`, `input_map` and `custom_params`
objects — anything secret-shaped must not be placed in those objects.
The Anthropic catalog surface lists cards classified as always-on chat. That
predicate treats a missing minimum permissively, so set the minimum and
scale-to-zero metadata explicitly. Catalog eligibility is not a capacity guarantee.

Service/pod watches supply readiness, replica state and resource allocation.
`scale_to_zero`, `min_replicas` and `idle_retention` in a card do not configure the
controller. Keep them consistent with the service. The cold-start guard examines
observed state/capacity, rather than trusting the card's scale-to-zero flag.

The wake helper currently probes `/v1/models`; setting `endpoints.health` does
not change it. Request arrival can activate the service even if the runtime's
response to that probe is not successful. Validate cached wake with a real request.

## Generated-example options

`custom_params.schema.<field>.example: false` omits that field from the generated
request while retaining it in the parameter table. This is useful for large binary
inputs or fields that belong to a secondary endpoint. It is not a request filter.

```json
{
  "custom_params": {
    "schema": {
      "num_poses": {"type": "integer", "default": 5, "description": "Requested poses"},
      "large_auxiliary_input": {"type": "array", "example": false}
    }
  }
}
```

The generator selects enum/default/type-based values and has special cases for
common names. Input-map entries are processed after custom schema fields and can
overwrite generated values. Nested domain maps can become placeholder strings;
the generated curl command is not automatically a valid scientific fixture.
Document a real request in the model README and test it. `min`, `max`, required
flags and schema descriptions do not enforce request constraints in the gateway.

## Starting chat card

The numbers below illustrate a small context/output configuration, not a model
recommendation. Replace identity, limits, capabilities and metadata together.

```yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: example-model-details
  namespace: models
  labels:
    model-details: "true"
data:
  details.json: |
    {
      "id": "example-model",
      "schema_version": 2,
      "type": "chat",
      "endpoints": {"primary": "/v1/chat/completions", "health": "/health"},
      "routing": {"k8s_name": "example-model", "no_stream": false},
      "limits": {"context_window": 4096, "max_completion_tokens": 512},
      "scaling": {"scale_to_zero": true, "min_replicas": 0,
                  "idle_retention": "15m", "cold_start_estimate": "2-5 minutes"},
      "behavior": {"supports_vision": false, "supports_tools": false,
                   "supports_system_prompt": true, "reasoning_model": false},
      "param_translation": {"thinking": {"mode": "none"}},
      "defaults": {"chat": {"temperature": 0.7, "max_tokens": 256}},
      "input_map": {
        "messages": {"type": "array", "required": true, "description": "Chat messages"},
        "max_tokens": {"type": "integer", "default": 256, "max": 512},
        "temperature": {"type": "float", "default": 0.7, "min": 0, "max": 2},
        "stream": {"type": "boolean", "default": false}
      },
      "output_map": {"choices": {"type": "array"}, "usage": {"type": "object"}},
      "catalog": {"description_short": "Replace with the model's task and features",
                  "owned_by": "model-publisher", "license": "verify-model-license",
                  "framework": "vllm", "domain": "nlp", "tags": ["chat"]}
    }
```

For tools, set the capability only after configuring the runtime parser and testing
tool arguments/results. For vision, document content blocks inside `messages`
(including image URLs/data URIs); a standalone `image` field does not enable chat
vision. Describe video separately when supported. For reasoning, configure both
behavior and the tested translation mode above.

## Non-chat card variations

Keep the same ConfigMap envelope. Replace the JSON task, endpoints, input/output
maps and catalog, and remove irrelevant chat defaults/capabilities. Set
`catalog.input_format` for custom tasks so the catalog does not infer chat input.

Embedding variation:

```json
{
  "type": "embedding",
  "endpoints": {"primary": "/v1/embeddings", "health": "/health"},
  "input_map": {"input": {"type": "string or array", "required": true}},
  "output_map": {"data": {"type": "array", "description": "Indexed embedding vectors"}},
  "catalog": {"embedding_dimensions": 1024, "input_format": {"input": "str or [str]"}}
}
```

The dimension is illustrative. Protein sequences, text or other inputs must match
the actual model contract; document pooling and units in the model's notes.

Reranking variation:

```json
{
  "type": "reranker",
  "endpoints": {"primary": "/v1/rerank", "health": "/health"},
  "input_map": {
    "query": {"type": "string", "required": true},
    "documents": {"type": "array", "required": true},
    "top_n": {"type": "integer"},
    "return_documents": {"type": "boolean", "default": false}
  },
  "output_map": {"results": {"type": "array", "description": "index, relevance_score and optional document"}}
}
```

Multi-endpoint audio (TTS) variation — `endpoints.clone`/`voices` drive the web page's
cloning examples (live-derived shape):

```json
{
  "type": "tts",
  "endpoints": {"primary": "/v1/audio/speech", "health": "/health",
                "clone": "/v1/audio/clone", "voices": "/v1/audio/voices"},
  "routing": {"k8s_name": "example-tts", "no_stream": true},
  "input_map": {
    "input": {"type": "string", "required": true, "description": "Text to synthesize"},
    "language": {"type": "string", "default": "en"},
    "voice": {"type": "string", "default": "preset-or-saved-clone-name"}
  },
  "custom_params": {
    "schema": {
      "speed": {"type": "number", "default": 1.0},
      "voice_sample": {"type": "string", "example": false, "description": "clone: base64 WAV reference clip"},
      "save_as": {"type": "string", "example": false, "description": "clone: name to persist the clip"}
    },
    "passthrough": true
  },
  "catalog": {"input_format": {"input": "text", "voice": "preset or clone name"}}
}
```

The `example: false` entries keep the large binary-input fields out of the generated
request body while documenting them in the parameter table.

Custom science/native server variation:

```json
{
  "type": "predict",
  "endpoints": {"primary": "/v1/science/predict", "health": "/health"},
  "routing": {"k8s_name": "example-model", "upstream_path": "/predict", "no_stream": true},
  "custom_params": {"passthrough": true},
  "input_map": {"sequence": {"type": "string", "required": true, "description": "Amino-acid sequence"}},
  "output_map": {"prediction": {"type": "object"}},
  "catalog": {"input_format": {"sequence": "amino-acid string"}}
}
```

These are mergeable examples of sections, not complete cards. Preserve the required
identity/envelope and matching scaling metadata. Scientific APIs need real domain
units and reference outputs, not copied chat-token limits. Usage objects returned
by custom servers must contain accounting metadata only: the gateway may retain
them in [usage records](../docs/LOGGING.md).

## Domain input/output examples

The existing card guide contains these useful domain patterns. They describe
contracts to adapt; confirm each field against the actual server. JSON blocks
below are object members, to insert inside the card object.

### Typed params with required/optional (most common)

```json
"input_map": {
  "protein_pdb": {
    "type": "string",
    "required": true,
    "description": "Protein structure in PDB format"
  },
  "ligand_smiles": {
    "type": "string",
    "required": true,
    "description": "Ligand as SMILES string"
  },
  "num_poses": {
    "type": "integer",
    "required": false,
    "default": 10,
    "description": "Number of docked poses to generate"
  }
},
"output_map": {
  "model": {"type": "string", "description": "Model name"},
  "poses": {"type": "array", "description": "Ranked poses with rank, confidence, and SDF content"}
}
```

### Nested objects with description strings (weather/climate)

```json
"input_map": {
  "surf_vars": {
    "2t": "2m temperature (K), shape [lat, lon]",
    "10u": "10m u-wind (m/s), shape [lat, lon]",
    "msl": "mean sea-level pressure (Pa), shape [lat, lon]"
  },
  "lat": "[90, ..., -90] float array",
  "lon": "[0, ..., 359.75] float array",
  "time": "ISO datetime string e.g. 2024-01-01T00:00:00"
},
"output_map": {
  "surf_vars": "same structure as input, 6h ahead",
  "step": "6h"
}
```

### Crystal/material structure (chemistry, physics)

```json
"input_map": {
  "structure": {
    "elements": "array of element symbols e.g. [\"Li\", \"Fe\", \"P\", \"O\"]",
    "positions": "array of [x,y,z] positions in Angstroms",
    "cell": "3x3 cell vectors",
    "pbc": "[bool, bool, bool] periodic boundary conditions"
  }
},
"output_map": {
  "energy_eV": "total potential energy in eV",
  "forces_eV_A": "per-atom forces in eV/Angstrom",
  "stress_eV_A3": "Voigt stress tensor"
}
```

### Binary/image inputs (vision, 3D reconstruction, medical)

```json
"input_map": {
  "images": "array of 2+ base64-encoded JPEG/PNG images",
  "output_format": "\"pointcloud\" (default) or \"depth\""
},
"output_map": {
  "pointclouds": [{"pts3d": "[[x,y,z], ...]", "confidence": "[float, ...]"}],
  "model": "dust3r"
}
```

### Text/sequence input (restoration, classification, generation)

```json
"input_map": {
  "text": {
    "type": "string",
    "required": true,
    "description": "Input text (format depends on model)"
  },
  "task": {
    "type": "string",
    "required": false,
    "description": "Task to perform (model-specific)"
  }
},
"output_map": {
  "model": {"type": "string", "description": "Model name"},
  "result": {"type": "string", "description": "Model output"}
}
```

### Audio classification and other native tasks

Audio classification is not the same contract as transcription or speech
synthesis. For a server accepting sample arrays, a custom route might describe:

```json
{
  "type": "audio-classification",
  "endpoints": {"primary": "/v1/science/identify", "health": "/health"},
  "input_map": {
    "audio": {"type": "array", "required": true, "description": "Floating-point audio samples"},
    "sample_rate": {"type": "integer", "default": 48000, "description": "Samples per second; verify the model requirement"}
  },
  "output_map": {"detections": {"type": "array", "description": "Classes and confidence scores"}},
  "catalog": {"input_format": {"audio": "float array", "sample_rate": "Hz"}}
}
```

The sample rate is illustrative. Image generation, segmentation, detection,
translation and other custom tasks follow the same approach: describe their
actual body/result and the native path, then verify it through the gateway.
Do not label every non-chat endpoint OpenAI-compatible.

### Completions-only input

```json
{
  "type": "completions",
  "endpoints": {"primary": "/v1/completions", "health": "/v1/models"},
  "input_map": {
    "prompt": {"type": "string", "required": true, "description": "Text or sequence prefix"},
    "max_tokens": {"type": "integer", "default": 256},
    "temperature": {"type": "float", "default": 1.0}
  },
  "output_map": {"choices": {"type": "array", "description": "Generated text and finish reason"}},
  "catalog": {"input_format": {"prompt": "string"}}
}
```

For this custom-forwarding path, parameter descriptions and example defaults do
not set backend defaults. In particular, an old `defaults.completions` block is
not consumed by the gateway. Supply required request parameters or configure the
runtime's defaults, and test the resulting behavior.
