# Asynchronous Task System (`/v1/tasks`) — Human & AI Agent Guide

The Aleph Asynchronous Task System (`/v1/tasks`) lets researchers, scripts, and AI agents submit multi-file or long-running inference jobs (such as multi-PDF OCR with `glm-ocr`, multi-step weather rollouts, multi-prompt or img2img batches, medical volume segmentation, or protein folding) using their **existing Aleph API key**, poll status/progress/ETA (`Retry-After` / `come_back_at`), inspect live error logs (`error.log`), optionally receive an email when finished, and pick up outputs within **24 hours of task completion**.

---

## 1. Core Principles (For Both Humans & AI Agents)

1. **Same API Key Everywhere**:
   Authenticate with your standard Aleph key via `Authorization: Bearer $TYK_KEY`, `x-api-key: $TYK_KEY`, `api-key: $TYK_KEY`, `x-goog-api-key: $TYK_KEY`, or `?api_key=$TYK_KEY`. Tasks are strictly isolated per API key (`404 Not Found` to any other key).
2. **One Submission = One Task (`1 -> 2 -> ... -> N` Sequential Loop on a Warm Pod)**:
   Submitting 1..N files (or a `.zip`/`.tar.gz` archive, `.txt`/`.jsonl` prompt list, or JSON `"inputs": [...]` array) creates **one single `task_id`**. The worker wakes the KServe predictor pod **once** and loops through the items **one by one (`item_0 -> item_1 -> ... -> item_{N-1}`)** on the warm GPU pod with **zero model reloads** between files.
3. **Self-Describing Model & Task Properties (Leveraging Card `input_map` & `custom_params`)**:
   Every model card (`details.yaml`) exposes:
   - Top-level `"mode": "api" | "task" | "both"` in `GET /v1/models?all=true`, `GET /v1/models?tasks=true`, `GET /v1/models/{model_id}`, `GET /v1/tasks/models`, and `GET /v1/tasks/models/{model_id}`.
   - Standard `"input_map"`, `"custom_params"` (`schema` + `passthrough`), `"output_map"`, `"defaults"`, plus `"tasks"` (`loop_mode`, `file_grouping`, `unit`, `retention_hours`, `accepted_inputs`, `output_formats`, `allows_unlisted_params: true`, `default_params`, `properties`, `envelope_properties`, `limits`, `endpoints`, and ready-to-run `examples`).
4. **Open Custom Parameter Forwarding (Cards Never Block Unlisted Parameters)**:
   `input_map` and `custom_params.schema` provide defaults and documentation — **never an allowlist**. Any parameter you supply (including unlisted backend parameters like `width`/`height` on `kandinsky-3` or extra vLLM sampling flags like `min_p`/`guided_json`) is merged and passed straight through to the predictor pod.
   - Chat/vLLM backends (including `glm-ocr`) run through the gateway's `prepare_chat()` pipeline (`defaults.chat`, `param_translation.thinking`, `limits.max_completion_tokens`, `routing.upstream_model_id`).
   - Custom/science/image backends run through the gateway's `forward_custom` routing rules (`routing.upstream_path`, `routing.strip_v1_prefix`, `endpoints.primary` / `endpoints.edit`, and `custom_params.passthrough`).
5. **Per-Item Fault Isolation & Live `error.log`**:
   By default (`continue_on_item_error=true`), if 1 file/item in a multi-item batch fails upstream (e.g., HTTP 400/422/500 or a Python/CUDA traceback), the worker records that item's failure in `manifest.json`, writes the full timestamped error, request parameters, and upstream traceback to `/v1/tasks/{task_id}/error.log`, checks predictor health, and continues processing the remaining items (`status: "succeeded_with_errors"` if other items succeed, or `"failed"` if all items fail).
6. **24-Hour Post-Completion Retention & Strictly Opt-In Email**:
   Task files remain available for **24 hours after `completed_at`** (`expires_at = completed_at + 24h`) and are then automatically deleted. Email notification is **off by default** and sent only when `notify_email` is explicitly supplied.

---

## 2. Step-by-Step Workflow for AI Agents & Humans

### Step 1: Discover Task Models & Query Task Properties

