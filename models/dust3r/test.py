"""dust3r gateway test — comprehensive.

Run externally via the gateway VIP + Tyk auth (preferred):
  GW_URL=http://<GATEWAY_VIP> TYK_KEY=<key> python3 models/dust3r/test.py

Run inside the gateway pod (legacy, no auth needed):
  cat models/dust3r/test.py | \
    kubectl exec -i -n models deploy/model-gateway -c gateway -- python3 -
"""
import base64, httpx, os, struct, time, zlib

G = os.environ.get("GW_URL", "http://localhost:8080")
_KEY = os.environ.get("TYK_KEY")
_HEADERS = {"Authorization": f"Bearer {_KEY}"} if _KEY else {}
MODEL = "dust3r"
EP = f"{G}/v1/science/reconstruct"
results = []


def record(icon, status, name, detail):
    results.append((icon, status, name, detail))
    print(f"[{icon}] {status} | {name}: {detail}", flush=True)


def png_b64(seed=7, w=64, h=64):
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


# ── 1. Wake ──────────────────────────────────────────────────────────
def wake():
    body = {"model": MODEL, "images": [png_b64(1, 64, 64), png_b64(2, 64, 64)]}
    for attempt in range(90):
        try:
            r = call(body, timeout=120)
        except Exception:
            time.sleep(4)
            continue
        if r.status_code == 200:
            d = r.json()
            ok = "pointclouds" in d
            record("PASS" if ok else "FAIL", 200, "wake",
                   f"attempts={attempt+1}")
            return
        if r.status_code in (404, 502, 503, 504):
            time.sleep(4)
            continue
        record("FAIL", r.status_code, "wake", r.text[:120])
        return
    record("FAIL", 503, "wake", "timed out after 90 attempts")


# ── 2-15. Checks ────────────────────────────────────────────────────
def checks():
    img1 = png_b64(42, 64, 64)
    img2 = png_b64(43, 64, 64)

    # 2. response schema
    r = call({"model": MODEL, "images": [img1, img2]})
    d = r.json() if r.status_code == 200 else {}
    expected_keys = {"model", "num_images", "alignment_loss", "pointclouds"}
    has_keys = expected_keys.issubset(set(d.keys()))
    record("PASS" if r.status_code == 200 and has_keys else "FAIL",
           r.status_code, "response schema", f"keys={sorted(d.keys())}")

    # 3. model echo
    record("PASS" if d.get("model") == MODEL else "FAIL",
           r.status_code, "model echo", d.get("model", "missing"))

    # 4. num_images == 2
    record("PASS" if d.get("num_images") == 2 else "FAIL",
           r.status_code, "num_images", str(d.get("num_images", "missing")))

    # 5. pointclouds is list of 2
    pcs = d.get("pointclouds", [])
    record("PASS" if isinstance(pcs, list) and len(pcs) == 2 else "FAIL",
           r.status_code, "pointclouds count", f"len={len(pcs)}")

    # 6. pointcloud entry schema
    if pcs:
        pc = pcs[0]
        pc_keys = {"image_idx", "num_points", "returned_points", "pts3d", "confidence"}
        has_pc_keys = pc_keys.issubset(set(pc.keys()))
        record("PASS" if has_pc_keys else "FAIL",
               r.status_code, "pointcloud entry schema", f"keys={sorted(pc.keys())}")
    else:
        record("FAIL", r.status_code, "pointcloud entry schema", "no pointclouds")

    # 7. pts3d contains 3D points (each [x,y,z])
    if pcs and pcs[0].get("pts3d"):
        pt = pcs[0]["pts3d"][0]
        is_3d = isinstance(pt, list) and len(pt) == 3
        record("PASS" if is_3d else "FAIL",
               r.status_code, "pts3d are [x,y,z]", f"first_pt={pt}")
    else:
        record("FAIL", r.status_code, "pts3d are [x,y,z]", "no points")

    # 8. confidence values are positive floats
    if pcs and pcs[0].get("confidence"):
        confs = pcs[0]["confidence"]
        all_pos = all(isinstance(c, (int, float)) and c > 0 for c in confs[:20])
        record("PASS" if all_pos else "FAIL",
               r.status_code, "confidence positive", f"first5={confs[:5]}")
    else:
        record("FAIL", r.status_code, "confidence positive", "no confidence")

    # 9. alignment_loss is finite number
    loss = d.get("alignment_loss")
    loss_ok = isinstance(loss, (int, float)) and loss > 0
    record("PASS" if loss_ok else "FAIL",
           r.status_code, "alignment_loss", str(loss))

    # 10. max_points parameter limits output
    r2 = call({"model": MODEL, "images": [img1, img2], "max_points": 50})
    d2 = r2.json() if r2.status_code == 200 else {}
    pcs2 = d2.get("pointclouds", [])
    if pcs2:
        ok = pcs2[0].get("returned_points", 9999) <= 50
        record("PASS" if ok else "FAIL",
               r2.status_code, "max_points=50 limit",
               f"returned={pcs2[0].get('returned_points')}")
    else:
        record("FAIL", r2.status_code, "max_points=50 limit", "no response")

    # 11. bbox present
    if pcs and pcs[0].get("bbox"):
        bbox = pcs[0]["bbox"]
        has_minmax = "min" in bbox and "max" in bbox
        record("PASS" if has_minmax else "FAIL",
               r.status_code, "bbox present", f"bbox={bbox}")
    else:
        record("FAIL", r.status_code, "bbox present", "no bbox")

    # 12. determinism — same inputs same loss (within tolerance)
    r3a = call({"model": MODEL, "images": [img1, img2], "max_points": 100})
    r3b = call({"model": MODEL, "images": [img1, img2], "max_points": 100})
    if r3a.status_code == 200 and r3b.status_code == 200:
        la = r3a.json().get("alignment_loss", 0)
        lb = r3b.json().get("alignment_loss", 0)
        close = abs(la - lb) / max(abs(la), 1e-9) < 0.1
        record("PASS" if close else "FAIL",
               200, "determinism", f"loss_a={la:.4f} loss_b={lb:.4f}")
    else:
        record("FAIL", r3a.status_code, "determinism", "request failed")

    # 13. guard — fewer than 2 images
    rg1 = call({"model": MODEL, "images": [img1]})
    record("EXP" if rg1.status_code >= 400 else "FAIL",
           rg1.status_code, "guard <2 images", rg1.text[:80])

    # 14. guard — bad model
    rg2 = httpx.post(EP, json={"model": "fake-nope-999", "images": [img1, img2]}, timeout=60, headers=_HEADERS)
    record("EXP" if rg2.status_code == 404 else "FAIL",
           rg2.status_code, "guard bad model", rg2.text[:80])

    # 15. guard — empty images list
    rg3 = call({"model": MODEL, "images": []})
    record("EXP" if rg3.status_code >= 400 else "FAIL",
           rg3.status_code, "guard empty images", rg3.text[:80])


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
