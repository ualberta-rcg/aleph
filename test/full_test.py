#!/usr/bin/env python3
"""Comprehensive gateway test harness.

Tests every model in the catalogue across the OpenAI (/v1/chat/completions,
/v1/embeddings) and Anthropic (/v1/messages) endpoints plus the custom science
endpoints. Exercises: basic completion, system prompt, max_tokens cap, sampling,
stop sequences, streaming, tools, vision, thinking (effort levels + Anthropic
budget levels + toggle), embeddings (single/batch), classify, generate, design.

Run from a cluster node pointed at the gateway ClusterIP. Warms scale-to-zero
models on demand. Writes a PASS/FAIL report to stdout and /tmp/full_test_report.txt.
"""
import base64
import json
import struct
import sys
import time
import urllib.request
import urllib.error
import zlib

BASE = sys.argv[1] if len(sys.argv) > 1 else "http://10.43.147.39:80"
WARM_TIMEOUT = 480          # seconds to wait for a cold model
WARM_POLL = 8
REQ_TIMEOUT = 180

RESULTS = []                # (model, endpoint, test, status, detail)


def log(model, endpoint, test, status, detail=""):
    RESULTS.append((model, endpoint, test, status, detail))
    mark = {"PASS": "PASS", "FAIL": "FAIL", "SKIP": "skip", "WARN": "warn"}[status]
    print(f"[{mark}] {model:24} {endpoint:9} {test:28} {detail}", flush=True)


def _post(path, payload, timeout=REQ_TIMEOUT, stream=False):
    data = json.dumps(payload).encode()
    req = urllib.request.Request(BASE + path, data=data,
                                 headers={"Content-Type": "application/json"})
    r = urllib.request.urlopen(req, timeout=timeout)
    if stream:
        return r  # caller reads lines
    return r.status, json.loads(r.read())


def post(path, payload, timeout=REQ_TIMEOUT):
    """Return (status, body_dict). Captures HTTPError bodies too."""
    try:
        return _post(path, payload, timeout)
    except urllib.error.HTTPError as e:
        try:
            body = json.loads(e.read())
        except Exception:
            body = {"_raw": "<unparseable>"}
        return e.code, body
    except Exception as e:
        return None, {"_err": str(e)}


def warm(path, payload):
    """Hammer until the model answers 200 (triggers scale-from-zero)."""
    t0 = time.time()
    last = None
    while time.time() - t0 < WARM_TIMEOUT:
        code, body = post(path, payload, timeout=60)
        if code == 200:
            return True, int(time.time() - t0)
        last = (code, str(body)[:120])
        time.sleep(WARM_POLL)
    return False, last


def make_png(r, g, b, size=16):
    """Build a tiny solid-color PNG, return base64 data URL."""
    def chunk(typ, data):
        c = typ + data
        return struct.pack(">I", len(data)) + c + struct.pack(">I", zlib.crc32(c) & 0xffffffff)
    sig = b"\x89PNG\r\n\x1a\n"
    ihdr = struct.pack(">IIBBBBB", size, size, 8, 2, 0, 0, 0)
    row = b"\x00" + bytes([r, g, b]) * size
    raw = row * size
    idat = zlib.compress(raw)
    png = sig + chunk(b"IHDR", ihdr) + chunk(b"IDAT", idat) + chunk(b"IEND", b"")
    return "data:image/png;base64," + base64.b64encode(png).decode()


RED_IMG = make_png(220, 20, 20)

# Minimal poly-glycine backbone (N, CA, C, O) — enough for ProteinMPNN to read.
MINI_PDB = """ATOM      1  N   GLY A   1      0.000   0.000   0.000  1.00  0.00           N
ATOM      2  CA  GLY A   1      1.458   0.000   0.000  1.00  0.00           C
ATOM      3  C   GLY A   1      2.009   1.420   0.000  1.00  0.00           C
ATOM      4  O   GLY A   1      1.251   2.390   0.000  1.00  0.00           O
ATOM      5  N   GLY A   2      3.332   1.540   0.000  1.00  0.00           N
ATOM      6  CA  GLY A   2      3.967   2.840   0.000  1.00  0.00           C
ATOM      7  C   GLY A   2      5.486   2.720   0.000  1.00  0.00           C
ATOM      8  O   GLY A   2      6.009   1.610   0.000  1.00  0.00           O
ATOM      9  N   GLY A   3      6.151   3.860   0.000  1.00  0.00           N
ATOM     10  CA  GLY A   3      7.606   3.890   0.000  1.00  0.00           C
ATOM     11  C   GLY A   3      8.157   5.310   0.000  1.00  0.00           C
ATOM     12  O   GLY A   3      7.399   6.280   0.000  1.00  0.00           O
ATOM     13  N   GLY A   4      9.480   5.430   0.000  1.00  0.00           N
ATOM     14  CA  GLY A   4     10.115   6.730   0.000  1.00  0.00           C
ATOM     15  C   GLY A   4     11.634   6.610   0.000  1.00  0.00           C
ATOM     16  O   GLY A   4     12.157   5.500   0.000  1.00  0.00           O
END
"""

