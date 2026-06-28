"""prostt5 test — POST /v1/translate {input, direction}.

ProstT5 translates protein AA sequences ↔ 3Di structure tokens. Sanity: results non-empty +
translated string differs in character set from input (3Di uses lowercase d/p/v... tokens).
Run: GW_URL=https://inference.vulcan.alliancecan.ca TYK_KEY=<key> GW_INSECURE=1 MODEL=prostt5 python3 models/prostt5/test.py
"""
import httpx, os, time

G = os.environ.get("GW_URL", "http://localhost:8080").rstrip("/")
_KEY = os.environ.get("TYK_KEY")
_HEADERS = {"Authorization": f"Bearer {_KEY}"} if _KEY else {}
_VERIFY = os.environ.get("GW_INSECURE", "").lower() not in ("1", "true", "yes", "on")
MODEL = os.environ.get("MODEL", "prostt5")
ENDPOINT = "/v1/translate"
SEQ = "MKTVVRQEL"  # short AA sequence
PAYLOAD = {"model": MODEL, "input": SEQ, "direction": "seq2struct"}
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
            record("PASS", 200, "WAKE + translate", f"attempts={attempt+1}"); return r.json()
        if r.status_code in (502, 503, 504):
            time.sleep(5); continue
        if r.status_code == 404 and attempt < 24:
            time.sleep(5); continue
        record("FAIL", r.status_code, "WAKE + translate", f"unexpected body={r.text[:120]}"); return None
    record("FAIL", 503, "WAKE + translate", "timed out waiting for warm model"); return None


def shape(d):
    res = d.get("results")
    ok = isinstance(res, list) and len(res) > 0
    record("PASS" if ok else "FAIL", 200, "SHAPE", f"keys={sorted(d.keys())} n_results={len(res or [])}")


def sanity(d):
    res = d.get("results") or []
    out = res[0] if res else ""
    # 3Di tokens are lowercase (d/p/v/a...); an AA seq is uppercase. Translation should change case-set.
    has_lower = any(c.islower() for c in out)
    ok = isinstance(out, str) and len(out.replace(" ", "")) > 0 and has_lower
    record("PASS" if ok else "FAIL", 200, "SANITY (seq→3Di)", f"out={out[:50]!r} has_lower={has_lower}")


def catalog():
    r = httpx.get(f"{G}/v1/models?all=true", headers=_HEADERS, verify=_VERIFY, timeout=30)
    m = next((x for x in r.json().get("data", []) if x["id"] == MODEL), None)
    record("PASS" if m else "FAIL", r.status_code, "Catalog entry",
           f"type={m.get('type') if m else 'MISSING'}")


if __name__ == "__main__":
    print("=" * 66, flush=True); print(f"{MODEL} translate test ({ENDPOINT})", flush=True)
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
