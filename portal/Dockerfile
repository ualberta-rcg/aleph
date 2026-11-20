# Build: docker build -t rkhoja/aleph:portal-<sha> portal/
# Pin deployed images by tag and digest, never :latest (see CLAUDE.md).
FROM golang:1.27.4@sha256:205c7636d74e0ffbe3d007162df7d74f859f5a8c8322dfb9f907977686c126cf AS src
WORKDIR /src
COPY go.mod ./
RUN go mod download
COPY . .

FROM src AS vet
RUN CGO_ENABLED=0 go vet ./...

FROM src AS test-source
RUN CGO_ENABLED=1 go test -race -count=1 ./internal/source

FROM src AS test-auth
RUN CGO_ENABLED=1 go test -race -count=1 ./internal/auth

FROM src AS test-catalog
RUN CGO_ENABLED=1 go test -race -count=1 ./internal/catalog

FROM src AS test-web
RUN CGO_ENABLED=1 go test -race -count=1 ./internal/web

FROM src AS build
RUN CGO_ENABLED=0 go vet ./... \
 && CGO_ENABLED=1 go test -race -count=1 ./... \
 && CGO_ENABLED=0 go build -trimpath -ldflags="-s -w" -o /out/fakelogs ./cmd/fakelogs \
 && CGO_ENABLED=0 go build -trimpath -ldflags="-s -w" -o /out/aleph-portal ./cmd/aleph-portal

# Static binary on distroless: no shell, no package manager, runs as nonroot (UID 65532).
FROM gcr.io/distroless/static-debian12:nonroot@sha256:afa5c872c891853ca7fcf1f12c3edb23f7eeef36189728842dd51042ff57f7ab
COPY --from=build /out/aleph-portal /aleph-portal
USER nonroot:nonroot
EXPOSE 8080
ENTRYPOINT ["/aleph-portal"]