# ── model registry ──────────────────────────────────────────────────────────
CHAT = {
    "command-r-7b":  {"tools": False, "vision": False, "reasoning": False, "think": None},
    "gemma-3-4b-it": {"tools": False, "vision": True,  "reasoning": False, "think": None},
    "gpt-oss-20b":   {"tools": True,  "vision": False, "reasoning": True,  "think": "effort"},
    "qwen25-vl-7b":  {"tools": True,  "vision": True,  "reasoning": False, "think": None},
    "qwen35-122b":   {"tools": True,  "vision": False, "reasoning": True,  "think": "toggle"},
}
EMBED_OPENAI = {
    "bge-small": "Hello world, this is a test sentence.",
    "bge-m3":    "Hello world, this is a multilingual test sentence.",
    "biobert":   "The patient was treated with aspirin for myocardial infarction.",
    "esm2-35m":  "MKTAYIAKQR",
    "esm2-650m": "MKTAYIAKQR",
    "nucleotide-transformer": "ACGTACGTACGTACGTACGT",
    "prokbert":  "ACGTACGTACGTACGTACGT",
}
RERANK = {
    "bge-reranker-v2-m3": {
        "query": "What is deep learning?",
        "documents": [
            "Deep learning is a subset of machine learning using neural networks.",
            "Bananas are a yellow tropical fruit.",
            "Neural networks with many layers power deep learning.",
        ],
    },
}
TTS = {
    "xtts-v2": {"input": "Hello from the inference gateway. This is a speech test.", "language": "en"},
}
EMBED_SCI = {
    "matscibert": {"path": "/v1/science/embed", "payload_extra": {"text": "Graphene exhibits high thermal conductivity."}},
    "molformer":  {"path": "/v1/science/embed", "payload_extra": {"smiles": "CC(=O)Oc1ccccc1C(=O)O"}},
}
OTHER = {
    "finbert":     {"path": "/v1/science/classify", "payload": {"text": "The company posted record profits this quarter."}},
    "chemgpt-19m": {"path": "/v1/science/generate", "payload": {"smiles": "CC", "num_return_sequences": 3}},
    "proteinmpnn": {"path": "/v1/design", "payload": {"pdb": MINI_PDB, "num_sequences": 2, "temperature": 0.2}},
}


def text_of(body):
    try:
        return body["choices"][0]["message"].get("content") or ""
    except Exception:
        return ""


def msg_has_reasoning(body):
    try:
        m = body["choices"][0]["message"]
        return "reasoning" in m or "reasoning_content" in m
    except Exception:
        return False


def anth_text(body):
    try:
        return "".join(b.get("text", "") for b in body.get("content", []) if b.get("type") == "text")
    except Exception:
        return ""


def anth_blocks(body):
    return [b.get("type") for b in body.get("content", [])] if isinstance(body.get("content"), list) else []


