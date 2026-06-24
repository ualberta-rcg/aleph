#!/usr/bin/env python3
"""Focused retest of the fixes: reasoning small-budget empties, command-r tools,
qwen-vl tools (auto + forced), prokbert batch embeddings."""
import json
import sys
import time
import urllib.request
import urllib.error

BASE = sys.argv[1] if len(sys.argv) > 1 else "http://10.43.147.39:80"


def post(path, payload, timeout=180):
    data = json.dumps(payload).encode()
    req = urllib.request.Request(BASE + path, data=data, headers={"Content-Type": "application/json"})
    try:
        r = urllib.request.urlopen(req, timeout=timeout)
        return r.status, json.loads(r.read())
    except urllib.error.HTTPError as e:
        try:
            return e.code, json.loads(e.read())
        except Exception:
            return e.code, {"_raw": "x"}
    except Exception as e:
        return None, {"_err": str(e)}


def warm(path, payload):
    t0 = time.time()
    while time.time() - t0 < 420:
        c, _ = post(path, payload, 60)
        if c == 200:
            return True
        time.sleep(8)
    return False


def txt(b):
    try:
        return b["choices"][0]["message"].get("content") or ""
    except Exception:
        return ""


def tcalls(b):
    try:
        return b["choices"][0]["message"].get("tool_calls")
    except Exception:
        return None


print(f"== retest {BASE} ==")

# 1) reasoning small-budget empties
for m in ("gpt-oss-20b", "qwen35-122b"):
    warm("/v1/chat/completions", {"model": m, "messages": [{"role": "user", "content": "hi"}], "max_tokens": 1})
    c, b = post("/v1/chat/completions", {"model": m, "messages": [{"role": "user", "content": "Reply with just: pong"}], "max_tokens": 64})
    print(f"[{'PASS' if c==200 and txt(b).strip() else 'FAIL'}] {m} openai basic(mt=64) -> {c} {txt(b)[:40]!r}")
    c, b = post("/v1/chat/completions", {"model": m, "messages": [{"role": "user", "content": ("filler "*400)+"\nReply: DONE"}], "max_tokens": 32})
    print(f"[{'PASS' if c==200 and txt(b).strip() else 'FAIL'}] {m} openai context(mt=32) -> {c} {txt(b)[:40]!r}")
    # explicit high effort + big budget should STILL reason and answer
    c, b = post("/v1/chat/completions", {"model": m, "messages": [{"role": "user", "content": "What is 12*12? number only"}], "reasoning_effort": "high", "max_tokens": 16384})
    leak = "reasoning" in (b.get("choices",[{}])[0].get("message",{}) if c==200 else {})
    print(f"[{'PASS' if c==200 and txt(b).strip() and not leak else 'FAIL'}] {m} openai explicit-high(mt=16384) -> {c} {txt(b)[:24]!r} leak={leak}")

# 2) command-r tools (pythonic)
warm("/v1/chat/completions", {"model": "command-r-7b", "messages": [{"role": "user", "content": "hi"}], "max_tokens": 1})
tools = [{"type": "function", "function": {"name": "get_weather", "description": "Get current weather for a city",
          "parameters": {"type": "object", "properties": {"city": {"type": "string"}}, "required": ["city"]}}}]
c, b = post("/v1/chat/completions", {"model": "command-r-7b", "messages": [{"role": "user", "content": "What's the weather in Paris? Use the get_weather tool."}], "tools": tools, "tool_choice": "auto", "max_tokens": 256})
tc = tcalls(b)
print(f"[{'PASS' if c==200 and tc else 'FAIL'}] command-r-7b openai tools(auto) -> {c} tool_calls={tc if tc else txt(b)[:60]!r}")

# 3) qwen-vl tools: auto + forced
warm("/v1/chat/completions", {"model": "qwen25-vl-7b", "messages": [{"role": "user", "content": "hi"}], "max_tokens": 1})
c, b = post("/v1/chat/completions", {"model": "qwen25-vl-7b", "messages": [{"role": "user", "content": "What's the weather in Paris? You must call the get_weather tool."}], "tools": tools, "tool_choice": "auto", "max_tokens": 256})
tc = tcalls(b)
print(f"[{'PASS' if c==200 and tc else 'WARN'}] qwen25-vl-7b openai tools(auto) -> {c} tool_calls={tc if tc else txt(b)[:50]!r}")
c, b = post("/v1/chat/completions", {"model": "qwen25-vl-7b", "messages": [{"role": "user", "content": "Weather in Paris?"}], "tools": tools, "tool_choice": {"type": "function", "function": {"name": "get_weather"}}, "max_tokens": 256})
tc = tcalls(b)
print(f"[{'PASS' if c==200 and tc else 'FAIL'}] qwen25-vl-7b openai tools(forced) -> {c} tool_calls={tc if tc else txt(b)[:50]!r}")

# 4) prokbert batch
warm("/v1/embeddings", {"model": "prokbert", "input": "ACGT"})
c, b = post("/v1/embeddings", {"model": "prokbert", "input": ["ACGTACGT", "TTTTGGGG"]})
n = len(b.get("data", [])) if c == 200 else 0
print(f"[{'PASS' if n==2 else 'FAIL'}] prokbert openai embed_batch -> {c} n={n}")

print("== done ==")
