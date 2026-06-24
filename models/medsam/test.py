"""medsam medical image segmentation gateway test (run inside the gateway pod).

Segmentation battery for MedSAM (flaviagiammarino/medsam-vit-base, GPU).
Accepts image (HxW RGB array) + bounding box prompts, returns masks + scores.

Run:  cat models/medsam/test.py | kubectl exec -i -n models deploy/model-gateway -c gateway -- python3 -
"""
import httpx, os, time

G = "http://localhost:8080"
MODEL = os.environ.get("MODEL", "medsam")
EP = "/v1/science/segment"
results = []


def record(icon, status, name, detail):
    results.append((icon, status, name, detail)); print(f"[{icon}] {status} | {name}: {detail}", flush=True)


def seg(body, timeout=300):
    body = {**body, "model": MODEL}
    try:
        r = httpx.post(f"{G}{EP}", json=body, timeout=timeout)
        try: return r, r.json()
        except Exception: return r, {}
    except Exception:
        return None, {}


def make_image(w=32, h=32, seed=42):
    """Synthetic HxW RGB array (no PIL needed)."""
    s = seed & 0x7FFFFFFF
    rows = []
    for _ in range(h):
        row = []
        for _ in range(w):
            px = []
            for _ in range(3):
                s = (1103515245 * s + 12345) & 0x7FFFFFFF; px.append(s % 256)
            row.append(px)
        rows.append(row)
    return rows


def wake():
    img = make_image(16, 16, 1)
    box = [[0, 0, 16, 16]]
    for attempt in range(72):
        r, d = seg({"image": img, "boxes": box})
        if r is not None and r.status_code == 200:
            has_masks = "masks" in d
            record("PASS" if has_masks else "FAIL", 200, "WAKE segment", f"attempts={attempt+1} has_masks={has_masks}")
            return
        if r is None or r.status_code in (503, 502, 504, 404): time.sleep(5); continue
        record("FAIL", r.status_code, "WAKE segment", f"body={r.text[:120]}"); return
    record("FAIL", 0, "WAKE segment", "timed out")


