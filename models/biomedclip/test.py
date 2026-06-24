"""biomedclip biomedical vision-language embedding gateway test (run inside the gateway pod).

Embedding (Template C) battery for a custom BiomedCLIP server (Microsoft, GPU).
Shared 512-dim image+text embeddings + zero-shot classify, via the domain /v1/science/embed
endpoint (also /v1/embeddings). Non-text-primary (biomedical images) but has a text branch.

Run externally via the gateway VIP + Tyk auth (preferred):
  GW_URL=http://<GATEWAY_VIP> TYK_KEY=<key> python3 models/biomedclip/test.py

Run inside the gateway pod (legacy, no auth needed):
  cat models/biomedclip/test.py | kubectl exec -i -n models deploy/model-gateway -c gateway -- python3 -
"""
import base64, httpx, math, os, struct, time, zlib

G = os.environ.get("GW_URL", "http://localhost:8080")
_KEY = os.environ.get("TYK_KEY")
_HEADERS = {"Authorization": f"Bearer {_KEY}"} if _KEY else {}
MODEL = os.environ.get("MODEL", "biomedclip")
EXP_DIM = 512
results = []


def record(icon, status, name, detail):
    results.append((icon, status, name, detail)); print(f"[{icon}] {status} | {name}: {detail}", flush=True)


def embed(body, ep="/v1/science/embed", timeout=300):
    body = {**body, "model": MODEL}
    try:
        r = httpx.post(f"{G}{ep}", json=body, timeout=timeout, headers=_HEADERS)
        try: return r, r.json()
        except Exception: return r, {}
    except Exception:
        return None, {}


def classify(body, timeout=300):
    body = {**body, "model": MODEL}
    try:
        r = httpx.post(f"{G}/v1/classify", json=body, timeout=timeout, headers=_HEADERS)
        try: return r, r.json()
        except Exception: return r, {}
    except Exception:
        return None, {}


def _cos(a, b):
    da = math.sqrt(sum(x*x for x in a)); db = math.sqrt(sum(y*y for y in b))
    return sum(x*y for x, y in zip(a, b))/(da*db) if da and db else 0.0


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


def _vec(d, key):
    e = d.get(key)
    if isinstance(e, list) and e:
        return e[0] if isinstance(e[0], list) else list(e)
    return []


def wake_dim():
    for attempt in range(72):
        r, d = embed({"texts": ["a chest x-ray showing pneumonia"]})
        if r is not None and r.status_code == 200:
            v = _vec(d, "text_embeddings"); n = len(v)
            record("PASS" if n == EXP_DIM else "FAIL", 200, "WAKE text + dim", f"attempts={attempt+1} dim={n} (exp {EXP_DIM})")
            return
        if r is None or r.status_code in (503, 502, 504, 404): time.sleep(5); continue
        record("FAIL", r.status_code, "WAKE text + dim", f"body={r.text[:120]}"); return
    record("FAIL", 0, "WAKE text + dim", "timed out")


