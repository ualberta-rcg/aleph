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

Real records from the production ledger (2026-09), with identities and key
fingerprints replaced by placeholders; all other values are as written.

A chat completion served to a browser-chat service key:

```json
{"ts":"2026-09-14T18:21:58Z","site":"aleph","identity":"service-webui","identity_type":"service","account":"service-webui","endpoint":"/v1/chat/completions","api":"openai","model":"qwen35-122b","status":200,"stream":false,"cold_start":false,"latency_ms":1000,"tokens":{"prompt":272,"completion":11,"total":283,"detail":{"prompt_tokens":272,"total_tokens":283,"completion_tokens":11,"prompt_tokens_details":null}},"context_window":131072,"max_completion_tokens":32768,"resources":{"model":"qwen35-122b","gpus":4,"cpu_cores":16.0,"system_ram_mib":131072,"node":"gpu-worker-5","gpu_product":"L40S","latency_ms":1000},"derived":{"gpu_seconds":4.0},"key_fp":{"sha256_8":"0123abcd","last4":"DEMO"}}
```

Read: 283 tokens through a 4-GPU model in 1 s — 4.0 allocated GPU-seconds.

An embeddings call from a retrieval-pipeline service key:

```json
{"ts":"2026-09-11T20:55:11Z","site":"aleph","identity":"service-rag","identity_type":"service","account":"service-rag","endpoint":"/v1/embeddings","api":"openai","model":"bge-m3","status":200,"stream":false,"cold_start":false,"latency_ms":137,"tokens":{"prompt":32,"completion":0,"total":32,"detail":{"prompt_tokens":32,"total_tokens":32}},"context_window":8192,"max_completion_tokens":0,"resources":{"model":"bge-m3","gpus":1,"vram_mib":8192,"cpu_cores":4.0,"system_ram_mib":8192,"node":"gpu-worker-2","gpu_product":"L40S","latency_ms":137},"derived":{"gpu_seconds":0.137},"key_fp":{"sha256_8":"0123abcd","last4":"DEMO"}}
```

Note `vram_mib: 8192` — one HAMi vGPU slice, not a whole card.

A speech transcription (counts only — never the transcript):

```json
{"ts":"2026-09-12T00:27:56Z","site":"aleph","identity":"service-notes","identity_type":"service","account":"service-notes","endpoint":"/v1/audio/transcriptions","api":"openai","model":"whisper-large-v3","status":200,"stream":false,"cold_start":false,"latency_ms":583,"tokens":{"prompt":0,"completion":0,"total":0,"detail":{"audio_input_bytes":1443884,"audio_output_bytes":50,"text_chars":10}},"context_window":0,"max_completion_tokens":0,"resources":{"model":"whisper-large-v3","gpus":1,"vram_mib":8192,"cpu_cores":8.0,"system_ram_mib":24576,"node":"gpu-worker-3","gpu_product":"L40S","latency_ms":583},"derived":{"gpu_seconds":0.583},"key_fp":{"sha256_8":"0123abcd","last4":"DEMO"}}
```

A scale-from-zero guard response (an attempt, not a served request):

```json
{"ts":"2026-09-11T19:32:02Z","site":"aleph","identity":"example-user","identity_type":"user","account":"example-user","endpoint":"/v1/embeddings","api":"openai","model":"ancient-greek-bert","status":503,"stream":false,"cold_start":true,"latency_ms":0,"tokens":{"prompt":0,"completion":0,"total":0,"detail":{}},"context_window":512,"max_completion_tokens":0,"resources":{"model":"ancient-greek-bert","cpu_cores":2.0,"system_ram_mib":4096,"latency_ms":0},"derived":{"gpu_seconds":0.0},"key_fp":{"sha256_8":"0123abcd","last4":"DEMO"}}
```

`context_window` and `max_completion_tokens` are model-card limits, not the size or
output budget of the particular call.

### Privacy and accounting, by design

