"""glm-4-32b comprehensive gateway test.

Auto-detecting non-reasoning battery. Reads the model's capabilities (vision, tools)
from the live /v1/models catalog and runs the checks that match: vision_works when
supported else vision_rejected; tools_works when supported else tools_rejected.
Streaming is detected at runtime (SSE for normal backends, JSON for no_stream cards).
Otherwise the standard battery: wake, OpenAI features, meta-tasks, Anthropic, guardrails.

The wake() loop retries through 503 model_starting, so this works against a cold model.

Run externally via the gateway VIP + Tyk auth (preferred):
  GW_URL=http://<GATEWAY_VIP> TYK_KEY=<key> MODEL=glm-4-32b python3 models/glm-4-32b/test.py

Run inside the gateway pod (legacy, no auth needed):
  cat models/glm-4-32b/test.py | \
      kubectl exec -i -n models deploy/model-gateway -c gateway -- env MODEL=glm-4-32b python3 -
"""
import httpx, json, os, time

G = os.environ.get("GW_URL", "http://localhost:8080")
_KEY = os.environ.get("TYK_KEY")
_HEADERS = {"Authorization": f"Bearer {_KEY}"} if _KEY else {}
_VERIFY = os.environ.get("GW_INSECURE", "").lower() not in ("1", "true", "yes", "on")
MODEL = os.environ.get("MODEL", "glm-4-32b")
results = []

# ── detect capabilities from the live catalog ─────────────────────────────────
_caps = httpx.get(f"{G}/v1/models", timeout=30, headers=_HEADERS, verify=_VERIFY).json()
_me = next((m for m in _caps.get("data", []) if m["id"] == MODEL), {})
CAP = _me.get("capabilities", {})
VISION = bool(CAP.get("vision"))
TOOLS = bool(CAP.get("tools"))
MAXOUT = int(_me.get("max_completion_tokens") or 8192) or 8192


def req(method, path, body=None, timeout=180, stream=False):
    if stream:
        return httpx.stream(method, f"{G}{path}", json=body, timeout=timeout, headers=_HEADERS, verify=_VERIFY)
    return httpx.request(method, f"{G}{path}", json=body, timeout=timeout, headers=_HEADERS, verify=_VERIFY)


def record(icon, status, name, detail):
    results.append((icon, status, name, detail))
    print(f"[{icon}] {status} | {name}: {detail}", flush=True)


def oai(body):
    r = req("POST", "/v1/chat/completions", body)
    d = r.json()
    return r, d, d["choices"][0]["message"]


def safe(m, n=60):
    c = m.get("content") or ""
    return (c[:n] + "…") if len(c) > n else c


def capmt(n):
    return min(n, MAXOUT)


# ── 1. WAKE (retry 503 model_starting) ────────────────────────────────────────
def wake():
    body = {"model": MODEL, "messages": [{"role": "user", "content": "Say hi"}],
            "max_tokens": 16, "temperature": 0}
    for attempt in range(90):  # ~7.5 min cap
        r = req("POST", "/v1/chat/completions", body)
        if r.status_code == 200:
            m = r.json()["choices"][0]["message"]
            record("PASS", 200, "WAKE + OAI basic", f"attempts={attempt+1} content={safe(m,30)!r}")
            return
        if r.status_code == 503:
            time.sleep(5); continue
        record("FAIL", r.status_code, "WAKE + OAI basic", f"unexpected body={r.text[:80]}")
        return
    record("FAIL", 503, "WAKE + OAI basic", "timed out waiting for warm model")


# ── OpenAI feature battery ────────────────────────────────────────────────────
def stream():
    with req("POST", "/v1/chat/completions", {"model": MODEL,
             "messages": [{"role": "user", "content": "Count 1 to 3"}],
             "max_tokens": 30, "stream": True}, stream=True) as r:
        ct = r.headers.get("content-type", "")
        if "event-stream" in ct:
            n = sum(1 for l in r.iter_lines() if l.startswith("data:") and "[DONE]" not in l)
            record("PASS" if r.status_code == 200 and n > 0 else "FAIL", r.status_code,
                   "OAI streaming", f"SSE chunks={n}")
        else:
            data = r.read()
            ok = r.status_code == 200 and b'"choices"' in data
            record("PASS" if ok else "FAIL", r.status_code,
                   "OAI streaming (no_stream→JSON)", f"ct={ct} bytes={len(data)}")

