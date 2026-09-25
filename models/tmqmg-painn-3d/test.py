"""tmqmg-painn-3d test — POST /v1/science/predict {model?, id?, charge, xyz}.

Five-member PaiNN ensemble: excited-state screening (30 vertical singlet states,
gas phase + acetone) for mononuclear transition-metal complexes from an XYZ
geometry and formal charge. The model ships its own regression oracle
(examples/example_request.json -> examples/example_prediction.json, the YADPOK
V-complex) — reused here directly instead of inventing new expected values.

Run: GW_URL=https://inference.vulcan.alliancecan.ca TYK_KEY=<key> MODEL=tmqmg-painn-3d \
  python3 models/tmqmg-painn-3d/test.py
"""
import json, math, os, ssl, time
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

G = os.environ.get("GW_URL", "http://localhost:8080").rstrip("/")
_KEY = os.environ.get("TYK_KEY")
_HEADERS = {"Authorization": f"Bearer {_KEY}"} if _KEY else {}
_VERIFY = os.environ.get("GW_INSECURE", "").lower() not in ("1", "true", "yes", "on")
_SSL_CTX = ssl.create_default_context() if _VERIFY else ssl._create_unverified_context()
MODEL = os.environ.get("MODEL", "tmqmg-painn-3d")
ENDPOINT = "/v1/science/predict"


class _Resp:
    """Minimal httpx-like response wrapper over urllib (stdlib only — no httpx
    module available on the Vulcan login node's default python3)."""

    def __init__(self, status_code, text):
        self.status_code = status_code
        self.text = text

    def json(self):
        return json.loads(self.text)


def _http(method, url, json_body=None, timeout=120):
    data = json.dumps(json_body).encode("utf-8") if json_body is not None else None
    headers = {**_HEADERS, "Content-Type": "application/json"} if data else dict(_HEADERS)
    request = Request(url, data=data, headers=headers, method=method)
    try:
        with urlopen(request, timeout=timeout, context=_SSL_CTX) as response:
            return _Resp(response.status, response.read().decode("utf-8"))
    except HTTPError as error:
        return _Resp(error.code, error.read().decode("utf-8", errors="replace"))
    except URLError as error:
        return _Resp(0, str(error.reason))

# The model's own checked-in fixture + frozen regression reference (YADPOK, a
# 41-atom neutral V complex). Source: tmqmg-painn-3d/examples/, scripts/smoke_test.py.
FIXTURE_DIR = Path(os.environ.get("TMQMG_FIXTURE_DIR", Path(__file__).resolve().parent))
_example_request = json.loads((FIXTURE_DIR / "example_request.json").read_text())
PAYLOAD = {**_example_request, "model": MODEL}
REFERENCE = {
    "gasphase_s1_energy_eV": 2.6991384029388428,
    "acetone_s1_energy_eV": 2.664933681488037,
    "gasphase_ct_label": "LLCT",
    "acetone_ct_label": "LMCT",
}

# Minimal 6-atom methane-like fixture (no transition metal) and a lone-atom
# fixture, for boundary/validation checks. Charge/atom-count/metal-count rules
# are documented in the model's README ("7-85 atoms, exactly one transition metal").
TOO_FEW_ATOMS_XYZ = "3\nwater, below the 7-atom minimum\nO 0 0 0\nH 0.96 0 0\nH -0.24 0.93 0\n"
NO_METAL_XYZ = (
    "8\nmethane-like, no transition metal\n"
    "C 0 0 0\nH 0.63 0.63 0.63\nH -0.63 -0.63 0.63\nH -0.63 0.63 -0.63\nH 0.63 -0.63 -0.63\n"
    "C 1.5 1.5 1.5\nH 2.13 2.13 2.13\nH 0.87 0.87 2.13\n"
)

results = []


def req(body, timeout=120):
    return _http("POST", f"{G}{ENDPOINT}", json_body=body, timeout=timeout)


def record(icon, status, name, detail):
    results.append((icon, status, name, detail))
    print(f"[{icon}] {status} | {name}: {detail}", flush=True)


def wake():
    for attempt in range(72):
        r = req(PAYLOAD)
        if r.status_code == 200:
            record("PASS", 200, "WAKE + predict", f"attempts={attempt+1}"); return r.json()
        if r.status_code == 503:
            time.sleep(5); continue
        record("FAIL", r.status_code, "WAKE + predict", f"unexpected body={r.text[:200]}"); return None
    record("FAIL", 503, "WAKE + predict", "timed out waiting for warm model"); return None


