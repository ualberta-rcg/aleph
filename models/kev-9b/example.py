"""kev-9b — worked example for the System One decision API (operator-authorized
extra file; the only non-contract file in this dir).

Kev is not a chat model. You hand it a document (the "state") plus typed
questions, and it returns calibrated probabilities — one prefill pass, no
generation. Run this to see every endpoint in action:

  source ~/.aleph_tyk.env
  python3 models/kev-9b/example.py
"""
import json, os
import httpx

GW = os.environ.get("GW_URL", "https://inference.vulcan.alliancecan.ca")
KEY = os.environ["TYK_KEY"]
H = {"Authorization": f"Bearer {KEY}"}


def systemone(state, questions, **extra):
    body = {"model": "kev-9b", "state": state, "questions": questions, **extra}
    r = httpx.post(f"{GW}/v1/systemone", json=body, headers=H, timeout=300)
    r.raise_for_status()
    return r.json()


# ── 1. The canonical example: route a customer complaint ──────────────────────
state = ("Shoes arrived two weeks late and in the wrong size. "
         "Also I see two charges on my card.")
questions = {
    "department":  {"type": "choice", "instructions": "Which team should handle this?",
                    "criteria": {"returns": "Exchanges, refunds, wrong or damaged items",
                                 "shipping": "Delivery status, delays, lost packages",
                                 "billing": "Charges, invoices, payment problems"}},
    "escalate":    {"type": "noul", "instructions": "Does this need urgent human attention?"},
    "frustration": {"type": "score", "instructions": "How frustrated is the customer?",
                    "criteria": ["Calm", "Frustrated", "Very angry"]},
}
out = systemone(state, questions)
print("== /v1/systemone — all three question types in ONE pass ==")
print(json.dumps(out, indent=2)[:900])

# Reading the result:
#   out["answers"]["department"]  -> {"choice": "...", "confidence": ..., "probabilities": {...}}
#   out["answers"]["escalate"]    -> {"noul": 0.93}          # P(yes)
#   out["answers"]["frustration"] -> {"score": 1.44, "legend": {...}, "probabilities": {...}}

# ── 2. Confidence-gated automation pattern ────────────────────────────────────
out = systemone(state, {"department": questions["department"]})
conf = out["answers"]["department"]["confidence"]
action = "auto-route" if conf >= 0.8 else "queue for human review"
print(f"\n== confidence gate: {conf:.2f} -> {action} ==")

# ── 3. Variants ────────────────────────────────────────────────────────────────
# /permute: option-order robustness check for a single choice question
r = httpx.post(f"{GW}/v1/systemone/permute", headers=H, timeout=300,
               json={"model": "kev-9b",                              # gateway routing only
                     "request": {"model": "kev-latest", "state": state,
                                 "questions": {"department": questions["department"]}},
                     "question": "department", "n_perm": 4})
print(f"\n== /v1/systemone/permute -> {r.status_code}: {str(r.json())[:120]}")

# /separate: force one forward pass per question (independent scoring)
r = httpx.post(f"{GW}/v1/systemone/separate", headers=H, timeout=300,
               json={"model": "kev-9b", "state": state, "questions": questions})
print(f"\n== /v1/systemone/separate -> {r.status_code}: answers {sorted(r.json().get('answers', {}))}")

# ── 4. State can be structured JSON — it is rendered as labelled text ─────────
out = systemone(
    {"patient": {"age": 71, "bp": "165/95", "complaint": "chest pain on exertion"}},
    {"triage": {"type": "choice", "instructions": "Assign triage level.",
                "criteria": {"1_resus": "Immediate life threat",
                             "2_urgent": "High risk, time-critical",
                             "3_standard": "Standard care"}}},
)
print(f"\n== structured state -> triage: {json.dumps(out['answers']['triage'])[:160]}")

# ── 5. The flagship pattern: content moderation gate ───────────────────────────
# (mastra-jev-moderation style: block decision + category in ONE pass)
msgs = ["You are worthless garbage and everyone hates you. Delete your account.",   # hostile
        "I had trouble logging in yesterday, but it works now. Thanks!"]            # benign
for m in msgs:
    out = systemone(m, {
        "block":     {"type": "noul", "instructions": "Must this message be blocked for harassment?"},
        "category":  {"type": "choice", "instructions": "Categorize the message.",
                      "criteria": {"harassment": "Attacks, insults, hate",
                                   "support": "Help, thanks, questions",
                                   "other": "Anything else"}}})
    a = out["answers"]
    gate = "BLOCK" if a["block"]["noul"] > 0.5 else "allow"
    print(f"\n== moderation: {gate} (noul={a['block']['noul']:.2f}, "
          f"category={a['category']['choice']}) ==")
