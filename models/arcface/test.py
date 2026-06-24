"""arcface gateway test — comprehensive (run inside the gateway pod).

512-dim ArcFace ResNet-100 face embeddings via /v1/vision/face.

Run:
  cat models/arcface/test.py | \
    kubectl exec -i -n models deploy/model-gateway -c gateway -- python3 -
"""
import base64, httpx, math, os, struct, time, zlib

G = os.environ.get("GW_URL", "http://localhost:8080")
MODEL = "arcface-resnet100"
EP = f"{G}/v1/vision/face"
EXP_DIM = 512
results = []


def record(icon, status, name, detail):
    results.append((icon, status, name, detail))
    print(f"[{icon}] {status} | {name}: {detail}", flush=True)


def png_b64(seed=7, w=112, h=112):
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


def _cos(a, b):
    da = math.sqrt(sum(x * x for x in a))
    db = math.sqrt(sum(y * y for y in b))
    return sum(x * y for x, y in zip(a, b)) / (da * db) if da and db else 0.0


def _vec(d):
    return d.get("embedding") or d.get("embeddings") or []


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
            v = _vec(d)
            ok = isinstance(v, list) and len(v) == EXP_DIM
            record("PASS" if ok else "FAIL", 200, "wake",
                   f"attempts={attempt+1} dim={len(v)}")
            return
        if r.status_code in (503, 502, 504, 404):
            time.sleep(4)
            continue
        record("FAIL", r.status_code, "wake", r.text[:120])
        return
    record("FAIL", 503, "wake", "timed out")


def checks():
    img = png_b64(42)

    r = call({"model": MODEL, "image": img})
    d = r.json() if r.status_code == 200 else {}
    v = _vec(d)
    record("PASS" if r.status_code == 200 and len(v) == EXP_DIM else "FAIL",
           r.status_code, "response schema + dim", f"dim={len(v)}")

    record("PASS" if d.get("model") == MODEL else "FAIL",
           r.status_code, "model echo", d.get("model", "missing"))

    record("PASS" if d.get("task") == "face" else "FAIL",
           r.status_code, "task echo", d.get("task", "missing"))

    all_float = all(isinstance(x, (int, float)) for x in v) if v else False
    record("PASS" if all_float else "FAIL",
           r.status_code, "all values floats", "")

    non_zero = any(abs(x) > 1e-8 for x in v) if v else False
    record("PASS" if non_zero else "FAIL",
           r.status_code, "embedding non-zero", "")

    # L2-normalized check (should be ~1.0)
    if v:
        norm = math.sqrt(sum(x * x for x in v))
        record("PASS" if 0.95 <= norm <= 1.05 else "FAIL",
               r.status_code, "L2 norm ~1.0", f"norm={norm:.4f}")
    else:
        record("FAIL", r.status_code, "L2 norm ~1.0", "no embedding")

    # distinctness
    r2 = call({"model": MODEL, "image": png_b64(99)})
    if r.status_code == 200 and r2.status_code == 200:
        v2 = _vec(r2.json())
        c = _cos(v, v2)
        record("PASS" if c < 0.999 else "FAIL",
               200, "distinctness", f"cos={c:.5f}")
    else:
        record("FAIL", r2.status_code, "distinctness", "request failed")

    # determinism
    r3 = call({"model": MODEL, "image": img})
    if r.status_code == 200 and r3.status_code == 200:
        v3 = _vec(r3.json())
        c2 = _cos(v, v3)
        record("PASS" if c2 > 0.9999 else "FAIL",
               200, "determinism", f"cos={c2:.5f}")
    else:
        record("FAIL", r3.status_code, "determinism", "request failed")

    # different size image
    r4 = call({"model": MODEL, "image": png_b64(10, 224, 224)})
    d4 = r4.json() if r4.status_code == 200 else {}
    record("PASS" if len(_vec(d4)) == EXP_DIM else "FAIL",
           r4.status_code, "different size 224x224", "")

    # data-URI prefix
    data_uri = "data:image/png;base64," + png_b64(13)
    r5 = call({"model": MODEL, "image": data_uri})
    record("PASS" if r5.status_code == 200 else "FAIL",
           r5.status_code, "data-URI prefix strip", "")

    # sequential batch
    batch_ok = True
    for i in range(5):
        rb = call({"model": MODEL, "image": png_b64(100 + i)})
        if rb.status_code != 200:
            batch_ok = False
            break
    record("PASS" if batch_ok else "FAIL",
           200 if batch_ok else rb.status_code,
           "sequential 5-image batch", "all 200" if batch_ok else f"failed i={i}")

    rg1 = httpx.post(EP, json={"model": "fake-nope-999", "image": png_b64(3)}, timeout=60)
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
