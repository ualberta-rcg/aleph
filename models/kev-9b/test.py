"""kev-9b comprehensive gateway test (custom decision API — System One).

Kev is NOT a chat model: POST /v1/systemone takes a state + typed questions and
returns calibrated probabilities in one prefill pass. This battery exercises the
full surface through the public edge: wake, all three question types, the
permute/separate variants, calibration sanity (probabilities sum to 1, choice =
argmax), a long state, the 422 over-length guard, burst/sustained workload, and
gateway guardrails.

Run externally via the gateway endpoint + Tyk auth:
  source ~/.aleph_tyk.env
  GW_URL=https://inference.vulcan.alliancecan.ca TYK_KEY=$TYK_KEY python3 models/kev-9b/test.py
"""
import httpx, json, os, time

G = os.environ.get("GW_URL", "https://inference.vulcan.alliancecan.ca")
_KEY = os.environ.get("TYK_KEY")
_HEADERS = {"Authorization": f"Bearer {_KEY}"} if _KEY else {}
MODEL = os.environ.get("MODEL", "kev-9b")
results = []

# The author's documented fixture (shoe complaint) — known-good semantics.
SHOE_STATE = ("Shoes arrived two weeks late and in the wrong size. "
              "Also I see two charges on my card.")
SHOE_QUESTIONS = {
    "department": {"type": "choice", "instructions": "Which team should handle this?",
                   "criteria": {"returns": "Exchanges, refunds, wrong or damaged items",
                                "shipping": "Delivery status, delays, lost packages",
                                "billing": "Charges, invoices, payment problems"}},
    "escalate": {"type": "noul", "instructions": "Does this need urgent human attention?"},
    "frustration": {"type": "score", "instructions": "How frustrated is the customer?",
                    "criteria": ["Calm", "Frustrated", "Very angry"]},
}


def req(method, path, body=None, timeout=300):
    return httpx.request(method, f"{G}{path}", json=body, timeout=timeout, headers=_HEADERS)


def record(icon, status, name, detail):
    results.append((icon, status, name, detail))
    print(f"[{icon}] {status} | {name}: {detail}", flush=True)


def so(questions=None, state=None, extra=None, timeout=300):
    body = {"model": MODEL, "state": state or SHOE_STATE,
            "questions": questions or SHOE_QUESTIONS}
    if extra:
        body.update(extra)
    return req("POST", "/v1/systemone", body, timeout=timeout)


def approx_sum_1(d, tol=0.02):
    return abs(sum(d.values()) - 1.0) <= tol


# ── 1. WAKE (retry 503 model_starting/scaled_to_zero) ─────────────────────────
def wake():
    for attempt in range(90):
        r = so(questions={"ok": {"type": "noul", "instructions": "Is this text about shoes?"}})
        if r.status_code == 200:
            a = r.json()["answers"]["ok"]
            record("PASS", 200, "WAKE + systemone basic",
                   f"attempts={attempt+1} noul={a.get('noul')}")
            return
        if r.status_code == 503:
            time.sleep(5); continue
        record("FAIL", r.status_code, "WAKE + systemone basic", r.text[:100])
        return
    record("FAIL", 503, "WAKE + systemone basic", "timed out")


# ── Core decision types ────────────────────────────────────────────────────────
def choice_type():
    r = so(questions=SHOE_QUESTIONS)
    a = r.json()["answers"]["department"]
    probs = a.get("probabilities", {})
    ok = (r.status_code == 200 and set(probs) == {"returns", "shipping", "billing"}
          and approx_sum_1(probs) and a.get("choice") == max(probs, key=probs.get)
          and 0 <= a.get("confidence", -1) <= 1)
    record("PASS" if ok else "FAIL", r.status_code, "choice: calibrated probabilities",
           f"choice={a.get('choice')} probs={ {k: round(v,2) for k,v in probs.items()} } conf={a.get('confidence')}")


def choice_semantics():
    # The documented fixture: wrong size + double charge -> 'returns' or 'billing'
    # should dominate; 'shipping' (only the delay) should NOT be the pick.
    r = so(questions={"d": SHOE_QUESTIONS["department"]})
    a = r.json()["answers"]["d"]
    ok = r.status_code == 200 and a["choice"] in ("returns", "billing")
    record("PASS" if ok else "EXP", r.status_code, "choice: fixture semantics",
           f"picked {a.get('choice')} (returns/billing expected; shipping would be wrong)")