def checks():
    img32 = make_image(32, 32, 10)

    # 2. basic segmentation with box
    r, d = seg({"image": img32, "boxes": [[4, 4, 28, 28]]})
    has_masks = isinstance(d.get("masks"), list) and len(d["masks"]) > 0
    record("PASS" if r.status_code == 200 and has_masks else "FAIL",
           r.status_code, "basic segment", f"has_masks={has_masks}")

    # 3. scores returned
    has_scores = isinstance(d.get("scores"), list) and len(d["scores"]) > 0
    record("PASS" if has_scores else "FAIL", r.status_code, "scores returned", f"has_scores={has_scores}")

    # 4. model echo
    record("PASS" if d.get("model") == "medsam" else "FAIL", r.status_code, "model echo", f"model={d.get('model')!r}")

    # 5. image_size returned
    isz = d.get("image_size")
    record("PASS" if isz == [32, 32] else "FAIL", r.status_code, "image_size", f"got={isz}")

    # 6. full-image box (no explicit box → should default)
    r, d = seg({"image": img32})
    record("PASS" if r.status_code == 200 and "masks" in d else "FAIL",
           r.status_code, "default box", f"status={r.status_code}")

    # 7. multi-box prompt
    r, d = seg({"image": img32, "boxes": [[0, 0, 16, 16], [16, 16, 32, 32]]})
    record("PASS" if r.status_code == 200 and "masks" in d else "FAIL",
           r.status_code, "multi-box", f"status={r.status_code}")

    # 8. small image (8x8)
    img8 = make_image(8, 8, 20)
    r, d = seg({"image": img8, "boxes": [[0, 0, 8, 8]]})
    record("PASS" if r.status_code == 200 and "masks" in d else "FAIL",
           r.status_code, "small image 8x8", f"status={r.status_code}")

    # 9. rectangular image
    img_rect = make_image(48, 24, 30)
    r, d = seg({"image": img_rect, "boxes": [[5, 5, 40, 20]]})
    record("PASS" if r.status_code == 200 and "masks" in d else "FAIL",
           r.status_code, "rect image 48x24", f"status={r.status_code}")

    # 10. missing image → error
    r, d = seg({"boxes": [[0, 0, 10, 10]]})
    record("PASS" if r is not None and r.status_code == 400 else "FAIL",
           r.status_code if r else 0, "missing image 400", f"status={r.status_code if r else 'err'}")

    # 11. empty body → error
    r, d = seg({})
    record("PASS" if r is not None and r.status_code == 400 else "FAIL",
           r.status_code if r else 0, "empty body 400", f"status={r.status_code if r else 'err'}")

    # 12. deterministic (same input → same output)
    img_det = make_image(16, 16, 99)
    _, d1 = seg({"image": img_det, "boxes": [[0, 0, 16, 16]]})
    _, d2 = seg({"image": img_det, "boxes": [[0, 0, 16, 16]]})
    s1 = d1.get("scores", []); s2 = d2.get("scores", [])
    record("PASS" if s1 and s2 and str(s1) == str(s2) else "FAIL",
           200, "deterministic", f"scores_match={str(s1)==str(s2)}")

    # 13. different images → different scores
    img_a = make_image(16, 16, 50); img_b = make_image(16, 16, 77)
    _, da = seg({"image": img_a, "boxes": [[0, 0, 16, 16]]})
    _, db = seg({"image": img_b, "boxes": [[0, 0, 16, 16]]})
    sa = str(da.get("scores", [])); sb = str(db.get("scores", []))
    record("PASS" if sa != sb else "EXP", 200, "diff images diff scores", f"same={sa==sb}")

    # 14. health endpoint (gateway returns 404 for /health — expected)
    try:
        r = httpx.get(f"{G}/health", timeout=10)
        d = r.json() if r.status_code == 200 else {}
        if r.status_code == 200 and d.get("status") == "ok":
            record("PASS", r.status_code, "health endpoint", f"status={d.get('status')}")
        elif r.status_code == 404:
            record("EXP", r.status_code, "health endpoint", "gateway returns 404 for /health")
        else:
            record("FAIL", r.status_code, "health endpoint", f"status={d.get('status')}")
    except Exception as e:
        record("EXP", 0, "health endpoint", f"gateway no /health: {e}")

    # 15. mask is boolean array
    r, d = seg({"image": img32, "boxes": [[4, 4, 28, 28]]})
    masks = d.get("masks", [])
    flat = []
    def _flatten(x):
        if isinstance(x, list):
            for i in x: _flatten(i)
        else: flat.append(x)
    if masks: _flatten(masks)
    all_bool = all(isinstance(v, bool) for v in flat[:100]) if flat else False
    record("PASS" if all_bool else "FAIL", r.status_code, "mask is boolean", f"sample_bool={all_bool} count={len(flat)}")

    # 16. scores are floats in [0,1]
    scores = d.get("scores", [])
    flat_scores = []
    def _flat_s(x):
        if isinstance(x, list):
            for i in x: _flat_s(i)
        else: flat_scores.append(x)
    _flat_s(scores)
    in_range = all(isinstance(s, (int, float)) and 0 <= s <= 1 for s in flat_scores) if flat_scores else False
    record("PASS" if in_range else "FAIL", r.status_code, "scores in [0,1]", f"range_ok={in_range} n={len(flat_scores)}")


def summary():
    p = sum(1 for i, *_ in results if i == "PASS"); f = sum(1 for i, *_ in results if i == "FAIL")
    e = sum(1 for i, *_ in results if i == "EXP")
    print(f"\n== {MODEL}: {p} PASS / {e} EXP / {f} FAIL of {len(results)} ==", flush=True); return 0 if f == 0 else 1


if __name__ == "__main__":
    wake(); checks()
    raise SystemExit(summary())
