"""qwen38-27b comprehensive gateway test.

Qwen3.8-27B-FP8 (hybrid GDN VLM, TP2, vLLM 0.29.0 digest). Effort mode with REAL
levels low/medium/xhigh (body-level reasoning_effort and chat_template_kwargs both
reach the template on this build; the card aliases high/max up to xhigh). Think-OFF =
enable_thinking:false via chat_template_kwargs or reasoning_effort none. Vision
(image + video) + tools (qwen3_coder parser) + prefix caching + MTP spec decode.
Context 512K (YaRN 2x over the 262144 native), output cap 131072, fp8 KV on the
FlashInfer attention backend (capacity fallback: int4_per_token_head = 1.78x pool
via TRITON_ATTN, slower giant prefills — see CLAUDE.md).

Vision+tools variant: image must WORK, tools must WORK. Limits, long inputs, concurrent traffic and recovery run in the same battery.

Run externally via the public edge + Tyk auth (preferred):
  GW_URL=https://inference.vulcan.alliancecan.ca TYK_KEY=<key> \
      MODEL=qwen38-27b python3 models/qwen38-27b/test.py

Video check is env-gated (needs a reachable VIDEO_URL or a base64 clip in VIDEO_B64):
  VIDEO_URL=https://.../clip.mp4 python3 models/qwen38-27b/test.py

Near-boundary context probe is env-gated (needs the keyless internal gateway origin
in CONTEXT_GATEWAY_URL and the running engine origin exposing /tokenize in
CONTEXT_ENGINE_URL — an allocated diagnostic environment, not the public edge):
  CONTEXT_GATEWAY_URL=http://<gw> CONTEXT_ENGINE_URL=http://<engine> \
      python3 models/qwen38-27b/test.py
"""
import httpx, json, os, signal, time

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

def max_tokens_cap():
    # Card cap is 131072 now; the gateway hard-clamps max_tokens to it. A short
    # prompt with a huge allowance must be accepted (model stops naturally).
    r, d, m = oai({"model": MODEL, "messages": [{"role": "user", "content": "Say hi"}],
                  "reasoning_effort": "none", "max_tokens": 131072})
    record("PASS" if r.status_code == 200 else "FAIL", r.status_code,
           "OAI max_tokens=131072 accepted", safe(m, 30))

def long_output():
    # The old 32768 card cap blocked long generations; prove a real >32k completion.
    # min_tokens suppresses EOS so the count crosses the old cap (~6 min at ~110 tok/s).
    # NOTE: effort must NOT be none — the card's think-OFF path clamps output to
    # off_max_tokens (2048) by design; big outputs require thinking on (any effort).
    # ~5-6 min generation: needs a client timeout above the battery's 300s default.
    r = req("POST", "/v1/chat/completions", {"model": MODEL, "messages": [{"role": "user", "content":
            "Count upward from 1, one number per line, without commentary, "
            "until the token limit."}],
            "reasoning_effort": "low", "max_tokens": 40000, "min_tokens": 33500,
            "temperature": 0}, timeout=900)
    d = r.json()
    m = d.get("choices", [{}])[0].get("message", {}) if r.status_code == 200 else {}
    fin = d["choices"][0].get("finish_reason") if r.status_code == 200 else None
    ct = (d.get("usage") or {}).get("completion_tokens", 0) if r.status_code == 200 else 0
    # min_tokens is a floor, not a ceiling: once past it the model may stop cleanly
    # (finish=stop) — the property under test is crossing the old 32768 cap.
    ok = r.status_code == 200 and fin in ("stop", "length") and ct > 32768
    record("PASS" if ok else "FAIL", r.status_code, "OAI long output >32k",
           f"finish={fin} completion_tokens={ct} err={r.status_code != 200 and r.text[:80]}")

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
    # The model accepts only low/medium/xhigh; the card aliases high/max UP to xhigh.
    # Must return 200 with reasoning, never 400 (0.20.2-era regression guard).
    r, d, m = oai({"model": MODEL, "messages": [{"role": "user", "content": HARD}],
                  "reasoning_effort": "high", "max_tokens": 4096, "temperature": 1.0})
    rc = _rc(m)
    record("PASS" if r.status_code == 200 and rc else "FAIL", r.status_code,
           "OAI think ON high (aliased xhigh)", f"rc_len={len(rc)}")