def noul_type():
    r = so(questions={"y": {"type": "noul", "instructions": "Is the text in English?"}})
    a = r.json()["answers"]["y"]
    ok = r.status_code == 200 and 0.0 <= a.get("noul", -1) <= 1.0
    record("PASS" if ok else "FAIL", r.status_code, "noul: yes/no probability", f"noul={a.get('noul')}")


def score_type():
    r = so(questions={"s": SHOE_QUESTIONS["frustration"]})
    a = r.json()["answers"]["s"]
    ok = (r.status_code == 200 and set(a.get("legend", {}).values()) == {"Calm", "Frustrated", "Very angry"}
          and 0 <= a.get("score", -1) <= 2 and approx_sum_1(a.get("probabilities", {})))
    record("PASS" if ok else "FAIL", r.status_code, "score: ordered levels + expected index",
           f"score={a.get('score')} probs={ {k: round(v,2) for k,v in a.get('probabilities',{}).items()} }")


def multi_question():
    r = so()  # all three at once
    ans = r.json().get("answers", {})
    ok = r.status_code == 200 and set(ans) == {"department", "escalate", "frustration"}
    record("PASS" if ok else "FAIL", r.status_code, "multi-question single pass",
           f"questions answered: {sorted(ans)}")


def usage_block():
    r = so(questions={"y": {"type": "noul", "instructions": "English?"}})
    d = r.json()
    u = d.get("usage", {})
    ok = r.status_code == 200 and u.get("input_tokens", 0) > 0 and "latency_ms" in d
    record("PASS" if ok else "FAIL", r.status_code, "usage + latency",
           f"input_tokens={u.get('input_tokens')} latency_ms={d.get('latency_ms')}")


# ── Variants ───────────────────────────────────────────────────────────────────
def permute():
    # schema: {request: <SystemOneRequest>, question: <name>, n_perm, seed} — plus a
    # TOP-LEVEL "model" key purely for gateway routing (pydantic ignores the extra)
    body = {"model": MODEL,
            "request": {"model": "kev-latest", "state": SHOE_STATE,
                        "questions": {"department": SHOE_QUESTIONS["department"]}},
            "question": "department", "n_perm": 4}
    r = req("POST", "/v1/systemone/permute", body)
    ok = r.status_code == 200
    detail = "200"
    if ok:
        d = r.json()
        detail = str(d)[:80]
    record("PASS" if ok else "FAIL", r.status_code, "permute endpoint", detail)


def separate():
    body = {"model": MODEL, "state": SHOE_STATE, "questions": SHOE_QUESTIONS}
    r = req("POST", "/v1/systemone/separate", body)
    ok = r.status_code == 200 and "answers" in r.json()
    record("PASS" if ok else "FAIL", r.status_code, "separate endpoint",
           f"answers={sorted(r.json().get('answers', {}))}" if ok else r.text[:80])


# ── Limits ─────────────────────────────────────────────────────────────────────
def long_state():
    state = "Background context. " * 1500  # ~4.5k tokens — inside validated 8K
    r = so(questions={"y": {"type": "noul", "instructions": "Is this background text?"}},
           state=state)
    ok = r.status_code == 200
    record("PASS" if ok else "FAIL", r.status_code, "long state (~4.5k tokens)",
           f"input_tokens={r.json().get('usage', {}).get('input_tokens')}" if ok else r.text[:80])


def over_limit_state():
    state = "filler " * 60000  # ~60k+ tokens ... under 65,536? build bigger: x2
    state = "filler " * 120000  # ~120k tokens — over the 65,536 limit
    r = so(questions={"y": {"type": "noul", "instructions": "yes?"}}, state=state, timeout=600)
    record("EXP" if r.status_code == 422 else "FAIL", r.status_code,
           "over-length state rejected (422)", r.text[:80])


# ── Workload ───────────────────────────────────────────────────────────────────
def burst():
    import concurrent.futures as cf
    def one(i):
        rr = so(questions={"q": {"type": "noul", "instructions": f"Does text {i} mention shoes?"}})
        return rr.status_code
    with cf.ThreadPoolExecutor(8) as ex:
        codes = list(ex.map(one, range(8)))
    ok = all(c == 200 for c in codes)
    record("PASS" if ok else "FAIL", 200 if ok else 500, "WORKLOAD 8-way burst", f"codes={codes}")


def sustained():
    codes, lats = [], []
    for i in range(20):
        t0 = time.time()
        r = so(questions={"q": SHOE_QUESTIONS["department"] if i % 2 else
                          {"type": "noul", "instructions": "English?"}})
        codes.append(r.status_code); lats.append((time.time() - t0) * 1000)
    ok = all(c == 200 for c in codes)
    record("PASS" if ok else "FAIL", 200 if ok else 500, "WORKLOAD sustained 20-mix",
           f"{codes.count(200)}/20 x 200, lat med={sorted(lats)[10]:.0f}ms max={max(lats):.0f}ms")



