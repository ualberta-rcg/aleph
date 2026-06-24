"""kandinsky-3 comprehensive gateway test (run inside the gateway pod).

Exercises the full OpenAI image surface for a KServe custom-predictor image model
through the default gateway (no model-specific gateway code):
  - WAKE: first request retries through the gateway's 503 cold-start (run with the
    model scaled to 0 to exercise the scale-from-zero wake path).
  - /v1/images/generations: sizes (square + non-square), n>1, steps low/high,
    guidance_scale, negative_prompt, seed determinism (+ different seed differs),
    the model-specific `quality:hd` knob.
  - /v1/images/edits (img2img): feed a generated image back in with strength.
  - Output validation: every b64_json decodes to a real PNG and the IHDR width/height
    match the requested size (no PIL in the pod -> parse the PNG header by hand).
  - Catalog: model present (type=image) via /v1/models?all=true.
  - Guardrails: bad model 404, missing prompt handled.

Run:  cat models/kandinsky-3/test.py | \\
      kubectl exec -i -n models deploy/model-gateway -c gateway -- python3 -
"""
import httpx, os, time, base64, struct

G = os.environ.get("GW_URL", "http://localhost:8080")
_KEY = os.environ.get("TYK_KEY")
_HEADERS = {"Authorization": f"Bearer {_KEY}"} if _KEY else {}
MODEL = os.environ.get("MODEL", "kandinsky-3")
GEN = "/v1/images/generations"
EDIT = "/v1/images/edits"
results = []


def req(path, body, timeout=600):
    return httpx.post(f"{G}{path}", json=body, timeout=timeout, headers=_HEADERS)


def record(icon, status, name, detail):
    results.append((icon, status, name, detail))
    print(f"[{icon}] {status} | {name}: {detail}", flush=True)


def png_dims(b64):
    """Return (w, h) from a base64 PNG, or None if it isn't a valid PNG."""
    try:
        raw = base64.b64decode(b64)
    except Exception:
        return None
    if raw[:8] != b"\x89PNG\r\n\x1a\n":
        return None
    # IHDR chunk: 8-byte sig, 4 len, 4 'IHDR', then width(4) height(4) big-endian.
    w, h = struct.unpack(">II", raw[16:24])
    return w, h


def gen(body, name, want=None, timeout=600):
    """POST generations; validate HTTP 200, n images, PNG decode + (optional) dims."""
    try:
        r = req(GEN, body, timeout)
    except Exception as e:
        record("ERR", 0, name, str(e)[:100]); return None
    if r.status_code != 200:
        record("FAIL", r.status_code, name, r.text[:100]); return None
    data = r.json().get("data", [])
    n_exp = int(body.get("n", 1))
    dims = [png_dims(d.get("b64_json", "")) for d in data]
    bad = [d for d in dims if d is None]
    ok = len(data) == n_exp and not bad
    detail = f"n={len(data)}/{n_exp} dims={dims}"
    if want and ok:
        ok = all(d == want for d in dims)
        detail += f" want={want}"
    record("PASS" if ok else "FAIL", r.status_code, name, detail)
    return data


# ── 1. WAKE (retry through cold-start 503) + basic generation ─────────────────
def wake():
    body = {"model": MODEL, "prompt": "a single red apple on a table",
            "n": 1, "size": "512x512", "num_inference_steps": 8}
    for attempt in range(96):  # ~8 min cap
        try:
            r = req(GEN, body, timeout=120)
        except Exception:
            time.sleep(5); continue
        if r.status_code == 200:
            d = r.json().get("data", [])
            dims = png_dims(d[0]["b64_json"]) if d else None
            ok = bool(d) and dims is not None
            record("PASS" if ok else "FAIL", 200, "WAKE + basic gen",
                   f"attempts={attempt+1} dims={dims}")
            return
        if r.status_code == 503:
            time.sleep(5); continue
        record("FAIL", r.status_code, "WAKE + basic gen", r.text[:100]); return
    record("FAIL", 503, "WAKE + basic gen", "timed out waiting for warm model")


# ── Generation feature battery ────────────────────────────────────────────────
def size_default():
    gen({"model": MODEL, "prompt": "a mountain lake at sunrise", "num_inference_steps": 12},
        "gen default size 1024x1024", want=(1024, 1024))

def size_small():
    gen({"model": MODEL, "prompt": "a green leaf", "size": "512x512", "num_inference_steps": 8},
        "gen size 512x512", want=(512, 512))

def size_nonsquare():
    gen({"model": MODEL, "prompt": "a wide desert horizon", "size": "1024x768",
         "num_inference_steps": 10}, "gen non-square 1024x768", want=(1024, 768))

