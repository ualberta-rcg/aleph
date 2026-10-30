"""glm-ocr comprehensive gateway & /v1/tasks test battery.

Exercises the asynchronous task surface (/v1/tasks) and GLM-OCR capabilities:
  1. Catalog & Introspection:
     - Absent from default chat-only GET /v1/models (mode="task")
     - Present in GET /v1/models?all=true with mode="task", type="ocr"
     - Present in GET /v1/tasks/models/glm-ocr with properties, defaults, examples
     - Present on GET / web page with .task-card styling and async task badge
  2. Guardrail:
     - Direct synchronous POST /v1/chat/completions to glm-ocr returns 400 task_only_model
  3. WAKE + Single Image OCR ("Text Recognition:"):
     - Wakes predictor 0->1 automatically via /v1/tasks and extracts text
  4. Table Recognition ("Table Recognition:") & Formula Recognition ("Formula Recognition:")
  5. Multi-PDF Sequential Page Loop (1 -> 2 -> ... -> N) + file_params page range + .zip result
  6. Partial Failure Resilience (continue_on_item_error=true) + live /v1/tasks/{id}/error.log
  7. Task Cleanup (DELETE /v1/tasks/{id})

Run externally via the gateway VIP + Tyk auth:
  GW_URL=http://<GATEWAY_VIP> TYK_KEY=<key> python3 models/glm-ocr/test.py

Run inside the gateway pod:
  cat models/glm-ocr/test.py | \\
      kubectl exec -i -n models deploy/model-gateway -c gateway -- python3 -
"""
from __future__ import annotations

import io
import json
import os
import sys
import time
import zipfile
import httpx
from PIL import Image, ImageDraw

G = os.environ.get("GW_URL", "http://localhost:8080").rstrip("/")
_KEY = os.environ.get("TYK_KEY", "test-glm-ocr-key")
_HEADERS = {"Authorization": f"Bearer {_KEY}"}
MODEL = os.environ.get("MODEL", "glm-ocr")
results: list[tuple[str, int, str, str]] = []


def record(icon: str, status: int, name: str, detail: str) -> None:
    results.append((icon, status, name, detail))
    print(f"[{icon}] {status} | {name}: {detail}", flush=True)


def make_text_png(lines: list[str], size: tuple[int, int] = (640, 240)) -> bytes:
    img = Image.new("RGB", size, color=(255, 255, 255))
    draw = ImageDraw.Draw(img)
    y = 30
    for line in lines:
        draw.text((30, y), line, fill=(0, 0, 0))
        y += 45
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


def make_pdf_bytes(page_texts: list[str]) -> bytes:
    pages: list[Image.Image] = []
    for txt in page_texts:
        img = Image.new("RGB", (640, 320), color=(255, 255, 255))
        draw = ImageDraw.Draw(img)
        draw.text((40, 60), txt, fill=(0, 0, 0))
        pages.append(img)
    buf = io.BytesIO()
    pages[0].save(buf, format="PDF", save_all=True, append_images=pages[1:])
    return buf.getvalue()


def poll_task(task_id: str, timeout_s: float = 480.0) -> dict:
    deadline = time.time() + timeout_s
    last = {}
    while time.time() < deadline:
        r = httpx.get(f"{G}/v1/tasks/{task_id}", headers=_HEADERS, timeout=30.0)
        if r.status_code == 200:
            last = r.json()
            if last.get("status") in ("completed", "failed", "cancelled"):
                return last
        time.sleep(2.5)
    return last


# ── 1. Catalog & Introspection ────────────────────────────────────────────────
def test_catalog() -> None:
    r_chat = httpx.get(f"{G}/v1/models", headers=_HEADERS, timeout=15.0)
    chat_ids = [m["id"] for m in (r_chat.json().get("data") or [])] if r_chat.status_code == 200 else []
    ok_absent = MODEL not in chat_ids
    record("PASS" if ok_absent else "FAIL", r_chat.status_code, "GET /v1/models (chat-only excludes task model)", f"present={MODEL in chat_ids}")

    r_all = httpx.get(f"{G}/v1/models?all=true", headers=_HEADERS, timeout=15.0)
    entry = next((m for m in (r_all.json().get("data") or []) if m.get("id") == MODEL), None) if r_all.status_code == 200 else None
    ok_all = bool(entry and entry.get("mode") == "task" and entry.get("type") == "ocr" and (entry.get("tasks") or {}).get("enabled") is True)
    record(
        "PASS" if ok_all else "FAIL",
        r_all.status_code,
        "GET /v1/models?all=true (includes glm-ocr mode=task)",
        f"mode={entry.get('mode') if entry else None} loop_mode={(entry or {}).get('tasks', {}).get('loop_mode')}",
    )

    r_tm = httpx.get(f"{G}/v1/tasks/models/{MODEL}", headers=_HEADERS, timeout=15.0)
    tm = r_tm.json() if r_tm.status_code == 200 else {}
    tinfo = tm.get("tasks") or {}
    props = tinfo.get("properties") or {}
    ok_tm = r_tm.status_code == 200 and "dpi" in props and "prompt" in props and "pages" in props
    record("PASS" if ok_tm else "FAIL", r_tm.status_code, "GET /v1/tasks/models/glm-ocr introspection", f"props={sorted(props.keys())}")

    r_web = httpx.get(f"{G}/", timeout=15.0)
    ok_web = r_web.status_code == 200 and MODEL in r_web.text and "task-card" in r_web.text and "async task" in r_web.text
    record("PASS" if ok_web else "FAIL", r_web.status_code, "GET / web catalog task-card & badge", f"len={len(r_web.text)}")