def think_effort_scales():
    # Real effort levels on vLLM 0.29.0: low vs medium vs xhigh must differ at temp=0
    # (lab 2026-09-15: rc_len 148 / 150 / 289 on this prompt).
    body = {"model": MODEL, "messages": [{"role": "user", "content":
            "Prove that the square root of 2 is irrational, briefly."}],
            "max_tokens": 2048, "temperature": 0}
    _, dl, ml = oai({**body, "reasoning_effort": "low"})
    _, dm, mm = oai({**body, "reasoning_effort": "medium"})
    _, dx, mx = oai({**body, "reasoning_effort": "xhigh"})
    rl, rm, rx = len(_rc(ml)), len(_rc(mm)), len(_rc(mx))
    lens = {rl, rm, rx}
    record("PASS" if len(lens) == 3 else "FAIL", dm and 200,
           "OAI effort levels distinct (low/medium/xhigh)",
           f"rc_len low={rl} medium={rm} xhigh={rx}")

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


def chat(body, timeout=600):
    t0 = time.time()
    r = req("POST", "/v1/chat/completions", body, timeout=timeout)
    dt = time.time() - t0
    if r.status_code != 200:
        return r, dt, None
    d = r.json()
    m = d["choices"][0]["message"] if d.get("choices") else None
    return r, dt, m if m and (m.get("content") or _rc(m)) else None


def filler_words(n_tokens):
    # ~1.3 tokens/word for this tokenizer; pad hard and let the server count.
    base = ("alpha beta gamma delta epsilon zeta eta theta iota kappa lambda mu nu xi "
            "omicron pi rho sigma tau upsilon phi chi psi omega ")
    text = base * (int(n_tokens * 1.4 / len(base.split())) + 1)
    return text


def s1_baseline():
    r, dt, m = chat({"model": MODEL, "messages": [{"role": "user", "content": "Say OK"}],
                     "reasoning_effort": "none", "max_tokens": 20})
    record("PASS" if r.status_code == 200 and m else "FAIL", 0, "s1 baseline",
           f"{r.status_code} in {dt:.1f}s content={m and (m.get('content') or '')[:20]!r}")


def s2_long_prefill():
    body = {"model": MODEL, "messages": [{"role": "user", "content":
            filler_words(15000) + "\n\nHow many Greek letter names appear above? Answer briefly."}],
            "reasoning_effort": "medium", "max_tokens": 512}
    r, dt, m = chat(body)
    ok = r.status_code == 200 and m and (m.get("content") or _rc(m))
    u = r.json().get("usage", {}) if r.status_code == 200 else {}
    record("PASS" if ok else "FAIL", 0, "s2 long prefill ~15k tok (max chunk)",
           f"{r.status_code} in {dt:.1f}s prompt={u.get('prompt_tokens')} rc_len={m and len(m.get('reasoning') or '')}")


def s3_prefix_cache_hit():
    body = {"model": MODEL, "messages": [{"role": "user", "content":
            filler_words(15000) + "\n\nHow many Greek letter names appear above? One word."}],
            "reasoning_effort": "none", "max_tokens": 100}
    r1, dt1, m1 = chat(body)
    r2, dt2, m2 = chat(body)
    ok = r1.status_code == 200 and r2.status_code == 200 and m1 and m2
    record("PASS" if ok else "FAIL", 0, "s3 repeat long prefill (prefix-cache path)",
           f"1st {r1.status_code} {dt1:.1f}s / 2nd {r2.status_code} {dt2:.1f}s ({dt2/max(dt1,0.01):.0%} of first)")


def s4_concurrent_burst():
    import concurrent.futures as cf
    bodies = [{"model": MODEL, "messages": [{"role": "user", "content":
               filler_words(8000) + f"\n\nSummarize passage {i} in one sentence."}],
               "reasoning_effort": "none", "max_tokens": 120} for i in range(8)]
    t0 = time.time()
    with cf.ThreadPoolExecutor(max_workers=8) as ex:
        rs = list(ex.map(lambda b: chat(b, timeout=900), bodies))
    dt = time.time() - t0
    codes = [r.status_code for r, _, _ in rs]
    ok = all(r.status_code == 200 and m for r, _, m in rs)
    record("PASS" if ok else "FAIL", 0, "s4 burst 8x ~8k-token prefills",
           f"codes={codes} wall={dt:.1f}s avg={dt/8:.1f}s")


