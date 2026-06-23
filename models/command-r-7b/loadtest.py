#!/usr/bin/env python3
"""Sustained-concurrency load generator for command-r-7b (scale test).

Holds CONC in-flight chat requests against the gateway for DURATION seconds,
so Knative's concurrency metric exceeds the per-pod target and scales up.

    GW_URL=http://129.128.190.55 TYK_KEY=<key> CONC=30 DURATION=150 \
        python3 models/command-r-7b/loadtest.py
"""
import asyncio
import os
import time

import httpx

GW = os.environ.get("GW_URL", "http://129.128.190.55")
KEY = os.environ.get("TYK_KEY", "")
MODEL = os.environ.get("MODEL", "command-r-7b")
CONC = int(os.environ.get("CONC", "30"))
DURATION = int(os.environ.get("DURATION", "150"))
MAX_TOKENS = int(os.environ.get("MAX_TOKENS", "200"))

HEADERS = {"Content-Type": "application/json"}
if KEY:
    HEADERS["Authorization"] = f"Bearer {KEY}"

ok = 0
err = 0
inflight = 0
stop_at = 0.0


async def worker(client: httpx.AsyncClient, wid: int):
    global ok, err, inflight
    body = {
        "model": MODEL,
        "messages": [{"role": "user", "content": "Write two sentences about the ocean."}],
        "max_tokens": MAX_TOKENS,
    }
    while time.time() < stop_at:
        inflight += 1
        try:
            r = await client.post(f"{GW}/v1/chat/completions", json=body, headers=HEADERS, timeout=120)
            if r.status_code == 200:
                ok += 1
            else:
                err += 1
        except Exception:
            err += 1
        finally:
            inflight -= 1


async def reporter():
    while time.time() < stop_at:
        await asyncio.sleep(10)
        elapsed = int(time.time() - (stop_at - DURATION))
        print(f"[{elapsed:3d}s] ok={ok} err={err} inflight≈{inflight} rps≈{ok/max(elapsed,1):.1f}", flush=True)


async def main():
    global stop_at
    stop_at = time.time() + DURATION
    print(f"Load test: {CONC} concurrent for {DURATION}s -> {GW} model={MODEL}", flush=True)
    async with httpx.AsyncClient(http2=False) as client:
        tasks = [asyncio.create_task(worker(client, i)) for i in range(CONC)]
        tasks.append(asyncio.create_task(reporter()))
        await asyncio.gather(*tasks)
    print(f"DONE: ok={ok} err={err}", flush=True)


if __name__ == "__main__":
    asyncio.run(main())