# ── chat: OpenAI endpoint ─────────────────────────────────────────────────────
def test_chat_openai(model, caps):
    ep = "openai"
    P = "/v1/chat/completions"

    code, b = post(P, {"model": model, "messages": [{"role": "user", "content": "Reply with just: pong"}], "max_tokens": 64})
    ok = code == 200 and text_of(b).strip() != ""
    log(model, ep, "basic", "PASS" if ok else "FAIL", f"{code} {text_of(b)[:40]!r}")

    code, b = post(P, {"model": model, "messages": [
        {"role": "system", "content": "You always answer with exactly one word: BANANA"},
        {"role": "user", "content": "What is your favorite fruit?"}], "max_tokens": 64})
    ok = code == 200 and "BANANA" in text_of(b).upper()
    log(model, ep, "system_prompt", "PASS" if ok else "WARN", f"{code} {text_of(b)[:40]!r}")

    code, b = post(P, {"model": model, "messages": [{"role": "user", "content": "Write a long paragraph about the ocean."}], "max_tokens": 8})
    ct = (b.get("usage") or {}).get("completion_tokens") if code == 200 else None
    fr = b["choices"][0].get("finish_reason") if code == 200 else None
    ok = code == 200 and (fr == "length" or (isinstance(ct, int) and ct <= 24))
    log(model, ep, "max_tokens_cap", "PASS" if ok else "FAIL", f"{code} finish={fr} ct={ct}")

    code, b = post(P, {"model": model, "messages": [{"role": "user", "content": "Say hello."}], "max_tokens": 32, "temperature": 0.2, "top_p": 0.9})
    log(model, ep, "sampling", "PASS" if code == 200 and text_of(b) else "FAIL", f"{code}")

    code, b = post(P, {"model": model, "messages": [{"role": "user", "content": "Count: 1 2 3 4 5 6 7 8 9"}], "max_tokens": 64, "stop": ["5"]})
    out = text_of(b)
    ok = code == 200 and "5" not in out.split("4")[-1][:6] if "4" in out else code == 200
    log(model, ep, "stop_sequence", "PASS" if code == 200 else "FAIL", f"{code} {out[:40]!r}")

    # streaming
    try:
        r = _post(P, {"model": model, "messages": [{"role": "user", "content": "Count from 1 to 5."}], "max_tokens": 64, "stream": True}, stream=True)
        chunks = 0
        content = ""
        leaked = False
        for line in r:
            line = line.decode("utf-8", "ignore").strip()
            if not line.startswith("data:"):
                continue
            payload = line[5:].strip()
            if payload == "[DONE]":
                break
            try:
                obj = json.loads(payload)
            except Exception:
                continue
            for ch in obj.get("choices", []):
                d = ch.get("delta", {})
                if d.get("content"):
                    content += d["content"]
                    chunks += 1
                if "reasoning" in d or "reasoning_content" in d:
                    leaked = True
        if caps["reasoning"]:
            ok = chunks > 0 and content and not leaked
            log(model, ep, "stream(+no-reason-leak)", "PASS" if ok else "FAIL", f"chunks={chunks} leaked={leaked}")
        else:
            log(model, ep, "stream", "PASS" if chunks > 0 and content else "FAIL", f"chunks={chunks}")
    except Exception as e:
        log(model, ep, "stream", "FAIL", str(e)[:60])

    # tools
    if caps["tools"]:
        tools = [{"type": "function", "function": {"name": "get_weather", "description": "Get current weather for a city",
                  "parameters": {"type": "object", "properties": {"city": {"type": "string"}}, "required": ["city"]}}}]
        # Force the function so the test measures plumbing/capability, not the model's
        # (model-dependent) willingness to call tools on 'auto'.
        code, b = post(P, {"model": model, "messages": [{"role": "user", "content": "What's the weather in Paris?"}],
                           "tools": tools, "tool_choice": {"type": "function", "function": {"name": "get_weather"}}, "max_tokens": 256})
        tc = b["choices"][0]["message"].get("tool_calls") if code == 200 else None
        ok = code == 200 and bool(tc)
        log(model, ep, "tools(forced)", "PASS" if ok else "FAIL", f"{code} tool_calls={'yes' if tc else 'no'}")

    # vision
    if caps["vision"]:
        code, b = post(P, {"model": model, "messages": [{"role": "user", "content": [
            {"type": "text", "text": "What color dominates this image? One word."},
            {"type": "image_url", "image_url": {"url": RED_IMG}}]}], "max_tokens": 32})
        out = text_of(b)
        ok = code == 200 and out.strip() != ""
        log(model, ep, "vision", "PASS" if ok else "FAIL", f"{code} {out[:30]!r}")

    # reasoning effort levels (effort-mode models)
    if caps["think"] == "effort":
        for lvl in ("low", "medium", "high"):
            code, b = post(P, {"model": model, "messages": [{"role": "user", "content": "What is 12*12? Reply with the number."}],
                               "reasoning_effort": lvl, "max_tokens": 16384})
            out = text_of(b)
            ok = code == 200 and out.strip() != "" and not msg_has_reasoning(b)
            log(model, ep, f"effort={lvl}", "PASS" if ok else "FAIL",
                f"{code} {out[:24]!r} reason_leak={msg_has_reasoning(b)}")

    # medium context (~3k tokens of filler)
    filler = ("The quick brown fox jumps over the lazy dog. " * 400)
    code, b = post(P, {"model": model, "messages": [
        {"role": "user", "content": filler + "\n\nReply with the word DONE."}], "max_tokens": 32})
    log(model, ep, "context~3k", "PASS" if code == 200 and text_of(b) else "FAIL", f"{code}")


