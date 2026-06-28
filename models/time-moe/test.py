"""time-moe test — POST /v1/forecast {time_series, prediction_length}.

TimeMoE-50M forecasts a numeric series. prediction_length MUST be in {1,96,192,336,720}.
Run: GW_URL=https://inference.vulcan.alliancecan.ca TYK_KEY=<key> GW_INSECURE=1 MODEL=time-moe python3 models/time-moe/test.py
"""
import httpx, os, time, math
G = os.environ.get("GW_URL", "http://localhost:8080").rstrip("/")
_KEY = os.environ.get("TYK_KEY"); _HEADERS = {"Authorization": f"Bearer {_KEY}"} if _KEY else {}
_VERIFY = os.environ.get("GW_INSECURE", "").lower() not in ("1", "true", "yes", "on")
MODEL = os.environ.get("MODEL", "time-moe"); ENDPOINT = "/v1/forecast"
PAYLOAD = {"model": MODEL, "time_series": [10 + i*0.7 + (i%5) for i in range(100)], "prediction_length": 96}
results = []
def req(body, timeout=300):
    return httpx.post(f"{G}{ENDPOINT}", json=body, timeout=timeout, headers=_HEADERS, verify=_VERIFY)
def record(icon, status, name, detail):
    results.append((icon, status, name, detail)); print(f"[{icon}] {status} | {name}: {detail}", flush=True)
def wake():
    for a in range(72):
        r = req(PAYLOAD)
        if r.status_code == 200: record("PASS", 200, "WAKE + forecast", f"attempts={a+1}"); return r.json()
        if r.status_code in (502,503,504): time.sleep(5); continue
        if r.status_code == 404 and a < 24: time.sleep(5); continue
        record("FAIL", r.status_code, "WAKE + forecast", f"body={r.text[:120]}"); return None
    record("FAIL", 503, "WAKE + forecast", "timed out"); return None
def shape(d):
    ok = isinstance(d.get("forecast"), list); record("PASS" if ok else "FAIL", 200, "SHAPE", f"keys={sorted(d.keys())}")
def sanity(d):
    fc = d.get("forecast") or []; ok = len(fc) > 0 and all(math.isfinite(v) for v in fc)
    record("PASS" if ok else "FAIL", 200, "SANITY", f"len={len(fc)} first={fc[:3] if fc else []}")
def model_echo(d):
    record("PASS" if d.get("model") == MODEL else "FAIL", 200, "MODEL-ECHO", f"model={d.get('model')!r}")
def catalog():
    r = httpx.get(f"{G}/v1/models?all=true", headers=_HEADERS, verify=_VERIFY, timeout=30)
    m = next((x for x in r.json().get("data", []) if x["id"] == MODEL), None)
    record("PASS" if m else "FAIL", r.status_code, "Catalog entry", f"type={m.get('type') if m else 'MISSING'}")
if __name__ == "__main__":
    print("="*66); print(f"{MODEL} forecast test ({ENDPOINT})"); print("="*66)
    d = wake()
    if d:
        for t in (shape, sanity, model_echo, catalog):
            try: t(d) if t is not catalog else t()
            except Exception as e: record("ERR", 0, t.__name__, str(e)[:120])
    else: catalog()
    p=sum(1 for x in results if x[0]=="PASS"); e=sum(1 for x in results if x[0]=="EXP")
    f=sum(1 for x in results if x[0] in ("FAIL","ERR")); s=sum(1 for x in results if x[0]=="SKIP")
    print(f"\n{'='*66}\nResults: {p} passed, {e} expected, {f} failed/err, {s} skipped of {len(results)}")
