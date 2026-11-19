# Build: docker build -t rkhoja/aleph:usage-ui-<sha> usage-ui/
# Pin the deployed image by tag and digest, never :latest (see CLAUDE.md).
FROM golang:1.27.4@sha256:205c7636d74e0ffbe3d007162df7d74f859f5a8c8322dfb9f907977686c126cf AS build
WORKDIR /src
COPY go.mod ./
RUN go mod download
COPY . .
RUN CGO_ENABLED=0 go test ./... \
 && CGO_ENABLED=0 go build -trimpath -ldflags="-s -w" -o /out/usage-ui ./cmd/usage-ui

# Static binary on distroless: no shell, no package manager, runs as non-root.
FROM gcr.io/distroless/static-debian12:nonroot@sha256:afa5c872c891853ca7fcf1f12c3edb23f7eeef36189728842dd51042ff57f7ab
COPY --from=build /out/usage-ui /usage-ui
USER nonroot:nonroot
EXPOSE 8080
ENTRYPOINT ["/usage-ui"]
