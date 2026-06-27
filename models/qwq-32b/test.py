"""qwq-32b comprehensive gateway test.

QwQ-32B (32.5B dense, FP16, TP2). **Always-on** reasoning (deepseek_r1 parser, <think> blocks;
no thinking toggle). Tools (hermes). Text-only. vLLM v0.20.2.

Always-on variant: the gateway exposes reasoning by default; on reasoning_effort=none / meta-tasks
it STRIPS the reasoning + caps max_tokens (the model can't stop thinking, so OFF reduces what fits
— content may be short/empty, the documented quirk).

Run externally via the gateway VIP + Tyk auth (preferred):
  GW_URL=http://<GATEWAY_VIP> TYK_KEY=<key> python3 models/qwq-32b/test.py

Run inside the gateway pod (legacy, no auth needed):
  cat models/qwq-32b/test.py | \
      kubectl exec -i -n models deploy/model-gateway -c gateway -- python3 -
"""
import httpx, json, os, time

G = os.environ.get("GW_URL", "http://localhost:8080")
_KEY = os.environ.get("TYK_KEY")
_HEADERS = {"Authorization": f"Bearer {_KEY}"} if _KEY else {}
_VERIFY = os.environ.get("GW_INSECURE", "").lower() not in ("1", "true", "yes", "on")
MODEL = os.environ.get("MODEL", "qwq-32b")
HARD = ("A farmer has 17 sheep. All but 9 die. How many sheep are left? "
        "Take that number, multiply by 7, then subtract 4.")
results = []


def req(method, path, body=None, timeout=300, stream=False):
    if stream:
        return httpx.stream(method, f"{G}{path}", json=body, timeout=timeout, headers=_HEADERS, verify=_VERIFY)
    return httpx.request(method, f"{G}{path}", json=body, timeout=timeout, headers=_HEADERS, verify=_VERIFY)


def record(icon, status, name, detail):
    results.append((icon, status, name, detail))
    print(f"[{icon}] {status} | {name}: {detail}", flush=True)


def _rc(msg):
    return msg.get("reasoning") or msg.get("reasoning_content") or ""


def oai(body):
    r = req("POST", "/v1/chat/completions", body)
    d = r.json()
    return r, d, d["choices"][0]["message"]


def safe(m, n=60):
    c = m.get("content") or ""
    return (c[:n] + "…") if len(c) > n else c


TOOLS = [{"type": "function", "function": {
    "name": "get_weather", "description": "Get weather for a city",
    "parameters": {"type": "object", "properties": {"city": {"type": "string"}},
                   "required": ["city"]}}}]
ANT_TOOLS = [{"name": "get_weather", "description": "Get weather",
              "input_schema": {"type": "object",
                               "properties": {"city": {"type": "string"}},
                               "required": ["city"]}}]


def wake():
    body = {"model": MODEL, "messages": [{"role": "user", "content": "Say hi"}],
            "max_tokens": 4096, "temperature": 0.6}  # generous: qwq thinks before answering
    for attempt in range(72):
        r = req("POST", "/v1/chat/completions", body)
        if r.status_code == 200:
            m = r.json()["choices"][0]["message"]
            record("PASS", 200, "WAKE + OAI basic", f"attempts={attempt+1} content={safe(m,30)!r} rc_len={len(_rc(m))}")
            return
        if r.status_code == 503:
            time.sleep(5); continue
        record("FAIL", r.status_code, "WAKE + OAI basic", f"unexpected status body={r.text[:80]}")
        return
    record("FAIL", 503, "WAKE + OAI basic", "timed out waiting for warm model")


def stream():
    with req("POST", "/v1/chat/completions", {"model": MODEL,
             "messages": [{"role": "user", "content": "Count 1 to 3"}], "max_tokens": 4096,
             "temperature": 0.6, "stream": True}, stream=True) as r:
        n = len([l for l in r.iter_lines() if l.startswith("data:") and "DONE" not in l])
    record("PASS" if r.status_code == 200 and n > 0 else "FAIL", r.status_code, "OAI streaming", f"{n} chunks")

def tools_oai():
    r, d, m = oai({"model": MODEL, "messages": [{"role": "user", "content": "Weather in Edmonton?"}],
                  "max_tokens": 4096, "temperature": 0.6, "tools": TOOLS})
    tc = m.get("tool_calls", [])
    name = tc[0]["function"]["name"] if tc else ""
    ok = r.status_code == 200 and tc and name == "get_weather"
    record("PASS" if ok else "FAIL", r.status_code, "OAI tools", f"tool_calls={len(tc)} name={name!r}")

