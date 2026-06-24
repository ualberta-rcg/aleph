"""retinanet gateway test (run inside the gateway pod)."""
import base64
import httpx
import os
import struct
import time
import zlib

G = os.environ.get("GW_URL", "http://localhost:8080")
MODEL = os.environ.get("MODEL", "retinanet-resnet50")
results = []


def record(icon, status, name, detail):
    results.append((icon, status, name, detail))
    print(f"[{icon}] {status} | {name}: {detail}", flush=True)


def png_b64(seed=13, w=640, h=640):
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


def call(body, timeout=300):
    return httpx.post(f"{G}/v1/vision/detect", json=body, timeout=timeout)


def wake():
    for attempt in range(90):
        r = call({"model": MODEL, "image": png_b64(1)}, timeout=120)
        if r.status_code == 200:
            d = r.json()
            ok = isinstance(d.get("detections"), list)
            record("PASS" if ok else "FAIL", r.status_code, "WAKE + schema", f"attempts={attempt+1} dets={len(d.get('detections', []))}")
            return
        if r.status_code == 503:
            time.sleep(4)
            continue
        record("FAIL", r.status_code, "WAKE + schema", r.text[:120]); return
    record("FAIL", 503, "WAKE + schema", "timed out")


def checks():
    r = call({"model": MODEL, "image": png_b64(2)})
    d = r.json() if r.headers.get("content-type", "").startswith("application/json") else {}
    dets = d.get("detections", [])
    ok = r.status_code == 200 and isinstance(dets, list)
    if ok and dets:
        ok = all(k in dets[0] for k in ("label", "score", "box"))
    record("PASS" if ok else "FAIL", r.status_code, "detect response shape", f"detections={len(dets)}")
    rm = call({"model": "fake-vision-nope", "image": png_b64(3)}, timeout=60)
    record("EXP" if rm.status_code == 404 else "FAIL", rm.status_code, "guard bad model", rm.text[:80])


if __name__ == "__main__":
    wake(); checks()
    p = sum(1 for x in results if x[0] == "PASS"); e = sum(1 for x in results if x[0] == "EXP")
    f = sum(1 for x in results if x[0] == "FAIL")
    print(f"\nResults: {p} passed, {e} expected, {f} failed of {len(results)}", flush=True)
    raise SystemExit(0 if f == 0 else 1)
