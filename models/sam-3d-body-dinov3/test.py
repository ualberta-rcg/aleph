"""sam-3d-body-dinov3 3D human mesh recovery gateway test.

Custom-server battery for SAM 3D Body (image of a person -> 3D mesh + keypoints).
Synthetic images have no people -> count 0 is acceptable; we assert well-formedness,
determinism, echo, and error handling. A real-person check is documented in README.
Run: GW_URL=https://inference.vulcan.alliancecan.ca TYK_KEY=<key> GW_INSECURE=1 python3 models/sam-3d-body-dinov3/test.py
"""
import base64, httpx, os, struct, time, zlib

G = os.environ.get("GW_URL", "http://localhost:8080")
_KEY = os.environ.get("TYK_KEY")
_HEADERS = {"Authorization": f"Bearer {_KEY}"} if _KEY else {}
_VERIFY = os.environ.get("GW_INSECURE", "").lower() not in ("1", "true", "yes", "on")
MODEL = os.environ.get("MODEL", "sam-3d-body-dinov3")
results = []


def record(icon, status, name, detail):
    results.append((icon, status, name, detail)); print(f"[{icon}] {status} | {name}: {detail}", flush=True)


def req(method, path, body=None, timeout=400):
    return httpx.request(method, f"{G}{path}", json=body, timeout=timeout, headers=_HEADERS, verify=_VERIFY)


def pose3d(body):
    r = req("POST", "/v1/science/pose3d", body)
    try: return r, r.json()
    except Exception: return r, {}


def png_b64(seed, w=64, h=64):
    raw = bytearray(); s = seed & 0x7FFFFFFF
    for _ in range(h):
        raw.append(0)
        for _ in range(w * 3):
            s = (1103515245 * s + 12345) & 0x7FFFFFFF; raw.append(s % 256)
    def chunk(typ, data):
        c = struct.pack(">I", len(data)) + typ + data
        return c + struct.pack(">I", zlib.crc32(typ + data) & 0xFFFFFFFF)
    ihdr = struct.pack(">IIBBBBB", w, h, 8, 2, 0, 0, 0)
    png = b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", ihdr) + chunk(b"IDAT", zlib.compress(bytes(raw))) + chunk(b"IEND", b"")
    return base64.b64encode(png).decode()


def wake():
    for attempt in range(110):
        r, d = pose3d({"model": MODEL, "image": png_b64(1)})
        if r.status_code == 200:
            ok = isinstance(d.get("count"), int) and isinstance(d.get("persons"), list)
            record("PASS" if ok else "FAIL", 200, "WAKE + well-formed",
                   f"attempts={attempt+1} count={d.get('count')}"); return
        if r.status_code in (503, 502, 504, 404): time.sleep(10); continue
        record("FAIL", r.status_code, "WAKE + well-formed", f"body={r.text[:100]}"); return
    record("FAIL", 0, "WAKE + well-formed", "timed out")


def checks():
    r, d = pose3d({"model": MODEL, "image": png_b64(2)})
    ok = r.status_code == 200 and "count" in d and isinstance(d.get("persons"), list) and "task" in d
    record("PASS" if ok else "FAIL", r.status_code, "well-formed response", f"count={d.get('count')} task={d.get('task')}")

    # person shape (if any found)
    persons = d.get("persons", [])
    if persons:
        p = persons[0]
        ok = "keypoints_3d" in p and "cam_t" in p and "vertex_count" in p
        record("PASS" if ok else "FAIL", 200, "person shape",
               f"kp3d={len(p.get('keypoints_3d') or [])} verts={p.get('vertex_count')} cam={p.get('cam_t')}")
    else:
        record("PASS", 200, "person shape", "no people on synthetic image (acceptable)")

    # deterministic
    _, d1 = pose3d({"model": MODEL, "image": png_b64(30)})
    _, d2 = pose3d({"model": MODEL, "image": png_b64(30)})
    record("PASS" if d1.get("count") == d2.get("count") else "FAIL", 200,
           "deterministic", f"c1={d1.get('count')} c2={d2.get('count')}")

    # return_vertices flag
    r, d = pose3d({"model": MODEL, "image": png_b64(40), "return_vertices": True})
    persons = d.get("persons", [])
    has_v = all("vertices" in p for p in persons) if persons else True
    record("PASS" if r.status_code == 200 and has_v else "FAIL", r.status_code,
           "return_vertices flag", f"persons={len(persons)} all_have_vertices={has_v}")

    # model echo
    r, d = pose3d({"model": MODEL, "image": png_b64(50)})
    record("PASS" if r.status_code == 200 and d.get("model") == MODEL else "FAIL",
           r.status_code, "model echo", f"model={d.get('model')!r}")

    # malformed
    r, _ = pose3d({"model": MODEL})
    record("PASS" if 400 <= r.status_code < 600 else "FAIL", r.status_code,
           "malformed handled", f"status={r.status_code}")

    # catalog
    r = req("GET", "/v1/models?all=true")
    m = next((x for x in r.json().get("data", []) if x.get("id") == MODEL), None)
    record("PASS" if m and m.get("type") == "pose3d" else "FAIL", r.status_code,
           "Catalog entry", f"type={m.get('type') if m else 'not found'}")


print("=" * 66, flush=True); print(f"{MODEL} 3D-pose gateway test", flush=True); print("=" * 66, flush=True)
for t in [wake, checks]:
    try: t()
    except Exception as e: record("ERR", 0, t.__name__, str(e)[:120])
p = sum(1 for x in results if x[0] == "PASS"); f = sum(1 for x in results if x[0] in ("FAIL", "ERR"))
print(f"\n{'=' * 66}\nResults: {p} passed, {f} failed/err of {len(results)}", flush=True)
