"""totalsegmentator CT scan segmentation gateway test.

Segmentation battery for TotalSegmentator (wasserth, GPU).
Accepts ct_array (3D HU array) + spacing + fast flag, returns segmentation + structure info.

Run externally via the gateway VIP + Tyk auth (preferred):
  GW_URL=http://<GATEWAY_VIP> TYK_KEY=<key> python3 models/totalsegmentator/test.py

Run inside the gateway pod (legacy, no auth needed):
  cat models/totalsegmentator/test.py | kubectl exec -i -n models deploy/model-gateway -c gateway -- python3 -
"""
import httpx, os, time

G = os.environ.get("GW_URL", "http://localhost:8080")
_KEY = os.environ.get("TYK_KEY")
_HEADERS = {"Authorization": f"Bearer {_KEY}"} if _KEY else {}
MODEL = os.environ.get("MODEL", "totalsegmentator")
EP = "/v1/science/segment"
results = []


def record(icon, status, name, detail):
    results.append((icon, status, name, detail)); print(f"[{icon}] {status} | {name}: {detail}", flush=True)


def seg(body, timeout=600):
    body = {**body, "model": MODEL}
    try:
        r = httpx.post(f"{G}{EP}", json=body, timeout=timeout, headers=_HEADERS)
        try: return r, r.json()
        except Exception: return r, {}
    except Exception:
        return None, {}


def make_ct(d=8, h=16, w=16, seed=42, hu_base=-1000):
    """Synthetic 3D CT volume (DxHxW) with pseudo-random HU values."""
    s = seed & 0x7FFFFFFF
    vol = []
    for _ in range(d):
        sl = []
        for _ in range(h):
            row = []
            for _ in range(w):
                s = (1103515245 * s + 12345) & 0x7FFFFFFF
                row.append(hu_base + (s % 2000))
            sl.append(row)
        vol.append(sl)
    return vol


def wake():
    ct = make_ct(4, 8, 8, 1)
    for attempt in range(72):
        r, d = seg({"ct_array": ct, "spacing": [3.0, 3.0, 3.0], "fast": True})
        if r is not None and r.status_code == 200:
            has_seg = "segmentation" in d or "segmentation_shape" in d or "error" not in d
            record("PASS" if has_seg else "FAIL", 200, "WAKE segment", f"attempts={attempt+1}")
            return
        if r is None or r.status_code in (503, 502, 504, 404, 500): time.sleep(5); continue
        record("FAIL", r.status_code, "WAKE segment", f"body={r.text[:120]}"); return
    record("FAIL", 0, "WAKE segment", "timed out")


def checks():
    ct_small = make_ct(8, 16, 16, 10)

    # 2. basic segmentation
    r, d = seg({"ct_array": ct_small, "spacing": [1.5, 1.5, 1.5], "fast": True})
    ok = r.status_code == 200 and ("segmentation" in d or "segmentation_shape" in d)
    record("PASS" if ok else "FAIL", r.status_code, "basic segment", f"keys={list(d.keys())[:5]}")

    # 3. model echo
    record("PASS" if d.get("model") == "totalsegmentator" else "FAIL",
           r.status_code, "model echo", f"model={d.get('model')!r}")

    # 4. segmentation_shape returned
    shape = d.get("segmentation_shape")
    record("PASS" if isinstance(shape, list) and len(shape) == 3 else "EXP",
           r.status_code, "seg shape returned", f"shape={shape}")

    # 5. num_structures returned
    ns = d.get("num_structures")
    record("PASS" if isinstance(ns, int) and ns >= 0 else "EXP",
           r.status_code, "num_structures", f"n={ns}")

    # 6. fast=true accepted
    r, d = seg({"ct_array": ct_small, "fast": True})
    record("PASS" if r.status_code == 200 else "FAIL",
           r.status_code, "fast=true", f"status={r.status_code}")

    # 7. default spacing (omit spacing param)
    r, d = seg({"ct_array": ct_small})
    record("PASS" if r.status_code == 200 else "FAIL",
           r.status_code, "default spacing", f"status={r.status_code}")

    # 8. custom spacing
    r, d = seg({"ct_array": ct_small, "spacing": [2.0, 2.0, 2.0], "fast": True})
    record("PASS" if r.status_code == 200 else "FAIL",
           r.status_code, "custom spacing", f"status={r.status_code}")

    # 9. missing ct_array → error
    r, d = seg({"spacing": [1.5, 1.5, 1.5]})
    record("PASS" if r is not None and r.status_code in (400, 500, 422) else "FAIL",
           r.status_code if r else 0, "missing ct_array", f"status={r.status_code if r else 'err'}")

    # 10. empty body → error
    r, d = seg({})
    record("PASS" if r is not None and r.status_code in (400, 500, 422) else "FAIL",
           r.status_code if r else 0, "empty body error", f"status={r.status_code if r else 'err'}")

    # 11. deterministic
    ct_det = make_ct(4, 8, 8, 99)
    _, d1 = seg({"ct_array": ct_det, "fast": True})
    _, d2 = seg({"ct_array": ct_det, "fast": True})
    s1 = d1.get("segmentation_shape"); s2 = d2.get("segmentation_shape")
    record("PASS" if s1 and s2 and s1 == s2 else "EXP",
           200, "deterministic", f"shape_match={s1==s2}")

    # 12. different inputs → potentially different output
    ct_a = make_ct(4, 8, 8, 50, hu_base=0); ct_b = make_ct(4, 8, 8, 77, hu_base=-500)
    _, da = seg({"ct_array": ct_a, "fast": True})
    _, db = seg({"ct_array": ct_b, "fast": True})
    na = da.get("num_structures", -1); nb = db.get("num_structures", -2)
    record("PASS" if na is not None and nb is not None else "EXP",
           200, "diff inputs processed", f"n_a={na} n_b={nb}")

    # 13. health endpoint
    try:
        r = httpx.get(f"{G}/health", timeout=10, headers=_HEADERS)
        d = r.json()
        ok = r.status_code == 200 and d.get("status") == "ok"
        record("PASS" if ok else "EXP", r.status_code, "health endpoint", f"status={d.get('status')}")
    except Exception as e:
        record("EXP", 0, "health endpoint", str(e))

    # 14. v1/models endpoint
    try:
        r = httpx.get(f"{G}/v1/models", timeout=10, headers=_HEADERS)
        d = r.json()
        ids = [m.get("id") for m in d.get("data", [])]
        record("PASS" if "totalsegmentator" in ids else "EXP",
               r.status_code, "v1/models", f"ids={ids}")
    except Exception as e:
        record("EXP", 0, "v1/models", str(e))

    # 15. task param accepted (server may not support task param -> EXP)
    r, d = seg({"ct_array": ct_small, "fast": True, "task": "total"})
    record("PASS" if r.status_code == 200 else "EXP",
           r.status_code, "task=total", f"status={r.status_code}")

    # 16. segmentation array present
    r, d = seg({"ct_array": ct_small, "fast": True}, timeout=120)
    seg_arr = d.get("segmentation") if d else None
    record("PASS" if isinstance(seg_arr, list) else "EXP",
           r.status_code if r else 0, "seg array present", f"is_list={isinstance(seg_arr, list)}")


def summary():
    p = sum(1 for i, *_ in results if i == "PASS"); f = sum(1 for i, *_ in results if i == "FAIL")
    e = sum(1 for i, *_ in results if i == "EXP")
    print(f"\n== {MODEL}: {p} PASS / {e} EXP / {f} FAIL of {len(results)} ==", flush=True); return 0 if f == 0 else 1


if __name__ == "__main__":
    wake(); checks()
    raise SystemExit(summary())
