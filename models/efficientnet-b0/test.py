"""efficientnet-b0 gateway test — comprehensive (run inside the gateway pod).

Run:
  cat models/efficientnet-b0/test.py | \
    kubectl exec -i -n models deploy/model-gateway -c gateway -- python3 -
"""
import base64, httpx, os, struct, time, zlib

G = os.environ.get("GW_URL", "http://localhost:8080")
MODEL = "efficientnet-b0"
EP = f"{G}/v1/vision/classify"
results = []


def record(icon, status, name, detail):
    results.append((icon, status, name, detail))
    print(f"[{icon}] {status} | {name}: {detail}", flush=True)


def png_b64(seed=7, w=224, h=224):
    raw = bytearray()
    s = seed & 0x7FFFFFFF
    for _ in range(h):
        raw.append(0)
        for _ in range(w * 3):
            s = (1103515245 * s + 12345) & 0x7FFFFFFF
            raw.append(s % 256)

    def chunk(typ, data):
        body = struct.pack(">I", len(data)) + typ + data
        return body + struct.pack(">I", zlib.crc32(typ + data) & 0xFFFFFFFF)

    ihdr = struct.pack(">IIBBBBB", w, h, 8, 2, 0, 0, 0)
    png = (b"\x89PNG\r\n\x1a\n"
           + chunk(b"IHDR", ihdr)
           + chunk(b"IDAT", zlib.compress(bytes(raw)))
           + chunk(b"IEND", b""))
    return base64.b64encode(png).decode()


def call(body, timeout=240):
    return httpx.post(EP, json=body, timeout=timeout)


# ── 1. Wake ──────────────────────────────────────────────────────────
def wake():
    body = {"model": MODEL, "image": png_b64(1)}
    for attempt in range(90):
        try:
            r = call(body, timeout=120)
        except Exception:
            time.sleep(4)
            continue
        if r.status_code == 200:
            d = r.json()
            ok = isinstance(d.get("predictions"), list) and len(d["predictions"]) > 0
            record("PASS" if ok else "FAIL", 200, "wake",
                   f"attempts={attempt+1} preds={len(d.get('predictions', []))}")
            return
        if r.status_code == 503:
            time.sleep(4)
            continue
        record("FAIL", r.status_code, "wake", r.text[:120])
        return
    record("FAIL", 503, "wake", "timed out")


