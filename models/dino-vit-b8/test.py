"""dino-vit-b8 visual embedding gateway test (run inside the gateway pod).

Embedding (Template C) battery for a custom DINO ViT-B/8 ONNX server (Meta, CPU).
768-dim self-supervised embeddings of a base64 image, via the domain /v1/science/embed endpoint.
Non-text (image) → does NOT expose OpenAI /v1/embeddings.

Run:  cat models/dino-vit-b8/test.py | kubectl exec -i -n models deploy/model-gateway -c gateway -- python3 -
"""
import base64, httpx, math, os, struct, time, zlib

G = "http://localhost:8080"
MODEL = os.environ.get("MODEL", "dino-vit-b8")
EXP_DIM = 768
results = []


def record(icon, status, name, detail):
    results.append((icon, status, name, detail)); print(f"[{icon}] {status} | {name}: {detail}", flush=True)


def embed(body, timeout=300):
    body = {**body, "model": MODEL}
    try:
        r = httpx.post(f"{G}/v1/science/embed", json=body, timeout=timeout)
        try: return r, r.json()
        except Exception: return r, {}
    except Exception:
        return None, {}


def _cos(a, b):
    da = math.sqrt(sum(x*x for x in a)); db = math.sqrt(sum(y*y for y in b))
    return sum(x*y for x, y in zip(a, b))/(da*db) if da and db else 0.0


def png_b64(seed, w=16, h=16):
    """Pure-stdlib RGB PNG (deterministic per seed), base64-encoded."""
    raw = bytearray()
    s = seed & 0x7FFFFFFF
    for _ in range(h):
        raw.append(0)  # filter byte per scanline
        for _ in range(w * 3):
            s = (1103515245 * s + 12345) & 0x7FFFFFFF
            raw.append(s % 256)
    def chunk(typ, data):
        c = struct.pack(">I", len(data)) + typ + data
        return c + struct.pack(">I", zlib.crc32(typ + data) & 0xFFFFFFFF)
    ihdr = struct.pack(">IIBBBBB", w, h, 8, 2, 0, 0, 0)  # 8-bit RGB
    png = b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", ihdr) + chunk(b"IDAT", zlib.compress(bytes(raw))) + chunk(b"IEND", b"")
    return base64.b64encode(png).decode()


def _vec(d): return d.get("embeddings") or d.get("embedding") or []


def wake_dim():
    img = png_b64(1)
    for attempt in range(72):
        r, d = embed({"image": img})
        if r is not None and r.status_code == 200:
            v = _vec(d); n = len(v)
            record("PASS" if n == EXP_DIM else "FAIL", 200, "WAKE + dim", f"attempts={attempt+1} dim={n} (exp {EXP_DIM})")
            return
        if r is None or r.status_code in (503, 502, 504, 404): time.sleep(5); continue
        record("FAIL", r.status_code, "WAKE + dim", f"body={r.text[:120]}"); return
    record("FAIL", 0, "WAKE + dim", "timed out")


def checks():
    r, d = embed({"image": png_b64(2)}); v = _vec(d)
    record("PASS" if r.status_code == 200 and len(v) == EXP_DIM and not all(x == 0 for x in v) else "FAIL",
           r.status_code, "non-zero real", f"zero={all(x==0 for x in v)} sample={[round(x,3) for x in v[:4]]}")
    _, d1 = embed({"image": png_b64(10)}); _, d2 = embed({"image": png_b64(20)})
    v1, v2 = _vec(d1), _vec(d2); c = _cos(v1, v2) if v1 and v2 else 1.0
    record("PASS" if c < 0.999 else "FAIL", 200, "distinctness", f"cos(a,b)={c:.5f}")
    img = png_b64(30); _, d1 = embed({"image": img}); _, d2 = embed({"image": img})
    v1, v2 = _vec(d1), _vec(d2); c = _cos(v1, v2) if v1 and v2 else 0.0
    record("PASS" if c > 0.9999 else "FAIL", 200, "deterministic", f"cos(x,x)={c:.5f}")
    r, d = embed({"image": png_b64(40)})
    record("PASS" if r.status_code == 200 and d.get("model") == MODEL else "FAIL", r.status_code, "model echo", f"model={d.get('model')!r}")
    r, _ = embed({})
    record("PASS" if r is not None and 400 <= r.status_code < 600 else "FAIL",
           r.status_code if r else 0, "malformed handled", f"status={r.status_code if r else 'err'}")


def summary():
    p = sum(1 for i, *_ in results if i == "PASS"); f = sum(1 for i, *_ in results if i == "FAIL")
    print(f"\n== {MODEL}: {p} PASS / {f} FAIL of {len(results)} ==", flush=True); return 0 if f == 0 else 1


if __name__ == "__main__":
    wake_dim(); checks()
    raise SystemExit(summary())