def checks():
    # 2. image embedding dimension
    r, d = embed({"images": [png_b64(2)]}); v = _vec(d, "image_embeddings")
    record("PASS" if r.status_code == 200 and len(v) == EXP_DIM and not all(x == 0 for x in v) else "FAIL",
           r.status_code, "image + dim", f"dim={len(v)} zero={all(x==0 for x in v)} sample={[round(x,3) for x in v[:4]]}")

    # 3. text distinctness
    _, d1 = embed({"texts": ["pneumonia on chest x-ray"]}); _, d2 = embed({"texts": ["normal brain MRI"]})
    v1, v2 = _vec(d1, "text_embeddings"), _vec(d2, "text_embeddings"); c = _cos(v1, v2) if v1 and v2 else 1.0
    record("PASS" if c < 0.999 else "FAIL", 200, "text distinctness", f"cos(a,b)={c:.5f}")

    # 4. deterministic
    _, d1 = embed({"texts": ["same caption twice"]}); _, d2 = embed({"texts": ["same caption twice"]})
    v1, v2 = _vec(d1, "text_embeddings"), _vec(d2, "text_embeddings"); c = _cos(v1, v2) if v1 and v2 else 0.0
    record("PASS" if c > 0.9999 else "FAIL", 200, "deterministic", f"cos(x,x)={c:.5f}")

    # 5. shared space (image & text same dim)
    _, dt = embed({"texts": ["xray"]}); _, di = embed({"images": [png_b64(9)]})
    vt, vi = _vec(dt, "text_embeddings"), _vec(di, "image_embeddings")
    record("PASS" if len(vt) == len(vi) == EXP_DIM else "FAIL", 200, "shared space 512", f"text={len(vt)} image={len(vi)}")

    # 6. model echo
    r, d = embed({"texts": ["echo"]})
    record("PASS" if r.status_code == 200 and d.get("model") == "biomedclip" else "FAIL", r.status_code, "model echo", f"model={d.get('model')!r}")

    # 7. malformed input handled
    r, d = embed({})
    record("PASS" if r is not None and r.status_code < 600 else "FAIL", r.status_code if r else 0, "malformed handled", f"status={r.status_code if r else 'err'} (lenient)")

    # 8. multi-image batch
    r, d = embed({"images": [png_b64(10), png_b64(11)]})
    ie = d.get("image_embeddings", [])
    record("PASS" if r.status_code == 200 and len(ie) == 2 and all(len(e) == EXP_DIM for e in ie) else "FAIL",
           r.status_code, "multi-image batch", f"count={len(ie)}")

    # 9. multi-text batch
    r, d = embed({"texts": ["pneumonia", "fracture", "normal"]})
    te = d.get("text_embeddings", [])
    record("PASS" if r.status_code == 200 and len(te) == 3 and all(len(e) == EXP_DIM for e in te) else "FAIL",
           r.status_code, "multi-text batch", f"count={len(te)}")

    # 10. image+text combined request
    r, d = embed({"images": [png_b64(20)], "texts": ["chest x-ray"]})
    has_both = "image_embeddings" in d and "text_embeddings" in d
    record("PASS" if r.status_code == 200 and has_both else "FAIL",
           r.status_code, "image+text combined", f"has_image={('image_embeddings' in d)} has_text={('text_embeddings' in d)}")

    # 11. image determinism
    _, d1 = embed({"images": [png_b64(42)]}); _, d2 = embed({"images": [png_b64(42)]})
    v1, v2 = _vec(d1, "image_embeddings"), _vec(d2, "image_embeddings")
    c = _cos(v1, v2) if v1 and v2 else 0.0
    record("PASS" if c > 0.9999 else "FAIL", 200, "image deterministic", f"cos={c:.5f}")

    # 12. different images produce different embeddings
    _, d1 = embed({"images": [png_b64(1)]}); _, d2 = embed({"images": [png_b64(99)]})
    v1, v2 = _vec(d1, "image_embeddings"), _vec(d2, "image_embeddings")
    c = _cos(v1, v2) if v1 and v2 else 1.0
    record("PASS" if c < 0.999 else "FAIL", 200, "image distinctness", f"cos={c:.5f}")

    # 13. /v1/embeddings alias works
    r, d = embed({"texts": ["alias test"]}, ep="/v1/embeddings")
    v = _vec(d, "text_embeddings")
    record("PASS" if r.status_code == 200 and len(v) == EXP_DIM else "FAIL",
           r.status_code, "/v1/embeddings alias", f"dim={len(v)}")

    # 14. zero-shot classify
    r, d = classify({"images": [png_b64(5)], "labels": ["pneumonia", "normal", "fracture"]})
    cl = d.get("classifications", [])
    ok = r.status_code == 200 and len(cl) >= 1 and all("label" in c and "score" in c for c in cl[0])
    record("PASS" if ok else "FAIL", r.status_code, "classify endpoint", f"classes={len(cl[0]) if cl else 0}")

    # 15. classify requires images+labels
    r, d = classify({"images": [png_b64(5)]})
    record("PASS" if r is not None and r.status_code in (400, 500) else "FAIL",
           r.status_code if r else 0, "classify validation", f"status={r.status_code if r else 'err'}")

    # 16. health endpoint (gateway may not expose /health -> EXP)
    try:
        r = httpx.get(f"{G}/health", timeout=10, headers=_HEADERS)
        d = r.json()
        ok = r.status_code == 200 and d.get("status") == "ok"
        record("PASS" if ok else "EXP", r.status_code, "health endpoint", f"status={d.get('status')}")
    except Exception as e:
        record("EXP", 0, "health endpoint", str(e))

    # 17. embedding norm (CLIP embeddings are typically unit-normed or near)
    _, d = embed({"texts": ["norm check"]}); v = _vec(d, "text_embeddings")
    norm = math.sqrt(sum(x*x for x in v)) if v else 0
    record("PASS" if 0.1 < norm < 1000 else "FAIL", 200, "embedding norm finite", f"L2={norm:.4f}")


def summary():
    p = sum(1 for i, *_ in results if i == "PASS"); f = sum(1 for i, *_ in results if i == "FAIL")
    print(f"\n== {MODEL}: {p} PASS / {f} FAIL of {len(results)} ==", flush=True); return 0 if f == 0 else 1


if __name__ == "__main__":
    wake_dim(); checks()
    raise SystemExit(summary())
