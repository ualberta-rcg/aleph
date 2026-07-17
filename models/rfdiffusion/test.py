"""Gateway test battery for rfdiffusion NIM.

Run inside the gateway pod:
  cat models/rfdiffusion/test.py | \
      kubectl exec -i -n models deploy/model-gateway -c gateway -- python3 -
"""
import httpx, os, time

G = os.environ.get("GW_URL", "http://localhost:8080")
_KEY = os.environ.get("TYK_KEY")
_HEADERS = {"Authorization": f"Bearer {_KEY}"} if _KEY else {}
_VERIFY = os.environ.get("GW_INSECURE", "").lower() not in ("1", "true", "yes", "on")
MODEL = os.environ.get("MODEL", "rfdiffusion")

ENDPOINT = "/v1/biology/ipd/rfdiffusion/generate"


def _fixture_pdb():
    """Fetch a small PDB fixture from RCSB (1R42, first 200 ATOM lines)."""
    try:
        r = httpx.get("https://files.rcsb.org/download/1R42.pdb", timeout=30)
        r.raise_for_status()
        lines = [l for l in r.text.splitlines() if l.startswith("ATOM")][:200]
        return "\n".join(lines)
    except Exception as e:
        raise RuntimeError(f"Failed to fetch PDB fixture: {e}")


PDB_FIXTURE = _fixture_pdb()
PAYLOAD = {
    "model": MODEL,
    "input_pdb": PDB_FIXTURE,
    "contigs": "A19-42/0 5-10",
    "hotspot_res": ["A30"],
    "diffusion_steps": 5
}
results = []


def req(method, path, body=None, timeout=600):
    return httpx.request(method, f"{G}{path}", json=body, timeout=timeout,
                         headers=_HEADERS, verify=_VERIFY)


def record(icon, status, name, detail):
    results.append((icon, status, name, detail))
    print(f"[{icon}] {status} | {name}: {detail}", flush=True)


def wake():
    for attempt in range(72):
        r = req("POST", ENDPOINT, PAYLOAD)
        if r.status_code == 200:
            record("PASS", 200, "WAKE + generate", f"attempts={attempt+1}")
            return
        if r.status_code in (502, 503, 504):
            time.sleep(5); continue
        if r.status_code == 404 and attempt < 24:
            time.sleep(5); continue
        record("FAIL", r.status_code, "WAKE + generate", f"body={r.text[:120]}")
        return
    record("FAIL", 503, "WAKE + generate", "timed out waiting for warm model")


def shape():
    r = req("POST", ENDPOINT, PAYLOAD)
    if r.status_code != 200:
        record("FAIL", r.status_code, "SHAPE", f"body={r.text[:120]}"); return
    d = r.json()
    ok = isinstance(d.get("output_pdb"), str) and len(d["output_pdb"]) > 0
    record("PASS" if ok else "FAIL", r.status_code, "SHAPE",
           f"output_pdb_chars={len(d.get('output_pdb', ''))}")


def sanity():
    r = req("POST", ENDPOINT, PAYLOAD)
    if r.status_code != 200:
        record("FAIL", r.status_code, "SANITY", f"body={r.text[:120]}"); return
    d = r.json()
    pdb = d.get("output_pdb", "")
    ok = isinstance(pdb, str) and pdb.startswith("ATOM") and "\n" in pdb
    record("PASS" if ok else "FAIL", r.status_code, "SANITY",
           f"atoms={pdb.count(chr(10))}")


def catalog():
    r = req("GET", "/v1/models?all=true")
    m = next((x for x in r.json().get("data", []) if x["id"] == MODEL), None)
    if not m:
        record("FAIL", 0, "Catalog entry", "not found"); return
    record("PASS", r.status_code, "Catalog entry", f"type={m.get('type')} endpoint={m.get('endpoint')}")


BATTERY = [wake, shape, sanity, catalog]

if __name__ == "__main__":
    print("=" * 66, flush=True)
    print(f"{MODEL} science test ({ENDPOINT})", flush=True)
    print("=" * 66, flush=True)
    for t in BATTERY:
        try:
            t()
        except Exception as e:
            record("ERR", 0, t.__name__, str(e)[:120])
    p = sum(1 for x in results if x[0] == "PASS")
    e = sum(1 for x in results if x[0] == "EXP")
    f = sum(1 for x in results if x[0] in ("FAIL", "ERR"))
    s = sum(1 for x in results if x[0] == "SKIP")
    print(f"\n{'=' * 66}\nResults: {p} passed, {e} expected, {f} failed/err, {s} skipped of {len(results)}",
          flush=True)
