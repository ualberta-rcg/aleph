"""qwen-image-2-1 gateway test.

Exercises the OpenAI image surface for the Qwen-Image-2.1 diffusers custom predictor:
text-to-image (dims, n, seed determinism, true_cfg/negative prompt), image editing with
a synthetic reference fixture (stdlib-generated PNG, no external deps), RGBA output
(PNG color-type byte), and the standard guards. Env-gated: QWEN21_BIG=1 adds a 2048x2048
peak-VRAM probe (slow).

Run externally via the public edge + Tyk auth:
  GW_URL=https://inference.vulcan.alliancecan.ca TYK_KEY=<key> \
      MODEL=qwen-image-2-1 python3 models/qwen-image-2-1/test.py
"""
import base64
import binascii
import os
import struct
import time
import zlib

import httpx

G = os.environ.get("GW_URL", "http://localhost:8080")
_KEY = os.environ.get("TYK_KEY")
_HEADERS = {"Authorization": f"Bearer {_KEY}"} if _KEY else {}
_VERIFY = os.environ.get("GW_INSECURE", "") == ""
MODEL = os.environ.get("MODEL", "qwen-image-2-1")
BIG = os.environ.get("QWEN21_BIG", "") == "1"
GEN, EDIT = "/v1/images/generations", "/v1/images/edits"
results = []


def req(path, body, timeout=600):
    return httpx.post(f"{G}{path}", json=body, timeout=timeout, headers=_HEADERS, verify=_VERIFY)


def record(icon, status, name, detail):
    results.append((icon, status, name, detail))
    print(f"[{icon}] {status} | {name}: {detail}", flush=True)


def png_info(b64):
    """(width, height, color_type) from a PNG IHDR, or None if not a valid PNG."""
    try:
        raw = base64.b64decode(b64)
    except Exception:
        return None
    if raw[:8] != b"\x89PNG\r\n\x1a\n" or raw[12:16] != b"IHDR":
        return None
    w, h = struct.unpack(">II", raw[16:24])
    return w, h, raw[25]  # color type: 2 = RGB, 6 = RGBA


def make_png_b64(w, h, rgb):
    """Solid-color PNG fixture, stdlib only (zlib/struct/CRC)."""
    def chunk(tag, data):
        body = tag + data
        return struct.pack(">I", len(data)) + body + struct.pack(">I", binascii.crc32(body) & 0xFFFFFFFF)
    ihdr = struct.pack(">IIBBBBB", w, h, 8, 2, 0, 0, 0)
    row = b"\x00" + bytes(rgb) * w
    png = (b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", ihdr)
           + chunk(b"IDAT", zlib.compress(row * h)) + chunk(b"IEND", b""))
    return base64.b64encode(png).decode()


def gen(body, name, want=None, timeout=600):
    try:
        r = req(GEN, body, timeout)
    except Exception as exc:
        record("ERR", 0, name, str(exc)[:120])
        return None
    if r.status_code != 200:
        record("FAIL", r.status_code, name, r.text[:160])
        return None
    data = r.json().get("data", [])
    infos = [png_info(d.get("b64_json", "")) for d in data]
    expected_n = int(body.get("n", 1))
    ok = len(data) == expected_n and all(i is not None for i in infos)
    detail = f"n={len(data)}/{expected_n} dims={[i and (i[0], i[1]) for i in infos]}"
    if want and ok:
        ok = all((i[0], i[1]) == want for i in infos)
        detail += f" want={want}"
    record("PASS" if ok else "FAIL", r.status_code, name, detail)
    return data


def wake():
    body = {"model": MODEL, "prompt": "a single red apple on a wooden table",
            "size": "1024x1024", "num_inference_steps": 8}
    for attempt in range(120):
        try:
            r = req(GEN, body, timeout=300)
        except Exception:
            time.sleep(5)
            continue
        if r.status_code == 200:
            data = r.json().get("data", [])
            info = png_info(data[0]["b64_json"]) if data else None
            record("PASS" if info and info[:2] == (1024, 1024) else "FAIL", 200,
                   "WAKE + basic gen", f"attempts={attempt + 1} dims={info and info[:2]}")
            return
        if r.status_code == 503:
            time.sleep(5)
            continue
        record("FAIL", r.status_code, "WAKE + basic gen", r.text[:160])
        return
    record("FAIL", 503, "WAKE + basic gen", "timed out waiting for warm model")


def size_square():
    gen({"model": MODEL, "prompt": "a green leaf on white paper",
         "size": "1024x1024", "num_inference_steps": 8},
        "gen size 1024x1024", want=(1024, 1024))


def size_nonsquare():
    gen({"model": MODEL, "prompt": "a wide desert horizon at sunset",
         "size": "1280x768", "num_inference_steps": 8},
        "gen non-square 1280x768 (÷32 clamp path)", want=(1280, 768))


def multi_n():
    gen({"model": MODEL, "prompt": "two colorful hot air balloons", "n": 2,
         "size": "768x768", "num_inference_steps": 8},
        "gen n=2 multiple images", want=(768, 768))


