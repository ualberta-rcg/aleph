"""depth-anything gateway test — comprehensive (run inside the gateway pod).

Run:
  cat models/depth-anything/test.py | \
    kubectl exec -i -n models deploy/model-gateway -c gateway -- python3 -
"""
import base64, httpx, os, struct, time, zlib

G = os.environ.get("GW_URL", "http://localhost:8080")
MODEL = "depth-anything-v2"
EP = f"{G}/v1/vision/depth"
results = []


def record(icon, status, name, detail):
    results.append((icon, status, name, detail))
    print(f"[{icon}] {status} | {name}: {detail}", flush=True)


def png_b64(seed=7, w=320, h=192):
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
    return httpx.post(EP, json=body, timeout=timeout)


# ── 1. Wake ──────────────────────────────────────────────────────────
def wake():
    body = {"model": MODEL, "image": png_b64(1, 320, 192)}
    for attempt in range(90):
        try:
            r = call(body, timeout=120)
        except Exception:
            time.sleep(4)
            continue
        if r.status_code == 200:
            d = r.json()
            ok = "depth_png_base64" in d
            record("PASS" if ok else "FAIL", 200, "wake",
                   f"attempts={attempt+1}")
            return
        if r.status_code == 503:
            time.sleep(4)
            continue
        record("FAIL", r.status_code, "wake", r.text[:120])
        return
    record("FAIL", 503, "wake", "timed out")


# ── 2-18. Checks ────────────────────────────────────────────────────
def checks():
    img = png_b64(42, 320, 240)

    # 2. response schema
    r = call({"model": MODEL, "image": img})
    d = r.json() if r.status_code == 200 else {}
    expected_keys = {"model", "task", "width", "height", "depth_png_base64", "depth_grid_64", "stats"}
    has_keys = expected_keys.issubset(set(d.keys()))
    record("PASS" if r.status_code == 200 and has_keys else "FAIL",
           r.status_code, "response schema", f"keys={sorted(d.keys())}")

    # 3. model echo
    record("PASS" if d.get("model") == MODEL else "FAIL",
           r.status_code, "model echo", d.get("model", "missing"))

    # 4. task echo
    record("PASS" if d.get("task") == "depth" else "FAIL",
           r.status_code, "task echo", d.get("task", "missing"))

    # 5. width/height match input
    record("PASS" if d.get("width") == 320 and d.get("height") == 240 else "FAIL",
           r.status_code, "width/height match", f"{d.get('width')}x{d.get('height')}")

    # 6. depth_png_base64 is valid base64
    dpng = d.get("depth_png_base64", "")
    try:
        raw_png = base64.b64decode(dpng)
        is_png = raw_png[:4] == b"\x89PNG"
        record("PASS" if is_png else "FAIL",
               r.status_code, "depth PNG valid", f"starts_with_PNG={is_png} bytes={len(raw_png)}")
    except Exception as e:
        record("FAIL", r.status_code, "depth PNG valid", str(e)[:80])

    # 7. depth_grid_64 is 64x64
    grid = d.get("depth_grid_64", [])
    grid_ok = isinstance(grid, list) and len(grid) == 64 and all(len(row) == 64 for row in grid)
    record("PASS" if grid_ok else "FAIL",
           r.status_code, "depth_grid_64 is 64x64",
           f"rows={len(grid)} cols={len(grid[0]) if grid else 0}")

    # 8. grid values in 0-1
    if grid_ok:
        flat = [v for row in grid for v in row]
        vals_ok = all(0 <= v <= 1.0 for v in flat)
        record("PASS" if vals_ok else "FAIL",
               r.status_code, "grid values 0-1",
               f"min={min(flat):.4f} max={max(flat):.4f}")
    else:
        record("FAIL", r.status_code, "grid values 0-1", "bad grid")

    # 9. stats present with valid fields
    stats = d.get("stats", {})
    stats_ok = all(k in stats for k in ("raw_min", "raw_max", "raw_mean"))
    record("PASS" if stats_ok else "FAIL",
           r.status_code, "stats fields", f"stats={stats}")

    # 10. small image (64x64)
    r2 = call({"model": MODEL, "image": png_b64(10, 64, 64)})
    d2 = r2.json() if r2.status_code == 200 else {}
    record("PASS" if r2.status_code == 200 and d2.get("width") == 64 else "FAIL",
           r2.status_code, "small image 64x64", f"w={d2.get('width')}")

    # 11. large image (640x480)
    r3 = call({"model": MODEL, "image": png_b64(11, 640, 480)})
    d3 = r3.json() if r3.status_code == 200 else {}
    record("PASS" if r3.status_code == 200 and d3.get("width") == 640 else "FAIL",
           r3.status_code, "large image 640x480", f"w={d3.get('width')}")

    # 12. square image (256x256)
    r4 = call({"model": MODEL, "image": png_b64(12, 256, 256)})
    record("PASS" if r4.status_code == 200 else "FAIL",
           r4.status_code, "square image 256x256", "")

    # 13. data-URI prefix
    data_uri = "data:image/png;base64," + png_b64(13, 128, 128)
    r5 = call({"model": MODEL, "image": data_uri})
    record("PASS" if r5.status_code == 200 else "FAIL",
           r5.status_code, "data-URI prefix strip", "")

    # 14. sequential 5-image batch
    batch_ok = True
    for i in range(5):
        rb = call({"model": MODEL, "image": png_b64(100 + i, 128, 128)})
        if rb.status_code != 200:
            batch_ok = False
            break
    record("PASS" if batch_ok else "FAIL",
           200 if batch_ok else rb.status_code,
           "sequential 5-image batch", "all 200" if batch_ok else f"failed i={i}")

    # 15. determinism
    img_d = png_b64(999, 128, 128)
    r6a = call({"model": MODEL, "image": img_d})
    r6b = call({"model": MODEL, "image": img_d})
    if r6a.status_code == 200 and r6b.status_code == 200:
        sa, sb = r6a.json().get("stats", {}), r6b.json().get("stats", {})
        same = abs(sa.get("raw_mean", 0) - sb.get("raw_mean", 0)) < 0.01
        record("PASS" if same else "FAIL",
               200, "determinism same image",
               f"mean={sa.get('raw_mean', 0):.4f}/{sb.get('raw_mean', 0):.4f}")
    else:
        record("FAIL", r6a.status_code, "determinism same image", "request failed")

    # 16. guard — bad model
    rg1 = httpx.post(EP, json={"model": "fake-nope-999", "image": png_b64(3)}, timeout=60)
    record("EXP" if rg1.status_code == 404 else "FAIL",
           rg1.status_code, "guard bad model", rg1.text[:80])

    # 17. guard — missing image
    rg2 = httpx.post(EP, json={"model": MODEL}, timeout=60)
    record("EXP" if rg2.status_code >= 400 else "FAIL",
           rg2.status_code, "guard missing image", rg2.text[:80])

    # 18. guard — empty image
    rg3 = call({"model": MODEL, "image": ""})
    record("EXP" if rg3.status_code >= 400 else "FAIL",
           rg3.status_code, "guard empty image", rg3.text[:80])


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