```bash
export GW_URL="https://<aleph-host>"
export TYK_KEY="<your-api-key>"

# 1. List all models (including task-only models like glm-ocr) and see each model's "mode" ("api" | "task" | "both")
curl -sS "$GW_URL/v1/models?all=true" \
  -H "Authorization: Bearer $TYK_KEY" | jq '.data[] | {id, type, mode, ready, scaled_up}'

# 2. List only task-capable models (mode == "task" or "both")
curl -sS "$GW_URL/v1/tasks/models" \
  -H "Authorization: Bearer $TYK_KEY" | jq '.data[] | {id, type, mode, loop_mode: .tasks.loop_mode, unit: .tasks.unit}'

# 3. Inspect a specific model's full task schema, input_map, custom_params, defaults, and curl examples
curl -sS "$GW_URL/v1/tasks/models/glm-ocr" \
  -H "Authorization: Bearer $TYK_KEY" | jq .
```

An AI agent should always call `GET /v1/tasks/models/{model_id}` (or `GET /v1/models/{model_id}`) first to read:
- `input_map` and `custom_params.schema` (or `tasks.properties`) for supported model parameters and their defaults,
- `tasks.envelope_properties` for task submission options (`files`, `inputs`, `params`, `file_params`, `notify_email`, `continue_on_item_error`, `unpack_archive`, `file_grouping`, `endpoint`),
- `tasks.accepted_inputs` and `tasks.output_formats`,
- `tasks.examples` for ready-to-run `curl` templates.

---

### Step 2: Submit a Task (`POST /v1/tasks`)

You can submit tasks either as **`multipart/form-data`** (for PDFs, images, `.zip`/`.tar.gz` archives, `.txt`/`.jsonl` prompt lists, or `.npy`/`.json` files) or as **`application/json`** (for structured JSON inputs or prompt arrays).

#### A. Multi-PDF / Image OCR (`glm-ocr`, `loop_mode: "pdf_pages"`)
```bash
# Submit 2 PDFs + custom parameters (dpi=250, prompt="Text Recognition:") + per-file override on paper2.pdf
curl -sS -X POST "$GW_URL/v1/tasks" \
  -H "Authorization: Bearer $TYK_KEY" \
  -F "model=glm-ocr" \
  -F "files=@paper1.pdf" \
  -F "files=@paper2.pdf" \
  -F "dpi=250" \
  -F "prompt=Text Recognition:" \
  -F "output_format=markdown" \
  -F 'file_params={"paper2.pdf": {"dpi": 300, "pages": "1-5", "prompt": "Table Recognition:"}}' | jq .
```

#### B. Uploading a `.zip` or `.tar.gz` Archive of Files (`unpack_archive=true`)
```bash
curl -sS -X POST "$GW_URL/v1/tasks" \
  -H "Authorization: Bearer $TYK_KEY" \
  -F "model=glm-ocr" \
  -F "files=@scanned_batch.zip" \
  -F "unpack_archive=true" \
  -F "dpi=200" | jq .
```

#### C. Image Generation / Editing Batch (`kandinsky-3`, `loop_mode: "items"`)
```bash
# 1. Text-to-image batch via JSON (including unlisted custom width/height parameters)
curl -sS -X POST "$GW_URL/v1/tasks" \
  -H "Authorization: Bearer $TYK_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "model": "kandinsky-3",
    "params": {
      "num_inference_steps": 25,
      "guidance_scale": 3.0,
      "width": 1024,
      "height": 1024,
      "seed": 42
    },
    "inputs": [
      {"prompt": "A snowy boreal forest under aurora borealis"},
      {"prompt": "A futuristic research laboratory with glass domes", "seed": 43}
    ]
  }' | jq .

# 2. Image-to-image (img2img) batch: uploading PNG files automatically selects endpoints.edit (/v1/images/edits)
#    and converts each uploaded binary PNG into base64 "image" for the warm predictor pod
curl -sS -X POST "$GW_URL/v1/tasks" \
  -H "Authorization: Bearer $TYK_KEY" \
  -F "model=kandinsky-3" \
  -F "files=@sketch1.png" \
  -F "files=@sketch2.png" \
  -F "prompt=Oil painting in autumn colors" \
  -F "strength=0.7" | jq .
```

