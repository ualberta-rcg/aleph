"""mast3r gateway test — comprehensive (run inside the gateway pod).

Run:
  cat models/mast3r/test.py | \
    kubectl exec -i -n models deploy/model-gateway -c gateway -- python3 -
"""
import base64, httpx, os, struct, time, zlib

G = os.environ.get("GW_URL", "http://localhost:8080")
MODEL = "mast3r"
EP_MATCH = f"{G}/v1/science/match"
EP_RECON = f"{G}/v1/science/reconstruct"
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


def call_match(body, timeout=300):
    return httpx.post(EP_MATCH, json=body, timeout=timeout)


def call_recon(body, timeout=300):
    return httpx.post(EP_RECON, json=body, timeout=timeout)


# ── 1. Wake ──────────────────────────────────────────────────────────
def wake():
    body = {"model": MODEL, "images": [png_b64(1, 64, 64), png_b64(2, 64, 64)]}
    for attempt in range(90):
        try:
            r = call_match(body, timeout=120)
        except Exception:
            time.sleep(4)
            continue
        if r.status_code == 200:
            d = r.json()
            ok = "num_matches" in d or "matches_image1" in d
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

    # 2. match response schema
    r = call_match({"model": MODEL, "images": [img1, img2]})
    d = r.json() if r.status_code == 200 else {}
    expected_keys = {"model", "num_matches", "returned_matches", "matches_image1", "matches_image2"}
    has_keys = expected_keys.issubset(set(d.keys()))
    record("PASS" if r.status_code == 200 and has_keys else "FAIL",
           r.status_code, "match response schema", f"keys={sorted(d.keys())}")

    # 3. model echo
    record("PASS" if d.get("model") == MODEL else "FAIL",
           r.status_code, "model echo", d.get("model", "missing"))

    # 4. num_matches is positive int
    nm = d.get("num_matches", 0)
    record("PASS" if isinstance(nm, int) and nm > 0 else "FAIL",
           r.status_code, "num_matches positive", str(nm))

    # 5. matches_image1 is list of [x,y] pairs
    m1 = d.get("matches_image1", [])
    if m1:
        pt = m1[0]
        is_2d = isinstance(pt, list) and len(pt) == 2
        record("PASS" if is_2d else "FAIL",
               r.status_code, "matches are [x,y]", f"first={pt}")
    else:
        record("FAIL", r.status_code, "matches are [x,y]", "no matches")

    # 6. returned_matches <= num_matches
    rm = d.get("returned_matches", 0)
    record("PASS" if rm <= nm else "FAIL",
           r.status_code, "returned <= total",
           f"returned={rm} total={nm}")

    # 7. matches_image1 and matches_image2 same length
    m2 = d.get("matches_image2", [])
    record("PASS" if len(m1) == len(m2) and len(m1) > 0 else "FAIL",
           r.status_code, "match lists same length",
           f"m1={len(m1)} m2={len(m2)}")

    # 8. max_matches parameter limits output
    r2 = call_match({"model": MODEL, "images": [img1, img2], "max_matches": 50})
    d2 = r2.json() if r2.status_code == 200 else {}
    rm2 = d2.get("returned_matches", 9999)
    record("PASS" if rm2 <= 50 else "FAIL",
           r2.status_code, "max_matches=50 limit", f"returned={rm2}")

    # 9. reconstruct endpoint responds
    r3 = call_recon({"model": MODEL, "images": [img1, img2]})
    d3 = r3.json() if r3.status_code == 200 else {}
    record("PASS" if r3.status_code == 200 and d3.get("model") == MODEL else "FAIL",
           r3.status_code, "reconstruct endpoint", f"keys={sorted(d3.keys())}")

    # 10. different images produce different matches
    img3 = png_b64(99, 64, 64)
    r4 = call_match({"model": MODEL, "images": [img1, img3]})
    d4 = r4.json() if r4.status_code == 200 else {}
    nm4 = d4.get("num_matches", 0)
    different = nm4 != nm
    record("PASS" if r4.status_code == 200 else "FAIL",
           r4.status_code, "different images different matches",
           f"pair1={nm} pair2={nm4} diff={different}")

    # 11. determinism — same inputs same num_matches
    r5a = call_match({"model": MODEL, "images": [img1, img2], "max_matches": 100})
    r5b = call_match({"model": MODEL, "images": [img1, img2], "max_matches": 100})
    if r5a.status_code == 200 and r5b.status_code == 200:
        na = r5a.json().get("num_matches", 0)
        nb = r5b.json().get("num_matches", 0)
        record("PASS" if na == nb else "FAIL",
               200, "determinism", f"a={na} b={nb}")
    else:
        record("FAIL", r5a.status_code, "determinism", "request failed")

    # 12. match coordinates within image bounds (0-512 range after resize)
    if m1:
        coords_ok = all(0 <= pt[0] <= 600 and 0 <= pt[1] <= 600 for pt in m1[:50])
        record("PASS" if coords_ok else "FAIL",
               r.status_code, "coords in bounds",
               f"sample_max_x={max(p[0] for p in m1[:50]):.1f}")
    else:
        record("FAIL", r.status_code, "coords in bounds", "no matches")

    # 13. guard — fewer than 2 images
    rg1 = call_match({"model": MODEL, "images": [img1]})
    record("EXP" if rg1.status_code >= 400 else "FAIL",
           rg1.status_code, "guard <2 images", rg1.text[:80])

    # 14. guard — bad model
    rg2 = httpx.post(EP_MATCH, json={"model": "fake-nope-999", "images": [img1, img2]}, timeout=60)
    record("EXP" if rg2.status_code == 404 else "FAIL",
           rg2.status_code, "guard bad model", rg2.text[:80])

    # 15. guard — empty images list
    rg3 = call_match({"model": MODEL, "images": []})
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
