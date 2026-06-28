"""timer-s1 test — POST /v1/forecast {time_series, prediction_length}. Quantile forecast."""
import httpx, os, time, math
G = os.environ.get("GW_URL", "http://localhost:8080").rstrip("/")
_KEY = os.environ.get("TYK_KEY"); _H = {"Authorization": f"Bearer {_KEY}"} if _KEY else {}
_V = os.environ.get("GW_INSECURE", "").lower() not in ("1","true","yes","on")
MODEL = os.environ.get("MODEL", "timer-s1"); EP = "/v1/forecast"
PL = {"model": MODEL, "time_series": [10+i*0.7+(i%5) for i in range(100)], "prediction_length": 96}
res = []
def req(b, t=300): return httpx.post(f"{G}{EP}", json=b, timeout=t, headers=_H, verify=_V)
def rec(i,s,n,d): res.append((i,s,n,d)); print(f"[{i}] {s} | {n}: {d}", flush=True)
def wake():
    for a in range(72):
        r=req(PL)
        if r.status_code==200: rec("PASS",200,"WAKE+forecast",f"attempts={a+1}"); return r.json()
        if r.status_code in (502,503,504): time.sleep(5); continue
        if r.status_code==404 and a<24: time.sleep(5); continue
        rec("FAIL",r.status_code,"WAKE+forecast",f"body={r.text[:100]}"); return None
    rec("FAIL",503,"WAKE+forecast","timed out"); return None
def shape(d):
    fc=d.get("forecast"); ok=isinstance(fc,dict) and "mean" in fc if isinstance(fc,dict) else isinstance(d.get("mean"),list)
    rec("PASS" if ok else "FAIL",200,"SHAPE",f"keys={sorted(d.keys())}")
def sanity(d):
    m=(d.get("forecast") or {}).get("mean") or d.get("mean") or []
    ok=len(m)>0 and all(math.isfinite(v) for v in m)
    rec("PASS" if ok else "FAIL",200,"SANITY",f"len={len(m)} first={m[:3] if m else []}")
def echo(d): rec("PASS" if d.get("model")==MODEL else "FAIL",200,"MODEL-ECHO",f"model={d.get('model')!r}")
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
