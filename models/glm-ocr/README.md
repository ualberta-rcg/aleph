# GLM-OCR (`glm-ocr`)

**Source**: [`zai-org/GLM-OCR`](https://huggingface.co/zai-org/GLM-OCR) (0.9B parameters — CogViT vision encoder + GLM-0.5B language decoder, MIT License)  
**Mode**: `"task"` (Asynchronous Task System via `POST /v1/tasks`)  
**Engine**: `vllm/vllm-openai:v0.32.0` (`--dtype=bfloat16 --max-model-len=16384`)  
**GPU Footprint**: 1× L40S HAMi slice (`nvidia.com/gpu: "1"`, `nvidia.com/gpumem: "12288"` = 12 GiB), scale-to-zero (`0 -> 2` replicas, 15m idle retention)

---

## Overview

`glm-ocr` is a document understanding and OCR model designed for:
- **Document Text Recognition** (`"prompt": "Text Recognition:"` — default): converts PDF pages and document images into clean, layout-preserving Markdown.
- **Table Recognition** (`"prompt": "Table Recognition:"`): reconstructs complex multi-row/multi-column tables into HTML/Markdown tables.
- **Formula Recognition** (`"prompt": "Formula Recognition:"`): extracts mathematical equations as LaTeX.
- **Structured Information Extraction**: pass a custom JSON schema prompt to extract structured fields.

Because real-world OCR workloads involve multi-page PDFs and multi-document batches, `glm-ocr` is exposed as an **asynchronous task model (`mode: "task"`)** at `/v1/tasks`. One submission wakes the `glm-ocr` predictor once, renders PDF pages at the requested `dpi`, and processes `page_1 -> page_2 -> ... -> page_N` sequentially against the warm pod.

---

## Quickstart (`curl`)

### 1. Discover Model & Task Properties

```bash
curl -sS "https://inference.vulcan.alliancecan.ca/v1/tasks/models/glm-ocr" \
  -H "Authorization: Bearer $KEY" | jq
```

### 2. Submit 1..N PDFs or Images in One Task

```bash
TASK_ID=$(curl -sS -X POST https://inference.vulcan.alliancecan.ca/v1/tasks \
  -H "Authorization: Bearer $KEY" \
  -F model=glm-ocr \
  -F "files=@paper1.pdf" \
  -F "files=@paper2.pdf" \
  -F "dpi=200" \
  -F "prompt=Text Recognition:" \
  -F 'file_params={"paper2.pdf":{"pages":"1-5","dpi":300}}' | jq -r '.task_id')
echo "Task ID: $TASK_ID"
```

### 3. Poll Progress & ETA

```bash
curl -sS https://inference.vulcan.alliancecan.ca/v1/tasks/$TASK_ID \
  -H "Authorization: Bearer $KEY" | jq '{status, completed_units, total_units, eta_seconds, output_files, error_count}'
```

### 4. Download Results (`.zip` or Individual Page/Document Markdown)

```bash
# Download complete .zip bundle (manifest.json, out/*.md, out/*.json, error.log)
curl -sS -L https://inference.vulcan.alliancecan.ca/v1/tasks/$TASK_ID/result \
  -H "Authorization: Bearer $KEY" -o "${TASK_ID}.zip"

# Or fetch a single document's Markdown directly
curl -sS https://inference.vulcan.alliancecan.ca/v1/tasks/$TASK_ID/files/out/paper1.md \
  -H "Authorization: Bearer $KEY"
```