#### D. Autoregressive Rollout (`loop_mode: "rollout_steps"`)
```bash
curl -sS -X POST "$GW_URL/v1/tasks" \
  -H "Authorization: Bearer $TYK_KEY" \
  -F "model=aurora" \
  -F "files=@initial_state_20260101.json" \
  -F "loop_mode=rollout_steps" \
  -F "steps=4" | jq .
```

---

### Step 3: Poll Task Status, Progress, ETA & Live Error Log (`GET /v1/tasks/{task_id}`)

```bash
TASK_ID="<task_id_from_post>"

# Poll task status (also returns Retry-After HTTP header while active)
curl -sS "$GW_URL/v1/tasks/$TASK_ID" \
  -H "Authorization: Bearer $TYK_KEY" | jq .
```

#### Polling Rules for AI Agents:
1. Check `status`:
   - Active states: `"queued"`, `"starting_model"`, `"running"`.
   - Terminal states: `"succeeded"`, `"succeeded_with_errors"`, `"failed"`, `"cancelled"`, `"expired"`.
2. While in an active state, sleep for the HTTP `Retry-After` header (or `eta_seconds` capped to `5..60` seconds) before polling again — never poll in a tight sub-second loop.
3. If `has_errors` is `true`:
   - Inspect `error_summary`, `errors[]`, and `error_log_tail` in the poll response, OR
   - Fetch the complete plain-text traceback log via `GET /v1/tasks/$TASK_ID/error.log` (or `GET /v1/tasks/$TASK_ID?include_error_log=true`).

---

### Step 4: Download Outputs (Incremental Per-File or Complete `.zip` Bundle)

```bash
# 1. Download an individual output file as soon as that file's status == "succeeded"
curl -sS -L "$GW_URL/v1/tasks/$TASK_ID/files/out/0000_paper1.md" \
  -H "Authorization: Bearer $TYK_KEY" -o paper1.md

# 2. Download the complete result ZIP (contains out/*, manifest.json, and error.log if any errors occurred)
curl -sS -L "$GW_URL/v1/tasks/$TASK_ID/result" \
  -H "Authorization: Bearer $TYK_KEY" -o "${TASK_ID}.zip"

# 3. Or fetch the JSON result summary + inline text outputs
curl -sS "$GW_URL/v1/tasks/$TASK_ID/result?format=json" \
  -H "Authorization: Bearer $TYK_KEY" | jq .
```

---

### Step 5: Cancel or Delete a Task Early (`DELETE /v1/tasks/{task_id}`)

```bash
curl -sS -X DELETE "$GW_URL/v1/tasks/$TASK_ID" \
  -H "Authorization: Bearer $TYK_KEY" | jq .
```

---

## 3. Endpoint Summary

| Method & Path | Description |
|---|---|
| `GET /v1/models?all=true` | List all models (including `mode: "task"` models like `glm-ocr`), with top-level `"mode": "api" \| "task" \| "both"` and `"tasks"` metadata |
| `GET /v1/models?tasks=true` | List only task-capable models (`mode in ("task", "both")`) |
| `GET /v1/models/{model_id}` | Full model card entry + live status + `input_map`, `custom_params`, `output_map`, and `tasks` metadata for one model |
| `GET /v1/tasks/models` | List all task-capable models with full self-describing task `properties`, `envelope_properties`, `default_params`, and `examples` |
| `GET /v1/tasks/models/{model_id}` | Detailed task schema, parameters, defaults, limits, and `curl` examples for `{model_id}` |
| `POST /v1/tasks` | Submit a new task (`multipart/form-data` or `application/json`) |
| `GET /v1/tasks` | List caller's tasks (`?status=`, `?limit=`) |
| `GET /v1/tasks/{task_id}` | Poll task status, per-file progress, `eta_seconds`, `come_back_at`, `has_errors`, `errors[]`, `error_log_tail` (`?include_error_log=true`) |
| `GET /v1/tasks/{task_id}/error.log` | Download full plain-text `error.log` (timestamps, request parameters, HTTP status codes, upstream tracebacks) |
| `GET /v1/tasks/{task_id}/result` | Download `<task_id>.zip` (`?format=zip`, default) or JSON manifest + outputs (`?format=json`) |
| `GET /v1/tasks/{task_id}/files/out/{filename}` | Download a single completed output file immediately |
| `DELETE /v1/tasks/{task_id}` | Cancel an active task or delete task artifacts immediately |
