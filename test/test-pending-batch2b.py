#!/usr/bin/env python3
"""Test pending batch2b science models — report only, no fixes."""
import json
import time
import urllib.request
import urllib.error

GW = "http://10.43.147.39:80"
TIMEOUT = 600

CASES = [
    {
        "model": "prithvi-eo",
        "path": "/v1/embed",
        "body": {
            "model": "prithvi-eo",
            "image": [[[0.1] * 6 for _ in range(224)] for _ in range(224)],
        },
        "ok": lambda d: "embeddings" in d and "shape" in d,
    },
    {
        "model": "prithvi-wxc",
        "path": "/v1/science/forecast",
        "body": {"model": "prithvi-wxc", "demo": True, "lead_time": 6},
        "ok": lambda d: d.get("forecast") and d.get("lead_time_hours") == 6,
    },
    {
        "model": "surya-366m",
        "path": "/v1/science/forecast",
        "body": {"model": "surya-366m", "demo": True},
        "ok": lambda d: "forecast" in d and "flare_risk" in d,
    },
    {
        "model": "terramind-flood",
        "path": "/v1/science/classify",
        "body": {"model": "terramind-flood", "demo": True},
        "ok": lambda d: "flood_mask" in d and "flood_area_pct" in d,
    },
    {
        "model": "totalsegmentator",
        "path": "/v1/science/segment",
        "body": {
            "model": "totalsegmentator",
            "ct_array": [[[0] * 16 for _ in range(16)] for _ in range(16)],
            "spacing": [2.0, 2.0, 2.0],
            "fast": True,
        },
        "ok": lambda d: "segmentation_shape" in d or "segmentation" in d,
    },
    {
        "model": "mattergen",
        "path": "/v1/science/generate",
        "body": {"model": "mattergen", "chemical_system": "Li-O", "num_structures": 1},
        "ok": lambda d: d.get("num_structures", 0) >= 1 and d.get("structures"),
        "timeout": 1500,
    },
]


def post(path, body, timeout):
    req = urllib.request.Request(
        f"{GW}{path}",
        data=json.dumps(body).encode(),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.status, json.load(r)


def test_case(case):
    model = case["model"]
    timeout = case.get("timeout", TIMEOUT)
    last_err = None
    for attempt in range(1, 25):
        try:
            code, data = post(case["path"], case["body"], timeout)
            if isinstance(data, dict) and data.get("error"):
                msg = data["error"] if isinstance(data["error"], str) else json.dumps(data["error"])[:200]
                if "scaled_to_zero" in msg or "starting up" in msg or "loading" in msg.lower():
                    print(f"  [{model}] cold start attempt {attempt}...", flush=True)
                    time.sleep(15)
                    last_err = msg
                    continue
                return "FAIL", f"http={code} error={msg[:180]}"
            if case["ok"](data):
                keys = list(data.keys())[:6]
                return "PASS", f"http={code} keys={keys}"
            return "FAIL", f"http={code} unexpected={json.dumps(data)[:180]}"
        except urllib.error.HTTPError as e:
            body = e.read().decode()[:200]
            if "scaled_to_zero" in body or "starting up" in body:
                print(f"  [{model}] cold start attempt {attempt}...", flush=True)
                time.sleep(15)
                last_err = body
                continue
            return "FAIL", f"http={e.code} {body[:160]}"
        except Exception as e:
            err = str(e)
            if "timed out" in err.lower():
                return "FAIL", f"timeout after {timeout}s"
            if attempt < 24:
                time.sleep(10)
                last_err = err
                continue
            return "FAIL", err[:180]
    return "FAIL", f"never ready: {last_err}"


def main():
    results = []
    for case in CASES:
        print(f"\n### {case['model']}", flush=True)
        status, note = test_case(case)
        print(f"  -> {status}: {note}", flush=True)
        results.append({"model": case["model"], "status": status, "note": note})
    print("\n=== RESULTS ===")
    for r in results:
        print(f"{r['model']:22s} {r['status']:6s} {r['note']}")
    with open("/tmp/batch2b-results.json", "w") as f:
        json.dump(results, f, indent=2)


if __name__ == "__main__":
    main()
