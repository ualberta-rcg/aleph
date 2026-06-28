"""mattersim force-field test — POST /v1/science/predict {elements, positions, lattice}.

MatterSim predicts energy (eV + eV/atom), per-atom forces, and stress. Also exercises the
/v1/science/relax (BFGS) endpoint. Sanity: energy finite, forces shaped [n_atoms][3].
Run: GW_URL=https://inference.vulcan.alliancecan.ca TYK_KEY=<key> GW_INSECURE=1 MODEL=mattersim python3 models/mattersim/test.py
"""
import httpx, os, time, math

G = os.environ.get("GW_URL", "http://localhost:8080").rstrip("/")
_KEY = os.environ.get("TYK_KEY")
_HEADERS = {"Authorization": f"Bearer {_KEY}"} if _KEY else {}
_VERIFY = os.environ.get("GW_INSECURE", "").lower() not in ("1", "true", "yes", "on")
MODEL = os.environ.get("MODEL", "mattersim")

# Si diamond cell, 2 atoms (periodic → stress).
PREDICT = {
    "model": MODEL,  # gateway routing field (server ignores it)
    "elements": ["Si", "Si"],
    "positions": [[0, 0, 0], [1.35, 1.35, 1.35]],
    "lattice": [[2.7, 2.7, 0], [2.7, 0, 2.7], [0, 2.7, 2.7]],
}
RELAX = dict(PREDICT, fmax=0.05, steps=50)
results = []


def req(path, body, timeout=200):
    return httpx.post(f"{G}{path}", json=body, timeout=timeout, headers=_HEADERS, verify=_VERIFY)


def record(icon, status, name, detail):
    results.append((icon, status, name, detail))
    print(f"[{icon}] {status} | {name}: {detail}", flush=True)


def _finite(x):
    return all(math.isfinite(v) for v in x)


def wake():
    for attempt in range(72):
        r = req("/v1/science/predict", PREDICT)
        if r.status_code == 200:
            record("PASS", 200, "WAKE + predict", f"attempts={attempt+1}"); return r.json()
        if r.status_code in (502, 503, 504):
            time.sleep(5); continue
        if r.status_code == 404 and attempt < 24:
            time.sleep(5); continue
        record("FAIL", r.status_code, "WAKE + predict", f"unexpected body={r.text[:90]}"); return None
    record("FAIL", 503, "WAKE + predict", "timed out waiting for warm model"); return None


def shape(d):
    ok = {"energy_ev", "forces_ev_per_angstrom"} <= set(d)
    record("PASS" if ok else "FAIL", 200, "SHAPE", f"keys={sorted(d.keys())}")


def sanity(d):
    e = d.get("energy_ev"); f = d.get("forces_ev_per_angstrom")
    n = len(PREDICT["elements"])
    ok = (isinstance(e, (int, float)) and math.isfinite(e)
          and isinstance(f, list) and len(f) == n and all(len(row) == 3 and _finite(row) for row in f))
    record("PASS" if ok else "FAIL", 200, "SANITY",
           f"energy={e} forces_shape=[{len(f) if isinstance(f,list) else '?'}][3] (n_atoms={n})")


def stress(d):
    s = d.get("stress_gpa")
    ok = isinstance(s, list) and _finite(s)  # periodic → stress present
    record("PASS" if ok else "FAIL", 200, "SANITY stress", f"stress_gpa={s}")


def relax_ep():
    r = req("/v1/science/relax", RELAX, timeout=300)
    d = r.json() if r.status_code == 200 else {}
    ok = r.status_code == 200 and "relaxed_positions" in d and "converged" in d
    record("PASS" if ok else "FAIL", r.status_code, "RELAX endpoint",
           f"converged={d.get('converged')} steps={d.get('steps')}")


def model_echo(d):
    record("PASS" if d.get("model") == MODEL else "FAIL", 200, "MODEL-ECHO", f"model={d.get('model')!r}")


def catalog():
    r = httpx.get(f"{G}/v1/models?all=true", headers=_HEADERS, verify=_VERIFY, timeout=30)
    m = next((x for x in r.json().get("data", []) if x["id"] == MODEL), None)
    record("PASS" if m else "FAIL", r.status_code, "Catalog entry",
           f"type={m.get('type') if m else 'MISSING'}")


if __name__ == "__main__":
    print("=" * 66, flush=True); print(f"{MODEL} force-field test (/v1/science/predict + /relax)", flush=True)
    print("=" * 66, flush=True)
    d = wake()
    if d:
        for t in (shape, sanity, stress, model_echo):
            try:
                t(d)
            except Exception as e:
                record("ERR", 0, t.__name__, str(e)[:120])
        try:
            relax_ep()
        except Exception as e:
            record("ERR", 0, "relax_ep", str(e)[:120])
        catalog()
    else:
        catalog()
    p = sum(1 for x in results if x[0] == "PASS"); e = sum(1 for x in results if x[0] == "EXP")
    f = sum(1 for x in results if x[0] in ("FAIL", "ERR")); s = sum(1 for x in results if x[0] == "SKIP")
    print(f"\n{'=' * 66}\nResults: {p} passed, {e} expected, {f} failed/err, {s} skipped of {len(results)}",
          flush=True)