def temp0():
    r, d, m = oai({"model": MODEL, "messages": [{"role": "user", "content": "Capital of France?"}],
                  "max_tokens": 20, "temperature": 0})
    record("PASS" if r.status_code == 200 else "FAIL", r.status_code, "OAI temp=0", safe(m))

def temp_topk():
    r, d, m = oai({"model": MODEL, "messages": [{"role": "user", "content": "Say hello"}],
                  "max_tokens": 20, "temperature": 0.3, "top_k": 50, "top_p": 0.9})
    record("PASS" if r.status_code == 200 else "FAIL", r.status_code, "OAI temp+top_k/top_p", safe(m))

def stop_seq():
    r, d, m = oai({"model": MODEL, "messages": [{"role": "user", "content": "Count: 1, 2, 3, 4, 5, 6, 7"}],
                  "max_tokens": 50, "stop": ["5"]})
    fin = d["choices"][0].get("finish_reason")
    record("PASS" if r.status_code == 200 else "FAIL", r.status_code, "OAI stop sequences", f"finish={fin} {safe(m)}")

def system():
    r, d, m = oai({"model": MODEL, "messages": [{"role": "system", "content": "You are a pirate. Speak like a pirate."},
                  {"role": "user", "content": "Hello!"}], "max_tokens": 30})
    record("PASS" if r.status_code == 200 else "FAIL", r.status_code, "OAI system prompt", safe(m))

def max_tokens():
    r, d, m = oai({"model": MODEL, "messages": [{"role": "user", "content": "Say hi"}], "max_tokens": capmt(4096)})
    record("PASS" if r.status_code == 200 else "FAIL", r.status_code, "OAI max_tokens", f"asked={capmt(4096)} {safe(m,30)!r}")

def truncation():
    r, d, m = oai({"model": MODEL, "messages": [{"role": "user", "content": "Tell me a very long story."}], "max_tokens": 5})
    fin = d["choices"][0].get("finish_reason"); ct = (d.get("usage") or {}).get("completion_tokens", 0)
    ok = r.status_code == 200 and fin == "length" and ct <= 8
    record("PASS" if ok else "FAIL", r.status_code, "OAI truncation max_tokens=5", f"finish={fin} completion_tokens={ct}")

def usage():
    r, d, m = oai({"model": MODEL, "messages": [{"role": "user", "content": "hi"}], "max_tokens": 10})
    u = d.get("usage") or {}
    pt, ct = u.get("prompt_tokens"), u.get("completion_tokens")
    ok = r.status_code == 200 and MODEL in (d.get("model") or "")
    record("PASS" if ok else "FAIL", r.status_code, "OAI usage + model echo",
           f"prompt={pt} completion={ct} model={d.get('model')!r}" + ("" if pt else " (no usage block — custom backend)"))

def resources():
    r, d, m = oai({"model": MODEL, "messages": [{"role": "user", "content": "hi"}], "max_tokens": 10})
    res = d.get("resources", {})
    record("PASS" if r.status_code == 200 and "model" in res else "FAIL", r.status_code,
           "OAI resources", f"keys={sorted(res.keys())}")


# ── Tools (works if supported, else rejected) ─────────────────────────────────
def _tools_body():
    return {"model": MODEL, "messages": [{"role": "user", "content": "What's the weather in Edmonton?"}],
            "max_tokens": 200,
            "tools": [{"type": "function", "function": {"name": "get_weather", "description": "Get current weather",
                       "parameters": {"type": "object", "properties": {"city": {"type": "string"}}}}}]}

def tools_works():
    r, d, m = oai(_tools_body())
    tc = m.get("tool_calls") or []
    record("PASS" if r.status_code == 200 else "FAIL", r.status_code, "OAI tools work",
           f"tool_calls={len(tc)} content={safe(m,30)!r}")

def tools_rejected():
    r = req("POST", "/v1/chat/completions", _tools_body())
    record("EXP" if r.status_code == 400 else "FAIL", r.status_code, "OAI tools rejected (no tools)",
           f"code={r.json().get('error',{}).get('code','')}")


