"""efficientnet-b0 gateway test (run inside the gateway pod).

Run:
  cat models/efficientnet-b0/test.py | \
    kubectl exec -i -n models deploy/model-gateway -c gateway -- python3 -
"""
import base64
import httpx
import os
import struct
import time
import zlib

G = os.environ.get("GW_URL", "http://localhost:8080")
MODEL = os.environ.get("MODEL", "efficientnet-b0")
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
    png = b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", ihdr) + chunk(b"IDAT", zlib.compress(bytes(raw))) + chunk(b"IEND", b"")
    return base64.b64encode(png).decode()


def call(body, timeout=240):
    return httpx.post(f"{G}/v1/vision/classify", json=body, timeout=timeout)


def wake():
    body = {"model": MODEL, "image": png_b64(1), "top_k": 5}
    for attempt in range(90):
        try:
            r = call(body, timeout=120)
        except Exception:
            time.sleep(4)
            continue
        if r.status_code == 200:
            d = r.json()
            preds = d.get("predictions", [])
            ok = isinstance(preds, list) and len(preds) > 0
            record("PASS" if ok else "FAIL", 200, "WAKE + predictions", f"attempts={attempt+1} preds={len(preds)}")
            return
        if r.status_code == 503:
            time.sleep(4)
            continue
        record("FAIL", r.status_code, "WAKE + predictions", r.text[:120])
        return
    record("FAIL", 503, "WAKE + predictions", "timed out waiting for warm model")


def checks():
    r = call({"model": MODEL, "image": png_b64(2), "top_k": 3})
    d = r.json() if r.headers.get("content-type", "").startswith("application/json") else {}
    preds = d.get("predictions", [])
    ok = r.status_code == 200 and isinstance(preds, list) and len(preds) == 3
    if ok:
        s = preds[0]
        ok = all(k in s for k in ("rank", "class_id", "label", "score"))
    record("PASS" if ok else "FAIL", r.status_code, "classify response shape", f"predictions={len(preds)}")

    rm = httpx.post(f"{G}/v1/vision/classify", json={"model": "fake-vision-nope", "image": png_b64(3)}, timeout=60)
    record("EXP" if rm.status_code == 404 else "FAIL", rm.status_code, "guard bad model", rm.text[:80])

    rb = httpx.post(f"{G}/v1/vision/classify", json={"model": MODEL}, timeout=60)
    record("EXP" if rb.status_code >= 400 else "FAIL", rb.status_code, "guard malformed", rb.text[:80])


def summary():
    p = sum(1 for x in results if x[0] == "PASS")
    e = sum(1 for x in results if x[0] == "EXP")
    f = sum(1 for x in results if x[0] in ("FAIL", "ERR"))
    print(f"\nResults: {p} passed, {e} expected, {f} failed of {len(results)}", flush=True)
    return 0 if f == 0 else 1


if __name__ == "__main__":
    wake()
    checks()
    raise SystemExit(summary())
