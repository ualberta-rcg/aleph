# Logging and metrics

Aleph records usage metadata for accounting and troubleshooting, and exposes
aggregate metrics for monitoring. The usage ledger identifies the caller and
model; it is not a conversation archive.

## What is recorded

| Information | Examples |
|---|---|
| Caller | Identity, account, and whether the key represents a user or service |
| Request | Timestamp, model ID, endpoint, API format, HTTP status, streaming flag |
| Usage | Input/output token counts and upstream usage details, including reasoning or cached-token counts when available |
| Timing | Request latency and cold-start guard events |
| Resources | Model resource allocation, resolved node/GPU information, and estimated GPU-seconds |
| Key reference | A short SHA-256 fingerprint and the key's last four characters; not the full key |
| Audio | Byte counts, duration when available, and text character counts |

The gateway's accounting code does not add prompts, answers, conversation history,
tool payloads, uploaded files, audio contents, transcripts, or filenames to the
ledger. Token and character fields are **counts**, not text.

This describes the gateway's usage ledger and metrics. It is not a retention
statement for browser chat history, client applications, or model-server and
infrastructure logs. The upstream `usage` object is retained in `tokens.detail`
without field filtering, so custom runtimes must keep that object limited to
usage metadata.

## Example usage records

These examples are synthetic. Identities, models, hardware, and numbers are
illustrative; none are copied from user logs.

A completed chat request:

```json
{
  "ts": "2026-01-01T12:00:00Z",
  "site": "example-site",
  "identity": "example-user",
  "identity_type": "user",
  "account": "example-project",
  "endpoint": "/v1/chat/completions",
  "api": "openai",
  "model": "example-chat",
  "status": 200,
  "stream": false,
  "cold_start": false,
  "latency_ms": 1500,
  "tokens": {
    "prompt": 100,
    "completion": 40,
    "total": 140,
    "detail": {
      "prompt_tokens": 100,
      "completion_tokens": 40,
      "total_tokens": 140
    }
  },
  "context_window": 32768,
  "max_completion_tokens": 4096,
  "resources": {
    "model": "example-chat",
    "gpus": 1,
    "vram_mib": 8192,
    "cpu_cores": 4,
    "system_ram_mib": 16384,
    "node": "example-worker",
    "gpu_product": "example-gpu",
    "latency_ms": 1500
  },
  "derived": {"gpu_seconds": 1.5},
  "key_fp": {"sha256_8": "0123abcd", "last4": "DEMO"}
}
```

This records 140 tokens and 1.5 seconds of latency, without the question or answer.
`context_window` and `max_completion_tokens` are model-card limits, not the size
or requested output budget of this particular call.

An audio transcription can instead carry this usage detail (excerpt):

```json
{
  "tokens": {
    "prompt": 0,
    "completion": 0,
    "total": 0,
    "detail": {
      "audio_input_bytes": 96000,
      "audio_seconds": 3.0,
      "text_chars": 42
    }
  }
}
```

The transcript itself is absent. Available detail varies by runtime and endpoint.

## How to interpret the numbers

- **Tokens can be incomplete.** If a backend omits usage, or a stream ends before
  its final usage event, counts may be zero. Zero does not prove no work occurred.
- **Cold-start records are attempts.** A guard response is logged with status
  `503`, `cold_start: true`, and zero latency/tokens. This includes capacity
  refusals; it does not prove that a new model pod started. Retries create more
  records. These events do not measure actual model-loading time.
- **GPU-seconds are an estimate:** GPU allocation count × request latency in
  seconds. Shared GPUs and concurrent requests mean this is not measured GPU
  utilization, exclusive GPU time, or a billing total.
- **Coverage is not a full access audit.** Authentication failures rejected by
  Tyk and some early gateway validation failures do not reach the usage logger.
  Per-model ledger counts and global request counters can therefore differ.
- **Identity follows the key.** A shared application's service key identifies
  that service, not necessarily its individual end user.

## Metrics

`GET /metrics` returns Prometheus text with per-model request, error, token,
cold-start, audio, and estimated GPU-time counters, plus model and replica gauges.
Metrics have model labels, not per-user identities or key fingerprints.

Synthetic example:

```text
gateway_model_requests_total{model="example-chat"} 12
gateway_model_errors_total{model="example-chat"} 2
gateway_model_total_tokens_total{model="example-chat"} 1400
gateway_model_cold_starts_total{model="example-chat"} 2
gateway_model_gpu_seconds_total{model="example-chat"} 15
gateway_model_replicas{model="example-chat"} 1
```

Counters live in memory and reset when a gateway process restarts. The replica
gauge counts Running predictor pods, not independently verified ready replicas.
By default, the endpoint combines gateway replicas; if a peer cannot be reached,
it falls back to local metrics, so a successful scrape can still be partial.

For monitoring, scrape the combined endpoint once, or scrape each replica's
`/metrics?local=true` and aggregate in your monitoring system. Do not sum multiple
copies of the combined view. Historical charts require a separately configured
metrics collector and retention policy.

## Storage and retention

The gateway writes one JSON object per line to a separate usage file. The supplied
deployment keeps these files on persistent storage in a directory per replica.
A complete report must consider retained files from all relevant replicas,
including rotated files and directories left by replaced pods.

The logger defaults to size-based rotation: a 50 MiB active file and up to five
rotated copies per replica directory. These are configurable defaults, **not a
retention period in days**. There is no time-based deletion policy in the usage
logger, and old replica directories are not removed by its file rotation.
Deployment operators determine archival, cleanup, backup, and metrics retention.
If file logging cannot initialize, the logger falls back to the process logging
stream; this is not a guarantee of complete or durable delivery.

## Get your usage information

For the hosted Vulcan service, contact
[support@tech.alliancecan.ca](mailto:support@tech.alliancecan.ca), mention **Aleph
usage or metrics**, and specify the time range, time zone, models, and whether you
need a usage summary or help with failed requests. Ask the operator to confirm
what records are still available and the applicable retention policy.

Do not send an API key or research content. Raw usage records contain caller
identities and are not exposed as a public per-user download API. Operators can
arrange an appropriately scoped report; a shared service key may require usage
information from the application itself to separate individual users.

For your own deployment, access to the ledger is an administrative storage
operation. Restrict raw-log access and filter exports to the intended recipient.
Implementation references: [usage logger](../gateway/app/usage.py),
[gateway handlers and metrics](../gateway/app/gateway.py), and
[identity handling](TYK-USERS.md).
