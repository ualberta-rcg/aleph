"""Gateway test battery for mistral-small-4-119b-2603 NIM.

Run inside the gateway pod:
  cat models/mistral-small-4-119b-2603/test.py | \
      kubectl exec -i -n models deploy/model-gateway -c gateway -- python3 -
"""
import httpx, os

G = os.environ.get("GW_URL", "http://localhost:8080")
_KEY = os.environ.get("TYK_KEY")
_HEADERS = {"Authorization": f"Bearer {_KEY}"} if _KEY else {}
_VERIFY = os.environ.get("GW_INSECURE", "").lower() not in ("1", "true", "yes", "on")
MODEL = os.environ.get("MODEL", "mistral-small-4-119b-2603")

def req(method, path, body=None, timeout=120):
    return httpx.request(method, f"{G}{path}", json=body, timeout=timeout,
                         headers=_HEADERS, verify=_VERIFY)

def record(icon, status, name, detail):
    results.append((icon, status, name, detail))
    print(f"[{icon}] {status} | {name}: {detail}", flush=True)

results = []


def basic():
    r = req("POST", "/v1/chat/completions", {
        "model": MODEL,
        "messages": [{"role": "user", "content": "Say the word 'pong' and nothing else."}],
        "max_tokens": 20,
        "temperature": 0.0
    })
    if r.status_code != 200:
        record("FAIL", r.status_code, "basic", r.text[:120]); return
    txt = r.json()["choices"][0]["message"].get("content", "")
    record("PASS" if "pong" in txt.lower() else "FAIL", r.status_code, "basic", txt[:80])


def stream():
    r = req("POST", "/v1/chat/completions", {
        "model": MODEL,
        "messages": [{"role": "user", "content": "Count 1 2 3"}],
        "max_tokens": 20,
        "stream": True,
        "temperature": 0.0
    })
    if r.status_code != 200:
        record("FAIL", r.status_code, "stream", r.text[:120]); return
    chunks = [ln for ln in r.text.splitlines() if ln.startswith("data:") and ln[5:].strip() != "[DONE]"]
    record("PASS" if len(chunks) >= 1 else "FAIL", r.status_code, "stream", f"chunks={len(chunks)}")


def system_prompt():
    r = req("POST", "/v1/chat/completions", {
        "model": MODEL,
        "messages": [
            {"role": "system", "content": "You reply only in JSON with key 'answer'."},
            {"role": "user", "content": "What is 2+2?"}
        ],
        "max_tokens": 40,
        "temperature": 0.0
    })
    if r.status_code != 200:
        record("FAIL", r.status_code, "system_prompt", r.text[:120]); return
    txt = r.json()["choices"][0]["message"].get("content", "")
    record("PASS" if '"answer"' in txt else "FAIL", r.status_code, "system_prompt", txt[:80])


def catalog():
    r = req("GET", "/v1/models?all=true")
    m = next((x for x in r.json().get("data", []) if x["id"] == MODEL), None)
    if not m:
        record("FAIL", 0, "catalog", "not found"); return
    record("PASS", r.status_code, "catalog", f"type={m.get('type')} endpoint={m.get('endpoint')}")


BATTERY = [basic, stream, system_prompt, catalog]

if __name__ == "__main__":
    print("=" * 66, flush=True)
    print(f"{MODEL} chat test", flush=True)
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
