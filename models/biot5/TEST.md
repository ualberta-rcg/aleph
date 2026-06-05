# biot5 — Test Report

Cluster 230, gateway ClusterIP `http://10.43.79.101:80`. Type: science-generate (CPU). id `biot5`.

## Status: FIXED + verified 2026-06-05
Old server used the un-fine-tuned `biot5-base` with a made-up prompt and raw SMILES →
garbage output (`<p>M <p>A ...`). Rewritten to the task-specific checkpoints with the
official prompt format and SELFIES conversion.

## Verified this pass

### POST /v1/science/generate — mol2text — PASS
```bash
curl -s -X POST $GW/v1/science/generate -H 'Content-Type: application/json' \
  -d '{"model":"biot5","task":"mol2text","input":"CC(=O)OC1=CC=CC=C1C(=O)O"}'
```
→ Accurate aspirin description: "...salicylic acid in which the hydrogen of the phenolic
hydroxy group is replaced by an acetoxy group... NSAID, COX inhibitor...". PASS.

### POST /v1/science/generate — text2mol — PASS
```bash
curl -s -X POST $GW/v1/science/generate -H 'Content-Type: application/json' \
  -d '{"model":"biot5","task":"text2mol","input":"The molecule is an aromatic ketone, acetophenone."}'
```
→ selfies `[C][C][=Branch1][C][=O][C][=C][C][=C][C][=C][Ring1][=Branch1]`,
smiles `CC(=O)C1=CC=CC=C1` (= acetophenone). Correct. PASS.

## Key fixes
- Use task-specific checkpoints `QizhiPei/biot5-base-mol2text` + `biot5-base-text2mol`
  (base model alone is not fine-tuned → garbage).
- Official prompt: "Definition: ...\n\nNow complete the following example -\nInput: <bom>{selfies}<eom>\nOutput: ".
- Auto-convert SMILES↔SELFIES via the `selfies` package; text2mol returns both.

## Not applicable
- OpenAI chat / Anthropic: N/A (task-based science generation, not conversational).

## Card parity
id=biot5, type=science-generate, gpu=false, status=production. Tasks: mol2text, text2mol.