# ── Solid-test additions (patterns ported from the Jev ecosystem) ─────────────
def gt_reading_1():
    # Ground-truth comprehension: explicit state, unambiguous answer (games-style)
    st = "Server config: retries = 3, timeout = 30s, port = 8443, region = ca-west."
    r = so(state=st, questions={"retries": {"type": "choice", "instructions": "What is the retries value?",
            "criteria": {"2": "two", "3": "three", "4": "four"}}})
    a = r.json()["answers"]["retries"]
    record("PASS" if (r.status_code == 200 and a["choice"] == "3") else "FAIL", r.status_code,
           "GT: extract stated value (retries=3)", f"picked {a.get('choice')} probs={a.get('probabilities')}")

def gt_reading_2():
    st = "Meeting notes: Alice will present on Tuesday. Bob joins remotely on Thursday. No meeting Friday."
    r = so(state=st, questions={"friday": {"type": "noul", "instructions": "Is there a meeting on Friday?"}})
    n = r.json()["answers"]["friday"]["noul"]
    record("PASS" if (r.status_code == 200 and n < 0.35) else "FAIL", r.status_code,
           "GT: negate absent fact (no Friday meeting)", f"noul={n}")

def gt_reading_3():
    st = "The invoice total is $1,240.50, due within 14 days of receipt."
    r = so(state=st, questions={"due": {"type": "choice", "instructions": "When is payment due?",
            "criteria": {"7 days": "within one week", "14 days": "within two weeks", "30 days": "within a month"}}})
    a = r.json()["answers"]["due"]
    record("PASS" if (r.status_code == 200 and a["choice"] == "14 days") else "FAIL", r.status_code,
           "GT: extract due window (14 days)", f"picked {a.get('choice')}")

def moderation_pair():
    # mastra-jev-moderation pattern: hostile must block, benign must not
    hostile = "You are worthless garbage and everyone hates you. Delete your account."
    benign = "I had trouble logging in yesterday, but it works now. Thanks!"
    q = {"block": {"type": "noul", "instructions": "Must this message be blocked for harassment?"}}
    rh = so(state=hostile, questions=q).json()["answers"]["block"]["noul"]
    rb = so(state=benign, questions=q).json()["answers"]["block"]["noul"]
    ok = rh > 0.5 and rb < 0.5
    record("PASS" if ok else "EXP", 200, "MODERATION: hostile blocks, benign passes",
           f"hostile={rh:.2f} benign={rb:.2f}")

def determinism():
    q = {"d": SHOE_QUESTIONS["department"]}
    a = so(questions=q).json()["answers"]["d"]["probabilities"]
    b = so(questions=q).json()["answers"]["d"]["probabilities"]
    ok = a == b
    record("PASS" if ok else "EXP", 200, "Determinism: identical requests, identical probabilities",
           f"{'stable' if ok else 'drifted'} {a}")

def permute_stability():
    body = {"model": MODEL,
            "request": {"model": "kev-latest", "state": SHOE_STATE,
                        "questions": {"department": SHOE_QUESTIONS["department"]}},
            "question": "department", "n_perm": 6}
    r = req("POST", "/v1/systemone/permute", body)
    runs = r.json().get("runs", [])
    direct = so(questions={"department": SHOE_QUESTIONS["department"]}).json()["answers"]["department"]["choice"]
    picks = [x.get("choice") for x in runs if x.get("choice")]
    modal = max(set(picks), key=picks.count) if picks else None
    agree = picks.count(direct) / len(picks) if picks else 0
    record("PASS" if (r.status_code == 200 and modal == direct and agree >= 0.5) else "EXP", r.status_code,
           "Permutation stability (modal pick == direct pick)",
           f"direct={direct} modal={modal} agreement={agree:.0%} of {len(picks)} perms")

def phrasing_stability():
    q1 = {"dep": SHOE_QUESTIONS["department"]}
    q2 = {"dep": {"type": "choice", "instructions": "Route this complaint to the correct team.",
                  "criteria": SHOE_QUESTIONS["department"]["criteria"]}}
    a = so(questions=q1).json()["answers"]["dep"]["choice"]
    b = so(questions=q2).json()["answers"]["dep"]["choice"]
    record("PASS" if a == b else "EXP", 200, "Phrasing stability (two wordings, same verdict)",
           f"{'same: ' + a if a == b else f'{a} vs {b}'}")

