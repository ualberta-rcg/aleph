"""qwen38-27b comprehensive gateway test.

Qwen3.8-27B-FP8 (hybrid GDN VLM, TP2, vLLM v0.28.0). Effort mode with REAL effort levels
(low/medium/xhigh via chat-template kwarg reasoning_effort) + binary enable_thinking off.
Vision (image + video) + tools (qwen3_coder parser) + prefix caching + MTP spec decode.

Vision+tools variant: image must WORK, tools must WORK. Otherwise the standard battery.

Run externally via the public edge + Tyk auth (preferred):
  GW_URL=https://inference.vulcan.alliancecan.ca TYK_KEY=<key> \
      MODEL=qwen38-27b python3 models/qwen38-27b/test.py

Video check is env-gated (needs a reachable VIDEO_URL or a base64 clip in VIDEO_B64):
  VIDEO_URL=https://.../clip.mp4 python3 models/qwen38-27b/test.py
"""
import httpx, json, os, time

G = os.environ.get("GW_URL", "http://localhost:8080")
_KEY = os.environ.get("TYK_KEY")
_HEADERS = {"Authorization": f"Bearer {_KEY}"} if _KEY else {}
_VERIFY = os.environ.get("GW_INSECURE", "").lower() not in ("1", "true", "yes", "on")
MODEL = os.environ.get("MODEL", "qwen38-27b")
HARD = ("A farmer has 17 sheep. All but 9 die. How many sheep are left? "
        "Take that number, multiply by 7, then subtract 4. Show your reasoning.")
RED_PNG = "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8z8BQDwAEhQGAhKmMIQAAAABJRU5ErkJggg=="
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
            "reasoning_effort": "none", "max_tokens": 20, "temperature": 0}
    for attempt in range(84):
        r = req("POST", "/v1/chat/completions", body)
        if r.status_code == 200:
            m = r.json()["choices"][0]["message"]
            record("PASS", 200, "WAKE + OAI basic", f"attempts={attempt+1} content={safe(m,30)!r}")
            return
        if r.status_code == 503:
            time.sleep(5); continue
        record("FAIL", r.status_code, "WAKE + OAI basic", f"unexpected status body={r.text[:80]}")
        return
    record("FAIL", 503, "WAKE + OAI basic", "timed out waiting for warm model")


def stream():
    with req("POST", "/v1/chat/completions", {"model": MODEL,
             "messages": [{"role": "user", "content": "Count 1 to 3"}], "max_tokens": 30,
             "reasoning_effort": "none", "stream": True}, stream=True) as r:
        n = len([l for l in r.iter_lines() if l.startswith("data:") and "DONE" not in l])
    record("PASS" if r.status_code == 200 and n > 0 else "FAIL", r.status_code, "OAI streaming", f"{n} chunks")

def temp0():
    r, d, m = oai({"model": MODEL, "messages": [{"role": "user", "content": "Capital of France? One word."}],
                  "reasoning_effort": "none", "max_tokens": 20, "temperature": 0})
    ok = r.status_code == 200 and "paris" in (m.get("content") or "").lower()
    record("PASS" if ok else "FAIL", r.status_code, "OAI temp=0 + answer", safe(m))

def temp_topk():
    r, d, m = oai({"model": MODEL, "messages": [{"role": "user", "content": "Say hello"}],
                  "reasoning_effort": "none", "max_tokens": 20, "temperature": 0.7, "top_k": 20})
    record("PASS" if r.status_code == 200 else "FAIL", r.status_code, "OAI temp+top_k", safe(m))

def top_p():
    r, d, m = oai({"model": MODEL, "messages": [{"role": "user", "content": "Say hello"}],
                  "reasoning_effort": "none", "max_tokens": 20, "top_p": 0.8})
    record("PASS" if r.status_code == 200 else "FAIL", r.status_code, "OAI top_p", safe(m))

def presence_pen():
    r, d, m = oai({"model": MODEL, "messages": [{"role": "user", "content": "Say hello"}],
                  "reasoning_effort": "none", "max_tokens": 20, "temperature": 0.7,
                  "top_p": 0.8, "presence_penalty": 1.5})
    record("PASS" if r.status_code == 200 else "FAIL", r.status_code,
           "OAI non-thinking sampling (presence_penalty=1.5)", safe(m))

