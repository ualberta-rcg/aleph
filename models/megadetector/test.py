"""megadetector gateway test — comprehensive.

Run externally via the gateway VIP + Tyk auth (preferred):
  GW_URL=http://<GATEWAY_VIP> TYK_KEY=<key> python3 models/megadetector/test.py

Run inside the gateway pod (legacy, no auth needed):
  cat models/megadetector/test.py | \
    kubectl exec -i -n models deploy/model-gateway -c gateway -- python3 -
"""
import base64, httpx, os, struct, time, zlib

G = os.environ.get("GW_URL", "http://localhost:8080")
_KEY = os.environ.get("TYK_KEY")
_HEADERS = {"Authorization": f"Bearer {_KEY}"} if _KEY else {}
MODEL = "megadetector"
EP = f"{G}/v1/vision/detect"
results = []


def record(icon, status, name, detail):
    results.append((icon, status, name, detail))
    print(f"[{icon}] {status} | {name}: {detail}", flush=True)


def png_b64(seed=7, w=640, h=480):
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


def call(body, timeout=300):
    return httpx.post(EP, json=body, timeout=timeout, headers=_HEADERS)


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
            ok = isinstance(d.get("detections"), list)
            record("PASS" if ok else "FAIL", 200, "wake",
                   f"attempts={attempt+1}")
            return
        if r.status_code == 503:
            time.sleep(4)
            continue
        record("FAIL", r.status_code, "wake", r.text[:120])
        return
    record("FAIL", 503, "wake", "timed out")


def checks():
    img = png_b64(42)

    # 2. single image — detections is nested array with 1 entry
    r = call({"model": MODEL, "image": img})
    d = r.json() if r.status_code == 200 else {}
    dets = d.get("detections", [])
    record("PASS" if r.status_code == 200 and isinstance(dets, list) and len(dets) == 1 else "FAIL",
           r.status_code, "single image nested array", f"len={len(dets)}")

    # 3. model echo
    record("PASS" if d.get("model") == MODEL else "FAIL",
           r.status_code, "model echo", d.get("model", "missing"))

    # 4. threshold echoed back
    record("PASS" if isinstance(d.get("threshold"), (int, float)) else "FAIL",
           r.status_code, "threshold echoed", f"threshold={d.get('threshold')}")

    # 5-8. detection field validation
    if dets and dets[0]:
        det = dets[0][0]
        has_fields = all(k in det for k in ("category", "bbox", "conf"))
        record("PASS" if has_fields else "FAIL",
               r.status_code, "detection fields", f"keys={list(det.keys())}")
        record("PASS" if det["category"] in ("animal", "human", "vehicle") else "FAIL",
               r.status_code, "category valid", det["category"])
        record("PASS" if isinstance(det["bbox"], list) and len(det["bbox"]) == 4 else "FAIL",
               r.status_code, "bbox format [x,y,w,h]", f"bbox={det['bbox']}")
        record("PASS" if 0 <= det["conf"] <= 1 else "FAIL",
               r.status_code, "conf range 0-1", f"conf={det['conf']:.3f}")
    else:
        for name in ("detection fields", "category valid", "bbox format [x,y,w,h]", "conf range 0-1"):
            record("PASS", r.status_code, name, "0 dets (noise image, ok)")

    # 9. batch mode — images array
    r2 = call({"model": MODEL, "images": [png_b64(10), png_b64(11)]})
    d2 = r2.json() if r2.status_code == 200 else {}
    dets2 = d2.get("detections", [])
    record("PASS" if r2.status_code == 200 and len(dets2) == 2 else "FAIL",
           r2.status_code, "batch 2 images", f"detections_count={len(dets2)}")

    # 10. threshold parameter
    r3 = call({"model": MODEL, "image": img, "threshold": 0.9})
    d3 = r3.json() if r3.status_code == 200 else {}
    record("PASS" if r3.status_code == 200 and d3.get("threshold") == 0.9 else "FAIL",
           r3.status_code, "threshold=0.9 used", f"threshold={d3.get('threshold')}")

    # 11. small image
    r4 = call({"model": MODEL, "image": png_b64(20, 128, 128)})
    record("PASS" if r4.status_code == 200 else "FAIL",
           r4.status_code, "small image 128x128", "")

    # 12. sequential 5-image batch
    batch_ok = True
    for i in range(5):
        rb = call({"model": MODEL, "image": png_b64(100 + i, 320, 240)})
        if rb.status_code != 200:
            batch_ok = False
            break
    record("PASS" if batch_ok else "FAIL",
           200 if batch_ok else rb.status_code,
           "sequential 5-image batch", "all 200" if batch_ok else f"failed i={i}")

    # 13. guard — bad model
    rg1 = httpx.post(EP, json={"model": "fake-nope-999", "image": png_b64(3)}, timeout=60, headers=_HEADERS)
    record("EXP" if rg1.status_code == 404 else "FAIL",
           rg1.status_code, "guard bad model", rg1.text[:80])

    # 14. guard — missing image
    rg2 = httpx.post(EP, json={"model": MODEL}, timeout=60, headers=_HEADERS)
    record("EXP" if rg2.status_code >= 400 else "FAIL",
           rg2.status_code, "guard missing image", rg2.text[:80])

    # 15. guard — empty image
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
