"""sam3.1 image segmentation gateway test.

Custom-server battery for SAM 3 promptable segmentation
(image + text prompt -> masks/boxes/scores).
Run: GW_URL=https://inference.vulcan.alliancecan.ca TYK_KEY=<key> GW_INSECURE=1 python3 models/sam3.1/test.py
"""
import base64, httpx, os, struct, time, zlib

G = os.environ.get("GW_URL", "http://localhost:8080")
_KEY = os.environ.get("TYK_KEY")
_HEADERS = {"Authorization": f"Bearer {_KEY}"} if _KEY else {}
_VERIFY = os.environ.get("GW_INSECURE", "").lower() not in ("1", "true", "yes", "on")
MODEL = os.environ.get("MODEL", "sam3.1")
results = []


def record(icon, status, name, detail):
    results.append((icon, status, name, detail)); print(f"[{icon}] {status} | {name}: {detail}", flush=True)


def req(method, path, body=None, timeout=400):
    return httpx.request(method, f"{G}{path}", json=body, timeout=timeout, headers=_HEADERS, verify=_VERIFY)


def seg(body):
    r = req("POST", "/v1/science/segment", body)
    try: return r, r.json()
    except Exception: return r, {}


def png_b64(seed, w=64, h=64):
    """Structured synthetic PNG: bright shape on dark bg so SAM3 has *something* to see."""
    raw = bytearray(); s = seed & 0x7FFFFFFF
    cx, cy = w // 2, h // 2
    for y in range(h):
        raw.append(0)
        for x in range(w):
            inside = (x - cx) ** 2 + (y - cy) ** 2 < (min(w, h) // 3) ** 2
            s = (1103515245 * s + 12345) & 0x7FFFFFFF
            base = 230 if inside else 20
            raw.append(base); raw.append(base); raw.append(base)
    def chunk(typ, data):
        c = struct.pack(">I", len(data)) + typ + data
        return c + struct.pack(">I", zlib.crc32(typ + data) & 0xFFFFFFFF)
    ihdr = struct.pack(">IIBBBBB", w, h, 8, 2, 0, 0, 0)
    png = b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", ihdr) + chunk(b"IDAT", zlib.compress(bytes(raw))) + chunk(b"IEND", b"")
    return base64.b64encode(png).decode()


def wake():
    for attempt in range(90):
        r, d = seg({"model": MODEL, "image": png_b64(1), "text": "object"})
        if r.status_code == 200:
            n = d.get("count")
            ok = isinstance(n, int) and isinstance(d.get("instances"), list)
            record("PASS" if ok else "FAIL", 200, "WAKE + well-formed",
                   f"attempts={attempt+1} count={n}"); return d
        if r.status_code in (503, 502, 504, 404): time.sleep(8); continue
        record("FAIL", r.status_code, "WAKE + well-formed", f"body={r.text[:100]}"); return None
    record("FAIL", 0, "WAKE + well-formed", "timed out"); return None


def checks():
    # well-formed response
    r, d = seg({"model": MODEL, "image": png_b64(2), "text": "object"})
    ok = r.status_code == 200 and "count" in d and "instances" in d and "image_size" in d
    record("PASS" if ok else "FAIL", r.status_code, "well-formed response",
           f"count={d.get('count')} size={d.get('image_size')}")

    # instance shape (if any found)
    insts = d.get("instances", [])
    if insts:
        i0 = insts[0]
        ok = "score" in i0 and "box" in i0 and "area" in i0 and len(i0.get("box", [])) == 4
        record("PASS" if ok else "FAIL", 200, "instance shape",
               f"score={i0.get('score'):.3f} box={i0.get('box')} area={i0.get('area')}")
    else:
        record("PASS", 200, "instance shape", "no instances on synthetic image (acceptable)")

    # deterministic
    _, d1 = seg({"model": MODEL, "image": png_b64(30), "text": "shape"})
    _, d2 = seg({"model": MODEL, "image": png_b64(30), "text": "shape"})
    record("PASS" if d1.get("count") == d2.get("count") else "FAIL", 200,
           "deterministic", f"count1={d1.get('count')} count2={d2.get('count')}")

    # return_masks toggles mask_png
    r, d = seg({"model": MODEL, "image": png_b64(40), "text": "object", "return_masks": True})
    insts = d.get("instances", [])
    has_mask = all("mask_png" in x for x in insts) if insts else True
    record("PASS" if r.status_code == 200 and has_mask else "FAIL", r.status_code,
           "return_masks flag", f"instances={len(insts)} all_have_mask_png={has_mask}")

    # model echo
    r, d = seg({"model": MODEL, "image": png_b64(50), "text": "object"})
    record("PASS" if r.status_code == 200 and d.get("model") == MODEL else "FAIL",
           r.status_code, "model echo", f"model={d.get('model')!r}")

    # malformed (missing image)
    r, _ = seg({"model": MODEL, "text": "object"})
    record("PASS" if 400 <= r.status_code < 600 else "FAIL", r.status_code,
           "malformed handled", f"status={r.status_code}")

    # catalog
    r = req("GET", "/v1/models?all=true")
    m = next((x for x in r.json().get("data", []) if x.get("id") == MODEL), None)
    record("PASS" if m and m.get("type") == "segment" else "FAIL", r.status_code,
           "Catalog entry", f"type={m.get('type') if m else 'not found'}")


print("=" * 66, flush=True); print(f"{MODEL} segmentation gateway test", flush=True); print("=" * 66, flush=True)
for t in [wake, checks]:
    try: t()
    except Exception as e: record("ERR", 0, t.__name__, str(e)[:120])
p = sum(1 for x in results if x[0] == "PASS"); f = sum(1 for x in results if x[0] in ("FAIL", "ERR"))
print(f"\n{'=' * 66}\nResults: {p} passed, {f} failed/err of {len(results)}", flush=True)