def stop_seq():
    r, d, m = oai({"model": MODEL, "messages": [{"role": "user", "content": "Count: 1, 2, 3, 4, 5, 6, 7"}],
                  "reasoning_effort": "none", "max_tokens": 50, "stop": ["5"]})
    fin = d["choices"][0].get("finish_reason")
    record("PASS" if r.status_code == 200 and fin == "stop" else "FAIL", r.status_code, "OAI stop sequences", f"finish={fin} {safe(m)}")

def system():
    r, d, m = oai({"model": MODEL, "messages": [{"role": "system", "content": "You are a pirate. Speak like a pirate."},
                  {"role": "user", "content": "Hello!"}], "reasoning_effort": "none", "max_tokens": 30})
    record("PASS" if r.status_code == 200 else "FAIL", r.status_code, "OAI system prompt", safe(m))

def tools_oai():
    r, d, m = oai({"model": MODEL, "messages": [{"role": "user", "content": "Weather in Edmonton?"}],
                  "reasoning_effort": "none", "max_tokens": 200, "tools": TOOLS})
    tc = m.get("tool_calls", [])
    name = tc[0]["function"]["name"] if tc else ""
    ok = r.status_code == 200 and tc and name == "get_weather"
    record("PASS" if ok else "FAIL", r.status_code, "OAI tools", f"tool_calls={len(tc)} name={name!r}")

def tools_think():
    r, d, m = oai({"model": MODEL, "messages": [{"role": "user", "content": "Weather in Edmonton?"}],
                  "reasoning_effort": "medium", "max_tokens": 2048, "tools": TOOLS})
    tc = m.get("tool_calls", [])
    rc = _rc(m)
    ok = r.status_code == 200 and tc
    record("PASS" if ok else "FAIL", r.status_code, "OAI tools + think ON",
           f"tool_calls={len(tc)} rc_len={len(rc)}")

def vision():
    r, d, m = oai({"model": MODEL, "max_tokens": 60, "reasoning_effort": "none",
            "messages": [{"role": "user", "content": [
                {"type": "text", "text": "What color is this image? One word."},
                {"type": "image_url", "image_url": {"url": RED_PNG}}]}]})
    record("PASS" if r.status_code == 200 and len(m.get("content") or "") > 0 else "FAIL",
           r.status_code, "OAI vision (image works)", safe(m, 40))

def video():
    url = os.environ.get("VIDEO_URL")
    b64 = os.environ.get("VIDEO_B64")
    if not url and not b64:
        record("SKIP", 0, "OAI vision (video)", "set VIDEO_URL or VIDEO_B64 to enable")
        return
    vurl = url or f"data:video/mp4;base64,{b64}"
    r, d, m = oai({"model": MODEL, "max_tokens": 100, "reasoning_effort": "none",
            "messages": [{"role": "user", "content": [
                {"type": "text", "text": "Describe this video in one sentence."},
                {"type": "video_url", "video_url": {"url": vurl}}]}]})
    ok = r.status_code == 200 and len(m.get("content") or "") > 0
    record("PASS" if ok else "FAIL", r.status_code, "OAI vision (video)", safe(m, 50))

def max_tokens():
    r, d, m = oai({"model": MODEL, "messages": [{"role": "user", "content": "Say hi"}],
                  "reasoning_effort": "none", "max_tokens": 8192})
    record("PASS" if r.status_code == 200 else "FAIL", r.status_code, "OAI max_tokens=8k", safe(m, 30))

def truncation():
    r, d, m = oai({"model": MODEL, "messages": [{"role": "user", "content": "Tell me a very long story."}],
                  "reasoning_effort": "none", "max_tokens": 5})
    fin = d["choices"][0].get("finish_reason"); ct = (d.get("usage") or {}).get("completion_tokens", 0)
    ok = r.status_code == 200 and fin == "length" and ct <= 8
    record("PASS" if ok else "FAIL", r.status_code, "OAI truncation max_tokens=5",
           f"finish={fin} completion_tokens={ct}")

def usage():
    r, d, m = oai({"model": MODEL, "messages": [{"role": "user", "content": "hi"}],
                  "reasoning_effort": "none", "max_tokens": 10})
    u = d.get("usage", {})
    ok = u.get("prompt_tokens") and MODEL in (d.get("model") or "")
    record("PASS" if ok else "FAIL", r.status_code, "OAI usage + model echo",
           f"prompt={u.get('prompt_tokens')} completion={u.get('completion_tokens')} model={d.get('model')!r}")