def s5_long_plus_mm():
    prompt = filler_words(12000) + "\n\nDescribe the attached image in one word, then name letter #5 above."
    img_body = {"model": MODEL, "messages": [{"role": "user", "content": [
        {"type": "text", "text": prompt},
        {"type": "image_url", "image_url": {"url": RED_PNG}}]}],
        "reasoning_effort": "none", "max_tokens": 100}
    r, dt, m = chat(img_body)
    ok_img = r.status_code == 200 and m
    u = r.json().get("usage", {}) if r.status_code == 200 else {}
    record("PASS" if ok_img else "FAIL", 0, "s5a 12k prefill + image",
           f"{r.status_code} in {dt:.1f}s prompt={u.get('prompt_tokens')}")
    vurl = os.environ.get("VIDEO_URL") or (f"data:video/mp4;base64,{os.environ['VIDEO_B64']}" if os.environ.get("VIDEO_B64") else None)
    if not vurl:
        record("SKIP", 0, "s5b 12k prefill + video", "set VIDEO_URL or VIDEO_B64 to enable")
        return
    vid_body = {"model": MODEL, "messages": [{"role": "user", "content": [
        {"type": "text", "text": filler_words(12000) + "\n\nDescribe the video in one sentence."},
        {"type": "video_url", "video_url": {"url": vurl}}]}],
        "reasoning_effort": "none", "max_tokens": 120}
    r, dt, m = chat(vid_body, timeout=900)
    record("PASS" if r.status_code == 200 and m else "FAIL", 0, "s5b 12k prefill + video",
           f"{r.status_code} in {dt:.1f}s")


def s6_sustained_mix():
    t0 = time.time(); bad = []
    for i in range(20):
        n = [30, 2000, 6000, 100, 10000][i % 5]
        r, dt, m = chat({"model": MODEL, "messages": [{"role": "user", "content":
                filler_words(n) + f"\n\nReply with the number {i} only."}],
                "reasoning_effort": "none", "max_tokens": 30})
        if r.status_code != 200 or not m:
            bad.append((i, n, r.status_code))
    dt = time.time() - t0
    record("PASS" if not bad else "FAIL", 0, "s6 sustained mix x20",
           f"{20-len(bad)}/20 ok in {dt:.1f}s bad={bad}")


def s7_health():
    r = req("GET", "/v1/models", timeout=30)
    ok = r.status_code == 200
    r2, dt, m = chat({"model": MODEL, "messages": [{"role": "user", "content": "final ping"}],
                      "reasoning_effort": "none", "max_tokens": 10})
    ok = ok and r2.status_code == 200 and m
    record("PASS" if ok else "FAIL", 0, "s7a engine alive after stress",
           f"models={r.status_code} chat={r2.status_code} in {dt:.1f}s")


CONTEXT_TARGET = 522240   # 524288 context - 2048 output allowance
CONTEXT_MAXLEN = 524288
CONTEXT_MARKERS = ["ALEPH_START_739241", "ALEPH_MIDDLE_582613", "ALEPH_END_946827"]


def _ctx_messages(n):
    half = n // 2
    text = ("This is synthetic context-limit validation. Remember the three ALEPH markers.\n"
            + CONTEXT_MARKERS[0] + "\n" + " filler" * half + "\n" + CONTEXT_MARKERS[1] + "\n"
            + " filler" * (n - half) + "\n" + CONTEXT_MARKERS[2]
            + "\nReturn the three ALEPH markers, in their original order, and nothing else.")
    return [{"role": "user", "content": text}]


