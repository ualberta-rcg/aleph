
## Verified 2026-06-05 (verification loop) — DEEP-FIXED
Multiple bugs:
- Checkpoints never downloaded (guard checked empty dir, not .pt files; HF repo wrong).
  Now download official IPD checkpoints (ligand/protein/soluble/membrane), guarded per-file.
- Handler always passed --checkpoint_ligand_mpnn; now maps model_type -> correct flag+weights.
- Missing openfold deps (ml_collections, dm-tree, scipy) for run.py's sc_utils import; made
  the side-chain-packing import optional (we don't pack), avoiding the fragile openfold chain.
- Wrong CLI args: LigandMPNN uses --batch_size/--number_of_batches/--temperature
  (not --num_seq_per_target/--sampling_temp).
Test (1CRN, protein_mpnn, 3 seqs): RC=0, designs match native sequence closely. PASS. status=production.