def max_tokens():
    r, d, m = oai({"model": MODEL, "messages": [{"role": "user", "content": "Say hi"}],
                  "max_tokens": 4096, "temperature": 0.6})
    record("PASS" if r.status_code == 200 else "FAIL", r.status_code, "OAI max_tokens=4k", safe(m, 30))

def truncation():
    r, d, m = oai({"model": MODEL, "messages": [{"role": "user", "content": "Tell me a very long story."}],
                  "max_tokens": 5, "temperature": 0.6})
    fin = d["choices"][0].get("finish_reason"); ct = (d.get("usage") or {}).get("completion_tokens", 0)
    ok = r.status_code == 200 and fin == "length" and ct <= 8
    record("PASS" if ok else "FAIL", r.status_code, "OAI truncation max_tokens=5",
           f"finish={fin} completion_tokens={ct}")

def usage():
    r, d, m = oai({"model": MODEL, "messages": [{"role": "user", "content": "hi"}], "max_tokens": 4096})
    u = d.get("usage", {})
    ok = u.get("prompt_tokens") and MODEL in (d.get("model") or "")
    record("PASS" if ok else "FAIL", r.status_code, "OAI usage + model echo",
           f"prompt={u.get('prompt_tokens')} completion={u.get('completion_tokens')} model={d.get('model')!r}")

def resources():
    r, d, m = oai({"model": MODEL, "messages": [{"role": "user", "content": "hi"}], "max_tokens": 4096})
    res = d.get("resources", {})
    record("PASS" if r.status_code == 200 and "model" in res else "FAIL", r.status_code,
           "OAI resources block", f"keys={sorted(res.keys())}")


def think_on():
    # default (no effort) -> always-on reasoning exposed
    r, d, m = oai({"model": MODEL, "messages": [{"role": "user", "content": HARD}],
                  "max_tokens": 4096, "temperature": 0.6})
    rc = _rc(m)
    record("PASS" if r.status_code == 200 and rc else "FAIL", r.status_code,
           "OAI think ON (default)", f"rc_len={len(rc)} content_len={len(m.get('content') or '')}")

def think_off():
    # reasoning_effort=none -> gateway strips reasoning + caps. qwq still thinks internally.
    r, d, m = oai({"model": MODEL, "messages": [{"role": "user", "content": "Capital of France?"}],
                  "reasoning_effort": "none", "max_tokens": 8000, "temperature": 0})
    rc = _rc(m); ct = (d.get("usage") or {}).get("completion_tokens", 0)
    record("PASS" if r.status_code == 200 and not rc else "FAIL", r.status_code,
           "OAI think OFF (stripped)", f"rc_len={len(rc)} {safe(m,30)!r} completion_tokens={ct}")

def think_stream():
    rn = cn = 0
    with req("POST", "/v1/chat/completions", {"model": MODEL, "messages": [{"role": "user", "content": HARD}],
             "max_tokens": 4096, "temperature": 0.6, "stream": True,
             "stream_options": {"include_usage": True}}, stream=True) as r:
        for line in r.iter_lines():
            if not line.startswith("data:") or "[DONE]" in line:
                continue
            try: o = json.loads(line[5:].strip())
            except Exception: continue
            for ch in o.get("choices", []):
                dd = ch.get("delta", {})
                if dd.get("reasoning") or dd.get("reasoning_content"): rn += 1
                if dd.get("content"): cn += 1
    record("PASS" if r.status_code == 200 and rn > 0 else "FAIL", r.status_code,
           "OAI stream think ON", f"reasoning_deltas={rn} content_deltas={cn}")

def _meta(signal, name, cap):
    r, d, m = oai({"model": MODEL, "messages": [{"role": "user",
                  "content": f"{signal} for: The quick brown fox jumps over the lazy dog."}],
                  "max_tokens": 512, "temperature": 0})
    rc = _rc(m); ct = (d.get("usage") or {}).get("completion_tokens", 0)
    # meta: reasoning must be stripped (rc absent). content may be short (qwq thinks a lot).
    record("PASS" if r.status_code == 200 and not rc else "FAIL", r.status_code,
           f"OAI meta {name}", f"rc_len={len(rc)} completion_tokens={ct} (cap {cap}) {safe(m,30)!r}")

def meta_title():   _meta("Generate a concise, 3-5 word title", "title", 80)
def meta_tags():    _meta("Generate 1-3 broad tags", "tags", 60)
def meta_followups(): _meta("Suggest 3-5 relevant follow-up questions", "followups", 220)