# ── 2. Guardrail: sync /v1/chat/completions rejected for mode="task" ──────────
def test_sync_guardrail() -> None:
    r = httpx.post(
        f"{G}/v1/chat/completions",
        headers=_HEADERS,
        json={"model": MODEL, "messages": [{"role": "user", "content": "hi"}]},
        timeout=15.0,
    )
    ok = r.status_code == 400 and "task_only_model" in r.text
    record("PASS" if ok else "FAIL", r.status_code, "POST /v1/chat/completions guardrail (400 task_only_model)", r.text[:120])


# ── 3. WAKE + Single Image OCR ("Text Recognition:") ─────────────────────────
def test_wake_and_single_image() -> None:
    png_bytes = make_text_png(["ALEPH DOCUMENT OCR 2026", "VULCAN CLUSTER TEST PASS"])
    r = httpx.post(
        f"{G}/v1/tasks",
        headers=_HEADERS,
        data={"model": MODEL, "prompt": "Text Recognition:", "max_tokens": "512"},
        files=[("files", ("sample1.png", png_bytes, "image/png"))],
        timeout=30.0,
    )
    if r.status_code != 202:
        record("FAIL", r.status_code, "WAKE + single image OCR submit", r.text[:120])
        return
    tid = r.json()["task_id"]
    final = poll_task(tid, timeout_s=480.0)
    status = final.get("status")
    out_files = final.get("output_files") or []
    md_resp = httpx.get(f"{G}/v1/tasks/{tid}/files/out/sample1.md", headers=_HEADERS, timeout=15.0)
    md_text = md_resp.text.strip() if md_resp.status_code == 200 else ""
    ok = status == "completed" and final.get("completed_units") == 1 and len(md_text) > 0
    record("PASS" if ok else "FAIL", 200 if ok else 500, "WAKE + single image OCR ('Text Recognition:')", f"status={status} files={out_files} text={md_text[:80]!r}")
    httpx.delete(f"{G}/v1/tasks/{tid}", headers=_HEADERS, timeout=15.0)


# ── 4. Table & Formula Recognition Prompts ────────────────────────────────────
def test_table_and_formula_prompts() -> None:
    tbl_png = make_text_png(["Model     | Slice  | Mode", "glm-ocr   | 12GiB  | task"])
    r = httpx.post(
        f"{G}/v1/tasks",
        headers=_HEADERS,
        data={"model": MODEL, "prompt": "Table Recognition:", "repetition_penalty": "1.05"},
        files=[("files", ("table1.png", tbl_png, "image/png"))],
        timeout=30.0,
    )
    if r.status_code != 202:
        record("FAIL", r.status_code, "Table Recognition submit", r.text[:120])
        return
    tid = r.json()["task_id"]
    final = poll_task(tid, timeout_s=180.0)
    md_resp = httpx.get(f"{G}/v1/tasks/{tid}/files/out/table1.md", headers=_HEADERS, timeout=15.0)
    ok = final.get("status") == "completed" and md_resp.status_code == 200 and len(md_resp.text.strip()) > 0
    record("PASS" if ok else "FAIL", md_resp.status_code, "Table Recognition prompt + custom param", f"text={md_resp.text.strip()[:80]!r}")
    httpx.delete(f"{G}/v1/tasks/{tid}", headers=_HEADERS, timeout=15.0)

    eq_png = make_text_png(["E = mc^2 + alpha_0"])
    r2 = httpx.post(
        f"{G}/v1/tasks",
        headers=_HEADERS,
        data={"model": MODEL, "prompt": "Formula Recognition:"},
        files=[("files", ("formula1.png", eq_png, "image/png"))],
        timeout=30.0,
    )
    tid2 = r2.json()["task_id"]
    final2 = poll_task(tid2, timeout_s=180.0)
    md_resp2 = httpx.get(f"{G}/v1/tasks/{tid2}/files/out/formula1.md", headers=_HEADERS, timeout=15.0)
    ok2 = final2.get("status") == "completed" and md_resp2.status_code == 200 and len(md_resp2.text.strip()) > 0
    record("PASS" if ok2 else "FAIL", md_resp2.status_code, "Formula Recognition prompt", f"text={md_resp2.text.strip()[:80]!r}")
    httpx.delete(f"{G}/v1/tasks/{tid2}", headers=_HEADERS, timeout=15.0)


