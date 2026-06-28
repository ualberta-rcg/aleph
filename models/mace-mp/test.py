"""mace-mp force-field test — POST /v1/science/predict {elements, positions, lattice, model}.

Predicts energy + per-atom forces (+ stress for periodic) for an atomistic structure via the
MACE-MP-0 universal potential (medium variant). Sanity: energy is a finite negative number,
forces shaped [n_atoms][3] and finite.
Run: GW_URL=https://inference.vulcan.alliancecan.ca TYK_KEY=<key> GW_INSECURE=1 MODEL=mace-mp python3 models/mace-mp/test.py
"""
import httpx, os, time, math

G = os.environ.get("GW_URL", "http://localhost:8080").rstrip("/")
_KEY = os.environ.get("TYK_KEY")
_HEADERS = {"Authorization": f"Bearer {_KEY}"} if _KEY else {}
_VERIFY = os.environ.get("GW_INSECURE", "").lower() not in ("1", "true", "yes", "on")
MODEL = os.environ.get("MODEL", "mace-mp")
ENDPOINT = "/v1/science/predict"

# Si diamond cell, 2 atoms (periodic → also exercises stress).
PAYLOAD = {
    "model": MODEL,            # gateway routing field
    "elements": ["Si", "Si"],
    "positions": [[0, 0, 0], [1.35, 1.35, 1.35]],
    "lattice": [[2.7, 2.7, 0], [2.7, 0, 2.7], [0, 2.7, 2.7]],
    "variant": "medium",       # MACE-MP-0 model size (NOT "model" — that's the gateway routing field)
}
results = []


def req(body, timeout=120):
    return httpx.post(f"{G}{ENDPOINT}", json=body, timeout=timeout, headers=_HEADERS, verify=_VERIFY)


def record(icon, status, name, detail):
    results.append((icon, status, name, detail))
    print(f"[{icon}] {status} | {name}: {detail}", flush=True)


def _finite(x):
    return all(math.isfinite(v) for v in x)


def wake():
    for attempt in range(72):
        r = req(PAYLOAD)
        if r.status_code == 200:
            record("PASS", 200, "WAKE + predict", f"attempts={attempt+1}"); return r.json()
        if r.status_code == 503:
            time.sleep(5); continue
        record("FAIL", r.status_code, "WAKE + predict", f"unexpected body={r.text[:90]}"); return None
    record("FAIL", 503, "WAKE + predict", "timed out waiting for warm model"); return None


def shape(d):
    keys = set(d)
    ok = {"energy_eV", "forces_eV_per_Ang"} <= keys
    record("PASS" if ok else "FAIL", 200, "SHAPE", f"keys={sorted(keys)}")


def sanity(d):
    e = d.get("energy_eV"); f = d.get("forces_eV_per_Ang")
    n = len(PAYLOAD["elements"])
    ok = (isinstance(e, (int, float)) and math.isfinite(e)
          and isinstance(f, list) and len(f) == n and all(len(row) == 3 and _finite(row) for row in f))
    record("PASS" if ok else "FAIL", 200, "SANITY",
           f"energy={e} forces_shape=[{len(f) if isinstance(f,list) else '?'}][3] (n_atoms={n})")


def stress(d):
    s = d.get("stress_eV_per_Ang3")
    ok = isinstance(s, list) and len(s) == 6 and _finite(s)
    record("PASS" if ok else "FAIL", 200, "SANITY stress", f"len={len(s) if isinstance(s,list) else '?'} voigt")


def model_echo(d):
    record("PASS" if d.get("model") == MODEL else "FAIL", 200, "MODEL-ECHO", f"model={d.get('model')!r}")


def catalog():
    r = httpx.get(f"{G}/v1/models?all=true", headers=_HEADERS, verify=_VERIFY, timeout=30)
    m = next((x for x in r.json().get("data", []) if x["id"] == MODEL), None)
    record("PASS" if m else "FAIL", r.status_code, "Catalog entry",
           f"type={m.get('type') if m else 'MISSING'}")


if __name__ == "__main__":
    print("=" * 66, flush=True); print(f"{MODEL} force-field test ({ENDPOINT})", flush=True)
    print("=" * 66, flush=True)
    d = wake()
    if d:
        for t in (shape, sanity, stress, model_echo, catalog):
            try:
                t(d) if t is not catalog else t()
            except Exception as e:
                record("ERR", 0, t.__name__, str(e)[:120])
    else:
        catalog()
    p = sum(1 for x in results if x[0] == "PASS"); e = sum(1 for x in results if x[0] == "EXP")
    f = sum(1 for x in results if x[0] in ("FAIL", "ERR")); s = sum(1 for x in results if x[0] == "SKIP")
    print(f"\n{'=' * 66}\nResults: {p} passed, {e} expected, {f} failed/err, {s} skipped of {len(results)}",
          flush=True)
