"""zoobot gateway test (run inside the gateway pod).

Run:
  cat models/zoobot/test.py | \
    kubectl exec -i -n models deploy/model-gateway -c gateway -- python3 -
"""
import base64
import httpx
import math
import os
import struct
import time
import zlib

G = os.environ.get("GW_URL", "http://localhost:8080")
MODEL = os.environ.get("MODEL", "zoobot-15m")
EXP_DIM = 640
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


def emb(body, timeout=300):
    return httpx.post(f"{G}/v1/vision/embed", json=body, timeout=timeout)


def _cos(a, b):
    da = math.sqrt(sum(x * x for x in a))
    db = math.sqrt(sum(y * y for y in b))
    return sum(x * y for x, y in zip(a, b)) / (da * db) if da and db else 0.0


def wake():
    body = {"model": MODEL, "image": png_b64(1)}
    for attempt in range(90):
        try:
            r = emb(body, timeout=120)
        except Exception:
            time.sleep(4)
            continue
        if r.status_code == 200:
            d = r.json()
            v = d.get("embedding", [])
            ok = isinstance(v, list) and len(v) == EXP_DIM
            record("PASS" if ok else "FAIL", 200, "WAKE + dim", f"attempts={attempt+1} dim={len(v)}")
            return
        if r.status_code == 503:
            time.sleep(4)
            continue
        record("FAIL", r.status_code, "WAKE + dim", r.text[:120])
        return
    record("FAIL", 503, "WAKE + dim", "timed out waiting for warm model")


def checks():
    r1 = emb({"model": MODEL, "image": png_b64(10)})
    r2 = emb({"model": MODEL, "image": png_b64(20)})
    d1 = r1.json() if r1.status_code == 200 else {}
    d2 = r2.json() if r2.status_code == 200 else {}
    v1, v2 = d1.get("embedding", []), d2.get("embedding", [])
    ok = r1.status_code == 200 and r2.status_code == 200 and len(v1) == EXP_DIM and len(v2) == EXP_DIM
    if ok:
        c = _cos(v1, v2)
        ok = c < 0.999
        record("PASS" if ok else "FAIL", 200, "distinctness", f"cos={c:.5f}")
    else:
        record("FAIL", r1.status_code, "distinctness", "embedding request failed")

    rm = emb({"model": "fake-vision-nope", "image": png_b64(3)}, timeout=60)
    record("EXP" if rm.status_code == 404 else "FAIL", rm.status_code, "guard bad model", rm.text[:80])

    rb = emb({"model": MODEL}, timeout=60)
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
