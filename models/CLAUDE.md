# Model deployment guidance

Follow [the add/update model workflow](../docs/ADD-A-MODEL.md) and
[repository conventions](../AGENTS.md).

Use [DETAILS-TEMPLATE-LLM.md](DETAILS-TEMPLATE-LLM.md) for cards and the appropriate
`test.*.py` template for validation. Read the affected model's README and notes
before changing it; runtime versions and hardware flags must be verified for that
model rather than copied as fleet-wide defaults.

Keep each model's README current with its deployment instructions, test results,
known limitations, and work in progress. Preserve its PVC during service updates.
