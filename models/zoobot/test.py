"""zoobot gateway test — comprehensive.

Run externally via the gateway VIP + Tyk auth (preferred):
  GW_URL=http://<GATEWAY_VIP> TYK_KEY=<key> python3 models/zoobot/test.py

Run inside the gateway pod (legacy, no auth needed):
  cat models/zoobot/test.py | \
    kubectl exec -i -n models deploy/model-gateway -c gateway -- python3 -
"""
import base64, httpx, math, os, struct, time, zlib

G = os.environ.get("GW_URL", "http://localhost:8080")
_KEY = os.environ.get("TYK_KEY")
_HEADERS = {"Authorization": f"Bearer {_KEY}"} if _KEY else {}
MODEL = "zoobot-15m"
EP = f"{G}/v1/vision/embed"
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
    png = (b"\x89PNG\r\n\x1a\n"
           + chunk(b"IHDR", ihdr)
           + chunk(b"IDAT", zlib.compress(bytes(raw)))
           + chunk(b"IEND", b""))
    return base64.b64encode(png).decode()


def call(body, timeout=300):
    return httpx.post(EP, json=body, timeout=timeout, headers=_HEADERS)


def _cos(a, b):
    da = math.sqrt(sum(x * x for x in a))
    db = math.sqrt(sum(y * y for y in b))
    return sum(x * y for x, y in zip(a, b)) / (da * db) if da and db else 0.0


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
            v = d.get("embedding", [])
            ok = isinstance(v, list) and len(v) == EXP_DIM
            record("PASS" if ok else "FAIL", 200, "wake",
                   f"attempts={attempt+1} dim={len(v)}")
            return
        if r.status_code == 503:
            time.sleep(4)
            continue
        record("FAIL", r.status_code, "wake", r.text[:120])
        return
    record("FAIL", 503, "wake", "timed out")


# ── 2-18. Checks ────────────────────────────────────────────────────
def checks():
    img = png_b64(42)

    # 2. response schema
    r = call({"model": MODEL, "image": img})
    d = r.json() if r.status_code == 200 else {}
    expected_keys = {"model", "task", "embedding", "dim"}
    has_keys = expected_keys.issubset(set(d.keys()))
    record("PASS" if r.status_code == 200 and has_keys else "FAIL",
           r.status_code, "response schema", f"keys={sorted(d.keys())}")

    # 3. model echo
    record("PASS" if d.get("model") == MODEL else "FAIL",
           r.status_code, "model echo", d.get("model", "missing"))

    # 4. task echo
    record("PASS" if d.get("task") == "embed" else "FAIL",
           r.status_code, "task echo", d.get("task", "missing"))

    # 5. embedding dimension
    emb = d.get("embedding", [])
    record("PASS" if len(emb) == EXP_DIM else "FAIL",
           r.status_code, f"embedding dim={EXP_DIM}", f"got {len(emb)}")

    # 6. dim field matches
    record("PASS" if d.get("dim") == EXP_DIM else "FAIL",
           r.status_code, "dim field", f"got {d.get('dim')}")

    # 7. all values are floats
    all_float = all(isinstance(v, (int, float)) for v in emb) if emb else False
    record("PASS" if all_float else "FAIL",
           r.status_code, "all values are floats", "")

    # 8. embedding is non-zero
    non_zero = any(abs(v) > 1e-8 for v in emb) if emb else False
    record("PASS" if non_zero else "FAIL",
           r.status_code, "embedding non-zero", "")

    # 9. distinctness — different images produce different embeddings
    r2 = call({"model": MODEL, "image": png_b64(99)})
    if r.status_code == 200 and r2.status_code == 200:
        emb2 = r2.json().get("embedding", [])
        c = _cos(emb, emb2)
        record("PASS" if c < 0.999 else "FAIL",
               200, "distinctness", f"cos={c:.5f}")
    else:
        record("FAIL", r2.status_code, "distinctness", "request failed")

    # 10. determinism — same image same embedding
    r3 = call({"model": MODEL, "image": img})
    if r.status_code == 200 and r3.status_code == 200:
        emb3 = r3.json().get("embedding", [])
        c2 = _cos(emb, emb3)
        record("PASS" if c2 > 0.999 else "FAIL",
               200, "determinism", f"cos={c2:.5f}")
    else:
        record("FAIL", r3.status_code, "determinism", "request failed")

    # 11. small image (64x64)
    r4 = call({"model": MODEL, "image": png_b64(10, 64, 64)})
    d4 = r4.json() if r4.status_code == 200 else {}
    record("PASS" if len(d4.get("embedding", [])) == EXP_DIM else "FAIL",
           r4.status_code, "small image 64x64", "")

    # 12. large image (512x512)
    r5 = call({"model": MODEL, "image": png_b64(11, 512, 512)})
    d5 = r5.json() if r5.status_code == 200 else {}
    record("PASS" if len(d5.get("embedding", [])) == EXP_DIM else "FAIL",
           r5.status_code, "large image 512x512", "")

    # 13. data-URI prefix
    data_uri = "data:image/png;base64," + png_b64(13)
    r6 = call({"model": MODEL, "image": data_uri})
    record("PASS" if r6.status_code == 200 else "FAIL",
           r6.status_code, "data-URI prefix strip", "")

    # 14. sequential 5-image batch
    batch_ok = True
    for i in range(5):
        rb = call({"model": MODEL, "image": png_b64(100 + i)})
        if rb.status_code != 200:
            batch_ok = False
            break
    record("PASS" if batch_ok else "FAIL",
           200 if batch_ok else rb.status_code,
           "sequential 5-image batch", "all 200" if batch_ok else f"failed i={i}")

    # 15. guard — bad model
    rg1 = httpx.post(EP, json={"model": "fake-nope-999", "image": png_b64(3)}, timeout=60, headers=_HEADERS)
    record("EXP" if rg1.status_code == 404 else "FAIL",
           rg1.status_code, "guard bad model", rg1.text[:80])

    # 16. guard — missing image
    rg2 = httpx.post(EP, json={"model": MODEL}, timeout=60, headers=_HEADERS)
    record("EXP" if rg2.status_code >= 400 else "FAIL",
           rg2.status_code, "guard missing image", rg2.text[:80])

    # 17. guard — empty image
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
