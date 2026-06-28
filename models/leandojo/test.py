"""leandojo test — POST /v1/science/retrieve {goal, num_premises}.

LeanDojo retrieves relevant Lean 4 Mathlib premises for a proof goal. Sanity: premises non-empty,
each has a name + numeric score.
Run: GW_URL=https://inference.vulcan.alliancecan.ca TYK_KEY=<key> GW_INSECURE=1 MODEL=leandojo python3 models/leandojo/test.py
"""
import httpx, os, time

G = os.environ.get("GW_URL", "http://localhost:8080").rstrip("/")
_KEY = os.environ.get("TYK_KEY")
_HEADERS = {"Authorization": f"Bearer {_KEY}"} if _KEY else {}
_VERIFY = os.environ.get("GW_INSECURE", "").lower() not in ("1", "true", "yes", "on")
MODEL = os.environ.get("MODEL", "leandojo")
ENDPOINT = "/v1/science/retrieve"
PAYLOAD = {"model": MODEL, "goal": "∀ n : ℕ, n + 0 = n", "num_premises": 5}
results = []


def req(body, timeout=300):
    return httpx.post(f"{G}{ENDPOINT}", json=body, timeout=timeout, headers=_HEADERS, verify=_VERIFY)


def record(icon, status, name, detail):
    results.append((icon, status, name, detail))
    print(f"[{icon}] {status} | {name}: {detail}", flush=True)


def wake():
    for attempt in range(72):
        r = req(PAYLOAD)
        if r.status_code == 200:
            record("PASS", 200, "WAKE + retrieve", f"attempts={attempt+1}"); return r.json()
        if r.status_code in (502, 503, 504):
            time.sleep(5); continue
        if r.status_code == 404 and attempt < 24:
            time.sleep(5); continue
        record("FAIL", r.status_code, "WAKE + retrieve", f"unexpected body={r.text[:120]}"); return None
    record("FAIL", 503, "WAKE + retrieve", "timed out waiting for warm model"); return None


def shape(d):
    ok = isinstance(d.get("premises"), list) and len(d["premises"]) > 0
    record("PASS" if ok else "FAIL", 200, "SHAPE", f"keys={sorted(d.keys())} n_premises={len(d.get('premises') or [])}")


def sanity(d):
    prem = d.get("premises") or []
    ok = len(prem) > 0 and all(isinstance(p.get("name"), str) and p.get("name")
                               and isinstance(p.get("score"), (int, float)) for p in prem)
    top = prem[0] if prem else {}
    record("PASS" if ok else "FAIL", 200, "SANITY", f"top_premise={top.get('name')!r} score={top.get('score')}")


def catalog():
    r = httpx.get(f"{G}/v1/models?all=true", headers=_HEADERS, verify=_VERIFY, timeout=30)
    m = next((x for x in r.json().get("data", []) if x["id"] == MODEL), None)
    record("PASS" if m else "FAIL", r.status_code, "Catalog entry",
           f"type={m.get('type') if m else 'MISSING'}")


if __name__ == "__main__":
    print("=" * 66, flush=True); print(f"{MODEL} retrieve test ({ENDPOINT})", flush=True)
    print("=" * 66, flush=True)
    d = wake()
    if d:
        for t in (shape, sanity, catalog):
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
