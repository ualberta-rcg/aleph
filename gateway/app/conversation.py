"""Lossless supported conversation fields, independent of model effort settings."""
from __future__ import annotations

import json


def normalize_reasoning(messages):
    """Accept both API spellings; canonical `reasoning` wins if both are strings."""
    result = []
    for message in messages or []:
        if not isinstance(message, dict):
            result.append(message)
            continue
        message = dict(message)
        if message.get("role") == "assistant":
            reasoning = message.get("reasoning")
            if not isinstance(reasoning, str):
                reasoning = message.get("reasoning_content")
            if isinstance(reasoning, str):
                message["reasoning"] = reasoning
                message["reasoning_content"] = reasoning
        result.append(message)
    return result


def anthropic_history(messages, convert_content):
    """Preserve thinking/tool exchanges while translating Anthropic messages."""
    result = []
    for message in messages or []:
        role = message.get("role", "user")
        blocks = message.get("content")
        if not isinstance(blocks, list):
            result.append({"role": role, "content": convert_content(blocks)})
            continue
        if role == "assistant":
            converted = {"role": role, "content": convert_content([
                b for b in blocks if isinstance(b, dict) and b.get("type") == "text"
            ])}
            thoughts = [b["thinking"] for b in blocks if isinstance(b, dict)
                        and b.get("type") == "thinking" and isinstance(b.get("thinking"), str)]
            if thoughts:
                converted["reasoning"] = "\n".join(thoughts)
            calls = [{"id": b["id"], "type": "function", "function": {
                "name": b["name"], "arguments": json.dumps(b.get("input", {})),
            }} for b in blocks if isinstance(b, dict) and b.get("type") == "tool_use"]
            if calls:
                converted["tool_calls"] = calls
            result.append(converted)
        elif role == "user":
            ordinary = []
            for block in blocks:
                if isinstance(block, dict) and block.get("type") == "tool_result":
                    if ordinary:
                        result.append({"role": "user", "content": convert_content(ordinary)})
                        ordinary = []
                    result.append({"role": "tool", "tool_call_id": block["tool_use_id"],
                                   "content": convert_content(block.get("content"))})
                else:
                    ordinary.append(block)
            if ordinary:
                result.append({"role": role, "content": convert_content(ordinary)})
        else:
            result.append({"role": role, "content": convert_content(blocks)})
    return normalize_reasoning(result)