def shape(d):
    solvents = d.get("solvents", {})
    ok = set(solvents) == {"gasphase", "acetone"} and all(
        len(solvents.get(s, {}).get("states", [])) == 30 for s in ("gasphase", "acetone")
    )
    record("PASS" if ok else "FAIL", 200, "SHAPE",
           f"solvents={sorted(solvents)} states={[len(solvents.get(s,{}).get('states',[])) for s in ('gasphase','acetone')]}")


def regression(d):
    gas = d["solvents"]["gasphase"]
    ace = d["solvents"]["acetone"]
    observed = {
        "gasphase_s1_energy_eV": gas["states"][0]["energy_eV"],
        "acetone_s1_energy_eV": ace["states"][0]["energy_eV"],
        "gasphase_ct_label": gas["visible_transition"]["direct_label"],
        "acetone_ct_label": ace["visible_transition"]["direct_label"],
    }
    energies_ok = all(
        math.isclose(observed[k], REFERENCE[k], abs_tol=5e-4)
        for k in ("gasphase_s1_energy_eV", "acetone_s1_energy_eV")
    )
    labels_ok = all(
        observed[k] == REFERENCE[k] for k in ("gasphase_ct_label", "acetone_ct_label")
    )
    ok = energies_ok and labels_ok
    record("PASS" if ok else "FAIL", 200, "REGRESSION vs example_prediction.json",
           f"observed={observed} reference={REFERENCE}")


def conditional_fields(d):
    # Regional peak present only when band predicted present; CT/NTO only when
    # the visible band probability is >= 0.5 (both true for this fixture).
    gas = d["solvents"]["gasphase"]
    nir = gas["bands"]["nir"]
    ok = (nir["present"] is False and nir["peak"] is None
          and gas["bands"]["visible"]["present"] is True
          and gas["bands"]["visible"]["peak"] is not None
          and "visible_transition" in gas)
    record("PASS" if ok else "FAIL", 200, "CONDITIONAL FIELDS",
           f"nir.present={nir['present']} nir.peak={nir['peak']} visible.present={gas['bands']['visible']['present']}")


def model_echo(d):
    record("PASS" if d.get("model") == MODEL else "FAIL", 200, "MODEL-ECHO", f"model={d.get('model')!r}")


def invalid_charge():
    body = {**PAYLOAD, "charge": 7}
    r = req(body, timeout=30)
    record("EXP" if r.status_code == 422 else "FAIL", r.status_code, "INVALID charge=7", r.text[:150])


def too_few_atoms():
    body = {"model": MODEL, "charge": 0, "xyz": TOO_FEW_ATOMS_XYZ}
    r = req(body, timeout=30)
    record("EXP" if r.status_code == 422 else "FAIL", r.status_code, "INVALID <7 atoms", r.text[:150])


def no_transition_metal():
    body = {"model": MODEL, "charge": 0, "xyz": NO_METAL_XYZ}
    r = req(body, timeout=30)
    record("EXP" if r.status_code == 422 else "FAIL", r.status_code, "INVALID zero transition metals", r.text[:150])


def missing_required_field():
    body = {"model": MODEL, "charge": 0}  # xyz omitted
    r = req(body, timeout=30)
    record("EXP" if r.status_code == 422 else "FAIL", r.status_code, "INVALID missing xyz", r.text[:150])


def catalog():
    r = _http("GET", f"{G}/v1/models?all=true", timeout=30)
    m = next((x for x in r.json().get("data", []) if x["id"] == MODEL), None)
    record("PASS" if m else "FAIL", r.status_code, "Catalog entry",
           f"type={m.get('type') if m else 'MISSING'}")


if __name__ == "__main__":
    print("=" * 66, flush=True); print(f"{MODEL} excited-state screening test ({ENDPOINT})", flush=True)
    print("=" * 66, flush=True)
    d = wake()
    if d:
        for t in (shape, regression, conditional_fields, model_echo):
            try:
                t(d)
            except Exception as e:
                record("ERR", 0, t.__name__, str(e)[:150])
    for t in (invalid_charge, too_few_atoms, no_transition_metal, missing_required_field, catalog):
        try:
            t()
        except Exception as e:
            record("ERR", 0, t.__name__, str(e)[:150])
    p = sum(1 for x in results if x[0] == "PASS"); e = sum(1 for x in results if x[0] == "EXP")
    f = sum(1 for x in results if x[0] in ("FAIL", "ERR")); s = sum(1 for x in results if x[0] == "SKIP")
    print(f"\n{'=' * 66}\nResults: {p} passed, {e} expected, {f} failed/err, {s} skipped of {len(results)}",
          flush=True)
    raise SystemExit(1 if f else 0)