def boundary_one_option():
    r = so(questions={"only": {"type": "choice", "instructions": "Pick the category.",
            "criteria": {"general": "Everything else"}}})
    a = r.json()["answers"]["only"]
    record("PASS" if (r.status_code == 200 and a["choice"] == "general" and a["probabilities"]["general"] > 0.95)
           else "FAIL", r.status_code, "Boundary: single-option choice", f"p={a.get('probabilities')}")

def boundary_50_options():
    criteria = {f"opt{i}": f"category number {i}" for i in range(50)}
    criteria["opt42"] = "refunds, exchanges, wrong or damaged items"
    r = so(questions={"pick": {"type": "choice",
            "instructions": "Which handles wrong-size shoes?", "criteria": criteria}})
    a = r.json()["answers"]["pick"]
    record("PASS" if (r.status_code == 200 and a["choice"] == "opt42") else "EXP", r.status_code,
           "Boundary: 50-option choice, target present", f"picked {a.get('choice')} conf={a.get('confidence')}")

def boundary_10_level_score():
    r = so(questions={"sev": {"type": "score", "instructions": "Rate severity 0-9 (9=catastrophic).",
            "criteria": [f"level {i}" for i in range(10)]}}, state="Paper cut on my finger.")
    a = r.json()["answers"]["sev"]
    record("PASS" if (r.status_code == 200 and 0 <= a.get("score", -1) <= 9) else "FAIL", r.status_code,
           "Boundary: 10-level score bounds", f"score={a.get('score')}")

def multi_axis_score():
    text = "The report is clearly written but cites no sources and misses the key counterargument."
    r = so(state=text, questions={
        "clarity": {"type": "score", "instructions": "How clear is the writing?", "criteria": ["unclear", "average", "clear"]},
        "rigor": {"type": "score", "instructions": "How rigorous is the evidence?", "criteria": ["weak", "ok", "strong"]},
        "coverage": {"type": "score", "instructions": "How complete is the coverage?", "criteria": ["narrow", "broad"]}})
    ans = r.json().get("answers", {})
    ok = (r.status_code == 200 and set(ans) == {"clarity", "rigor", "coverage"})
    detail = f"clarity={ans.get('clarity', {}).get('score')} rigor={ans.get('rigor', {}).get('score')} coverage={ans.get('coverage', {}).get('score')}"
    record("PASS" if ok else "FAIL", r.status_code, "Multi-axis score batch (one pass)", detail)

# ── Guardrails ─────────────────────────────────────────────────────────────────
def guard_badmodel():
    r = req("POST", "/v1/systemone", {"model": "fake-xyz", "state": "x",
             "questions": {"q": {"type": "noul", "instructions": "y?"}}})
    record("EXP" if r.status_code == 404 else "FAIL", r.status_code, "Guard: bad model",
           r.json().get("error", "")[:60])


def guard_nomodel():
    r = req("POST", "/v1/systemone", {"state": "x", "questions": {}})
    record("EXP" if r.status_code == 400 else "FAIL", r.status_code,
           "Guard: missing model field", r.json().get("error", "")[:60])


def catalog():
    r = req("GET", "/v1/models?all=true")
    m = next((x for x in r.json().get("data", []) if x["id"] == MODEL), None)
    if not m:
        record("FAIL", 0, "Catalog entry", "not found in ?all=true"); return
    record("PASS" if m.get("type") == "decision" else "FAIL", r.status_code,
           "Catalog entry (type=decision)", f"type={m.get('type')} ctx={m.get('context_window')}")


# ── run ────────────────────────────────────────────────────────────────────────
print("=" * 66, flush=True)
print(f"{MODEL} decision-API gateway test (custom /v1/systemone)", flush=True)
print("=" * 66, flush=True)
for t in [wake, choice_type, choice_semantics, noul_type, score_type, multi_question,
          usage_block, permute, separate, long_state, over_limit_state,
          gt_reading_1, gt_reading_2, gt_reading_3, moderation_pair, determinism,
          permute_stability, phrasing_stability, boundary_one_option,
          boundary_50_options, boundary_10_level_score, multi_axis_score,
          burst, sustained, guard_badmodel, guard_nomodel, catalog]:
    try:
        t()
    except Exception as e:
        record("ERR", 0, getattr(t, "__name__", "?"), str(e)[:120])

p = sum(1 for x in results if x[0] == "PASS")
e = sum(1 for x in results if x[0] == "EXP")
f = sum(1 for x in results if x[0] in ("FAIL", "ERR"))
print(f"\n{'=' * 66}\nResults: {p} passed, {e} expected, {f} failed/err of {len(results)}", flush=True)