def resources():
    r, d, m = oai({"model": MODEL, "messages": [{"role": "user", "content": "hi"}],
                  "reasoning_effort": "none", "max_tokens": 10})
    res = d.get("resources", {})
    record("PASS" if r.status_code == 200 and "model" in res else "FAIL", r.status_code,
           "OAI resources block", f"keys={sorted(res.keys())}")

def prefix_cache():
    body = {"model": MODEL, "messages": [{"role": "user", "content":
            "Name the first 15 elements of the periodic table, one per line."}],
            "reasoning_effort": "none", "max_tokens": 400, "temperature": 0}
    r1, d1, m1 = oai(body)
    t0 = time.time()
    r2, d2, m2 = oai(body)
    dt = time.time() - t0
    same = (m1.get("content") or "").strip() == (m2.get("content") or "").strip()
    ok = r1.status_code == 200 and r2.status_code == 200 and same
    record("PASS" if ok else "FAIL", r2.status_code, "OAI prefix-cache repeat (deterministic)",
           f"identical={same} second_call={dt:.1f}s")

def think_on_medium():
    r, d, m = oai({"model": MODEL, "messages": [{"role": "user", "content": HARD}],
                  "reasoning_effort": "medium", "max_tokens": 4096, "temperature": 1.0})
    rc = _rc(m)
    record("PASS" if r.status_code == 200 and rc else "FAIL", r.status_code,
           "OAI think ON medium", f"rc_len={len(rc)} content_len={len(m.get('content') or '')}")

def think_on_high_alias():
    # high/xhigh alias down to medium on this vLLM build (protocol enum blocks xhigh,
    # model rejects high) — must still return 200 with reasoning, never 400.
    r, d, m = oai({"model": MODEL, "messages": [{"role": "user", "content": HARD}],
                  "reasoning_effort": "high", "max_tokens": 4096, "temperature": 1.0})
    rc = _rc(m)
    record("PASS" if r.status_code == 200 and rc else "FAIL", r.status_code,
           "OAI think ON high (aliased medium)", f"rc_len={len(rc)}")

def think_effort_scales():
    # Body-level reasoning_effort reaches the chat template: low vs medium must produce
    # different outputs at temp=0 (verified rc_len 699 vs 655 on the sqrt(2) prompt).
    body = {"model": MODEL, "messages": [{"role": "user", "content":
            "Prove that the square root of 2 is irrational, briefly."}],
            "max_tokens": 2048, "temperature": 0}
    _, dl, ml = oai({**body, "reasoning_effort": "low"})
    _, dm, mm = oai({**body, "reasoning_effort": "medium"})
    rl, rm = len(_rc(ml)), len(_rc(mm))
    differ = (ml.get("content") or "") != (mm.get("content") or "") or rl != rm
    record("PASS" if differ else "FAIL", dm and 200, "OAI effort levels distinct (low vs medium)",
           f"rc_len low={rl} medium={rm} content_differs={differ}")

def think_off():
    r, d, m = oai({"model": MODEL, "messages": [{"role": "user", "content": "Capital of France?"}],
                  "reasoning_effort": "none", "max_tokens": 8000, "temperature": 0})
    rc = _rc(m); ct = (d.get("usage") or {}).get("completion_tokens", 0)
    record("PASS" if r.status_code == 200 and not rc else "FAIL", r.status_code,
           "OAI think OFF", f"rc_len={len(rc)} {safe(m,30)!r} completion_tokens={ct}")

def think_budget():
    r, d, m = oai({"model": MODEL, "messages": [{"role": "user", "content": HARD}],
                  "thinking_token_budget": 2000, "max_tokens": 20000, "temperature": 1.0})
    rc = _rc(m); ct = (d.get("usage") or {}).get("completion_tokens", 0)
    record("PASS" if r.status_code == 200 and rc and ct <= 2600 else "FAIL", r.status_code,
           "OAI fake token-budget", f"rc_len={len(rc)} completion_tokens={ct} (budget 2000)")

