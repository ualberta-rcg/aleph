"""borzoi test — POST /v1/science/predict {sequence, n_bins}.

Predicts RNA-seq track signal from a DNA sequence (padded to 524,288 bp). Sanity: bins_returned and
num_tracks > 0, predictions is a finite [n_bins, n_tracks] grid. Uses n_bins=4 to keep the payload
small (full track count is large).
Run: GW_URL=https://inference.vulcan.alliancecan.ca TYK_KEY=<key> GW_INSECURE=1 MODEL=borzoi python3 models/borzoi/test.py
"""
import httpx, os, time, math, random

G = os.environ.get("GW_URL", "http://localhost:8080").rstrip("/")
_KEY = os.environ.get("TYK_KEY")
_HEADERS = {"Authorization": f"Bearer {_KEY}"} if _KEY else {}
_VERIFY = os.environ.get("GW_INSECURE", "").lower() not in ("1", "true", "yes", "on")
MODEL = os.environ.get("MODEL", "borzoi")
ENDPOINT = "/v1/science/predict"

random.seed(11)
SEQ = "".join(random.choice("ACGT") for _ in range(4000))
PAYLOAD = {"model": MODEL, "sequence": SEQ, "n_bins": 4}
results = []


def req(body, timeout=200):
    return httpx.post(f"{G}{ENDPOINT}", json=body, timeout=timeout, headers=_HEADERS, verify=_VERIFY)


def record(icon, status, name, detail):
    results.append((icon, status, name, detail))
    print(f"[{icon}] {status} | {name}: {detail}", flush=True)


def wake():
    for attempt in range(72):
        r = req(PAYLOAD)
        if r.status_code == 200:
            record("PASS", 200, "WAKE + predict", f"attempts={attempt+1}"); return r.json()
        if r.status_code in (502, 503, 504):
            time.sleep(5); continue
        if r.status_code == 404 and attempt < 24:
            time.sleep(5); continue
        record("FAIL", r.status_code, "WAKE + predict", f"unexpected body={r.text[:120]}"); return None
    record("FAIL", 503, "WAKE + predict", "timed out waiting for warm model"); return None


def shape(d):
    nb = d.get("bins_returned"); nt = d.get("num_tracks")
    ok = nb == 4 and isinstance(nt, int) and nt > 0
    record("PASS" if ok else "FAIL", 200, "SHAPE", f"bins_returned={nb} num_tracks={nt} keys={sorted(d.keys())}")


def sanity(d):
    preds = d.get("predictions")
    ok = (isinstance(preds, list) and len(preds) == 4
          and all(isinstance(row, list) and row and all(isinstance(v, (int, float)) and math.isfinite(v)
                                                        for v in row) for row in preds))
    record("PASS" if ok else "FAIL", 200, "SANITY",
           f"predictions_shape=[{len(preds) if isinstance(preds,list) else '?'}][{len(preds[0]) if preds and isinstance(preds[0],list) else '?'}]")


def model_echo(d):
    record("PASS" if d.get("model") == MODEL else "FAIL", 200, "MODEL-ECHO", f"model={d.get('model')!r}")


def catalog():
    r = httpx.get(f"{G}/v1/models?all=true", headers=_HEADERS, verify=_VERIFY, timeout=30)
    m = next((x for x in r.json().get("data", []) if x["id"] == MODEL), None)
    record("PASS" if m else "FAIL", r.status_code, "Catalog entry",
           f"type={m.get('type') if m else 'MISSING'}")


if __name__ == "__main__":
    print("=" * 66, flush=True); print(f"{MODEL} predict test ({ENDPOINT})", flush=True)
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
