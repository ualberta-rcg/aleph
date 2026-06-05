# chem-t5 — Test Report

Cluster 230, gateway ClusterIP `http://10.43.79.101:80`. Type: science-generate (CPU). id `chem-t5`.

## Status: FIXED + verified 2026-06-05
GT4SD multitask-text-and-chemistry-t5. Old server used invented task prompts → wrong output
(caption returned a SMILES). Replaced with the EXACT GT4SD training prompt templates.

## Verified this pass

### caption (SMILES → description) — PASS
```bash
curl -s -X POST $GW/v1/science/generate -H 'Content-Type: application/json' \
  -d '{"model":"chem-t5","task":"caption","input":"CC(=O)NC(CC1=CC=C(C=C1)O)C(=O)O"}'
```
→ "The molecule is a N-acetyltyrosine ... human urinary metabolite ... monocarboxylic acid." PASS.

### forward_synthesis (reactants → product) — PASS
```bash
curl -s -X POST $GW/v1/science/generate -H 'Content-Type: application/json' \
  -d '{"model":"chem-t5","task":"forward_synthesis","input":"CC(=O)O.OCC"}'
```
→ valid product SMILES. PASS.

## Tasks (exact GT4SD prompts now used)
- forward_synthesis: "Predict the product of the following reaction: "
- retrosynthesis: "Predict the reaction that produces the following product: "
- caption: "Caption the following SMILES: "
- generate (desc→SMILES): "Write in SMILES the described molecule: "
- paragraph_to_actions: "Which actions are described in the following paragraph: "

## Card parity
id=chem-t5, type=science-generate, gpu=false, status=production.
