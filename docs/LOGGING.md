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

Access mechanics: the endpoint serves on the gateway container port 8080 (the
in-cluster Service exposes 80). The gateway container has no `curl` or `wget` —
fetch from outside it:

```bash
pip=$(kubectl get pod -n models <gateway-pod> -o jsonpath={.status.podIP})
curl -s "http://$pip:8080/metrics"        # from a node/admin shell
```

Only models with traffic since the last process start have non-zero counter
series; the gauge families enumerate the whole catalog. Counters are point-in-time
snapshots unless you deploy a scraper.

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

### Administrative audit is separate

The control-plane `tyk-admin.sh` command has its own audit file. It records operator
and target identity, actions such as creation/rotation/revocation, and validation
results. Single-key invalidation records a prefix of the supplied key or hash.
It is not the per-request model usage ledger described above and does not inherit
that ledger's PVC storage or rotation settings. Its writes are best-effort; the
helper supplies no retention mechanism. See [Tyk administration](TYK-USERS.md#state-audit-and-configuration-ownership)
for configuration and access implications.

## Operator token history

The supplied `63-model-gateway.yaml` sets `GATEWAY_USAGE_LOG` to
`/var/log/aleph/usage.log`, mounting PVC `models/model-gateway-usage-logs` through
`subPathExpr: $(POD_NAME)`. Inspect the binding without reading records:

```bash
kubectl get pvc model-gateway-usage-logs -n models \
  -o custom-columns=CLAIM:.metadata.name,STATUS:.status.phase,PV:.spec.volumeName
kubectl get pods -n models -l app=model-gateway
```

A current gateway pod sees only its own ledger directory. For historical reporting,
use the site's authorized read-only mount or snapshot of the full PVC. Include
retained directories from replaced pods, active files and rotations exactly once;
avoid also counting copies in archives. A consistent snapshot avoids rotation or
an incomplete trailing record during collection. Do not create a new storage mount
or reporting workload without the necessary authorization.

### Collecting the full ledger

Three authorized patterns reach the complete ledger (a single replica is never the
ledger — `kubectl exec deploy/model-gateway` round-robins to one pod):

```bash
# (a) Loop over every gateway pod — quick, current replicas only:
for pod in $(kubectl get pods -n models -l app=model-gateway -o name); do
  kubectl exec -n models "$pod" -c gateway --     sh -c 'cat /var/log/aleph/usage.log /var/log/aleph/usage.log.[1-9] 2>/dev/null'
done

# (b) Temporary pod mounting the whole PVC — sees retired replicas' directories too:
kubectl run pvc-peek -n models --image=busybox:1.36 --restart=Never --   sleep 600 --overrides="$(printf '%s' '{"spec":{"volumes":[{"name":"logs","persistentVolumeClaim":{"claimName":"model-gateway-usage-logs"}}],"containers":[{"name":"pvc-peek","command":["sleep","600"],"volumeMounts":[{"name":"logs","mountPath":"/logs"}]}]}}')"
kubectl exec -n models pvc-peek -- sh -c 'cat /logs/*/usage.log /logs/*/usage.log.[1-9] 2>/dev/null'
kubectl delete pod pvc-peek -n models

# (c) Node-side: read the NFS export directory the kubelet mounts (operator shell):
#   /var/lib/kubelet/pods/<gateway-pod-uid>/volumes/kubernetes.io~nfs/<pv>/*/usage.log*
```

Include active files and all rotations; directories from replaced pods are part of
the history. When sources can overlap (a snapshot plus live reads, or archives),
deduplicate on `(ts, identity, model, latency_ms, tokens.completion)` — endpoint
and prompt counts break remaining ties.

### Auditing coverage before reporting

Report the span you actually covered, and check for holes first:

```bash
kubectl exec -n models pvc-peek -- sh -c 'for f in /logs/*/usage.log*; do
  [ -f "$f" ] || continue
  printf "%s %s %s\n" "$f" "$(wc -l < "$f")" "$(tail -1 "$f" | cut -c1-19)"
done'
```

Timestamps are normalized UTC `YYYY-MM-DDTHH:MM:SSZ`, so lexicographic `ts >=`
comparisons window records correctly. Count malformed lines rather than skipping
them silently.

Agree on the identity/account, models, UTC interval, and whether the report covers
all attempts or only successful responses. Aggregate within the cluster and return
only the authorized summary. Token fields are `tokens.prompt`, `tokens.completion`,
and `tokens.total`; GPU-time estimates are `derived.gpu_seconds`. Redis key state
is not this history. There is no per-user history API.

This example aggregates successful requests for one identity over a half-open UTC
interval, using an explicitly selected set of snapshot files. Replace the example
paths and identity privately. It streams records instead of loading the ledger
into memory; run substantial reporting work in an appropriate allocated environment.

```bash
LEDGER_FILES=(/private/snapshot/example-replica/usage.log /private/snapshot/example-replica/usage.log.1)
jq -n --arg who example-user \
  --arg start '2026-01-01T00:00:00Z' --arg end '2026-01-02T00:00:00Z' '
  reduce inputs as $r
    ({requests:0, input_tokens:0, output_tokens:0, total_tokens:0, estimated_gpu_seconds:0};
     if $r.identity == $who and $r.ts >= $start and $r.ts < $end
        and $r.status >= 200 and $r.status < 300 then
       .requests += 1 |
       .input_tokens += ($r.tokens.prompt // 0) |
       .output_tokens += ($r.tokens.completion // 0) |
       .total_tokens += ($r.tokens.total // 0) |
       .estimated_gpu_seconds += ($r.derived.gpu_seconds // 0)
     else . end)
' "${LEDGER_FILES[@]}"
```

The same report in the streamed-Python shape used for fleet-wide operator reports
(per-day and per-identity tables, GPU-time, bad-line counts; run in an allocated
environment):

```python
import json, sys, collections
who, start, end = "example-user", "2026-01-01T00:00:00Z", "2026-01-02T00:00:00Z"
per_day = collections.Counter(); gpu_s = 0.0; bad = 0
for line in sys.stdin:                      # feed collected usage.log* files
    try: r = json.loads(line)
    except json.JSONDecodeError: bad += 1; continue
    if who in (None, r.get("identity")) and start <= r.get("ts","") < end        and 200 <= int(r.get("status", 0)) < 300:
        per_day[r["ts"][:10]] += r.get("tokens",{}).get("total",0)
        gpu_s += r.get("derived",{}).get("gpu_seconds",0.0)
print(dict(per_day), round(gpu_s/3600, 2), "gpu-hours", bad, "bad lines")
```

The string comparisons assume the logger's normalized `YYYY-MM-DDTHH:MM:SSZ`
timestamps. This example excludes cold-start/error attempts; count those separately
when reporting failures. Report which retained files and time span were covered,
missing records or backend usage, and shared-key attribution limits. Do not report
a zero count as proof of no compute use. Do not expose raw records, key fingerprints,
or unrelated identities. Never silently ignore malformed input to claim a complete
report.

### Verifying whether a key was ever used

The `key_fp` field answers "did this key ever work" without exposing the key: hash
the candidate key (`sha256(value).hexdigest()[-8:]` + last 4 characters), then grep
it across every replica's rotations. Zero matches across all replicas and rotations
means no usage record ever carried that key — typically requests were rejected by
Tyk (401/403/429 produce no usage records at all) or the key was never sent.

## Measure physical GPU usage

Measure on the selected GPU worker, using private site access details. This bounded
sample reports each physical GPU's UUID, utilization, VRAM and power without listing
processes or users:

```bash
timeout 15s nvidia-smi \
  --query-gpu=timestamp,uuid,name,utilization.gpu,memory.used,memory.total,power.draw \
  --format=csv --loop=5
```

Exit status 124 is expected when `timeout` ends sampling. GPU utilization is a
sampled activity percentage, memory used is occupancy, and power is watts; none is
a per-user billing measure. A loaded idle model can occupy substantial VRAM with
low utilization. Measure on the host for physical totals: a shared serving container
can expose a virtualized memory view.

For allocation, inspect the model/pod resource requests and HAMi assignment. For
per-request accounting, use the ledger's estimated GPU-seconds. Multiple concurrent
requests and GPU sharing prevent adding those estimates into physical utilization.

Historical utilization needs a verified GPU telemetry exporter and a time-series
collector with retention. Discover the site's existing monitoring configuration
before assuming DCGM or HAMi telemetry is scraped. Gateway `/metrics` provides
request/accounting counters, not a historical record of physical GPU utilization.
For a physical busy-time estimate, integrate sampled utilization/100 over elapsed
seconds per GPU; label sampling gaps and the approximation, and do not attribute
shared-device activity to a researcher without additional measurements.

### Runtime load and throughput

The local `scripts/vllm_stats.py` illustrates another useful layer: running and
waiting requests, KV-cache occupancy, and prompt/generation token counters from
the serving runtime's own `/metrics`. Its historical parser accepts both
`kv_cache_usage_perc` and `gpu_cache_usage_perc`; inspect the actual runtime's
metric names and labels before using it with another version. These are backend
metrics, not the gateway's combined `/metrics` output.

For a selected authorized backend, take two bounded samples from the same process.
Token throughput is the counter difference divided by elapsed seconds. Detect
process restarts/counter resets and combine distinct replicas once. Running/waiting
requests show load; KV-cache occupancy describes the runtime cache, not total
physical VRAM or GPU utilization. Verify the container's port and available HTTP
tool rather than assuming every runtime serves metrics on port 8080.