# ── Vision (works if supported, else rejected) ────────────────────────────────
_PX = "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg=="
def _vision_body():
    return {"model": MODEL, "max_tokens": 40,
            "messages": [{"role": "user", "content": [
                {"type": "text", "text": "What is in this image? One word."},
                {"type": "image_url", "image_url": {"url": _PX}}]}]}

def vision_works():
    r, d, m = oai(_vision_body())
    record("PASS" if r.status_code == 200 else "FAIL", r.status_code, "OAI vision work", safe(m, 30))

def vision_rejected():
    r = req("POST", "/v1/chat/completions", _vision_body())
    record("EXP" if r.status_code == 400 else "FAIL", r.status_code, "Guard: vision rejected",
           f"code={r.json().get('error',{}).get('code','')}")


# ── Meta-tasks (OpenWebUI title/tags/followups — must be short, no reasoning) ──
def _meta(signal, name, cap):
    r, d, m = oai({"model": MODEL, "messages": [{"role": "user",
                  "content": f"{signal} for: The quick brown fox jumps over the lazy dog."}],
                  "max_tokens": capmt(512), "temperature": 0})
    ct = (d.get("usage") or {}).get("completion_tokens", 0)
    record("PASS" if r.status_code == 200 and ct <= cap else "FAIL", r.status_code,
           f"OAI meta {name}", f"completion_tokens={ct} (cap {cap}) {safe(m,30)!r}")

def meta_title():    _meta("Generate a concise, 3-5 word title", "title", 120)
def meta_tags():     _meta("Generate 1-3 broad tags", "tags", 100)
def meta_followups(): _meta("Suggest 3-5 relevant follow-up questions", "followups", 300)


# ── Anthropic feature battery ─────────────────────────────────────────────────
def _ant_text(d):
    return next((b.get("text", "") for b in d.get("content", []) if b.get("type") == "text"), "")

def ant_basic():
    r = req("POST", "/v1/messages", {"model": MODEL, "max_tokens": 30, "temperature": 0,
            "messages": [{"role": "user", "content": "What is 3+3? Just the number."}]})
    d = r.json()
    record("PASS" if r.status_code == 200 else "FAIL", r.status_code, "ANT basic", f"{_ant_text(d)[:50]!r}")

def ant_stream():
    with req("POST", "/v1/messages", {"model": MODEL, "max_tokens": 30, "stream": True,
             "messages": [{"role": "user", "content": "Say hi"}]}, stream=True) as r:
        ct = r.headers.get("content-type", "")
        if "event-stream" in ct:
            etypes = set(l.split(": ", 1)[1].strip() for l in r.iter_lines() if l.startswith("event:"))
            record("PASS" if r.status_code == 200 else "FAIL", r.status_code, "ANT streaming", f"types={etypes}")
        else:
            data = r.read()
            ok = r.status_code == 200 and b'"content"' in data
            record("PASS" if ok else "FAIL", r.status_code, "ANT streaming (no_stream→JSON)", f"ct={ct}")

def ant_system():
    r = req("POST", "/v1/messages", {"model": MODEL, "max_tokens": 30,
            "system": "You are a pirate.", "messages": [{"role": "user", "content": "Hello!"}]})
    d = r.json()
    record("PASS" if r.status_code == 200 else "FAIL", r.status_code, "ANT system", f"{_ant_text(d)[:50]!r}")

def ant_temp0():
    r = req("POST", "/v1/messages", {"model": MODEL, "max_tokens": 20, "temperature": 0,
            "messages": [{"role": "user", "content": "Capital of France?"}]})
    d = r.json()
    record("PASS" if r.status_code == 200 else "FAIL", r.status_code, "ANT temp=0", f"{_ant_text(d)[:50]!r}")

def ant_stop():
    r = req("POST", "/v1/messages", {"model": MODEL, "max_tokens": 50, "stop_sequences": ["5"],
            "messages": [{"role": "user", "content": "Count: 1,2,3,4,5,6,7"}]})
    d = r.json()
    record("PASS" if r.status_code == 200 else "FAIL", r.status_code, "ANT stop_sequences",
           f"stop_reason={d.get('stop_reason')}")

