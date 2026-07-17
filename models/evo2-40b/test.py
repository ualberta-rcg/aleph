"""Gateway test battery for evo2-40b NIM.

Run inside the gateway pod:
  cat models/evo2-40b/test.py | \
      kubectl exec -i -n models deploy/model-gateway -c gateway -- python3 -
"""
import httpx, os

G = os.environ.get("GW_URL", "http://localhost:8080")
_KEY = os.environ.get("TYK_KEY")
_HEADERS = {"Authorization": f"Bearer {_KEY}"} if _KEY else {}
_VERIFY = os.environ.get("GW_INSECURE", "").lower() not in ("1", "true", "yes", "on")
MODEL = os.environ.get("MODEL", "evo2-40b")

def req(method, path, body=None, timeout=120):
    return httpx.request(method, f"{G}{path}", json=body, timeout=timeout,
                         headers=_HEADERS, verify=_VERIFY)

def record(icon, status, name, detail):
    results.append((icon, status, name, detail))
    print(f"[{icon}] {status} | {name}: {detail}", flush=True)

results = []


def generate():
    r = req("POST", "/v1/biology/arc/evo2/generate", {
        "model": MODEL,
        "sequence": "ATGCGATCGATCGATCGATCG",
        "num_tokens": 8,
        "temperature": 0.7,
        "top_k": 1,
        "top_p": 0.9
    })
    if r.status_code != 200:
        record("FAIL", r.status_code, "generate", r.text[:200]); return
    d = r.json()
    seq = d.get("sequence", "")
    record("PASS" if seq and len(seq) > len("ATGCGATCGATCGATCGATCG") else "FAIL",
           r.status_code, "generate", f"len={len(seq)}")


def catalog():
    r = req("GET", "/v1/models?all=true")
    m = next((x for x in r.json().get("data", []) if x["id"] == MODEL), None)
    if not m:
        record("FAIL", 0, "catalog", "not found"); return
    record("PASS", r.status_code, "catalog", f"type={m.get('type')} endpoint={m.get('endpoint')}")


BATTERY = [generate, catalog]

if __name__ == "__main__":
    print("=" * 66, flush=True)
    print(f"{MODEL} science test", flush=True)
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