def vision_rejected():
    r = req("POST", "/v1/chat/completions", {"model": MODEL, "max_tokens": 20,
            "messages": [{"role": "user", "content": [{"type": "text", "text": "Describe this."},
                {"type": "image_url", "image_url": {"url": "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg=="}}]}]})
    record("EXP" if r.status_code == 400 else "FAIL", r.status_code, "Guard: vision rejected",
           f"code={r.json().get('error',{}).get('code','')}")


def ant_basic():
    r = req("POST", "/v1/messages", {"model": MODEL, "max_tokens": 4096, "temperature": 0.6,
            "messages": [{"role": "user", "content": "What is 3+3? Just the number."}]})
    d = r.json(); t = next((b.get("text", "") for b in d.get("content", []) if b.get("type") == "text"), "")
    record("PASS" if r.status_code == 200 else "FAIL", r.status_code, "ANT basic", f"{t[:50]!r}")

def ant_stream():
    with req("POST", "/v1/messages", {"model": MODEL, "max_tokens": 4096, "stream": True,
             "messages": [{"role": "user", "content": "Say hi"}]}, stream=True) as r:
        etypes = set(l.split(": ", 1)[1].strip() for l in r.iter_lines() if l.startswith("event:"))
    record("PASS" if r.status_code == 200 else "FAIL", r.status_code, "ANT streaming", f"types={etypes}")

def ant_tools():
    r = req("POST", "/v1/messages", {"model": MODEL, "max_tokens": 4096, "temperature": 0.6,
            "messages": [{"role": "user", "content": "Weather in Edmonton?"}], "tools": ANT_TOOLS})
    d = r.json(); blocks = d.get("content", [])
    tub = [b for b in blocks if b.get("type") == "tool_use"]
    record("PASS" if r.status_code == 200 and tub else "FAIL", r.status_code, "ANT tools",
           f"tool_use_blocks={len(tub)}")

def ant_think_on():
    # thinking enabled -> thinking block present (always-on, exposed)
    r = req("POST", "/v1/messages", {"model": MODEL, "max_tokens": 4096,
            "messages": [{"role": "user", "content": HARD}],
            "thinking": {"type": "enabled", "budget_tokens": 4096}})
    d = r.json(); blocks = d.get("content", [])
    has = any(b.get("type") == "thinking" for b in blocks)
    record("PASS" if r.status_code == 200 and has else "FAIL", r.status_code, "ANT think ON",
           f"has_thinking={has} types={[b.get('type') for b in blocks]}")

def ant_think_off():
    r = req("POST", "/v1/messages", {"model": MODEL, "max_tokens": 8000, "temperature": 0,
            "thinking": {"type": "disabled"}, "messages": [{"role": "user", "content": "Capital of France?"}]})
    d = r.json(); blocks = d.get("content", [])
    has = any(b.get("type") == "thinking" for b in blocks)
    record("PASS" if r.status_code == 200 and not has else "FAIL", r.status_code, "ANT think OFF (stripped)",
           f"has_thinking={has} output_tokens={d.get('usage',{}).get('output_tokens')}")

def guard_embed():
    r = req("GET", "/v1/models?all=true")
    embed = next((m["id"] for m in r.json().get("data", []) if m.get("type") == "embedding"), None)
    if not embed:
        record("SKIP", 0, "Guard: embed via ANT", "no embed model"); return
    r2 = req("POST", "/v1/messages", {"model": embed, "max_tokens": 10,
             "messages": [{"role": "user", "content": "test"}]})
    record("EXP" if r2.status_code == 400 else "FAIL", r2.status_code, "Guard: embed via ANT",
           f"code={r2.json().get('error',{}).get('code','')}")

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
    ok = c.get("reasoning") and c.get("tools") and not c.get("vision")
    record("PASS" if ok else "FAIL", r.status_code, "Catalog capabilities",
           f"vision={c.get('vision')} tools={c.get('tools')} reasoning={c.get('reasoning')} "
           f"ctx={m.get('context_window')} max_out={m.get('max_completion_tokens')}")


print("=" * 66, flush=True); print(f"{MODEL} comprehensive gateway test (always-on)", flush=True)
print("=" * 66, flush=True)
for t in [wake, stream, tools_oai, max_tokens, truncation, usage, resources,
          think_on, think_off, think_stream, meta_title, meta_tags, meta_followups, vision_rejected,
          ant_basic, ant_stream, ant_tools, ant_think_on, ant_think_off,
          guard_embed, guard_badmodel, catalog]:
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
