# Working on `portal/`

Read root [`CLAUDE.md`](../CLAUDE.md) and [`AGENTS.md`](../AGENTS.md) first, then [`portal/README.md`](README.md).

## Component Rules

- **Zero persistence & strict privacy**: Never persist per-user usage tables to disk or log raw API keys, session cookies, or real researcher identities/records in commits, tests, or documentation. Use `cmd/fakelogs` (`internal/fake`) for synthetic fixtures.
- **No cluster IPs, VIPs, or secrets in Git**: Keep `k8s/local-nodeport-test.yaml` tokenized (`__NFS_SERVER__`, `__NFS_USAGE_LOGS_PATH__`, `__PORTAL_ORIGIN__`). Render tokens into a temporary untracked file only when applying to an authorized cluster.
- **In-house testing uses `NodePort` only**: `k8s/local-nodeport-test.yaml` exposes `Service` `type: NodePort` (`30080`, `externalTrafficPolicy: Local`) on `aleph1` with RFC-1918 ingress `NetworkPolicy`. Never add `externalIPs`, `LoadBalancer` VIPs, or host/NAT changes for internal portal testing.
- **Fail-closed auth guards**: Never weaken the startup invariants in `internal/auth/session.go`: `MOCK_OIDC_ENABLED=true` must exit non-zero on any `https://` `PUBLIC_ORIGIN` or without `ALLOW_MOCK_OIDC=yes-local-testing-only`.
- **Docker Hub image tags**: `.github/workflows/deploy-portal.yml` publishes `rkhoja/aleph:portal-<shortsha>` and `rkhoja/aleph:portal-latest` (never `:latest` or `gateway-*`). Always pin `rkhoja/aleph:portal-<shortsha>@sha256:...` in manifests before applying.
- **Extensible navigation**: Add future portal sections via `TabSpec` in `internal/web/nav.go` rather than hardcoding tab lists across templates.
- **Testing**: `portal/Dockerfile` and `.github/workflows/deploy-portal.yml` run `go vet ./...` and `go test -race -count=1 ./...` during the container build. Record every repository change in root `CHANGELOG.md`.
