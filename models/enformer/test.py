"""enformer test — POST /v1/science/predict {sequence, organism}.

Predicts human regulatory tracks from a DNA sequence (padded to 196,608 bp). Sanity: human_shape is
[896, 5313] (or [896, n] with return_tracks) and human_mean is finite.
Run: GW_URL=https://inference.vulcan.alliancecan.ca TYK_KEY=<key> GW_INSECURE=1 MODEL=enformer python3 models/enformer/test.py
"""
import httpx, os, time, math, random

G = os.environ.get("GW_URL", "http://localhost:8080").rstrip("/")
_KEY = os.environ.get("TYK_KEY")
_HEADERS = {"Authorization": f"Bearer {_KEY}"} if _KEY else {}
_VERIFY = os.environ.get("GW_INSECURE", "").lower() not in ("1", "true", "yes", "on")
MODEL = os.environ.get("MODEL", "enformer")
ENDPOINT = "/v1/science/predict"

# A few kb of random ACGT — enformer pads to 196,608 bp with N.
random.seed(7)
SEQ = "".join(random.choice("ACGT") for _ in range(4000))
PAYLOAD = {"model": MODEL, "sequence": SEQ, "organism": "human"}
results = []


def req(body, timeout=590):
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
    hs = d.get("human_shape")
    ok = isinstance(hs, list) and hs[:1] == [896] and hs[-1] == 5313
    record("PASS" if ok else "FAIL", 200, "SHAPE", f"human_shape={hs} keys={sorted(d.keys())}")


def sanity(d):
    m = d.get("human_mean")
    sample = d.get("human_sample")
    ok = (isinstance(m, (int, float)) and math.isfinite(m)
          and isinstance(sample, list) and len(sample) == 10)
    record("PASS" if ok else "FAIL", 200, "SANITY", f"human_mean={m} sample_len={len(sample) if isinstance(sample,list) else sample}")


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
