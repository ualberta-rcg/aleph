# Endpoint Paths

Reference set of HTTP endpoint paths the inference platform serves. The gateway
routes by path family and forwards each request to the backing model's declared
endpoint; the model cards (`details.yaml` → `endpoints.primary`) are the source of
truth for which path each model listens on.

> Sourced from the legacy POC cluster (`/root/kuberflow-working/` on the 232
> cluster) as the reference surface. Aleph's gateway forwards `/v1/{path}`
> generically, so treat this as a **coverage checklist**, not a hard-coded list —
> a card can declare any path its `server.py` exposes. (232 specifics are kept in
> the local working dir.)

## Chat / text
- `/v1/chat/completions` — OpenAI chat
- `/v1/completions` — completion-only (non-chat) LLM
- `/v1/messages` (also `/anthropic/v1/messages`) — Anthropic-native
- `/v1/messages/count_tokens` (also `/anthropic/v1/messages/count_tokens`) — Anthropic token count

The `/anthropic/` prefix is a Tyk listen path (`model-anthropic`, strip prefix, keyed).
Tyk injects `X-Aleph-Api: anthropic` so `GET /anthropic/v1/models` returns the
always-on chat list in Anthropic shape. Same keys as `/v1/` (keys need
`access_rights` on both `model-gateway` and `model-anthropic`).

## Embeddings / rerank
- `/v1/embeddings`, `/v1/rerank`, `/v1/embed` (science-embed alias)

## Audio (TTS / STT)
- `/v1/audio/speech` (TTS), `/v1/audio/transcriptions` (STT),
  `/v1/audio/clone` (voice cloning), `/v1/audio/voices` (voice listing)

## Images
- `/v1/images/generations` (text→image), `/v1/images/edits` (img2img)

## Vision
- `/v1/vision/{classify, detect, segment, depth, embed, face, pose}`

## Science (`/v1/science/*`)
- `classify, deidentify, detect, embed, energy, forecast, generate, identify,
  info, match, predict, reconstruct, retrieve, segment, relax`

## Top-level science-ish (no `/science/` prefix)
- `/v1/{predict, forecast, generate, classify, detect, embed}`
- `/v1/design` (protein design), `/v1/dock` (molecular docking), `/v1/structure` (folding)
- `/v1/restore` (text restoration), `/v1/translate` (AA↔3Di)

## Public catalogue mirror (keyless)
- `/serving/api/v1/*` — mirrors the main `/v1/*` endpoints for unauthenticated
  catalogue / preview access.

## Notable / model-specific
- `/v1/deterministic_2_8_deg` — benchmark/model-specific path.
