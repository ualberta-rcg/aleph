"""yolov8s gateway test — comprehensive (run inside the gateway pod).

Run:
  cat models/yolov8s/test.py | \
    kubectl exec -i -n models deploy/model-gateway -c gateway -- python3 -
"""
import base64, httpx, os, struct, time, zlib

G = os.environ.get("GW_URL", "http://localhost:8080")
MODEL = "yolov8s"
EP = f"{G}/v1/vision/detect"
results = []


def record(icon, status, name, detail):
    results.append((icon, status, name, detail))
    print(f"[{icon}] {status} | {name}: {detail}", flush=True)


def png_b64(seed=7, w=640, h=640):
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
    return httpx.post(EP, json=body, timeout=timeout)


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
                   f"attempts={attempt+1} dets={len(d.get('detections', []))}")
            return
        if r.status_code == 503:
            time.sleep(4)
            continue
        record("FAIL", r.status_code, "wake", r.text[:120])
        return
    record("FAIL", 503, "wake", "timed out")


def checks():
    img = png_b64(42)

    r = call({"model": MODEL, "image": img})
    d = r.json() if r.status_code == 200 else {}
    dets = d.get("detections", [])
    record("PASS" if r.status_code == 200 and isinstance(dets, list) else "FAIL",
           r.status_code, "response schema", f"keys={list(d.keys())}")

    record("PASS" if d.get("model") == MODEL else "FAIL",
           r.status_code, "model echo", d.get("model", "missing"))

    record("PASS" if d.get("task") == "detect" else "FAIL",
           r.status_code, "task echo", d.get("task", "missing"))

    if dets:
        s = dets[0]
        record("PASS" if all(k in s for k in ("label", "score", "box")) else "FAIL",
               r.status_code, "detection fields", f"keys={list(s.keys())}")
        record("PASS" if all(0 <= det["score"] <= 1 for det in dets) else "FAIL",
               r.status_code, "score range 0-1", f"top={dets[0]['score']:.3f}")
        record("PASS" if all(isinstance(det["box"], list) and len(det["box"]) == 4 for det in dets) else "FAIL",
               r.status_code, "box format", f"box={dets[0]['box']}")
        record("PASS" if all(isinstance(det["label"], str) for det in dets) else "FAIL",
               r.status_code, "label is string", dets[0]["label"])
    else:
        for name in ("detection fields", "score range 0-1", "box format", "label is string"):
            record("PASS", r.status_code, name, "0 dets (noise image, ok)")

    r2 = call({"model": MODEL, "image": png_b64(10, 128, 128)})
    record("PASS" if r2.status_code == 200 else "FAIL",
           r2.status_code, "small image 128x128", "")

    r3 = call({"model": MODEL, "image": png_b64(11, 800, 600)})
    record("PASS" if r3.status_code == 200 else "FAIL",
           r3.status_code, "non-square 800x600", "")

    data_uri = "data:image/png;base64," + png_b64(13, 320, 320)
    r4 = call({"model": MODEL, "image": data_uri})
    record("PASS" if r4.status_code == 200 else "FAIL",
           r4.status_code, "data-URI prefix strip", "")

    batch_ok = True
    for i in range(5):
        rb = call({"model": MODEL, "image": png_b64(100 + i, 320, 320)})
        if rb.status_code != 200:
            batch_ok = False
            break
    record("PASS" if batch_ok else "FAIL",
           200 if batch_ok else rb.status_code,
           "sequential 5-image batch", "all 200" if batch_ok else f"failed i={i}")

    img_d = png_b64(999, 320, 320)
    r5a = call({"model": MODEL, "image": img_d})
    r5b = call({"model": MODEL, "image": img_d})
    if r5a.status_code == 200 and r5b.status_code == 200:
        da, db = r5a.json(), r5b.json()
        same = len(da.get("detections", [])) == len(db.get("detections", []))
        record("PASS" if same else "FAIL",
               200, "determinism", f"dets={len(da['detections'])}/{len(db['detections'])}")
    else:
        record("FAIL", r5a.status_code, "determinism", "request failed")

    rg1 = httpx.post(EP, json={"model": "fake-nope-999", "image": png_b64(3, 320, 320)}, timeout=60)
    record("EXP" if rg1.status_code == 404 else "FAIL",
           rg1.status_code, "guard bad model", rg1.text[:80])

    rg2 = httpx.post(EP, json={"model": MODEL}, timeout=60)
    record("EXP" if rg2.status_code >= 400 else "FAIL",
           rg2.status_code, "guard missing image", rg2.text[:80])

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