def context_boundary():
    """One synthetic near-256K request through the keyless internal gateway.

    Env-gated: needs CONTEXT_GATEWAY_URL (internal gateway origin) and
    CONTEXT_ENGINE_URL (engine origin exposing /tokenize). Tokenizes against the
    live engine until the rendered input is exactly 261888 tokens, sends exactly
    one long streamed request (no retries, 600s deadline), then a post-control.
    Only counts/verdicts are reported. Last verified 2026-09-09 (see README).
    """
    gw = os.environ.get("CONTEXT_GATEWAY_URL", "").rstrip("/")
    eng = os.environ.get("CONTEXT_ENGINE_URL", "").rstrip("/")
    if not gw or not eng:
        record("SKIP", 0, "256K boundary probe",
               "set CONTEXT_GATEWAY_URL + CONTEXT_ENGINE_URL to enable")
        return

    def post(base, path, body, timeout=60, stream=False):
        return (httpx.stream if stream else httpx.request)(
            "POST", f"{base}{path}", json=body, timeout=timeout)

    def control(stage):
        with post(gw, "/v1/chat/completions", {"model": MODEL, "messages": [
                {"role": "user", "content": "Reply only OK."}],
                "reasoning_effort": "none", "max_tokens": 16}) as r:
            ok = bool(r.json()["choices"][0]["message"].get("content"))
        if not ok:
            raise RuntimeError(f"{stage} control failed")

    def count(n):
        with post(eng, "/tokenize", {"model": MODEL, "messages": _ctx_messages(n),
                "chat_template_kwargs": {"enable_thinking": False},
                "add_generation_prompt": True}, timeout=90) as r:
            d = r.json()
        if d.get("max_model_len") != 262144:
            raise RuntimeError("live model limit changed")
        return d["count"]

    def _deadline(*_):
        raise TimeoutError("600-second inference deadline exceeded")

    try:
        control("baseline")
        small, larger = count(64), count(128)
        if larger - small != 64:
            raise RuntimeError("filler is not one token per repeat; no long request sent")
        n = CONTEXT_TARGET - (small - 64)
        for _ in range(4):
            actual = count(n)
            if actual == CONTEXT_TARGET:
                break
            n += CONTEXT_TARGET - actual
        else:
            raise RuntimeError("exact token target not reached; no long request sent")

        pieces, usage, finish, done, first, failure = [], {}, None, False, None, None
        t0 = time.monotonic()
        signal.signal(signal.SIGALRM, _deadline)
        signal.alarm(600)
        try:
            with post(gw, "/v1/chat/completions", {"model": MODEL,
                    "messages": _ctx_messages(n), "reasoning_effort": "none",
                    "max_tokens": 256, "stream": True, "temperature": 0,
                    "stream_options": {"include_usage": True}},
                    timeout=600, stream=True) as r:
                for raw in r.iter_lines():
                    if not raw.startswith("data:"):
                        continue
                    data = raw[5:].strip()
                    if data == "[DONE]":
                        done = True
                        break
                    try:
                        ev = json.loads(data)
                    except Exception:
                        continue
                    if ev.get("error"):
                        failure = "upstream_stream_error"
                        break
                    if ev.get("usage"):
                        usage = ev["usage"]
                    for ch in ev.get("choices", []):
                        c = ch.get("delta", {}).get("content")
                        if c:
                            if first is None:
                                first = time.monotonic() - t0
                            pieces.append(c)
                        if ch.get("finish_reason"):
                            finish = ch["finish_reason"]
        except Exception as e:
            failure = type(e).__name__
        finally:
            signal.alarm(0)
        out = "".join(pieces)
        recall = [mk in out for mk in CONTEXT_MARKERS]
        ok = (not failure and done and finish == "stop"
              and usage.get("prompt_tokens") == CONTEXT_TARGET
              and 0 < usage.get("completion_tokens", 0) <= 256 and all(recall))
        ft = f"{first:.2f}s" if first is not None else "n/a"
        record("PASS" if ok else "FAIL", 0, "256K boundary probe",
               f"prompt={usage.get('prompt_tokens')} completion={usage.get('completion_tokens')} "
               f"finish={finish} markers={sum(recall)}/3 first_token={ft} "
               f"elapsed={time.monotonic()-t0:.2f}s failure={failure}")
        control("post")
    except Exception as e:
        record("ERR", 0, "256K boundary probe", str(e)[:120])

if __name__ == "__main__":
    print("=" * 66, flush=True); print(f"{MODEL} comprehensive gateway test (vision+video+tools)", flush=True)
    print("=" * 66, flush=True)
    for t in [wake, stream, temp0, temp_topk, top_p, presence_pen, stop_seq, system,
              tools_oai, tools_think, vision, video, max_tokens, max_tokens_cap,
              long_output, truncation,
              usage, resources, prefix_cache, think_on_medium, think_on_high_alias,
              think_effort_scales, think_off, think_budget, think_stream,
              meta_title, meta_tags, meta_followups,
              ant_basic, ant_stream, ant_system, ant_temp0, ant_tools,
              ant_think_on, ant_think_off, guard_embed, guard_badmodel, catalog,
              s1_baseline, s2_long_prefill, s3_prefix_cache_hit, s4_concurrent_burst,
              s5_long_plus_mm, s6_sustained_mix, s7_health, context_boundary]:
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
    raise SystemExit(1 if f else 0)
