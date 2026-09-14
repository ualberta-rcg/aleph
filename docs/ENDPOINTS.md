# Endpoints and client configuration

Use the model's public ID and supported request format from the
[live catalog](https://inference.vulcan.alliancecan.ca/) or its
[`models/` directory](../models/). A path being routed by the gateway does not
mean every model implements it. Model cards describe the contract; the gateway
handlers and the selected runtime determine what actually works.

## Connect a client

| Client | Base URL | Authentication |
|---|---|---|
| Direct HTTP requests and model `test.py` scripts | `https://<aleph-host>` | `Authorization: Bearer <aleph-key>`; tests use `GW_URL` and `TYK_KEY` |
| OpenAI-compatible clients that append `/chat/completions`, `/embeddings`, etc. | `https://<aleph-host>/v1` | Aleph key in the client's API-key setting |
| Anthropic-compatible clients, including Claude Code | `https://<aleph-host>/anthropic` | Aleph key as Bearer authorization or `x-api-key` |

Replace `<aleph-host>` with your deployment's hostname. The hosted origin is
`https://inference.vulcan.alliancecan.ca`. Avoid doubling `/v1` when a client
appends its own path. Keep TLS verification enabled.

Tyk authenticates `/v1/` and `/anthropic/` requests. Access to both requires key
rights for `model-gateway` and `model-anthropic`; see [API keys](TYK-USERS.md).
The gateway's internal service is behind this authentication layer. Calling it
directly does not validate a public API key.

With `GW_URL` set to the origin and `TYK_KEY` supplied privately:

```bash
curl --fail-with-body "$GW_URL/v1/models?all=true" \
  -H "Authorization: Bearer $TYK_KEY"

curl --fail-with-body "$GW_URL/v1/chat/completions" \
  -H "Authorization: Bearer $TYK_KEY" \
  -H 'Content-Type: application/json' \
  -d '{"model":"gpt-oss-20b","messages":[{"role":"user","content":"What is 3+4? Reply with the number only."}],"max_tokens":64,"temperature":0}'
```

Replace the example model with an available chat model. For supported streaming,
add `"stream":true` to the body and use `curl -N`.

### Claude Code

Set these in the shell that launches the client, with `MODEL` set to a supported
chat model and `TYK_KEY` already supplied privately:

```bash
export ANTHROPIC_BASE_URL="$GW_URL/anthropic"
export ANTHROPIC_AUTH_TOKEN="$TYK_KEY"
export ANTHROPIC_MODEL="$MODEL"
```

The [settings example](claude-code.settings.json.example) also shows model alias
and fallback preferences. Its model IDs and optional client settings are examples,
not requirements of the endpoint; adapt them to your available models and client
version. Do not overwrite existing personal settings or commit a real key.
HTTP validation below does not establish that every Claude Code feature works.

## Catalog and platform endpoints

| Method and path | Behavior |
|---|---|
| `GET /` | Keyless HTML catalog with model details and examples. |
| `GET /v1/models` | Chat model list in OpenAI-style shape. Listing does not prove readiness. |
| `GET /v1/models?all=true` | Full catalog, including non-chat models, inputs, endpoints and deployment information. |
| `GET /anthropic/v1/models` | Tyk strips `/anthropic` and marks the request as Anthropic. Returns always-on chat models in Anthropic list shape; `all=true` does not expand this list. Other chat models remain callable by ID. |
| `GET /metrics` | Aggregate gateway metrics; `?local=true` selects the receiving replica. See [Logging and metrics](LOGGING.md). |

The gateway also selects Anthropic catalog format when the request carries an
`anthropic-version` header. Use ordinary `/v1/models?all=true` without that header
to retrieve the full catalog.


## Dedicated inference handlers

| Method and path | Request and response |
|---|---|
| `POST /v1/chat/completions` | JSON `model` and `messages`; OpenAI-style chat response or SSE. Features such as tools, vision and reasoning depend on the card/runtime. |
| `POST /v1/messages` | JSON `model`, `messages` and `max_tokens`; Anthropic-style response or SSE. Only chat-type models are accepted. |
| `POST /v1/messages/count_tokens` | JSON `model` and Anthropic message input; forwards to the chat runtime's token-count endpoint and returns `input_tokens` when supported. It is not a generic gateway-side tokenizer. |
| `POST /v1/embeddings` | JSON `model` and `input`; embeddings in the selected model's supported format. Inputs may be text or domain data such as protein sequences. |
| `POST /v1/rerank` | JSON `model`, `query`, `documents`, and optional `top_n`/`return_documents`; gateway maps to TEI's native rerank contract and returns ranked results. |
| `POST /v1/audio/speech` | JSON including `model` and `input`; returns audio bytes with the upstream content type. Voice and other fields are model-specific. |
| `POST /v1/audio/transcriptions` | Multipart form with model and audio file, or model-supported JSON input; dedicated handling preserves multipart uploads. |
| `POST /v1/audio/clone` | Model-supported multipart reference audio or JSON voice sample; use the model's documented fields. |
| `GET /v1/audio/voices?model=<model-id>` | Voice listing from the selected runtime. Supply the model explicitly; the current handler defaults to `xtts-v2`. |

The two Messages POST paths are also available publicly beneath `/anthropic`,
for example `/anthropic/v1/messages/count_tokens`. Tyk removes that prefix before
the request reaches the gateway. It supplies caller identity for usage accounting.

## Model-specific paths

The catch-all handles other `/v1/` paths. Examples include:

| Family | Examples; support must be checked per model |
|---|---|
| Text completions | `/v1/completions` with `model` and `prompt` |
| Images | `/v1/images/generations`, `/v1/images/edits` |
| Vision | `/v1/vision/classify`, `/v1/vision/detect`, `/v1/vision/segment`, `/v1/vision/depth` |
| Science | `/v1/science/predict`, `/v1/science/embed`, `/v1/science/energy`, `/v1/science/forecast` |
| Other model APIs | `/v1/predict`, `/v1/forecast`, `/v1/design`, `/v1/dock`, `/v1/structure`, `/v1/translate` |

Use POST with a JSON object containing `model` and the model's documented inputs.
The catch-all is JSON-only: it does not provide generic multipart upload handling.
Although it also accepts GET, it still requires `model` in a JSON request body
and forwards upstream as POST. A query parameter alone is insufficient.

The requested path normally stays unchanged. A card's `routing.upstream_path`
overrides it; otherwise `routing.strip_v1_prefix` can remove `/v1`.
`custom_params.passthrough` removes `model` and `stream` from the native payload.
`endpoints.primary` documents the intended public entry point; it does not
automatically rewrite arbitrary requests to that path.

This forwarding path is buffered, not a generic streaming adapter. Paths such as
`/v1/embed` are not universal aliases for `/v1/embeddings`, and `/v1/responses`
has no dedicated compatibility handler. A catch-all response alone does not prove
support for those APIs.

## Errors and retries

- Missing public credentials return `401`; an authenticated key still needs the
  appropriate API rights and is subject to rate limits.
- Unknown models return `404`. Invalid inputs and unsupported features can return
  `400` or a runtime-specific validation error; inspect the response body.
- A cold start can return `503 model_scaled_to_zero` with `Retry-After`.
  `503 insufficient_capacity` means the gateway did not schedule a wake-up.
  `503 model_not_ready` is another readiness response. Not every `503` is the same.
- Follow retry guidance with a bounded deadline. Do not retry invalid requests
  indefinitely or treat catalog membership as guaranteed capacity.