# ── 5. Multi-PDF Sequential Loop (1 -> 2 -> ... -> N) + file_params + .zip ───
def test_multi_pdf_and_zip() -> None:
    pdf1 = make_pdf_bytes(["PDF1 PAGE ONE CONTENT", "PDF1 PAGE TWO CONTENT"])
    pdf2 = make_pdf_bytes(["PDF2 PAGE ONE SELECTED", "PDF2 PAGE TWO SKIPPED"])
    r = httpx.post(
        f"{G}/v1/tasks",
        headers=_HEADERS,
        data={
            "model": MODEL,
            "dpi": "150",
            "prompt": "Text Recognition:",
            "file_params": json.dumps({"doc2.pdf": {"pages": "1", "dpi": 200}}),
        },
        files=[
            ("files", ("doc1.pdf", pdf1, "application/pdf")),
            ("files", ("doc2.pdf", pdf2, "application/pdf")),
        ],
        timeout=30.0,
    )
    if r.status_code != 202:
        record("FAIL", r.status_code, "Multi-PDF task submit", r.text[:120])
        return
    init_m = r.json()
    tid = init_m["task_id"]
    final = poll_task(tid, timeout_s=240.0)
    zresp = httpx.get(f"{G}/v1/tasks/{tid}/result", headers=_HEADERS, timeout=30.0)
    names: list[str] = []
    if zresp.status_code == 200:
        with zipfile.ZipFile(io.BytesIO(zresp.content), "r") as zf:
            names = sorted(zf.namelist())
    ok = (
        init_m.get("total_units") == 3
        and final.get("status") == "completed"
        and final.get("completed_units") == 3
        and "manifest.json" in names
        and "out/doc1.md" in names
        and "out/doc2.md" in names
    )
    record(
        "PASS" if ok else "FAIL",
        zresp.status_code,
        "Multi-PDF sequential loop (3 pages across 2 PDFs) + .zip bundle",
        f"total_units={init_m.get('total_units')} completed={final.get('completed_units')} zip={names}",
    )
    httpx.delete(f"{G}/v1/tasks/{tid}", headers=_HEADERS, timeout=15.0)


# ── 6. Corrupted PDF Mid-Batch -> error.log + continue_on_item_error=true ─────
def test_partial_failure_and_error_log() -> None:
    good_png = make_text_png(["VALID PAGE AFTER ERROR"])
    bad_pdf = b"NOT_A_VALID_PDF_HEADER_CORRUPT_BYTES"
    r = httpx.post(
        f"{G}/v1/tasks",
        headers=_HEADERS,
        data={"model": MODEL, "continue_on_item_error": "true"},
        files=[
            ("files", ("broken.pdf", bad_pdf, "application/pdf")),
            ("files", ("good.png", good_png, "image/png")),
        ],
        timeout=30.0,
    )
    if r.status_code != 202:
        record("FAIL", r.status_code, "Partial failure task submit", r.text[:120])
        return
    tid = r.json()["task_id"]
    final = poll_task(tid, timeout_s=180.0)
    err_resp = httpx.get(f"{G}/v1/tasks/{tid}/error.log", headers=_HEADERS, timeout=15.0)
    ok = (
        final.get("status") == "completed"
        and final.get("completed_units") == 1
        and final.get("failed_units") == 1
        and final.get("error_count") == 1
        and "broken.pdf" in err_resp.text
    )
    record(
        "PASS" if ok else "FAIL",
        err_resp.status_code,
        "Partial failure resilience + /v1/tasks/{id}/error.log",
        f"completed={final.get('completed_units')} failed={final.get('failed_units')} err_log_len={len(err_resp.text)}",
    )
    del_resp = httpx.delete(f"{G}/v1/tasks/{tid}", headers=_HEADERS, timeout=15.0)
    after_resp = httpx.get(f"{G}/v1/tasks/{tid}", headers=_HEADERS, timeout=15.0)
    ok_del = del_resp.status_code == 200 and after_resp.status_code == 404
    record("PASS" if ok_del else "FAIL", after_resp.status_code, "DELETE /v1/tasks/{id} cleanup", f"deleted={del_resp.json().get('deleted')}")


if __name__ == "__main__":
    test_catalog()
    test_sync_guardrail()
    test_wake_and_single_image()
    test_table_and_formula_prompts()
    test_multi_pdf_and_zip()
    test_partial_failure_and_error_log()

    passed = sum(1 for r in results if r[0] == "PASS")
    total = len(results)
    print(f"\n=== SUMMARY: {passed}/{total} PASSED ===", flush=True)
    sys.exit(0 if passed == total else 1)
