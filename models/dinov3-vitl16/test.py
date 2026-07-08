"""dinov3-vitl16 vision embedding gateway test.

Template C battery for DINOv3 ViT-L/16 (1024-dim CLS embeddings).
Run: GW_URL=https://inference.vulcan.alliancecan.ca TYK_KEY=<key> GW_INSECURE=1 python3 models/dinov3-vitl16/test.py
"""
import base64, httpx, math, os, struct, time, zlib

G = os.environ.get("GW_URL", "http://localhost:8080")
_KEY = os.environ.get("TYK_KEY")
_HEADERS = {"Authorization": f"Bearer {_KEY}"} if _KEY else {}
_VERIFY = os.environ.get("GW_INSECURE", "").lower() not in ("1", "true", "yes", "on")
MODEL = os.environ.get("MODEL", "dinov3-vitl16")
EXP_DIM = 1024
results = []


def record(icon, status, name, detail):
    results.append((icon, status, name, detail)); print(f"[{icon}] {status} | {name}: {detail}", flush=True)


def req(method, path, body=None, timeout=300):
    return httpx.request(method, f"{G}{path}", json=body, timeout=timeout, headers=_HEADERS, verify=_VERIFY)


def embed(body):
    r = req("POST", "/v1/science/embed", body)
    try: return r, r.json()
    except Exception: return r, {}


def png_b64(seed, w=16, h=16):
    raw = bytearray(); s = seed & 0x7FFFFFFF
    for _ in range(h):
        raw.append(0)
        for _ in range(w * 3):
            s = (1103515245 * s + 12345) & 0x7FFFFFFF; raw.append(s % 256)
    def chunk(typ, data):
        c = struct.pack(">I", len(data)) + typ + data
        return c + struct.pack(">I", zlib.crc32(typ + data) & 0xFFFFFFFF)
    ihdr = struct.pack(">IIBBBBB", w, h, 8, 2, 0, 0, 0)
    png = b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", ihdr) + chunk(b"IDAT", zlib.compress(bytes(raw))) + chunk(b"IEND", b"")
    return base64.b64encode(png).decode()


def _vec(d): return d.get("embedding") or d.get("embeddings") or []
def _cos(a, b):
    da = math.sqrt(sum(x*x for x in a)); db = math.sqrt(sum(y*y for y in b))
    return sum(x*y for x,y in zip(a,b))/(da*db) if da and db else 0.0


def wake_dim():
    for attempt in range(72):
        r, d = embed({"model": MODEL, "image": png_b64(1)})
        if r.status_code == 200:
            n = len(_vec(d))
            record("PASS" if n == EXP_DIM else "FAIL", 200, "WAKE + dim", f"attempts={attempt+1} dim={n} (exp {EXP_DIM})"); return
        if r.status_code in (503, 502, 504, 404): time.sleep(5); continue
        record("FAIL", r.status_code, "WAKE + dim", f"body={r.text[:80]}"); return
    record("FAIL", 0, "WAKE + dim", "timed out")


def checks():
    # non-zero real embedding
    r, d = embed({"model": MODEL, "image": png_b64(2)}); v = _vec(d)
    record("PASS" if r.status_code == 200 and len(v) == EXP_DIM and not all(x==0 for x in v) else "FAIL",
           r.status_code, "non-zero real", f"dim={len(v)} sample={[round(x,3) for x in v[:4]]}")

    # distinctness
    _, d1 = embed({"model": MODEL, "image": png_b64(10)}); _, d2 = embed({"model": MODEL, "image": png_b64(20)})
    c = _cos(_vec(d1), _vec(d2))
    record("PASS" if c < 0.999 else "FAIL", 200, "distinctness", f"cos={c:.5f}")

    # deterministic
    _, d1 = embed({"model": MODEL, "image": png_b64(30)}); _, d2 = embed({"model": MODEL, "image": png_b64(30)})
    c = _cos(_vec(d1), _vec(d2))
    record("PASS" if c > 0.9999 else "FAIL", 200, "deterministic", f"cos={c:.5f}")

    # model echo
    r, d = embed({"model": MODEL, "image": png_b64(40)})
    record("PASS" if r.status_code == 200 and d.get("model") == MODEL else "FAIL", r.status_code, "model echo", f"model={d.get('model')!r}")

    # malformed
    r, _ = embed({"model": MODEL})
    record("PASS" if 400 <= r.status_code < 600 else "FAIL", r.status_code, "malformed handled", f"status={r.status_code}")

    # embedding norm
    r, d = embed({"model": MODEL, "image": png_b64(50)}); v = _vec(d)
    norm = math.sqrt(sum(x*x for x in v)) if v else 0
    record("PASS" if 0.1 < norm < 1e6 else "FAIL", r.status_code, "embedding norm", f"L2={norm:.4f}")

    # catalog
    r = req("GET", "/v1/models?all=true")
    m = next((x for x in r.json().get("data",[]) if x.get("id") == MODEL), None)
    record("PASS" if m and m.get("type") == "embedding" else "FAIL", r.status_code, "Catalog entry", f"type={m.get('type') if m else 'not found'}")


print("="*66, flush=True); print(f"{MODEL} vision-embedding gateway test", flush=True); print("="*66, flush=True)
for t in [wake_dim, checks]:
    try: t()
    except Exception as e: record("ERR", 0, t.__name__, str(e)[:120])
p = sum(1 for x in results if x[0]=="PASS"); f = sum(1 for x in results if x[0] in ("FAIL","ERR"))
print(f"\n{'='*66}\nResults: {p} passed, {f} failed/err of {len(results)}", flush=True)
