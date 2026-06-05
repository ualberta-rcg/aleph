# 232 → 230 Model Migration Tracker

Authoritative worklist for migrating all ≤2-GPU models from POC cluster 232
(`/root/kuberflow-working/models/`) to cluster 230 (HAMi). Smallest-first.

Process per model: see [CLAUDE.md](CLAUDE.md). One commit per model; update
[../CHANGELOG.md](../CHANGELOG.md) before each commit.

Status legend: `[ ]` pending · `[~]` in progress · `[x]` done · `[s]` skipped (with reason)

Totals: 138 to migrate — 54 (gpu=0) + 80 (gpu=1) + 4 (gpu=2).

## Already on 230 (skip)

bge-m3, bge-reranker-v2-m3, biobert, chemgpt-19m, command-r-7b, esm2-35m,
esm2-650m, finbert, gemma-4b (=gemma-3-4b-it), gpt-oss-20b, matscibert, molformer,
nucleotide-transformer, prokbert, proteinmpnn, qwen25-vl-7b, qwen35-122b, xtts-v2.
Excluded >2 GPU: qwen3-235b (4), qwen35-122b (4).

## Wave 1 — gpu=0 bucket (CPU/tiny → sub-GPU HAMi), 54

- [x] ablang2 (embedding, CPU, dim=480; ablang2==0.2.1 fix)
- [x] agront (DNA embedding, GPU 1/gpumem8192, dim=1500; RawDeployment->Knative)
- [s] aion (BLOCKED: needs real `aion` codec API + astro inputs; 232 server was a stub — see models/aion/CLAUDE.md)
- [ ] alphafold2
- [x] arcface (face/vision, CPU, ONNX, dim=512)
- [x] biomedbert (embedding, CPU, dim=768; id=biomedbert-110m)
- [ ] biot5
- [ ] birdnet-analyzer
- [ ] chem-t5
- [ ] chemberta
- [ ] chronos-bolt
- [ ] clap
- [ ] clay
- [ ] climatebert
- [ ] clinicalbert
- [ ] depth-anything
- [ ] dino-vit-b8
- [ ] dnabert-2
- [ ] dnabert-s
- [ ] efficientnet-b0
- [ ] galileo
- [ ] geneformer-v2
- [ ] graphcast
- [ ] hyenadna
- [ ] labram
- [ ] lag-llama
- [ ] leandojo
- [ ] led
- [ ] ligandmpnn
- [ ] longformer
- [ ] mace-mp-0
- [ ] maskrcnn
- [ ] medsam
- [ ] megadetector
- [ ] moirai-large
- [ ] multilingual-e5-small
- [ ] neuralgcm
- [ ] omnigenome
- [ ] presto
- [ ] pubmedbert
- [ ] retinanet
- [ ] rita
- [ ] satmae
- [ ] scibert
- [ ] science-embed
- [ ] seisbench
- [ ] specter2
- [ ] splicebert
- [ ] sundial
- [ ] tinyllama
- [ ] ttm
- [ ] yolov8n
- [ ] yolov8s
- [ ] zoobot

## Wave 2 — gpu=1 bucket, 80

- [ ] aeneas
- [ ] ancient-greek-bert
- [ ] ankh
- [ ] astroclip
- [ ] astropt
- [ ] astrosage
- [ ] aurora
- [ ] biogpt
- [ ] biolinkbert
- [ ] biomed-roberta
- [ ] biomedbert-large
- [ ] biomedclip
- [ ] boltz-1
- [ ] borzoi
- [ ] brainlm
- [ ] caduceus
- [ ] chemgpt
- [ ] chgnet
- [ ] climax
- [ ] clinical-longformer
- [ ] croma
- [ ] crysta-llm
- [ ] deepseek-v2-lite-16b
- [ ] diffdock
- [ ] dust3r
- [ ] earthpt
- [ ] enformer
- [ ] ernierna
- [ ] esm1b
- [ ] esm2-150m
- [ ] esm2-3b
- [ ] esmc-300m
- [ ] esmfold
- [ ] fengwu
- [ ] fourcastnet3
- [ ] gemma-4-26b-a4b
- [ ] gena-lm
- [ ] gena-lm-large
- [ ] geneformer
- [ ] granite-geospatial-biomass
- [ ] granite-geospatial-ocean
- [ ] ithaca
- [ ] kandinsky-3
- [ ] mace-mh-1
- [ ] mace-mp
- [ ] mast3r
- [ ] mattergen
- [ ] mattersim
- [ ] medcpt-article
- [ ] medcpt-query
- [ ] moirai
- [ ] moirai-moe
- [ ] moment
- [ ] naturecode-earth
- [ ] pangu-weather
- [ ] phi-4-reasoning
- [ ] prithvi-eo
- [ ] prithvi-wxc
- [ ] progen2
- [ ] prostt5
- [ ] protgpt2
- [ ] qwen25-vl-3b
- [ ] rnabert
- [ ] rnafm
- [ ] rnamsm
- [ ] sapbert
- [ ] saprot-650m
- [ ] scgpt
- [ ] scincl
- [ ] speaches
- [ ] stanford-deidentifier
- [ ] surya
- [ ] terramind-flood
- [ ] thor
- [ ] time-moe
- [ ] timer
- [ ] timer-xl-1b
- [ ] timesfm
- [ ] totalsegmentator
- [ ] uma-m

## Wave 3 — gpu=2 bucket (tensor-parallel), 4

- [ ] geogalactica
- [ ] gpt-oss-120b
- [ ] medgemma-27b-it
- [ ] oceangpt-30b