Nothing that was said, typed, uploaded, or generated is stored — the schema holds
counts only (see [What is recorded](#what-is-recorded)). What **is** kept is the
accounting spine: caller identity/account/type, model, token counts, allocated
resources, and derived GPU-time. That field set deliberately mirrors
scheduler-style accounting — user, account, elapsed time, allocated-resource-time —
so the ledger can eventually feed a research-computing allocation/fairshare system.
That integration is future work; today the ledger is report-only.

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
- **`count_tokens` is metadata-only.** Its `input_tokens` lands in `tokens.detail`
  and is never added to the totals.
- **Identity follows the key.** A shared application's service key identifies
  that service, not necessarily its individual end user.

## Metrics

`GET /metrics` returns Prometheus text. Metrics have model labels, not per-user
identities or key fingerprints.

Complete family list (verified against a live scrape, 2026-09-14):

| Family | Meaning |
|---|---|
| `gateway_model_requests_total` | Served requests per model |
| `gateway_model_errors_total` | Errored requests per model |
| `gateway_model_prompt_tokens_total` / `_completion_tokens_total` / `_total_tokens_total` | Token counters per model |
| `gateway_model_cold_starts_total` | Scale-from-zero events per model |
| `gateway_model_gpu_seconds_total` | Approximate GPU-seconds (gpus x latency) per model |
| `gateway_model_audio_seconds_total` | Audio duration seconds per model (STT) |
| `gateway_model_audio_bytes_in_total` | Uploaded audio bytes per model |
| `gateway_model_audio_bytes_out_total` | Returned audio/SSE bytes per model |
| `gateway_model_tts_chars_total` | TTS/clone input characters per model |
| `gateway_model_replicas` (gauge) | Running predictor pods per model |
| `gateway_model_scaled_up` (gauge) | 1 if the model has at least one predictor pod |
| `gateway_models_ready` / `gateway_models_total` (gauges) | Ready carded models / discovered cards |
| `gateway_requests_total` / `gateway_requests_error_total` | Global request/error counters |

Real excerpt (values as scraped 2026-09-14):

```text
# HELP gateway_requests_total Total requests handled.
gateway_requests_total 352860
# HELP gateway_model_requests_total Served requests per model.
gateway_model_requests_total{model="gpt-oss-120b"} 225151
gateway_model_requests_total{model="qwen35-122b"} 39220
# HELP gateway_models_ready Models with a ready ISVC.
gateway_models_ready 102
```

### Why the numbers are live

- Counters increment **on the request path** — verified by scrapes 130 s apart moving
  `gateway_requests_total` by exactly the then-busy model's per-model delta, with no
  scraper activity. Gauges recompute from Kubernetes watches (cards, ISVC readiness,
  predictor replicas). A scrape only reads.
- A normal scrape is a **cluster snapshot assembled on demand**: the answering pod
  fetches each peer's `/metrics?local=true` (2 s timeout per peer) and sums.
  Verified: the combined value equaled the exact sum of the three per-pod local
  values taken the same second. Local scrapes answer in ~5 ms; combined in ~70–130 ms.
- The counter **window is the current pods' lifetimes**, not fleet-forever — a
  gateway restart resets that pod's contribution. At measurement the combined view
  spanned ~4.8 days (three pods since their last rollout). Gauges are instantaneous.
- Gauges count **cards**, not InferenceServices: card-less services are invisible
  here. Scale-to-zero models count as ready; `gateway_model_replicas` distinguishes
  sleeping (0) from running (1+).

Counters live in memory and reset when a gateway process restarts. The replica
gauge counts Running predictor pods, not independently verified ready replicas.
If a peer cannot be reached, the endpoint falls back to local metrics, so a
successful scrape can still be partial.

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
series; the gauge families enumerate the whole catalog.

## Storage and retention

The gateway writes one JSON object per line to a per-replica directory on the
usage PVC: **one directory per pod name**, and rollouts, restarts, and canaries
each leave a new set — nothing removes the old ones.

The source default is size-based rotation of a 50 MiB active file with up to five
rotated copies, configurable (`GATEWAY_USAGE_LOG_MAX_BYTES`,
`GATEWAY_USAGE_LOG_BACKUPS`). **The deployed image currently retains a single
rotation** (~100 MiB per pod), so the effective depth is image behavior until an
image carrying the configuration is deployed.

Reference observation (2026-09-14): 26 directories (3 live pods + 23 retired),
44 files, ~1.06 GiB on the 10 Gi claim — retired generations held 79% of the
bytes; earliest retained record three weeks old. At then-current write rates
(~8 MB/day/pod) the two-file budget holds roughly two weeks; at an observed peak
(~50 MB/day) it held about two days. There is no time-based deletion; operators
own archiving, pruning retired directories, and backup — the claim's reclaim
policy does not protect this data.

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

On NFS, in-container `du` can understate directory sizes; use `ls`/`stat` byte
counts when the audit must be exact.

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
