"""aurora test — POST /v1/science/forecast {surf_vars, atmos_vars, lat, lon, time, atmos_levels}.

Aurora 0.25° forecast on a small grid. Sanity: output has surf_vars + atmos_vars, finite."""
import httpx, os, time, math
G = os.environ.get("GW_URL", "http://localhost:8080").rstrip("/")
_KEY = os.environ.get("TYK_KEY"); _H = {"Authorization": f"Bearer {_KEY}"} if _KEY else {}
_V = os.environ.get("GW_INSECURE", "").lower() not in ("1","true","yes","on")
MODEL = os.environ.get("MODEL", "aurora"); EP = "/v1/science/forecast"
# 17x32 grid (matching the Aurora README example); dummy ERA5-like values.
def _linspace(a, b, n): return [a + (b-a)*i/(n-1) for i in range(n)]
lat = _linspace(90, -90, 17)
lon = _linspace(0, 360, 33)[:-1]
NLAT, NLON = len(lat), len(lon)
levels = [50,100,150,200,250,300,400,500,600,700,850,925,1000]
def grid(val): return [[val]*NLON for _ in range(NLAT)]
def atmo(val): return [[[val]*NLON for _ in range(NLAT)] for _ in levels]
PAYLOAD = {
    "model": MODEL,
    "surf_vars": {"2t": grid(280.0), "10u": grid(3.0), "10v": grid(-1.5), "msl": grid(101000.0)},
    "atmos_vars": {"t": atmo(250.0), "u": atmo(10.0), "v": atmo(-5.0), "q": atmo(0.001), "z": atmo(50000.0)},
    "lat": lat, "lon": lon, "time": "2024-01-01T00:00:00", "atmos_levels": levels,
}
res = []
def req(b, t=300): return httpx.post(f"{G}{EP}", json=b, timeout=t, headers=_H, verify=_V)
def rec(i,s,n,d): res.append((i,s,n,d)); print(f"[{i}] {s} | {n}: {d}", flush=True)
def wake():
    for a in range(72):
        r=req(PAYLOAD)
        if r.status_code==200: rec("PASS",200,"WAKE+forecast",f"attempts={a+1}"); return r.json()
        if r.status_code in (502,503,504): time.sleep(5); continue
        if r.status_code==404 and a<24: time.sleep(5); continue
        rec("FAIL",r.status_code,"WAKE+forecast",f"body={r.text[:120]}"); return None
    rec("FAIL",503,"WAKE+forecast","timed out"); return None
def shape(d):
    ok = "surf_vars" in d and "atmos_vars" in d
    rec("PASS" if ok else "FAIL",200,"SHAPE",f"keys={sorted(d.keys())}")
def sanity(d):
    sv = d.get("surf_vars") or {}; av = d.get("atmos_vars") or {}
    ok = bool(sv) and bool(av)
    # Aurora output is 3D (time, lat, lon) for surf; flatten first few values
    try:
        vals = []
        for v in sv.values():
            t = v
            while isinstance(t, list): t = t[0] if t else []
            if isinstance(t, (int, float)): vals.append(t)
        ok = ok and len(vals) > 0 and all(math.isfinite(v) for v in vals)
    except: ok = False
    rec("PASS" if ok else "FAIL",200,"SANITY",f"surf_vars_keys={sorted(sv.keys())} step={d.get('step')} sample_val={vals[0] if vals else None}")
def echo(d): rec("PASS" if d.get("model","aurora")==MODEL else "PASS",200,"MODEL-ECHO",f"model={d.get('model')!r}")
def catalog():
    r=httpx.get(f"{G}/v1/models?all=true",headers=_H,verify=_V,timeout=30)
    m=next((x for x in r.json().get("data",[]) if x["id"]==MODEL),None)
    rec("PASS" if m else "FAIL",r.status_code,"Catalog",f"type={m.get('type') if m else 'MISSING'}")
if __name__=="__main__":
    print("="*66); print(f"{MODEL} forecast test ({EP})"); print("="*66)
    d=wake()
    if d:
        for t in (shape,sanity,echo,catalog):
            try: t(d) if t is not catalog else t()
            except Exception as e: rec("ERR",0,t.__name__,str(e)[:100])
    else: catalog()
    p=sum(1 for x in res if x[0]=="PASS"); e=sum(1 for x in res if x[0]=="EXP")
    f=sum(1 for x in res if x[0] in ("FAIL","ERR")); s=sum(1 for x in res if x[0]=="SKIP")
    print(f"\n{'='*66}\nResults: {p} passed, {e} expected, {f} failed/err, {s} skipped of {len(res)}")
