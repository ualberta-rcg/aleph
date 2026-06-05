#!/usr/bin/env python3
"""Exercise thinking/reasoning levels across all chat models.
- gpt-oss: reasoning_effort low/medium/high should scale reasoning tokens.
- non-reasoning models: reasoning_effort must be ignored gracefully (no error).
- truncation check: gpt-oss high effort at the default vs max budget.
"""
import json, urllib.request

U = "http://172.26.92.230:30808/v1/chat/completions"
KEY = open("/tmp/ttk").read().strip()
MODELS = ["gpt-oss-20b", "command-r-7b", "gemma-3-4b-it", "qwen25-vl-7b"]

Q = ("You have a 3-liter jug and a 5-liter jug and unlimited water. "
     "Explain step by step how to measure exactly 4 liters, then double-check.")
HARD = ("Count the number of distinct integer solutions to a+b+c+d=20 with each "
        "variable between 0 and 9 inclusive. Show your full reasoning, then give the number.")


def call(model, q, effort=None, max_tokens=None):
    body = {"model": model, "messages": [{"role": "user", "content": q}], "temperature": 0.3}
    if effort:
        body["reasoning_effort"] = effort
    if max_tokens:
        body["max_tokens"] = max_tokens
    req = urllib.request.Request(U, data=json.dumps(body).encode(),
        headers={"Authorization": "Bearer " + KEY, "Content-Type": "application/json"})
    try:
        d = json.loads(urllib.request.urlopen(req, timeout=180).read())
    except urllib.error.HTTPError as e:
        return {"err": f"HTTP {e.code}: {e.read()[:120].decode(errors='ignore')}"}
    except Exception as e:
        return {"err": str(e)[:140]}
    if "choices" not in d:
        return {"err": "no-choices " + json.dumps(d)[:140]}
    ch = d["choices"][0]
    msg = ch["message"]
    usage = d.get("usage", {}) or {}
    det = usage.get("completion_tokens_details") or {}
    reasoning = msg.get("reasoning") or msg.get("reasoning_content") or ""
    return {
        "finish": ch.get("finish_reason"),
        "compl": usage.get("completion_tokens"),
        "reason_tok": det.get("reasoning_tokens"),
        "reason_chars": len(reasoning),
        "answer": (msg.get("content") or "").strip().replace("\n", " "),
    }


def show(tag, r):
    if "err" in r:
        print(f"    {tag:26s} ERR {r['err']}")
        return
    ans = r["answer"][:70]
    print(f"    {tag:26s} finish={r['finish']:>6} compl={str(r['compl']):>5} "
          f"reason_tok={str(r['reason_tok']):>5} reason_chars={r['reason_chars']:>5} | {ans}")


print("### Phase 1: effort levels, max_tokens=4096, jug puzzle")
for m in MODELS:
    print(f"\n{m}:")
    for eff in [None, "low", "medium", "high"]:
        show(f"effort={eff}", call(m, Q, effort=eff, max_tokens=4096))

print("\n\n### Phase 2: gpt-oss-20b HIGH effort on hard combinatorics")
print("gpt-oss-20b:")
show("high, default budget", call("gpt-oss-20b", HARD, effort="high"))
show("high, max_tokens=32768", call("gpt-oss-20b", HARD, effort="high", max_tokens=32768))
