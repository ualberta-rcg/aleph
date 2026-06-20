"""astroclip multimodal embedding gateway test (run inside the gateway pod).

Embedding (Template C) battery for a custom Lightning server (Polymathic AI AstroCLIP, GPU).
1024-dim cross-attention embeddings of galaxy images (g,r,z 144x144) and optical spectra,
via the domain /v1/science/embed endpoint. AstroCLIP is non-text (image/spectrum input), so
it does NOT expose OpenAI /v1/embeddings and stays on /v1/science/embed.

Run:  cat models/astroclip/test.py | \
      kubectl exec -i -n models deploy/model-gateway -c gateway -- python3 -
"""
import httpx, json, math, os, time

G = "http://localhost:8080"
MODEL = os.environ.get("MODEL", "astroclip")
EXP_DIM = 1024
results = []


def record(icon, status, name, detail):
    results.append((icon, status, name, detail))
    print(f"[{icon}] {status} | {name}: {detail}", flush=True)


def science_embed(body, timeout=300):
    """POST /v1/science/embed through the gateway (model field required by catch-all)."""
    body = {**body, "model": MODEL}
    r = httpx.post(f"{G}/v1/science/embed", json=body, timeout=timeout)
    try:
        return r, r.json()
    except Exception:
        return r, {}


def _cos(a, b):
    da = math.sqrt(sum(x * x for x in a))
    db = math.sqrt(sum(y * y for y in b))
    return sum(x * y for x, y in zip(a, b)) / (da * db) if da and db else 0.0


def rand_img(seed):
    # Deterministic pseudo-random 144x144x3 (g,r,z) cutout. Real model run on synthetic input;
    # we only verify embedding shape/dim/distinctness, not astronomical correctness.
    rng = _RNG(seed)
    return [[[rng.next() for _ in range(3)] for _ in range(144)] for _ in range(144)]


def rand_spec(seed, n=512):
    rng = _RNG(seed)
    return [rng.next() for _ in range(n)]


class _RNG:
    """Tiny deterministic LCG (random module seeded per-call would also work)."""
    def __init__(self, seed):
        self.s = seed & 0x7FFFFFFF
    def next(self):
        self.s = (1103515245 * self.s + 12345) & 0x7FFFFFFF
        return round((self.s % 1000) / 1000.0, 4)


def wake_image_dim():
    img = rand_img(1)
    for attempt in range(72):
        r, d = science_embed({"image": img, "modality": "image"})
        if r.status_code == 200:
            n = len(d.get("embeddings", []))
            rec = "PASS" if n == EXP_DIM else "FAIL"
            record(rec, 200, "WAKE image + dim", f"attempts={attempt+1} dim={n} (exp {EXP_DIM})")
            return
        if r.status_code in (503, 502, 404):
            time.sleep(5)
            continue
        record("FAIL", r.status_code, "WAKE image + dim", f"body={r.text[:120]}")
        return
    record("FAIL", 0, "WAKE image + dim", "timed out")


def spectrum_dim():
    r, d = science_embed({"spectrum": rand_spec(2), "modality": "spectrum"})
    n = len(d.get("embeddings", []))
    zero = all(v == 0 for v in d.get("embeddings", []))
    rec = "PASS" if r.status_code == 200 and n == EXP_DIM and not zero else "FAIL"
    record(rec, r.status_code, "spectrum + dim", f"dim={n} zero={zero}")


def shape_field():
    r, d = science_embed({"image": rand_img(3), "modality": "image"})
    emb = d.get("embeddings", [])
    shape = d.get("shape")
    ok = r.status_code == 200 and shape == [len(emb)] == [EXP_DIM]
    record("PASS" if ok else "FAIL", r.status_code, "shape field", f"shape={shape} len={len(emb)}")


def inmodal_distinct():
    _, d1 = science_embed({"image": rand_img(10), "modality": "image"})
    _, d2 = science_embed({"image": rand_img(20), "modality": "image"})
    e1, e2 = d1.get("embeddings"), d2.get("embeddings")
    if not e1 or not e2:
        record("FAIL", 0, "in-modal distinct", "missing embeddings")
        return
    c = _cos(e1, e2)
    # Distinct inputs must not be identical (cos < 0.999). AstroCLIP image embeddings of
    # random images sit close in the learned manifold but are not identical.
    record("PASS" if c < 0.999 else "FAIL", 200, "in-modal distinct", f"cos(img_a,img_b)={c:.5f}")


def crossmodal_sanity():
    _, di = science_embed({"image": rand_img(30), "modality": "image"})
    _, ds = science_embed({"spectrum": rand_spec(40), "modality": "spectrum"})
    ei, es = di.get("embeddings"), ds.get("embeddings")
    if not ei or not es:
        record("FAIL", 0, "cross-modal cos", "missing embeddings")
        return
    c = _cos(ei, es)
    # Both 1024-dim and share a space; just assert finite + in [-1, 1].
    ok = -1.0 <= c <= 1.0
    record("PASS" if ok else "FAIL", 200, "cross-modal cos", f"cos(img,spec)={c:.5f}")


def deterministic():
    """Same image twice -> identical embedding (no sampling)."""
    img = rand_img(50)
    _, d1 = science_embed({"image": img, "modality": "image"})
    _, d2 = science_embed({"image": img, "modality": "image"})
    e1, e2 = d1.get("embeddings"), d2.get("embeddings")
    if not e1 or not e2:
        record("FAIL", 0, "deterministic", "missing embeddings")
        return
    c = _cos(e1, e2)
    record("PASS" if c > 0.9999 else "FAIL", 200, "deterministic", f"cos(img,img)={c:.5f}")


def modality_echo():
    r, d = science_embed({"image": rand_img(60), "modality": "image"})
    ok = r.status_code == 200 and d.get("modality") == "image" and d.get("model") == MODEL
    record("PASS" if ok else "FAIL", r.status_code, "modality echo", f"modality={d.get('modality')!r} model={d.get('model')!r}")


def demo_path():
    r, d = science_embed({"demo": True, "modality": "image"})
    emb = d.get("embeddings", [])
    ok = r.status_code == 200 and d.get("demo") is True and len(emb) == EXP_DIM
    record("PASS" if ok else "FAIL", r.status_code, "demo path", f"demo={d.get('demo')} len={len(emb)}")


def malformed():
    """No image/spectrum and no demo -> server should 4xx/5xx, not hang."""
    r, _ = science_embed({"modality": "image"})
    record("PASS" if 400 <= r.status_code < 600 else "FAIL", r.status_code, "malformed handled", f"status={r.status_code}")


def summary():
    passed = sum(1 for i, *_ in results if i == "PASS")
    failed = sum(1 for i, *_ in results if i == "FAIL")
    print(f"\n== {MODEL}: {passed} PASS / {failed} FAIL of {len(results)} ==", flush=True)
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    wake_image_dim()
    spectrum_dim()
    shape_field()
    inmodal_distinct()
    crossmodal_sanity()
    deterministic()
    modality_echo()
    demo_path()
    malformed()
    raise SystemExit(summary())
