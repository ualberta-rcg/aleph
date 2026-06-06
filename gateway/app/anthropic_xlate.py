"""
Anthropic Messages API <-> OpenAI Chat Completions translation.

One thin module (per GATEWAY-ARCHITECTURE.md): convert an Anthropic /v1/messages
request into an OpenAI chat-completions body, run it through the gateway's normal
chat pipeline, then convert the OpenAI response (and SSE stream) back to Anthropic
shape. Common core only — unsupported Anthropic fields are dropped on input.
"""
from __future__ import annotations

import json
import time
import uuid
from typing import Any


# ── content blocks ─────────────────────────────────────────────────────────────
def _flatten_text(content: Any) -> str:
    """Anthropic `system` / simple content -> a plain string."""
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts = []
        for b in content:
            if isinstance(b, dict) and b.get("type") == "text":
                parts.append(b.get("text", ""))
        return "\n".join(parts)
    return ""


def _convert_user_content(content: Any) -> Any:
    """Anthropic message content -> OpenAI content (string, or multimodal array)."""
    if isinstance(content, str):
        return content
    if not isinstance(content, list):
        return ""
    has_media = any(
        isinstance(b, dict) and b.get("type") in ("image", "tool_result", "tool_use")
        for b in content
    )
    if not has_media:
        return _flatten_text(content)
    out: list[dict] = []
    for b in content:
        if not isinstance(b, dict):
            continue
        btype = b.get("type")
        if btype == "text":
            out.append({"type": "text", "text": b.get("text", "")})
        elif btype == "image":
            src = b.get("source", {}) or {}
            if src.get("type") == "base64":
                url = f"data:{src.get('media_type','image/png')};base64,{src.get('data','')}"
            else:
                url = src.get("url", "")
            out.append({"type": "image_url", "image_url": {"url": url}})
        elif btype == "tool_result":
            # Best-effort: fold tool output back in as text.
            out.append({"type": "text", "text": _flatten_text(b.get("content"))})
    return out or _flatten_text(content)


# ── request: Anthropic -> OpenAI ────────────────────────────────────────────────
def to_openai(body: dict) -> dict:
    out: dict[str, Any] = {"model": body.get("model")}

    if body.get("max_tokens") is not None:
        out["max_tokens"] = body["max_tokens"]

    messages: list[dict] = []
    system = body.get("system")
    if system:
        messages.append({"role": "system", "content": _flatten_text(system)})
    for m in body.get("messages", []) or []:
        role = m.get("role", "user")
        messages.append({"role": role, "content": _convert_user_content(m.get("content"))})
    out["messages"] = messages

    for a_key, o_key in (("temperature", "temperature"), ("top_p", "top_p"),
                         ("top_k", "top_k"), ("stream", "stream")):
        if body.get(a_key) is not None:
            out[o_key] = body[a_key]
    if body.get("stop_sequences"):
        out["stop"] = body["stop_sequences"]

    # Tools: Anthropic {name, description, input_schema} -> OpenAI function tools.
    if body.get("tools"):
        tools = []
        for t in body["tools"]:
            if not isinstance(t, dict) or "name" not in t:
                continue
            tools.append({
                "type": "function",
                "function": {
                    "name": t["name"],
                    "description": t.get("description", ""),
                    "parameters": t.get("input_schema", {"type": "object"}),
                },
            })
        if tools:
            out["tools"] = tools

    # tool_choice: Anthropic {type: auto|any|tool|none} -> OpenAI form.
    tc = body.get("tool_choice")
    if isinstance(tc, dict):
        ttype = tc.get("type")
        if ttype == "auto":
            out["tool_choice"] = "auto"
        elif ttype == "any":
            out["tool_choice"] = "required"
        elif ttype == "none":
            out["tool_choice"] = "none"
        elif ttype == "tool" and tc.get("name"):
            out["tool_choice"] = {"type": "function", "function": {"name": tc["name"]}}
    return out