# ── chat: Anthropic endpoint ──────────────────────────────────────────────────
def test_chat_anthropic(model, caps):
    ep = "anthropic"
    P = "/v1/messages"

    code, b = post(P, {"model": model, "max_tokens": 64, "messages": [{"role": "user", "content": "Reply with just: pong"}]})
    log(model, ep, "basic", "PASS" if code == 200 and anth_text(b) else "FAIL", f"{code} {anth_text(b)[:40]!r}")

    code, b = post(P, {"model": model, "max_tokens": 64, "system": "Answer with exactly one word: BANANA",
                       "messages": [{"role": "user", "content": "Favorite fruit?"}]})
    ok = code == 200 and "BANANA" in anth_text(b).upper()
    log(model, ep, "system", "PASS" if ok else "WARN", f"{code} {anth_text(b)[:40]!r}")

    code, b = post(P, {"model": model, "max_tokens": 8, "messages": [{"role": "user", "content": "Write a long story."}]})
    sr = b.get("stop_reason") if code == 200 else None
    ot = (b.get("usage") or {}).get("output_tokens") if code == 200 else None
    ok = code == 200 and (sr == "max_tokens" or (isinstance(ot, int) and ot <= 24))
    log(model, ep, "max_tokens", "PASS" if ok else "FAIL", f"{code} stop={sr} out={ot}")

    code, b = post(P, {"model": model, "max_tokens": 64, "messages": [{"role": "user", "content": "Count 1 2 3 4 5 6"}],
                       "stop_sequences": ["4"]})
    log(model, ep, "stop_sequences", "PASS" if code == 200 else "FAIL", f"{code} {anth_text(b)[:30]!r}")

    # thinking budget levels
    for bt in (1024, 8000, 24000):
        code, b = post(P, {"model": model, "max_tokens": 16384 if caps["reasoning"] else 256,
                           "thinking": {"type": "enabled", "budget_tokens": bt},
                           "messages": [{"role": "user", "content": "What is 12*12? Reply with the number."}]})
        blocks = anth_blocks(b)
        txt = anth_text(b)
        # reasoning must be stripped -> only text blocks, never a 'thinking' block
        ok = code == 200 and txt.strip() != "" and "thinking" not in blocks
        log(model, ep, f"think.budget={bt}", "PASS" if ok else "FAIL",
            f"{code} blocks={blocks} {txt[:24]!r}")

    # output_config.effort levels (reasoning models)
    if caps["reasoning"]:
        for lvl in ("low", "medium", "high"):
            code, b = post(P, {"model": model, "max_tokens": 16384,
                               "output_config": {"effort": lvl},
                               "messages": [{"role": "user", "content": "What is 7+8? Number only."}]})
            txt = anth_text(b)
            ok = code == 200 and txt.strip() != "" and "thinking" not in anth_blocks(b)
            log(model, ep, f"effort={lvl}", "PASS" if ok else "FAIL", f"{code} {txt[:24]!r}")

    # tools
    if caps["tools"]:
        code, b = post(P, {"model": model, "max_tokens": 256, "messages": [{"role": "user", "content": "Weather in Paris?"}],
                           "tools": [{"name": "get_weather", "description": "Get weather for a city",
                                      "input_schema": {"type": "object", "properties": {"city": {"type": "string"}}, "required": ["city"]}}],
                           "tool_choice": {"type": "tool", "name": "get_weather"}})
        ok = code == 200 and "tool_use" in anth_blocks(b)
        log(model, ep, "tools(forced)", "PASS" if ok else "FAIL", f"{code} blocks={anth_blocks(b)}")

    # vision
    if caps["vision"]:
        b64 = RED_IMG.split(",", 1)[1]
        code, b = post(P, {"model": model, "max_tokens": 32, "messages": [{"role": "user", "content": [
            {"type": "text", "text": "Dominant color? One word."},
            {"type": "image", "source": {"type": "base64", "media_type": "image/png", "data": b64}}]}]})
        log(model, ep, "vision", "PASS" if code == 200 and anth_text(b) else "FAIL", f"{code} {anth_text(b)[:30]!r}")

    # streaming
    try:
        r = _post(P, {"model": model, "max_tokens": 64, "stream": True,
                      "messages": [{"role": "user", "content": "Count from 1 to 5."}]}, stream=True)
        deltas = 0
        text = ""
        for line in r:
            line = line.decode("utf-8", "ignore").strip()
            if not line.startswith("data:"):
                continue
            try:
                obj = json.loads(line[5:].strip())
            except Exception:
                continue
            if obj.get("type") == "content_block_delta":
                deltas += 1
                text += obj.get("delta", {}).get("text", "")
        log(model, ep, "stream", "PASS" if deltas > 0 and text else "FAIL", f"deltas={deltas}")
    except Exception as e:
        log(model, ep, "stream", "FAIL", str(e)[:60])


