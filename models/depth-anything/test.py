"""depth-anything gateway test (run inside the gateway pod).

Run:
  cat models/depth-anything/test.py | \
    kubectl exec -i -n models deploy/model-gateway -c gateway -- python3 -
"""
import base64
import httpx
import os
import struct
import time
import zlib

G = os.environ.get("GW_URL", "http://localhost:8080")
MODEL = os.environ.get("MODEL", "depth-anything-v2")
results = []


def record(icon, status, name, detail):
    results.append((icon, status, name, detail))
    print(f"[{icon}] {status} | {name}: {detail}", flush=True)


def png_b64(seed=7, w=320, h=192):
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
    return base64.b64encode(png).decode(), w, h


def call(body, timeout=300):
    return httpx.post(f"{G}/v1/vision/depth", json=body, timeout=timeout)


def wake():
    b64, w, h = png_b64(1)
    body = {"model": MODEL, "image": b64}
    for attempt in range(90):
        try:
            r = call(body, timeout=120)
        except Exception:
            time.sleep(4)
            continue
        if r.status_code == 200:
            d = r.json()
            ok = "depth_png_base64" in d and d.get("width") == w and d.get("height") == h
            record("PASS" if ok else "FAIL", 200, "WAKE + depth payload", f"attempts={attempt+1} size={d.get('width')}x{d.get('height')}")
            return
        if r.status_code == 503:
            time.sleep(4)
            continue
        record("FAIL", r.status_code, "WAKE + depth payload", r.text[:120])
        return
    record("FAIL", 503, "WAKE + depth payload", "timed out waiting for warm model")


def checks():
    b64, _, _ = png_b64(2)
    r = call({"model": MODEL, "image": b64})
    d = r.json() if r.headers.get("content-type", "").startswith("application/json") else {}
    ok = (
        r.status_code == 200
        and isinstance(d.get("depth_grid_64"), list)
        and "stats" in d
        and isinstance(d.get("depth_png_base64"), str)
    )
    record("PASS" if ok else "FAIL", r.status_code, "depth response shape", f"keys={sorted(d.keys()) if d else []}")

    rm = httpx.post(f"{G}/v1/vision/depth", json={"model": "fake-vision-nope", "image": b64}, timeout=60)
    record("EXP" if rm.status_code == 404 else "FAIL", rm.status_code, "guard bad model", rm.text[:80])

    rb = httpx.post(f"{G}/v1/vision/depth", json={"model": MODEL}, timeout=60)
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