def desired_thinking(body: dict) -> tuple[bool, str | None, int | None]:
    """Extract raw Anthropic thinking hints — no per-model effort mapping.

    Returns (enabled, raw_effort, budget_tokens). Effort strings are passed through
    as sent by the client; the model card's effort_aliases / effort_map resolve them.
    """
    oc = body.get("output_config") or {}
    if oc.get("effort") is not None:
        return True, str(oc["effort"]).lower(), None

    th = body.get("thinking") or {}
    ttype = th.get("type")
    if ttype == "adaptive":
        return True, None, None
    if ttype == "enabled":
        bt = th.get("budget_tokens")
        if isinstance(bt, int):
            return True, None, bt
        return True, None, None
    if ttype == "disabled":
        return False, None, None
    return False, None, None


# ── response: OpenAI -> Anthropic ────────────────────────────────────────────────
_STOP_MAP = {
    "stop": "end_turn",
    "length": "max_tokens",
    "tool_calls": "tool_use",
    "content_filter": "end_turn",
    None: "end_turn",
}


def from_openai(resp: dict, model: str) -> dict:
    choices = resp.get("choices") or [{}]
    choice = choices[0]
    msg = choice.get("message", {}) or {}

    blocks: list[dict] = []
    text = msg.get("content")
    if text:
        blocks.append({"type": "text", "text": text})
    for tc in msg.get("tool_calls") or []:
        fn = tc.get("function", {}) or {}
        try:
            args = json.loads(fn.get("arguments") or "{}")
        except Exception:
            args = {}
        blocks.append({
            "type": "tool_use",
            "id": tc.get("id", "toolu_" + uuid.uuid4().hex[:24]),
            "name": fn.get("name", ""),
            "input": args,
        })
    if not blocks:
        blocks.append({"type": "text", "text": ""})

    usage = resp.get("usage", {}) or {}
    return {
        "id": resp.get("id", "msg_" + uuid.uuid4().hex[:24]),
        "type": "message",
        "role": "assistant",
        "model": model,
        "content": blocks,
        "stop_reason": _STOP_MAP.get(choice.get("finish_reason"), "end_turn"),
        "stop_sequence": None,
        "usage": {
            "input_tokens": usage.get("prompt_tokens", 0),
            "output_tokens": usage.get("completion_tokens", 0),
        },
    }


# ── streaming: OpenAI SSE -> Anthropic SSE ───────────────────────────────────────
def _sse(event: str, data: dict) -> bytes:
    return f"event: {event}\ndata: {json.dumps(data)}\n\n".encode()


def stream_start_events(model: str) -> list[bytes]:
    msg_id = "msg_" + uuid.uuid4().hex[:24]
    return [
        _sse("message_start", {
            "type": "message_start",
            "message": {
                "id": msg_id, "type": "message", "role": "assistant",
                "model": model, "content": [],
                "stop_reason": None, "stop_sequence": None,
                "usage": {"input_tokens": 0, "output_tokens": 0},
            },
        }),
        _sse("content_block_start", {
            "type": "content_block_start", "index": 0,
            "content_block": {"type": "text", "text": ""},
        }),
    ]


def stream_delta_event(text: str) -> bytes:
    return _sse("content_block_delta", {
        "type": "content_block_delta", "index": 0,
        "delta": {"type": "text_delta", "text": text},
    })


def stream_stop_events(finish_reason: str | None, output_tokens: int,
                       resources: dict | None = None) -> list[bytes]:
    delta = {
        "type": "message_delta",
        "delta": {"stop_reason": _STOP_MAP.get(finish_reason, "end_turn"),
                  "stop_sequence": None},
        "usage": {"output_tokens": output_tokens},
    }
    if resources:
        delta["resources"] = resources
    return [
        _sse("content_block_stop", {"type": "content_block_stop", "index": 0}),
        _sse("message_delta", delta),
        _sse("message_stop", {"type": "message_stop"}),
    ]


def parse_openai_sse_line(line: str) -> dict | None:
    line = line.strip()
    if not line.startswith("data:"):
        return None
    payload = line[len("data:"):].strip()
    if not payload or payload == "[DONE]":
        return None
    try:
        return json.loads(payload)
    except Exception:
        return None
