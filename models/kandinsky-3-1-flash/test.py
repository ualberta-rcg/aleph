"""kandinsky-3-1-flash gateway test.

Exercises the OpenAI image generation surface for the Kandinsky 3.1 Flash
custom predictor through the Aleph gateway.

Run externally (public edge serves a self-signed cert -> GW_INSECURE=1):
  GW_URL=https://inference.vulcan.alliancecan.ca TYK_KEY=<TYK_KEY> GW_INSECURE=1 \
    MODEL=kandinsky-3-1-flash python3 models/kandinsky-3-1-flash/test.py

Run inside the gateway pod:
  cat models/kandinsky-3-1-flash/test.py | \\
      kubectl exec -i -n models deploy/model-gateway -c gateway -- python3 -
"""
import base64
import os
import struct
import time

import httpx


G = os.environ.get("GW_URL", "http://localhost:8080")
_KEY = os.environ.get("TYK_KEY")
_HEADERS = {"Authorization": f"Bearer {_KEY}"} if _KEY else {}
_VERIFY = os.environ.get("GW_INSECURE", "") == ""
MODEL = os.environ.get("MODEL", "kandinsky-3-1-flash")
GEN = "/v1/images/generations"
EDIT = "/v1/images/edits"
results = []


def req(path, body, timeout=900):
    return httpx.post(f"{G}{path}", json=body, timeout=timeout, headers=_HEADERS, verify=_VERIFY)


def record(icon, status, name, detail):
    results.append((icon, status, name, detail))
    print(f"[{icon}] {status} | {name}: {detail}", flush=True)


def png_dims(b64):
    try:
        raw = base64.b64decode(b64)
    except Exception:
        return None
    if raw[:8] != b"\x89PNG\r\n\x1a\n":
        return None
    return struct.unpack(">II", raw[16:24])


def gen(body, name, want=None, timeout=900):
    try:
        r = req(GEN, body, timeout)
    except Exception as exc:
        record("ERR", 0, name, str(exc)[:120])
        return None
    if r.status_code != 200:
        record("FAIL", r.status_code, name, r.text[:160])
        return None
    data = r.json().get("data", [])
    expected_n = int(body.get("n", 1))
    dims = [png_dims(d.get("b64_json", "")) for d in data]
    ok = len(data) == expected_n and all(d is not None for d in dims)
    detail = f"n={len(data)}/{expected_n} dims={dims}"
    if want and ok:
        ok = all(d == want for d in dims)
        detail += f" want={want}"
    record("PASS" if ok else "FAIL", r.status_code, name, detail)
    return data


def wake():
    body = {
        "model": MODEL,
        "prompt": "a single red apple on a wooden table",
        "n": 1,
        "size": "512x512",
        "num_inference_steps": 4,
    }
    for attempt in range(120):
        try:
            r = req(GEN, body, timeout=180)
        except Exception:
            time.sleep(5)
            continue
        if r.status_code == 200:
            data = r.json().get("data", [])
            dims = png_dims(data[0]["b64_json"]) if data else None
            record("PASS" if dims == (512, 512) else "FAIL", 200, "WAKE + basic gen",
                   f"attempts={attempt + 1} dims={dims}")
            return
        if r.status_code == 503:
            time.sleep(5)
            continue
        record("FAIL", r.status_code, "WAKE + basic gen", r.text[:160])
        return
    record("FAIL", 503, "WAKE + basic gen", "timed out waiting for warm model")


def size_small():
    gen(
        {
            "model": MODEL,
            "prompt": "a green leaf on white paper",
            "size": "512x512",
            "num_inference_steps": 4,
        },
        "gen size 512x512",
        want=(512, 512),
    )


def size_nonsquare():
    gen(
        {
            "model": MODEL,
            "prompt": "a wide desert horizon at sunset",
            "size": "768x512",
            "num_inference_steps": 4,
        },
        "gen non-square 768x512",
        want=(768, 512),
    )


def multi_n():
    gen(
        {
            "model": MODEL,
            "prompt": "two colorful hot air balloons",
            "n": 2,
            "size": "512x512",
            "num_inference_steps": 4,
        },
        "gen n=2 multiple images",
        want=(512, 512),
    )


def guidance_and_negative():
    gen(
        {
            "model": MODEL,
            "prompt": "a forest clearing with a small cabin",
            "negative_prompt": "people, text, watermark",
            "guidance_scale": 4.0,
            "size": "512x512",
            "num_inference_steps": 4,
        },
        "gen negative_prompt + guidance_scale",
        want=(512, 512),
    )


def seed_determinism():
    body = {
        "model": MODEL,
        "prompt": "a lighthouse on a cliff at night",
        "size": "512x512",
        "num_inference_steps": 4,
        "seed": 12345,
    }
    a = gen(dict(body), "gen seed=12345 (A)", want=(512, 512))
    b = gen(dict(body), "gen seed=12345 (B)", want=(512, 512))
    if a and b:
        same = a[0]["b64_json"] == b[0]["b64_json"]
        record("PASS" if same else "FAIL", 200, "seed determinism",
               f"identical_bytes={same}")


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


def edit_unsupported():
    try:
        r = req(
            EDIT,
            {"model": MODEL, "prompt": "x", "image": "not-a-real-image"},
            timeout=60,
        )
    except Exception as exc:
        record("ERR", 0, "Edit unsupported", str(exc)[:120])
        return
    record("EXP" if r.status_code == 501 else "FAIL", r.status_code,
           "Edit unsupported (use kandinsky-3-1)", r.text[:120])


def bad_model_guard():
    try:
        r = req(GEN, {"model": "fake-xyz-nope", "prompt": "x"}, timeout=60)
    except Exception as exc:
        record("ERR", 0, "Guard: bad model", str(exc)[:120])
        return
    record("EXP" if r.status_code in (400, 404) else "FAIL", r.status_code,
           "Guard: bad model", r.text[:120])


print("=" * 66, flush=True)
print(f"{MODEL} image gateway test", flush=True)
print("=" * 66, flush=True)

for test in [
    wake,
    size_small,
    size_nonsquare,
    multi_n,
    guidance_and_negative,
    seed_determinism,
    catalog,
    edit_unsupported,
    bad_model_guard,
]:
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
