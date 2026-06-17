#!/usr/bin/env python3
"""Replay Open WebUI title/tags/follow_ups meta-task prompts (captured from 232's
qwen3-235b logs) against our chat models, verify each returns parseable JSON."""
import json, re, sys, urllib.request

U = "http://172.26.92.230:30808/v1/chat/completions"
KEY = open("/tmp/cvk").read().strip()

CHAT = """USER: Explain options trading in simple terms if I'm familiar with stocks.
ASSISTANT: Options are contracts giving the right (not obligation) to buy (call) or sell (put) a stock at a strike price by an expiry date. You pay a premium; max loss when buying is the premium. They offer leverage, hedging and income vs. owning shares outright."""

TITLE = """### Task:
Generate a concise, 3-5 word title with an emoji summarizing the chat history.
### Guidelines:
- The title should clearly represent the main theme of the conversation.
- Your entire response must consist solely of the JSON object.
### Output:
JSON format: { "title": "your concise title here" }
### Chat History:
<chat_history>
%s
</chat_history>""" % CHAT

TAGS = """### Task:
Generate 1-3 broad tags categorizing the main themes of the chat history, along with 1-3 more specific subtopic tags.
### Guidelines:
- Start with high-level domains (e.g. Science, Technology, Business, Health)
- If content is too short or too diverse, use only ["General"]
### Output:
JSON format: { "tags": ["tag1", "tag2", "tag3"] }
### Chat History:
<chat_history>
%s
</chat_history>""" % CHAT

FOLLOW = """### Task:
Suggest 3-5 relevant follow-up questions that the user might naturally ask next, based on the chat history.
### Guidelines:
- Write all follow-up questions from the user's point of view, directed to the assistant.
- Response must be a JSON object with a "follow_ups" key containing an array of strings, no extra text.
### Output:
JSON format: { "follow_ups": ["Question 1?", "Question 2?", "Question 3?"] }
### Chat History:
<chat_history>
%s
</chat_history>""" % CHAT

TASKS = [
    ("title",      TITLE,  "title",     {"temperature": 0.2, "max_tokens": 80}),
    ("tags",       TAGS,   "tags",      {"temperature": 0.2, "max_tokens": 80}),
    ("follow_ups", FOLLOW, "follow_ups",{"temperature": 0.7, "top_p": 0.8, "max_tokens": 220}),
]
MODELS = ["gpt-oss-20b", "command-r-7b", "gemma-3-4b-it", "qwen25-vl-7b"]


def call(model, prompt, extra):
    body = {"model": model, "messages": [{"role": "user", "content": prompt}]}
    body.update(extra)
    req = urllib.request.Request(U, data=json.dumps(body).encode(),
        headers={"Authorization": "Bearer " + KEY, "Content-Type": "application/json"})
    try:
        r = urllib.request.urlopen(req, timeout=120)
        d = json.loads(r.read())
    except Exception as e:
        return None, f"HTTP-ERR {e}"
    if "choices" not in d:
        return None, "ERR " + json.dumps(d)[:120]
    return d["choices"][0]["message"].get("content") or "", None


def extract_json(text, key):
    if text is None:
        return None
    t = re.sub(r"```(json)?", "", text).strip()
    m = re.search(r"\{.*\}", t, re.S)
    if not m:
        return None
    try:
        obj = json.loads(m.group(0))
    except Exception:
        return None
    return obj if key in obj else None


for model in MODELS:
    print(f"\n=== {model} ===")
    for name, prompt, key, extra in TASKS:
        content, err = call(model, prompt, extra)
        if err:
            print(f"  {name:11s} FAIL {err}")
            continue
        obj = extract_json(content, key)
        if obj is None:
            print(f"  {name:11s} BAD-JSON -> {repr(content)[:90]}")
        else:
            print(f"  {name:11s} OK   -> {json.dumps(obj.get(key))[:90]}")