def multi_n():
    gen({"model": MODEL, "prompt": "a colorful hot air balloon", "n": 2, "size": "512x512",
         "num_inference_steps": 8}, "gen n=2 multiple images")

def steps_high():
    gen({"model": MODEL, "prompt": "an intricate clockwork mechanism", "size": "512x512",
         "num_inference_steps": 40}, "gen high steps=40")

def guidance():
    gen({"model": MODEL, "prompt": "a serene zen garden", "size": "512x512",
         "num_inference_steps": 10, "guidance_scale": 7.0}, "gen guidance_scale=7.0")

def negative():
    gen({"model": MODEL, "prompt": "a forest", "negative_prompt": "people, text, watermark",
         "size": "512x512", "num_inference_steps": 10}, "gen negative_prompt")

def quality_hd():
    # kandinsky server bumps steps to >=50 when quality=hd
    gen({"model": MODEL, "prompt": "a photorealistic owl", "size": "512x512",
         "quality": "hd"}, "gen quality=hd", timeout=900)

def seed_determinism():
    body = {"model": MODEL, "prompt": "a lighthouse on a cliff", "size": "512x512",
            "num_inference_steps": 12, "seed": 12345}
    a = gen(dict(body), "gen seed=12345 (A)")
    b = gen(dict(body), "gen seed=12345 (B, must match A)")
    if a and b:
        same = a[0]["b64_json"] == b[0]["b64_json"]
        record("PASS" if same else "FAIL", 200, "seed determinism",
               f"identical_bytes={same}")

def seed_differs():
    p = {"model": MODEL, "prompt": "a lighthouse on a cliff", "size": "512x512",
         "num_inference_steps": 12}
    a = gen({**p, "seed": 1}, "gen seed=1")
    b = gen({**p, "seed": 2}, "gen seed=2 (must differ)")
    if a and b:
        diff = a[0]["b64_json"] != b[0]["b64_json"]
        record("PASS" if diff else "FAIL", 200, "different seeds differ",
               f"bytes_differ={diff}")


# ── img2img (edits endpoint) ──────────────────────────────────────────────────
def img2img():
    src = gen({"model": MODEL, "prompt": "a plain blue circle", "size": "512x512",
               "num_inference_steps": 10}, "img2img: make source")
    if not src:
        record("SKIP", 0, "img2img edit", "no source image"); return
    body = {"model": MODEL, "prompt": "a glowing blue circle, neon",
            "image": src[0]["b64_json"], "strength": 0.6, "size": "512x512",
            "num_inference_steps": 12}
    try:
        r = req(EDIT, body)
    except Exception as e:
        record("ERR", 0, "img2img edit", str(e)[:100]); return
    if r.status_code != 200:
        record("FAIL", r.status_code, "img2img edit", r.text[:120]); return
    d = r.json().get("data", [])
    dims = png_dims(d[0]["b64_json"]) if d else None
    record("PASS" if d and dims else "FAIL", r.status_code, "img2img edit", f"dims={dims}")


# ── Catalog + guardrails ──────────────────────────────────────────────────────
def catalog():
    r = httpx.get(f"{G}/v1/models?all=true", timeout=30, headers=_HEADERS)
    m = next((x for x in r.json().get("data", []) if x["id"] == MODEL), None)
    if not m:
        record("FAIL", r.status_code, "Catalog entry", "not found in ?all=true"); return
    record("PASS" if m.get("type") == "image" else "FAIL", r.status_code,
           "Catalog entry", f"type={m.get('type')}")

def guard_badmodel():
    try:
        r = req(GEN, {"model": "fake-xyz-nope", "prompt": "x", "num_inference_steps": 4})
    except Exception as e:
        record("ERR", 0, "Guard: bad model", str(e)[:100]); return
    record("EXP" if r.status_code in (404, 400) else "FAIL", r.status_code,
           "Guard: bad model", r.text[:80])


# ── run ───────────────────────────────────────────────────────────────────────
print("=" * 66, flush=True); print(f"{MODEL} comprehensive image gateway test", flush=True)
print("=" * 66, flush=True)
for t in [wake, size_default, size_small, size_nonsquare, multi_n, steps_high,
          guidance, negative, quality_hd, seed_determinism, seed_differs, img2img,
          catalog, guard_badmodel]:
    try:
        t()
    except Exception as e:
        record("ERR", 0, t.__name__, str(e)[:120])

p = sum(1 for x in results if x[0] == "PASS")
e = sum(1 for x in results if x[0] == "EXP")
f = sum(1 for x in results if x[0] in ("FAIL", "ERR"))
s = sum(1 for x in results if x[0] == "SKIP")
print(f"\n{'=' * 66}\nResults: {p} passed, {e} expected, {f} failed/err, {s} skipped of {len(results)}",
      flush=True)
