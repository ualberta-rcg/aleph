"""tiny-aya-global chat gateway test.

Template A battery (trimmed, non-reasoning text-only chat).
Run: GW_URL=https://inference.vulcan.alliancecan.ca TYK_KEY=<key> GW_INSECURE=1 MODEL=tiny-aya-global python3 models/tiny-aya-global/test.py
"""
import httpx, json, os, time

G = os.environ.get("GW_URL", "http://localhost:8080")
_KEY = os.environ.get("TYK_KEY")
_HEADERS = {"Authorization": f"Bearer {_KEY}"} if _KEY else {}
_VERIFY = os.environ.get("GW_INSECURE", "").lower() not in ("1", "true", "yes", "on")
MODEL = os.environ.get("MODEL", "tiny-aya-global")
results = []


def record(icon, status, name, detail):
    results.append((icon, status, name, detail)); print(f"[{icon}] {status} | {name}: {detail}", flush=True)


def req(method, path, body=None, timeout=300, stream=False):
    if stream:
        return httpx.stream(method, f"{G}{path}", json=body, timeout=timeout, headers=_HEADERS, verify=_VERIFY)
    return httpx.request(method, f"{G}{path}", json=body, timeout=timeout, headers=_HEADERS, verify=_VERIFY)


def oai(body):
    r = req("POST", "/v1/chat/completions", body)
    d = r.json()
    return r, d, d.get("choices", [{}])[0].get("message", {})


def safe(m, n=60):
    c = m.get("content") or ""
    return (c[:n] + "…") if len(c) > n else c


def wake():
    body = {"model": MODEL, "messages": [{"role": "user", "content": "Say hi"}], "max_tokens": 20, "temperature": 0}
    for attempt in range(72):
        r = req("POST", "/v1/chat/completions", body)
        if r.status_code == 200:
            m = r.json()["choices"][0]["message"]
            record("PASS", 200, "WAKE + OAI basic", f"attempts={attempt+1} content={safe(m,30)!r}"); return
        if r.status_code == 503: time.sleep(5); continue
        record("FAIL", r.status_code, "WAKE + OAI basic", f"unexpected status body={r.text[:80]}"); return
    record("FAIL", 503, "WAKE + OAI basic", "timed out waiting for warm model")


def temp0():
    r, d, m = oai({"model": MODEL, "messages": [{"role": "user", "content": "Capital of France? One word."}], "max_tokens": 20, "temperature": 0})
    ok = r.status_code == 200 and "paris" in (m.get("content") or "").lower()
    record("PASS" if ok else "FAIL", r.status_code, "OAI temp=0 + answer", safe(m))


def system():
    r, d, m = oai({"model": MODEL, "messages": [{"role": "system", "content": "You are a pirate. Speak like a pirate."}, {"role": "user", "content": "Hello!"}], "max_tokens": 30})
    record("PASS" if r.status_code == 200 else "FAIL", r.status_code, "OAI system prompt", safe(m))


def stream():
    with req("POST", "/v1/chat/completions", {"model": MODEL, "messages": [{"role": "user", "content": "Count 1 to 3"}], "max_tokens": 30, "stream": True}, stream=True) as r:
        n = len([l for l in r.iter_lines() if l.startswith("data:") and "DONE" not in l])
    record("PASS" if r.status_code == 200 and n > 0 else "FAIL", r.status_code, "OAI streaming", f"{n} chunks")


def usage():
    r, d, m = oai({"model": MODEL, "messages": [{"role": "user", "content": "hi"}], "max_tokens": 10})
    u = d.get("usage", {})
    ok = u.get("prompt_tokens") and MODEL in (d.get("model") or "")
    record("PASS" if ok else "FAIL", r.status_code, "OAI usage + model echo", f"prompt={u.get('prompt_tokens')} model={d.get('model')!r}")


def ant_basic():
    r = req("POST", "/v1/messages", {"model": MODEL, "max_tokens": 30, "temperature": 0, "messages": [{"role": "user", "content": "What is 3+3? Just the number."}]})
    d = r.json()
    t = next((b.get("text", "") for b in d.get("content", []) if b.get("type") == "text"), "")
    record("PASS" if r.status_code == 200 else "FAIL", r.status_code, "ANT basic", f"{t[:50]!r}")


def catalog():
    r = req("GET", "/v1/models")
    m = next((x for x in r.json().get("data", []) if x["id"] == MODEL), None)
    if not m: record("FAIL", 0, "Catalog entry", f"{MODEL} not found"); return
    record("PASS" if m.get("type") == "chat" else "FAIL", r.status_code, "Catalog entry", f"type={m.get('type')} ctx={m.get('context_window')}")


BATTERY = [wake, temp0, system, stream, usage, ant_basic, catalog]

if __name__ == "__main__":
    print("=" * 66, flush=True); print(f"{MODEL} chat gateway test", flush=True); print("=" * 66, flush=True)
    for t in BATTERY:
        try: t()
        except Exception as e: record("ERR", 0, t.__name__, str(e)[:120])
    p = sum(1 for x in results if x[0] == "PASS")
    f = sum(1 for x in results if x[0] in ("FAIL", "ERR"))
    print(f"\n{'=' * 66}\nResults: {p} passed, {f} failed/err of {len(results)}", flush=True)