def ant_vision_works():
    r = req("POST", "/v1/messages", {"model": MODEL, "max_tokens": 40,
            "messages": [{"role": "user", "content": [
                {"type": "text", "text": "What is in this image? One word."},
                {"type": "image", "source": {"type": "base64", "media_type": "image/png", "data": _PX.split(",",1)[1]}}]}]})
    d = r.json()
    record("PASS" if r.status_code == 200 else "FAIL", r.status_code, "ANT vision work", f"{_ant_text(d)[:40]!r}")

def ant_vision_rejected():
    r = req("POST", "/v1/messages", {"model": MODEL, "max_tokens": 40,
            "messages": [{"role": "user", "content": [
                {"type": "image", "source": {"type": "base64", "media_type": "image/png", "data": _PX.split(",",1)[1]}}]}]})
    record("EXP" if r.status_code == 400 else "FAIL", r.status_code, "Guard: ANT vision rejected",
           f"code={r.json().get('error',{}).get('code','')}")


# ── Guardrails ────────────────────────────────────────────────────────────────
def guard_embed():
    r = req("GET", "/v1/models?all=true")
    embed = next((m["id"] for m in r.json().get("data", []) if m.get("type") == "embedding"), None)
    if not embed:
        record("SKIP", 0, "Guard: embed via chat", "no embed model"); return
    r2 = req("POST", "/v1/chat/completions", {"model": embed, "max_tokens": 10,
             "messages": [{"role": "user", "content": "test"}]})
    if r2.status_code in (400, 422):
        record("EXP", r2.status_code, "Guard: embed via chat", "rejected (non-chat)")
    elif r2.status_code == 503:
        record("SKIP", r2.status_code, "Guard: embed via chat", "embed model cold — can't verify")
    else:
        record("FAIL", r2.status_code, "Guard: embed via chat", f"unexpected code={r2.status_code}")

def guard_badmodel():
    r = req("POST", "/v1/chat/completions", {"model": "fake-xyz",
            "messages": [{"role": "user", "content": "test"}]})
    record("EXP" if r.status_code == 404 else "FAIL", r.status_code, "Guard: bad model",
           str(r.json().get("error", ""))[:50])

def catalog():
    r = req("GET", "/v1/models")
    m = next((x for x in r.json().get("data", []) if x["id"] == MODEL), None)
    if not m:
        record("FAIL", 0, "Catalog entry", "not found"); return
    c = m.get("capabilities", {})
    ok = (c.get("vision") == VISION) and (c.get("tools") == TOOLS) and not c.get("reasoning")
    record("PASS" if ok else "FAIL", r.status_code, "Catalog capabilities",
           f"vision={c.get('vision')} tools={c.get('tools')} reasoning={c.get('reasoning')} ctx={m.get('context_window')}")


# ── run ───────────────────────────────────────────────────────────────────────
print("=" * 66, flush=True)
print(f"{MODEL} comprehensive gateway test (non-reasoning, auto-detected)", flush=True)
print(f"vision={VISION} tools={TOOLS} maxout={MAXOUT}", flush=True)
print("=" * 66, flush=True)
for t in [wake, stream, temp0, temp_topk, stop_seq, system, max_tokens, truncation, usage, resources,
          tools_works if TOOLS else tools_rejected,
          vision_works if VISION else vision_rejected,
          meta_title, meta_tags, meta_followups,
          ant_basic, ant_stream, ant_system, ant_temp0, ant_stop,
          ant_vision_works if VISION else ant_vision_rejected,
          guard_embed, guard_badmodel, catalog]:
    try:
        t()
    except Exception as e:
        record("ERR", 0, getattr(t, "__name__", "?"), str(e)[:120])

p = sum(1 for x in results if x[0] == "PASS")
e = sum(1 for x in results if x[0] == "EXP")
f = sum(1 for x in results if x[0] in ("FAIL", "ERR"))
s = sum(1 for x in results if x[0] == "SKIP")
print(f"\n{'=' * 66}\nResults: {p} passed, {e} expected, {f} failed/err, {s} skipped of {len(results)}", flush=True)
