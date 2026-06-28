"""moment test — POST /v1/forecast {time_series, prediction_length}.

MOMENT-1-large forecasts a numeric series. Sanity: forecast length == prediction_length, finite.
Run: GW_URL=https://inference.vulcan.alliancecan.ca TYK_KEY=<key> GW_INSECURE=1 MODEL=moment python3 models/moment/test.py
"""
import httpx, os, time, math

G = os.environ.get("GW_URL", "http://localhost:8080").rstrip("/")
_KEY = os.environ.get("TYK_KEY")
_HEADERS = {"Authorization": f"Bearer {_KEY}"} if _KEY else {}
_VERIFY = os.environ.get("GW_INSECURE", "").lower() not in ("1", "true", "yes", "on")
MODEL = os.environ.get("MODEL", "moment")
ENDPOINT = "/v1/forecast"
HORIZON = 96
# A trending series padded to 512 (MOMENT prefers 512-len input).
TS = [10 + i * 0.7 + (i % 5) for i in range(512)]
PAYLOAD = {"model": MODEL, "time_series": TS, "prediction_length": HORIZON}
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
            record("PASS", 200, "WAKE + forecast", f"attempts={attempt+1}"); return r.json()
        if r.status_code in (502, 503, 504):
            time.sleep(5); continue
        if r.status_code == 404 and attempt < 24:
            time.sleep(5); continue
        record("FAIL", r.status_code, "WAKE + forecast", f"unexpected body={r.text[:120]}"); return None
    record("FAIL", 503, "WAKE + forecast", "timed out waiting for warm model"); return None


def shape(d):
    ok = isinstance(d.get("forecast"), list)
    record("PASS" if ok else "FAIL", 200, "SHAPE", f"keys={sorted(d.keys())}")


def sanity(d):
    fc = d.get("forecast") or []
    ok = isinstance(fc, list) and len(fc) == HORIZON and all(math.isfinite(v) for v in fc)
    record("PASS" if ok else "FAIL", 200, "SANITY", f"forecast_len={len(fc)} (horizon={HORIZON}) first={fc[:3] if fc else []}")


def model_echo(d):
    record("PASS" if d.get("model") == MODEL else "FAIL", 200, "MODEL-ECHO", f"model={d.get('model')!r}")


def catalog():
    r = httpx.get(f"{G}/v1/models?all=true", headers=_HEADERS, verify=_VERIFY, timeout=30)
    m = next((x for x in r.json().get("data", []) if x["id"] == MODEL), None)
    record("PASS" if m else "FAIL", r.status_code, "Catalog entry",
           f"type={m.get('type') if m else 'MISSING'}")


if __name__ == "__main__":
    print("=" * 66, flush=True); print(f"{MODEL} forecast test ({ENDPOINT})", flush=True)
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
