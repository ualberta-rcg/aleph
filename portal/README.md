# Aleph User Portal (`portal/`)

Self-service web portal for Aleph researchers to inspect personal token and estimated GPU-hour usage, model speed and context-window pressure, recorded gateway errors, printable grant statements, CSV exports, and live connection snippets.

UI design, SVG charting, coverage bar, and print/CSV foundations are adapted from PR #2 (`ualberta-rcg/aleph#2`), paired with a stateless, zero-persistence live ledger backend tailored to Aleph's production gateway and Tyk authentication model.

## Architecture & Privacy Design

- **Zero disk persistence & minimal RAM**: Unlike batch rollup services, `aleph-portal` writes **nothing** to disk (`readOnlyRootFilesystem: true`) and never holds cluster-wide per-user aggregates in RAM. A background 30-second pass indexes only file byte bounds (`dev`, `ino`, complete-line offset, head bytes, oldest/newest timestamps) and a compact `key_fp -> {identity, account, identity_type}` map (~100 KiB).
- **On-demand rotation-safe scans**: Signed-in requests prune files by `[from, to]`, use a fast byte-substring prefilter before `json.Unmarshal`, verify `(dev, ino)` across opens so concurrent `RotatingFileHandler` rollovers trigger a clean re-index + retry, throttle cold NFS scans via a single-slot semaphore (`PORTAL_MAX_CONCURRENT_SCANS=1`), and cache only active signed-in users for 60 seconds (evicted immediately on `POST /logout`).
- **Dual-Scope Attribution**:
  - `ScopeIdentity`: attributes non-service records (`identity_type` `"user"` and historical `"poc"`) across personal key rotations.
  - `ScopeKeyFP`: attributes records strictly matching one `{"sha256_8","last4"}` fingerprint for admin-minted `type:service` researcher keys and newly minted keys not yet seen in the ledger, while blocking shared service identities (`DENIED_IDENTITIES`).
- **Honest live gateway accounting**:
  - `503` + `cold_start=true` reflects both scale-from-zero wakeups (`model_scaled_to_zero`) and capacity refusals (`insufficient_capacity`).
  - Estimated GPU-hours report `gpus × latency_s` (allocated GPUs × request duration, an upper-bound estimate when concurrent requests share a replica).
  - Async `/v1/tasks` worker units execute under `task-worker` without caller key attribution and are explicitly noted as excluded from personal totals.
- **Prometheus seam**: `DATA_SOURCE=prometheus` (`internal/source/prometheus.go`) fails closed (`503` on `/readyz`) until a private subject-labeled log-to-Prometheus pipeline is wired; it never treats the gateway's public model-level `/metrics` counters as personal usage.

## Tabs & Endpoints

| Path | Description |
|---|---|
| `GET /` | **Overview** — total tokens, requests, estimated GPU-hours, period-over-period delta, daily/weekly inline SVG bar charts, endpoint breakdown |
| `GET /models` | **Models** — per-model prompt/completion/reasoning tokens, output speed (tok/s), peak context fill (`>= 80%` callout) |
| `GET /errors` | **Errors** — recorded HTTP `>= 400` gateway errors by status code and model, scale-from-zero `503` breakdown |
| `GET /report` | **Report** — complete-UTC-day grant statement (print-styled) + CSV download |
| `GET /connect` | **Connect** — live model IDs fetched dynamically from `model-gateway` (`/v1/models?all=true`) with `curl`, Python `openai`, Open WebUI, and Claude Code `/anthropic` snippets |
| `GET /keys` | **Account** — session/scope metadata, PAM `~/.aleph_tyk.env` usage, CLI Bearer CSV export (`curl`), and OIDC-gated key rotation seam |
| `GET /usage.csv` | **CSV export** — accepts browser session cookie or `Authorization: Bearer $TYK_KEY`; escapes formula prefixes (`=`, `+`, `-`, `@`, `\t`, `\r`) |
| `GET /healthz`, `GET /readyz` | Liveness and readiness probes |

## Configuration

| Variable | Default | Purpose |
|---|---|---|
| `PORTAL_LISTEN_ADDR` | `:8080` | HTTP listen address |
| `PUBLIC_ORIGIN` | *(required)* | Canonical origin (`http://...` for local NodePort testing; `https://...` for public TLS) |
| `PORTAL_SESSION_SECRET` | *(required)* | `>= 32`-byte secret (or `>= 64` hex chars) for HMAC-SHA256 stateless session cookies |
| `ALLOW_INSECURE_HTTP` | `false` | Required (`true`) when `PUBLIC_ORIGIN` uses `http://` |
| `MOCK_OIDC_ENABLED` | `false` | Enables local-only Mock OIDC login (`POST /login/mock-oidc`); fails closed if `PUBLIC_ORIGIN` uses `https://` |
| `ALLOW_MOCK_OIDC` | `""` | Must equal `yes-local-testing-only` when `MOCK_OIDC_ENABLED=true` |
| `DATA_SOURCE` | `ledger` | `ledger` (read-only JSONL mount) or `prometheus` (fail-closed seam) |
| `LEDGER_DIR` | `/var/log/aleph` | Root directory containing `model-gateway-*` usage log directories |
| `LEDGER_BACKUPS` | `5` | Number of `usage.log.N` backups per live gateway pod |
| `PORTAL_MAX_CONCURRENT_SCANS` | `1` | Cold-scan concurrency limit across NFS |
| `TYK_VALIDATE_URL` | `http://gateway-svc-tyk-oss-tyk-gateway.tyk.svc.cluster.local:8080/v1/models` | Internal Tyk endpoint used to verify pasted API keys |
| `CATALOG_URL` | `http://model-gateway.models.svc.cluster.local/v1/models?all=true` | Internal `model-gateway` catalog endpoint for `/connect` |
| `DENIED_IDENTITIES` | `openwebui,service-webui,deepthought,task-worker,litellm,anonymous,unknown` | Comma-separated shared identities blocked from personal sessions |

## Local Synthetic Development

Generate synthetic gateway JSONL logs and run locally without real user records:

```bash
go run ./cmd/fakelogs -out /tmp/aleph-fake-logs -users alice,bob,Kevin -days 21
PORTAL_SESSION_SECRET="$(openssl rand -hex 32)" \
PUBLIC_ORIGIN="http://localhost:30080" \
ALLOW_INSECURE_HTTP=true \
MOCK_OIDC_ENABLED=true \
ALLOW_MOCK_OIDC=yes-local-testing-only \
PORTAL_LISTEN_ADDR=":30080" \
LEDGER_DIR=/tmp/aleph-fake-logs \
TYK_VALIDATE_URL=disabled \
CATALOG_URL=disabled \
go run ./cmd/aleph-portal
```

## Isolated In-House NodePort Deployment

See [`k8s/local-nodeport-test.yaml`](k8s/local-nodeport-test.yaml). It deploys into isolated `namespace: aleph-portal` with:
- Read-only `PersistentVolume`/`PersistentVolumeClaim` bound to the existing usage-log NFS export (`Retain`, `ReadOnlyMany`, `ro`).
- Standard `Service` of `type: NodePort` (`nodePort: 30080`, `externalTrafficPolicy: Local`) with `nodeSelector: { kubernetes.io/hostname: aleph1 }` and RFC-1918-only ingress `NetworkPolicy` — no VIP, no extra IPs, and no host/NAT changes.