# ── 2-19. Checks ────────────────────────────────────────────────────
def checks():
    img = png_b64(42)

    # 2. basic response schema (default top_k=5)
    r = call({"model": MODEL, "image": img})
    d = r.json() if r.status_code == 200 else {}
    preds = d.get("predictions", [])
    record("PASS" if r.status_code == 200 and len(preds) == 5 else "FAIL",
           r.status_code, "default top_k=5", f"got {len(preds)} predictions")

    # 3. model echo
    record("PASS" if d.get("model") == MODEL else "FAIL",
           r.status_code, "model echo", d.get("model", "missing"))

    # 4. task echo
    record("PASS" if d.get("task") == "classify" else "FAIL",
           r.status_code, "task echo", d.get("task", "missing"))

    # 5. prediction fields
    if preds:
        s = preds[0]
        has_fields = all(k in s for k in ("rank", "class_id", "label", "score"))
        record("PASS" if has_fields else "FAIL",
               r.status_code, "prediction fields", f"keys={list(s.keys())}")

        # 6. score range 0-1
        scores_ok = all(0 <= p["score"] <= 1 for p in preds)
        record("PASS" if scores_ok else "FAIL",
               r.status_code, "score range 0-1",
               f"top={preds[0]['score']:.4f}")

        # 7. rank ordering
        ranks_ok = [p["rank"] for p in preds] == list(range(1, len(preds) + 1))
        record("PASS" if ranks_ok else "FAIL",
               r.status_code, "rank ordering", f"ranks={[p['rank'] for p in preds]}")

        # 8. label is string
        labels_ok = all(isinstance(p["label"], str) and len(p["label"]) > 0 for p in preds)
        record("PASS" if labels_ok else "FAIL",
               r.status_code, "label is string", preds[0]["label"])

        # 9. class_id is int in 0-999
        ids_ok = all(isinstance(p["class_id"], int) and 0 <= p["class_id"] <= 999 for p in preds)
        record("PASS" if ids_ok else "FAIL",
               r.status_code, "class_id 0-999", f"top={preds[0]['class_id']}")
    else:
        for name in ("prediction fields", "score range 0-1", "rank ordering", "label is string", "class_id 0-999"):
            record("FAIL", r.status_code, name, "no predictions returned")

    # 10. top_k=1
    r2 = call({"model": MODEL, "image": img, "top_k": 1})
    d2 = r2.json() if r2.status_code == 200 else {}
    record("PASS" if len(d2.get("predictions", [])) == 1 else "FAIL",
           r2.status_code, "top_k=1", f"got {len(d2.get('predictions', []))}")

    # 11. top_k=10
    r3 = call({"model": MODEL, "image": img, "top_k": 10})
    d3 = r3.json() if r3.status_code == 200 else {}
    record("PASS" if len(d3.get("predictions", [])) == 10 else "FAIL",
           r3.status_code, "top_k=10", f"got {len(d3.get('predictions', []))}")

    # 12. small image (32x32)
    r4 = call({"model": MODEL, "image": png_b64(10, 32, 32)})
    record("PASS" if r4.status_code == 200 else "FAIL",
           r4.status_code, "small image 32x32", "")

    # 13. large image (640x480)
    r5 = call({"model": MODEL, "image": png_b64(11, 640, 480)})
    record("PASS" if r5.status_code == 200 else "FAIL",
           r5.status_code, "large image 640x480", "")

    # 14. data-URI prefix
    data_uri = "data:image/png;base64," + png_b64(13)
    r6 = call({"model": MODEL, "image": data_uri})
    record("PASS" if r6.status_code == 200 else "FAIL",
           r6.status_code, "data-URI prefix strip", "")

    # 15. sequential 5-image batch
    batch_ok = True
    for i in range(5):
        rb = call({"model": MODEL, "image": png_b64(100 + i)})
        if rb.status_code != 200:
            batch_ok = False
            break
    record("PASS" if batch_ok else "FAIL",
           200 if batch_ok else rb.status_code,
           "sequential 5-image batch", "all 200" if batch_ok else f"failed i={i}")

    # 16. determinism — same image same results
    img_d = png_b64(999, 128, 128)
    r7a = call({"model": MODEL, "image": img_d, "top_k": 3})
    r7b = call({"model": MODEL, "image": img_d, "top_k": 3})
    if r7a.status_code == 200 and r7b.status_code == 200:
        pa, pb = r7a.json()["predictions"], r7b.json()["predictions"]
        same = [p["class_id"] for p in pa] == [p["class_id"] for p in pb]
        record("PASS" if same else "FAIL",
               200, "determinism same image", f"ids={[p['class_id'] for p in pa]}")
    else:
        record("FAIL", r7a.status_code, "determinism same image", "request failed")

    # 17. guard — bad model
    rg1 = httpx.post(EP, json={"model": "fake-nope-999", "image": png_b64(3)}, timeout=60)
    record("EXP" if rg1.status_code == 404 else "FAIL",
           rg1.status_code, "guard bad model", rg1.text[:80])

    # 18. guard — missing image
    rg2 = httpx.post(EP, json={"model": MODEL}, timeout=60)
    record("EXP" if rg2.status_code >= 400 else "FAIL",
           rg2.status_code, "guard missing image", rg2.text[:80])

    # 19. guard — empty image
    rg3 = call({"model": MODEL, "image": ""})
    record("EXP" if rg3.status_code >= 400 else "FAIL",
           rg3.status_code, "guard empty image", rg3.text[:80])


def summary():
    p = sum(1 for x in results if x[0] == "PASS")
    e = sum(1 for x in results if x[0] == "EXP")
    f = sum(1 for x in results if x[0] in ("FAIL", "ERR"))
    print(f"\nResults: {p} PASS, {e} EXP, {f} FAIL of {len(results)}", flush=True)
    return 0 if f == 0 else 1


if __name__ == "__main__":
    wake()
    checks()
    raise SystemExit(summary())