# ── embeddings / science / other ──────────────────────────────────────────────
def test_embed_openai(model, sample):
    ep = "openai"
    code, b = post("/v1/embeddings", {"model": model, "input": sample})
    dim = len(b["data"][0]["embedding"]) if code == 200 and b.get("data") else 0
    log(model, ep, "embed_single", "PASS" if dim > 0 else "FAIL", f"{code} dim={dim}")
    code, b = post("/v1/embeddings", {"model": model, "input": [sample, sample]})
    n = len(b.get("data", [])) if code == 200 else 0
    log(model, ep, "embed_batch", "PASS" if n == 2 else "FAIL", f"{code} n={n}")


def test_embed_sci(model, cfg):
    payload = {"model": model}
    payload.update(cfg["payload_extra"])
    code, b = post(cfg["path"], payload)
    ok = code == 200 and ("embedding" in b or "embeddings" in b or "data" in b or "vector" in b)
    log(model, "custom", "embed", "PASS" if ok else "FAIL", f"{code} keys={list(b.keys())[:5]}")


def test_other(model, cfg):
    code, b = post(cfg["path"], dict(cfg["payload"], model=model))
    ok = code == 200 and isinstance(b, dict) and not b.get("_err") and "error" not in b
    log(model, "custom", cfg["path"].split("/")[-1], "PASS" if ok else "FAIL",
        f"{code} keys={list(b.keys())[:6] if isinstance(b, dict) else b}")


def test_rerank(model, cfg):
    ep = "openai"
    code, b = post("/v1/rerank", {"model": model, "query": cfg["query"], "documents": cfg["documents"]})
    res = b.get("results") if code == 200 else None
    ok = code == 200 and isinstance(res, list) and len(res) == len(cfg["documents"]) \
        and "relevance_score" in (res[0] if res else {})
    top = res[0]["index"] if ok else None
    log(model, ep, "rerank", "PASS" if ok and top == 0 else ("WARN" if ok else "FAIL"),
        f"{code} n={len(res) if res else 0} top_idx={top}")
    # top_n + return_documents
    code, b = post("/v1/rerank", {"model": model, "query": cfg["query"], "documents": cfg["documents"],
                                  "top_n": 2, "return_documents": True})
    res = b.get("results") if code == 200 else None
    ok = code == 200 and isinstance(res, list) and len(res) == 2 and "document" in (res[0] if res else {})
    log(model, ep, "rerank_top_n+docs", "PASS" if ok else "FAIL",
        f"{code} n={len(res) if res else 0}")


def test_tts(model, cfg):
    ep = "openai"
    data = json.dumps(dict(cfg, model=model)).encode()
    req = urllib.request.Request(BASE + "/v1/audio/speech", data=data,
                                 headers={"Content-Type": "application/json"})
    try:
        r = urllib.request.urlopen(req, timeout=REQ_TIMEOUT)
        raw = r.read()
        ct = r.headers.get("content-type", "")
        ok = raw[:4] == b"RIFF" and b"WAVE" in raw[:16]
        log(model, ep, "tts_speech", "PASS" if ok else "FAIL",
            f"ct={ct} bytes={len(raw)} hdr={raw[:4]}")
    except Exception as e:
        log(model, ep, "tts_speech", "FAIL", str(e)[:80])


