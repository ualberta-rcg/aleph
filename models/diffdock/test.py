"""diffdock docking test — POST /v1/dock {protein_pdb, ligand_smiles, num_poses}.

Docks a ligand (aspirin) into a protein (crambin, 1CRN — read from test_protein.pdb) and returns
ranked SDF poses with confidence. Sanity: poses non-empty, each has rank/confidence/sdf.
Run: GW_URL=https://inference.vulcan.alliancecan.ca TYK_KEY=<key> GW_INSECURE=1 MODEL=diffdock python3 models/diffdock/test.py
"""
import httpx, os, time

G = os.environ.get("GW_URL", "http://localhost:8080").rstrip("/")
_KEY = os.environ.get("TYK_KEY")
_HEADERS = {"Authorization": f"Bearer {_KEY}"} if _KEY else {}
_VERIFY = os.environ.get("GW_INSECURE", "").lower() not in ("1", "true", "yes", "on")
MODEL = os.environ.get("MODEL", "diffdock")
ENDPOINT = "/v1/dock"
_HERE = os.path.dirname(os.path.abspath(__file__))
PROTEIN_PDB = open(os.path.join(_HERE, "test_protein.pdb")).read()  # crambin (1CRN) ATOM records
PAYLOAD = {
    "model": MODEL,  # gateway routing field
    "protein_pdb": PROTEIN_PDB,
    "ligand_smiles": "CC(=O)Oc1ccccc1C(=O)O",  # aspirin
    "num_poses": 3,
    "inference_steps": 20,
}
results = []


def req(body, timeout=600):
    return httpx.post(f"{G}{ENDPOINT}", json=body, timeout=timeout, headers=_HEADERS, verify=_VERIFY)


def record(icon, status, name, detail):
    results.append((icon, status, name, detail))
    print(f"[{icon}] {status} | {name}: {detail}", flush=True)


def wake():
    for attempt in range(72):
        r = req(PAYLOAD)
        if r.status_code == 200:
            record("PASS", 200, "WAKE + dock", f"attempts={attempt+1}"); return r.json()
        if r.status_code in (502, 503, 504):
            time.sleep(5); continue
        if r.status_code == 404 and attempt < 24:
            time.sleep(5); continue
        record("FAIL", r.status_code, "WAKE + dock", f"unexpected body={r.text[:120]}"); return None
    record("FAIL", 503, "WAKE + dock", "timed out waiting for warm model"); return None


def shape(d):
    ok = "poses" in d and isinstance(d["poses"], list)
    record("PASS" if ok else "FAIL", 200, "SHAPE", f"keys={sorted(d.keys())} warning={d.get('warning')}")


def sanity(d):
    poses = d.get("poses") or []
    ok = len(poses) > 0 and all(
        isinstance(p.get("sdf"), str) and len(p["sdf"]) > 20
        and isinstance(p.get("confidence"), (int, float))
        and isinstance(p.get("rank"), int) for p in poses)
    record("PASS" if ok else "FAIL", 200, "SANITY",
           f"num_poses={len(poses)} top_conf={poses[0].get('confidence') if poses else 'n/a'}")


def model_echo(d):
    record("PASS" if d.get("model") == MODEL else "FAIL", 200, "MODEL-ECHO", f"model={d.get('model')!r}")


def catalog():
    r = httpx.get(f"{G}/v1/models?all=true", headers=_HEADERS, verify=_VERIFY, timeout=30)
    m = next((x for x in r.json().get("data", []) if x["id"] == MODEL), None)
    record("PASS" if m else "FAIL", r.status_code, "Catalog entry",
           f"type={m.get('type') if m else 'MISSING'}")


if __name__ == "__main__":
    print("=" * 66, flush=True); print(f"{MODEL} dock test ({ENDPOINT})", flush=True)
    print("=" * 66, flush=True)
    d = wake()
    if d:
        for t in (shape, sanity, model_echo, catalog):
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