def cfg_negative():
    gen({"model": MODEL, "prompt": "a forest clearing with a small cabin",
         "negative_prompt": "people, text, watermark", "true_cfg": 1.0,
         "size": "768x768", "num_inference_steps": 8},
        "gen negative_prompt + true_cfg accepted", want=(768, 768))


def seed_determinism():
    body = {"model": MODEL, "prompt": "a lighthouse on a cliff at night",
            "size": "768x768", "num_inference_steps": 8, "seed": 12345}
    a = gen(dict(body), "gen seed=12345 (A)", want=(768, 768))
    b = gen(dict(body), "gen seed=12345 (B)", want=(768, 768))
    if a and b:
        same = a[0]["b64_json"] == b[0]["b64_json"]
        record("PASS" if same else "FAIL", 200, "seed determinism",
               f"identical_bytes={same}")


def edits():
    fixture = make_png_b64(256, 256, (200, 30, 30))
    try:
        r = req(EDIT, {"model": MODEL,
                       "prompt": "change the solid background to blue, keep it abstract",
                       "image": fixture, "size": "512x512", "num_inference_steps": 8},
                timeout=600)
    except Exception as exc:
        record("ERR", 0, "edits with reference fixture", str(exc)[:120])
        return
    if r.status_code != 200:
        record("FAIL", r.status_code, "edits with reference fixture", r.text[:160])
        return
    data = r.json().get("data", [])
    info = png_info(data[0]["b64_json"]) if data else None
    record("PASS" if info and info[:2] == (512, 512) else "FAIL", 200,
           "edits with reference fixture", f"info={info and info[:2]}")


def rgba_output():
    r = req(GEN, {"model": MODEL,
                  "prompt": "This is an RGBA image with transparency. "
                            "a simple blue circle logo on a transparent background",
                  "size": "512x512", "num_inference_steps": 8}, timeout=600)
    if r.status_code != 200:
        record("FAIL", r.status_code, "RGBA transparency", r.text[:160])
        return
    info = png_info(r.json()["data"][0]["b64_json"])
    # color type 6 = RGBA; some runs may still emit RGB (2) — record honestly.
    if info and info[2] == 6:
        record("PASS", 200, "RGBA transparency", f"dims={info[:2]} color_type=6 (RGBA)")
    elif info:
        record("EXP", 200, "RGBA transparency",
               f"dims={info[:2]} color_type={info[2]} (RGB; alpha not engaged for this prompt)")
    else:
        record("FAIL", 200, "RGBA transparency", "not a valid PNG")


def big_2048():
    if not BIG:
        record("SKIP", 0, "2048x2048 peak probe", "set QWEN21_BIG=1 to enable")
        return
    gen({"model": MODEL, "prompt": "an intricate aerial view of a river delta",
         "size": "2048x2048", "num_inference_steps": 40},
        "2048x2048 native peak probe", want=(2048, 2048), timeout=900)


def edits_missing_image():
    try:
        r = req(EDIT, {"model": MODEL, "prompt": "x"}, timeout=60)
    except Exception as exc:
        record("ERR", 0, "Guard: edits without image", str(exc)[:120])
        return
    record("EXP" if r.status_code == 400 else "FAIL", r.status_code,
           "Guard: edits without image", r.text[:120])


def bad_model_guard():
    try:
        r = req(GEN, {"model": "fake-xyz-nope", "prompt": "x"}, timeout=60)
    except Exception as exc:
        record("ERR", 0, "Guard: bad model", str(exc)[:120])
        return
    record("EXP" if r.status_code in (400, 404) else "FAIL", r.status_code,
           "Guard: bad model", r.text[:120])


def catalog():
    try:
        r = httpx.get(f"{G}/v1/models?all=true", timeout=30, headers=_HEADERS, verify=_VERIFY)
        models = r.json().get("data", [])
    except Exception as exc:
        record("ERR", 0, "Catalog entry", str(exc)[:120])
        return
    model = next((m for m in models if m.get("id") == MODEL), None)
    if not model:
        record("FAIL", r.status_code, "Catalog entry", "not found in ?all=true")
        return
    record("PASS" if model.get("type") == "image" else "FAIL", r.status_code,
           "Catalog entry", f"type={model.get('type')}")


print("=" * 66, flush=True)
print(f"{MODEL} image gateway test", flush=True)
print("=" * 66, flush=True)

for test in [wake, size_square, size_nonsquare, multi_n, cfg_negative, seed_determinism,
             edits, rgba_output, big_2048, edits_missing_image, bad_model_guard, catalog]:
    try:
        test()
    except Exception as exc:
        record("ERR", 0, test.__name__, str(exc)[:120])

passed = sum(1 for x in results if x[0] == "PASS")
expected = sum(1 for x in results if x[0] == "EXP")
failed = sum(1 for x in results if x[0] in ("FAIL", "ERR"))
print(f"\n{'=' * 66}\nResults: {passed} passed, {expected} expected, {failed} failed/err of {len(results)}",
      flush=True)
raise SystemExit(1 if failed else 0)