def think_stream():
    rn = cn = 0
    with req("POST", "/v1/chat/completions", {"model": MODEL, "messages": [{"role": "user", "content": HARD}],
             "reasoning_effort": "medium", "max_tokens": 4096, "temperature": 1.0, "stream": True,
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
    record("PASS" if r.status_code == 200 and not rc and ct <= cap else "FAIL", r.status_code,
           f"OAI meta {name}", f"rc_len={len(rc)} completion_tokens={ct} (cap {cap}) {safe(m,30)!r}")

def meta_title():   _meta("Generate a concise, 3-5 word title", "title", 80)
def meta_tags():    _meta("Generate 1-3 broad tags", "tags", 60)
def meta_followups(): _meta("Suggest 3-5 relevant follow-up questions", "followups", 220)

def ant_basic():
    r = req("POST", "/v1/messages", {"model": MODEL, "max_tokens": 30, "temperature": 0,
            "thinking": {"type": "disabled"},
            "messages": [{"role": "user", "content": "What is 3+3? Just the number."}]})
    d = r.json(); t = next((b.get("text", "") for b in d.get("content", []) if b.get("type") == "text"), "")
    record("PASS" if r.status_code == 200 else "FAIL", r.status_code, "ANT basic", f"{t[:50]!r}")

def ant_stream():
    with req("POST", "/v1/messages", {"model": MODEL, "max_tokens": 30, "stream": True,
             "thinking": {"type": "disabled"}, "messages": [{"role": "user", "content": "Say hi"}]},
             stream=True) as r:
        etypes = set(l.split(": ", 1)[1].strip() for l in r.iter_lines() if l.startswith("event:"))
    record("PASS" if r.status_code == 200 else "FAIL", r.status_code, "ANT streaming", f"types={etypes}")

def ant_system():
    r = req("POST", "/v1/messages", {"model": MODEL, "max_tokens": 30, "thinking": {"type": "disabled"},
            "system": "You are a pirate.", "messages": [{"role": "user", "content": "Hello!"}]})
    d = r.json(); t = next((b.get("text", "") for b in d.get("content", []) if b.get("type") == "text"), "")
    record("PASS" if r.status_code == 200 else "FAIL", r.status_code, "ANT system", f"{t[:50]!r}")

def ant_temp0():
    r = req("POST", "/v1/messages", {"model": MODEL, "max_tokens": 20, "temperature": 0,
            "thinking": {"type": "disabled"}, "messages": [{"role": "user", "content": "Capital of France?"}]})
    d = r.json(); t = next((b.get("text", "") for b in d.get("content", []) if b.get("type") == "text"), "")
    record("PASS" if r.status_code == 200 else "FAIL", r.status_code, "ANT temp=0", f"{t[:50]!r}")

def ant_tools():
    r = req("POST", "/v1/messages", {"model": MODEL, "max_tokens": 200, "thinking": {"type": "disabled"},
            "messages": [{"role": "user", "content": "Weather in Edmonton?"}], "tools": ANT_TOOLS})
    d = r.json(); blocks = d.get("content", [])
    tub = [b for b in blocks if b.get("type") == "tool_use"]
    record("PASS" if r.status_code == 200 and tub else "FAIL", r.status_code, "ANT tools",
           f"tool_use_blocks={len(tub)}")

def ant_think_on():
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
    record("PASS" if r.status_code == 200 and not has else "FAIL", r.status_code, "ANT think OFF",
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
    ok = c.get("reasoning") and c.get("tools") and c.get("vision")
    record("PASS" if ok else "FAIL", r.status_code, "Catalog capabilities",
           f"vision={c.get('vision')} tools={c.get('tools')} reasoning={c.get('reasoning')} "
           f"ctx={m.get('context_window')} max_out={m.get('max_completion_tokens')}")


print("=" * 66, flush=True); print(f"{MODEL} comprehensive gateway test (vision+video+tools)", flush=True)
print("=" * 66, flush=True)
for t in [wake, stream, temp0, temp_topk, top_p, presence_pen, stop_seq, system,
          tools_oai, tools_think, vision, video, max_tokens, truncation,
          usage, resources, prefix_cache, think_on_medium, think_on_high_alias,
          think_effort_scales, think_off, think_budget, think_stream,
          meta_title, meta_tags, meta_followups,
          ant_basic, ant_stream, ant_system, ant_temp0, ant_tools,
          ant_think_on, ant_think_off, guard_embed, guard_badmodel, catalog]:
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