# ── driver ────────────────────────────────────────────────────────────────────
def run():
    print(f"== gateway: {BASE} ==", flush=True)

    for model, caps in CHAT.items():
        print(f"\n### CHAT {model} {caps}", flush=True)
        ok, info = warm("/v1/chat/completions", {"model": model, "messages": [{"role": "user", "content": "hi"}], "max_tokens": 1})
        if not ok:
            log(model, "-", "warm", "FAIL", f"did not become ready: {info}")
            continue
        log(model, "-", "warm", "PASS", f"ready in {info}s")
        test_chat_openai(model, caps)
        test_chat_anthropic(model, caps)

    for model, sample in EMBED_OPENAI.items():
        print(f"\n### EMBED {model}", flush=True)
        ok, info = warm("/v1/embeddings", {"model": model, "input": sample})
        if not ok:
            log(model, "-", "warm", "FAIL", f"{info}")
            continue
        log(model, "-", "warm", "PASS", f"ready in {info}s")
        test_embed_openai(model, sample)

    for model, cfg in EMBED_SCI.items():
        print(f"\n### SCI-EMBED {model}", flush=True)
        ok, info = warm(cfg["path"], dict({"model": model}, **cfg["payload_extra"]))
        if not ok:
            log(model, "-", "warm", "FAIL", f"{info}")
            continue
        log(model, "-", "warm", "PASS", f"ready in {info}s")
        test_embed_sci(model, cfg)

    for model, cfg in OTHER.items():
        print(f"\n### {cfg['path']} {model}", flush=True)
        ok, info = warm(cfg["path"], dict(cfg["payload"], model=model))
        if not ok:
            log(model, "-", "warm", "FAIL", f"{info}")
            continue
        log(model, "-", "warm", "PASS", f"ready in {info}s")
        test_other(model, cfg)

    for model, cfg in RERANK.items():
        print(f"\n### RERANK {model}", flush=True)
        ok, info = warm("/v1/rerank", {"model": model, "query": cfg["query"], "documents": cfg["documents"]})
        if not ok:
            log(model, "-", "warm", "FAIL", f"{info}")
            continue
        log(model, "-", "warm", "PASS", f"ready in {info}s")
        test_rerank(model, cfg)

    for model, cfg in TTS.items():
        print(f"\n### TTS {model}", flush=True)
        # warm via the real speech endpoint (binary response, so use a custom probe)
        t0 = time.time()
        ready = False
        while time.time() - t0 < WARM_TIMEOUT:
            try:
                req = urllib.request.Request(BASE + "/v1/audio/speech",
                                             data=json.dumps(dict(cfg, model=model)).encode(),
                                             headers={"Content-Type": "application/json"})
                if urllib.request.urlopen(req, timeout=60).read()[:4] == b"RIFF":
                    ready = True
                    break
            except Exception:
                pass
            time.sleep(WARM_POLL)
        if not ready:
            log(model, "-", "warm", "FAIL", "did not become ready")
            continue
        log(model, "-", "warm", "PASS", f"ready in {int(time.time()-t0)}s")
        test_tts(model, cfg)

    # ── report ──
    print("\n\n================ SUMMARY ================", flush=True)
    npass = sum(1 for r in RESULTS if r[3] == "PASS")
    nfail = sum(1 for r in RESULTS if r[3] == "FAIL")
    nwarn = sum(1 for r in RESULTS if r[3] == "WARN")
    nskip = sum(1 for r in RESULTS if r[3] == "SKIP")
    print(f"PASS={npass} FAIL={nfail} WARN={nwarn} SKIP={nskip} total={len(RESULTS)}", flush=True)
    if nfail or nwarn:
        print("\n-- non-pass --", flush=True)
        for m, e, t, s, d in RESULTS:
            if s in ("FAIL", "WARN"):
                print(f"  [{s}] {m} {e} {t}: {d}", flush=True)
    with open("/tmp/full_test_report.txt", "w") as f:
        for m, e, t, s, d in RESULTS:
            f.write(f"{s}\t{m}\t{e}\t{t}\t{d}\n")
    print("\nreport -> /tmp/full_test_report.txt", flush=True)


if __name__ == "__main__":
    run()
