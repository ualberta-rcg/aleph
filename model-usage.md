# Aleph Model Usage Guide

API contract for each model: endpoints, request/response shape, and caller-facing quirks. Deployment status is in `models.md`.

## `ablang2`

**Antibody language model (embeddings + CDR restore)**

**Endpoint:** `POST /v1/embeddings`, `POST /v1/restore` **Protocol:** OpenAI embeddings  
**Input:** `antibody amino-acid sequence str or [str]` **Output:** 480-dim vectors  
**Model path:** `models/ablang2/`

### When to use

- antibody chain embeddings and CDR restoration

### Avoid

- general protein LM, chat, vision

### Example

```bash
curl -s -X POST "$GW/v1/embeddings" -H "Content-Type: application/json" \
  -d '{"model":"ablang2","input":"EVQLLESGGEVKKPGASVKVSCRASGYTFRNYGLTWVRQAPGQGLEWMGWISAYNGNTNYAQKFQGRVTLTTDTSTSTAYMELRSLRSDDTAVYFCARDVPGHGAAFMDVWGTGTTVTVSS"}'

curl -s -X POST "$GW/v1/restore" -H "Content-Type: application/json" \
  -d '{"model":"ablang2","input":"EVQLLESGGGLVQPGG*LRLSCAASGFTFSSYAMSWVRQAPGKGLEWVSAISGSGGSTYYADSVKGRFTISRDNSKNTLYLQMNSLRAEDTAVYYCAKDYW"}'
```

### Quirks

- Use `model_to_use='ablang2-paired'`; weights cached on first init (~5 min).
- **Verified 2026-06-05:** embeddings + restore PASS after heavy/light pair fix.
- Gateway `GET /v1/models` is chat-only; use `?all=true` for embedding models.
- Test status: **FIXED** (READY).
- Scale-to-zero: first request may incur cold-start delay.

## `aeneas`

> ⚠ Not currently serving reliably — see `models.md` (FAIL).

**Generative neural network for contextualising Latin inscriptions (DeepMind Nature 2025)**

**Endpoint:** `POST /v1/science/predict` **Protocol:** custom science JSON  
**Input:** `text`, `demo` **Output:** model-specific JSON response  
**Model path:** `models/aeneas/`

### When to use

- Latin inscription restoration, dating, and geographic attribution

### Avoid

- chat, non-Latin text, production until FAIL fixed
- Production until cluster verification passes

### Example

```bash
curl -s -X POST "$GW/v1/science/predict" -H "Content-Type: application/json" \
  -d '{"model":"aeneas","demo":true}'
```

### Quirks

- Input: Latin uppercase, 50–750 chars, `#` for unknown gaps.
- **FAIL:** alphabet lacks `[`/`#` gap handling + JAX activator timeout on GPU cold start.
- Compare with **ithaca** (Greek, `?` gaps) which passed after JAX CUDA fix.
- Test status: **FAIL** (READY).
- Scale-to-zero: first request may incur cold-start delay.

## `agront`

**AgroNT 1B plant-genome DNA language model (embeddings)**

**Endpoint:** `POST /v1/embeddings` **Protocol:** OpenAI embeddings  
**Input:** `plant DNA sequence (ACGT...), up to ~6000 bp` **Output:** 1500-dim vectors  
**Model path:** `models/agront/`

### When to use

- genomics embeddings (1500-dim)

### Avoid

- chat, generation, or unrelated modalities

### Example

```bash
curl -s -X POST "$GW/v1/embeddings" -H "Content-Type: application/json" \
  -d '{"model":"agront","input":"What is protein folding?"}'
```

### Quirks

- 1500-dim DNA
- Test status: **PASS** (READY).
- Scale-to-zero: first request may incur cold-start delay.

## `aion`

**AION-base 300M astronomical multimodal foundation model. 39 data types from DESI, SDSS, Gaia, HSC.**

**Endpoint:** `POST /v1/science/embed` **Protocol:** custom science JSON  
**Input:** `modality`, `flux`, `flux_g/flux_r/flux_i/flux_z`, `num_encoder_tokens` **Output:** model-specific JSON response  
**Model path:** `models/aion/`

### When to use

- astronomy embeddings

### Avoid

- chat, generation, or unrelated modalities

### Example

```bash
curl -s -X POST "$GW/v1/science/embed" -H "Content-Type: application/json" \
  -d '{"model":"aion","text":"sample input"}'
```

### Quirks

- rewrote to real AION CodecManager API; legacy_image + photometry -> 768-dim; was non-functional
- Test status: **FIXED** (READY).
- Scale-to-zero: first request may incur cold-start delay.

## `alphafold2`

**AlphaFold2 protein structure prediction (via ColabFold)**

**Endpoint:** `POST /v1/science/predict` **Protocol:** custom science JSON  
**Input:** `sequence`/`text`/`demo` **Output:** prediction JSON  
**Model path:** `models/alphafold2/`

### When to use

- protein/structure prediction

### Avoid

- chat, fast approximate folds at scale

### Example

```bash
curl -s -X POST "$GW/v1/science/predict" -H "Content-Type: application/json" \
  -d '{"model":"alphafold2","demo":true}'
```

### Quirks

- demo folds seq -> PDB
- Test status: **PASS** (READY).
- Scale-to-zero: first request may incur cold-start delay.

## `ancient-greek-bert`

**Ancient Greek BERT**

**Endpoint:** `POST /v1/science/embed` **Protocol:** custom science JSON  
**Input:** `input` string or array **Output:** embedding vectors  
**Model path:** `models/ancient-greek-bert/`

### When to use

- scientific-nlp embeddings

### Avoid

- chat, generation, or unrelated modalities

### Example

```bash
curl -s -X POST "$GW/v1/science/embed" -H "Content-Type: application/json" \
  -d '{"model":"ancient-greek-bert","text":"sample input"}'
```

### Quirks

- 768-dim (field: text)
- Test status: **PASS** (READY).
- Scale-to-zero: first request may incur cold-start delay.

## `ankh`

**T5-based protein language model from ElnaggarLab (TUM, 113M params)**

**Endpoint:** `POST /v1/embeddings` **Protocol:** OpenAI embeddings  
**Input:** `input`, `sequences` **Output:** model-specific JSON response  
**Model path:** `models/ankh/`

### When to use

- proteomics embeddings

### Avoid

- chat, generation, or unrelated modalities

### Example

```bash
curl -s -X POST "$GW/v1/embeddings" -H "Content-Type: application/json" \
  -d '{"model":"ankh","input":"MKTVRQERLKSIVRILERSKEPVSGAQ"}'
```

### Quirks

- T5 fp16->fp32 NaN fix; 768-dim protein PASS
- Test status: **FIXED** (READY).
- Scale-to-zero: first request may incur cold-start delay.

## `arcface`

**ArcFace ResNet-100**

**Endpoint:** `POST /v1/vision/face` **Protocol:** vision JSON (base64 image)  
**Input:** `input` string or array **Output:** 512-dim vectors  
**Model path:** `models/arcface/`

### When to use

- face verification embeddings (512-dim L2-normalized)
- Gateway model id: `arcface-resnet100`

### Avoid

- general vision, non-face images

### Example

```bash
curl -s -X POST "$GW/v1/vision/face" -H "Content-Type: application/json" \
  -d '{"model":"arcface-resnet100"}'
```

### Quirks

- id=arcface-resnet100; face embedding
- Test status: **PASS** (READY).
- Scale-to-zero: first request may incur cold-start delay.
- Use model id `arcface-resnet100` in requests.

## `astroclip`

> ⚠ Not currently serving reliably — see `models.md` (FAIL).

**AstroCLIP cross-modal CLIP for galaxy images and optical spectra. 512-dim joint embedding space.**

**Endpoint:** `POST /v1/science/embed` **Protocol:** custom science JSON  
**Input:** `image`, `spectrum`, `modality`, `demo` **Output:** model-specific JSON response  
**Model path:** `models/astroclip/`

### When to use

- astronomy embeddings

### Avoid

- chat, generation, or unrelated modalities
- Production until cluster verification passes

### Example

```bash
curl -s -X POST "$GW/v1/science/embed" -H "Content-Type: application/json" \
  -d '{"model":"astroclip","text":"sample input"}'
```

### Quirks

- AstroCLIP lib not installed; demo-only stub
- Test status: **FAIL** (READY).
- Scale-to-zero: first request may incur cold-start delay.

## `astropt`

> ⚠ Not currently serving reliably — see `models.md` (FAIL).

**AstroPT v2.0 95M autoregressive galaxy image transformer. 8.6M galaxies from SDSS/DESI.**

**Endpoint:** `POST /v1/science/embed` **Protocol:** custom science JSON  
**Input:** `image`, `demo` **Output:** model-specific JSON response  
**Model path:** `models/astropt/`

### When to use

- astronomy embeddings

### Avoid

- chat, generation, or unrelated modalities
- Production until cluster verification passes

### Example

```bash
curl -s -X POST "$GW/v1/science/embed" -H "Content-Type: application/json" \
  -d '{"model":"astropt","text":"sample input"}'
```

### Quirks

- patchify preprocessing wrong (needs 32x32x3 tokens)
- Test status: **FAIL** (READY).
- Scale-to-zero: first request may incur cold-start delay.

## `astrosage`

**AstroSage-8B, astronomy/astrophysics LLM**

**Endpoint:** `POST /v1/chat/completions` **Protocol:** OpenAI chat  
**Input:** `messages[]` **Output:** assistant message (+ reasoning if enabled)  
**Model path:** `models/astrosage/`

### When to use

- instruction-following chat in science domain

### Avoid

- embedding-only workloads, batch offline inference without chat API

### Example

```bash
curl -s -X POST "$GW/v1/chat/completions" -H "Content-Type: application/json" \
  -d '{"model":"astrosage","messages":[{"role":"user","content":"Hello"}]}'
```

### Quirks

- OpenAI + Anthropic endpoints both work
- Test status: **PASS** (READY).
- Scale-to-zero: first request may incur cold-start delay.

## `aurora`

**Microsoft Aurora 1.3B atmospheric foundation model for global weather forecasting at 0.25-degree resolution.**

**Endpoint:** `POST /v1/science/forecast` **Protocol:** custom science JSON  
**Input:** `lat`, `lon`, `time`, `atmos_levels` **Output:** model-specific JSON response  
**Model path:** `models/aurora/`

### When to use

- time-series / weather forecasting

### Avoid

- chat, static embeddings

### Example

```bash
curl -s -X POST "$GW/v1/science/forecast" -H "Content-Type: application/json" \
  -d '{"model":"aurora","demo":true}'
```

### Quirks

- full weather batch -> 6h forecast
- Test status: **PASS** (READY).
- Scale-to-zero: first request may incur cold-start delay.

## `bge-m3`

**BAAI bge-m3 multilingual embeddings, 8K ctx (TEI, CPU)**

**Endpoint:** `POST /v1/embeddings` **Protocol:** OpenAI embeddings  
**Input:** `input` string or array **Output:** 1024-dim vectors  
**Model path:** `models/bge-m3/`

### When to use

- nlp embeddings (1024-dim)

### Avoid

- chat, generation, or unrelated modalities

### Example

```bash
curl -s -X POST "$GW/v1/embeddings" -H "Content-Type: application/json" \
  -d '{"model":"bge-m3","input":"What is protein folding?"}'
```

### Quirks

- embeddings batch multilingual, dim=1024, matches card
- Test status: **PASS** (READY).

## `bge-reranker-v2-m3`

**BAAI bge-reranker-v2-m3 multilingual cross-encoder (TEI, CPU)**

**Endpoint:** `POST /v1/rerank` **Protocol:** Cohere-style rerank  
**Input:** `query` + `documents[]` **Output:** ranked docs + scores  
**Model path:** `models/bge-reranker-v2-m3/`

### When to use

- passage reranking for RAG

### Avoid

- generation or raw embedding

### Example

```bash
curl -s -X POST "$GW/v1/rerank" -H "Content-Type: application/json" \
  -d '{"model":"bge-reranker-v2-m3","query":"pandas","documents":["pandas docs","numpy docs"]}'
```

### Quirks

- /v1/rerank correct ranking (panda docs top), scores OK
- Test status: **PASS** (READY).

## `bge-small`

**BAAI bge-small-en-v1.5**

**Endpoint:** `POST /v1/embeddings` **Protocol:** OpenAI embeddings  
**Input:** `input` string or array **Output:** 384-dim vectors  
**Model path:** `models/bge-small/`

### When to use

- compact English text embeddings for RAG/semantic search

### Avoid

- multilingual long-context (use bge-m3), chat

### Example

```bash
curl -s -X POST "$GW/v1/embeddings" -H "Content-Type: application/json" \
  -d '{"model":"bge-small","input":"What is protein folding?"}'
```

### Quirks

- 384-dim text embedding
- Test status: **PASS** (READY).

## `biobert`

**BioBERT base (v1.**

**Endpoint:** `POST /v1/embeddings` **Protocol:** OpenAI embeddings  
**Input:** `biomedical text str or [str]` **Output:** 768-dim vectors  
**Model path:** `models/biobert/`

### When to use

- biomedical embeddings (768-dim)

### Avoid

- chat, generation, or unrelated modalities

### Example

```bash
curl -s -X POST "$GW/v1/embeddings" -H "Content-Type: application/json" \
  -d '{"model":"biobert","input":"What is protein folding?"}'
```

### Quirks

- 768-dim
- Test status: **PASS** (READY).
- Scale-to-zero: first request may incur cold-start delay.

## `biogpt`

**BioGPT**

**Endpoint:** `POST /v1/completions` **Protocol:** OpenAI completions  
**Input:** `prompt` **Output:** completion text  
**Model path:** `models/biogpt/`

### When to use

- biomedical-specific generation

### Avoid

- general chat or unrelated tasks

### Example

```bash
curl -s -X POST "$GW/v1/completions" -H "Content-Type: application/json" \
  -d '{"model":"biogpt","prompt":"The mitochondria is"}'
```

### Quirks

- coherent biomedical text completion
- Test status: **PASS** (READY).
- Scale-to-zero: first request may incur cold-start delay.

## `biolinkbert`

**BioLinkBERT**

**Endpoint:** `POST /v1/embeddings` **Protocol:** OpenAI embeddings  
**Input:** `input` string or array **Output:** embedding vectors  
**Model path:** `models/biolinkbert/`

### When to use

- biomedical embeddings

### Avoid

- chat, generation, or unrelated modalities

### Example

```bash
curl -s -X POST "$GW/v1/embeddings" -H "Content-Type: application/json" \
  -d '{"model":"biolinkbert","input":"What is protein folding?"}'
```

### Quirks

- 768-dim
- Test status: **PASS** (READY).
- Scale-to-zero: first request may incur cold-start delay.

## `biomed-roberta`

**BioMed-RoBERTa**

**Endpoint:** `POST /v1/embeddings` **Protocol:** OpenAI embeddings  
**Input:** `input` string or array **Output:** embedding vectors  
**Model path:** `models/biomed-roberta/`

### When to use

- biomedical embeddings

### Avoid

- chat, generation, or unrelated modalities

### Example

```bash
curl -s -X POST "$GW/v1/embeddings" -H "Content-Type: application/json" \
  -d '{"model":"biomed-roberta","input":"What is protein folding?"}'
```

### Quirks

- 768-dim
- Test status: **PASS** (READY).
- Scale-to-zero: first request may incur cold-start delay.

## `biomedbert`

**BiomedBERT**

**Endpoint:** `POST /v1/embeddings` **Protocol:** OpenAI embeddings  
**Input:** `biomedical text str or [str]` **Output:** 768-dim vectors  
**Model path:** `models/biomedbert/`

### When to use

- biomedical embeddings (768-dim)
- Gateway model id: `biomedbert-110m`

### Avoid

- chat, generation, or unrelated modalities

### Example

```bash
curl -s -X POST "$GW/v1/embeddings" -H "Content-Type: application/json" \
  -d '{"model":"biomedbert-110m","input":"What is protein folding?"}'
```

### Quirks

- embeddings PASS dim=768 (id biomedbert-110m)
- Test status: **PASS** (READY).
- Scale-to-zero: first request may incur cold-start delay.
- Use model id `biomedbert-110m` in requests.

## `biomedbert-large`

**BiomedBERT-large**

**Endpoint:** `POST /v1/science/embed` **Protocol:** custom science JSON  
**Input:** `input` string or array **Output:** embedding vectors  
**Model path:** `models/biomedbert-large/`

### When to use

- biomedical embeddings

### Avoid

- chat, generation, or unrelated modalities

### Example

```bash
curl -s -X POST "$GW/v1/science/embed" -H "Content-Type: application/json" \
  -d '{"model":"biomedbert-large","text":"sample input"}'
```

### Quirks

- 1024-dim (field: text)
- Test status: **PASS** (READY).
- Scale-to-zero: first request may incur cold-start delay.

## `biomedclip`

**BiomedCLIP biomedical vision-language model**

**Endpoint:** `POST /v1/embeddings` **Protocol:** OpenAI embeddings  
**Input:** `input` string or array **Output:** embedding vectors  
**Model path:** `models/biomedclip/`

### When to use

- biomedical embeddings

### Avoid

- chat, generation, or unrelated modalities

### Example

```bash
curl -s -X POST "$GW/v1/embeddings" -H "Content-Type: application/json" \
  -d '{"model":"biomedclip","input":"What is protein folding?"}'
```

### Quirks

- text_embeddings (texts/images)
- Test status: **PASS** (READY).
- Scale-to-zero: first request may incur cold-start delay.

## `biot5`

**BioT5**

**Endpoint:** `POST /v1/science/generate` **Protocol:** custom science JSON  
**Input:** `SELFIES or text (task-dependent)` **Output:** model-specific JSON  
**Model path:** `models/biot5/`

### When to use

- biochemistry-specific generation

### Avoid

- general chat or unrelated tasks

### Example

```bash
curl -s -X POST "$GW/v1/science/generate" -H "Content-Type: application/json" \
  -d '{"model":"biot5","smiles":"CCO"}'
```

### Quirks

- task-specific checkpoints + SELFIES; mol2text & text2mol correct (was garbage)
- Test status: **FIXED** (READY).
- Scale-to-zero: first request may incur cold-start delay.

## `birdnet-analyzer`

**BirdNET-Analyzer**

**Endpoint:** `POST /v1/science/identify` **Protocol:** custom science JSON  
**Input:** `model` + payload fields **Output:** JSON response  
**Model path:** `models/birdnet-analyzer/`

### When to use

- BirdNET-Analyzer — bird species ID from audio (6000+ species)

### Avoid

- unrelated modalities or production if FAIL

### Example

```bash
curl -s -X POST "$GW/v1/science/identify" -H "Content-Type: application/json" \
  -d '{"model":"birdnet-analyzer"}'
```

### Quirks

- end-to-end OK; synthetic tone -> no detections (expected)
- Test status: **PASS** (READY).
- Scale-to-zero: first request may incur cold-start delay.

## `boltz-1`

> ⚠ Not currently serving reliably — see `models.md` (FAIL).

**Open-source biomolecular structure prediction (protein/RNA/DNA/ligand, MIT)**

**Endpoint:** `POST /v1/science/predict` **Protocol:** custom science JSON  
**Input:** `sequence`, `type`, `demo`, `use_msa_server` **Output:** model-specific JSON response  
**Model path:** `models/boltz-1/`

### When to use

- protein/structure prediction

### Avoid

- chat, fast approximate folds at scale
- Production until cluster verification passes

### Example

```bash
curl -s -X POST "$GW/v1/science/predict" -H "Content-Type: application/json" \
  -d '{"model":"boltz-1","demo":true}'
```

### Quirks

- torch runtime error during folding; needs deep-fix
- Test status: **FAIL** (READY).
- Scale-to-zero: first request may incur cold-start delay.

## `borzoi`

**RNA-seq prediction from 524kb genomic sequences (Calico, ~500M)**

**Endpoint:** `POST /v1/science/predict` **Protocol:** custom science JSON  
**Input:** `sequence`, `n_bins` **Output:** model-specific JSON response  
**Model path:** `models/borzoi/`

### When to use

- RNA-seq prediction from 524kb genomic sequences (Calico, ~500M)

### Avoid

- unrelated modalities or production if FAIL

### Example

```bash
curl -s -X POST "$GW/v1/science/predict" -H "Content-Type: application/json" \
  -d '{"model":"borzoi","demo":true}'
```

### Quirks

- genomics: 6144 tracks x 16 bins
- Test status: **PASS** (READY).
- Scale-to-zero: first request may incur cold-start delay.

## `brainlm`

> ⚠ Not currently serving reliably — see `models.md` (FAIL).

**BrainLM 650M fMRI foundation model (ViT-MAE) for brain activity embeddings from 424 ROI time-series.**

**Endpoint:** `POST /v1/embeddings` **Protocol:** OpenAI embeddings  
**Input:** `fmri`, `model_size` **Output:** model-specific JSON response  
**Model path:** `models/brainlm/`

### When to use

- neuroscience embeddings

### Avoid

- chat, generation, or unrelated modalities
- Production until cluster verification passes

### Example

```bash
curl -s -X POST "$GW/v1/embeddings" -H "Content-Type: application/json" \
  -d '{"model":"brainlm","input":"What is protein folding?"}'
```

### Quirks

- ViT-MAE API unpack error; needs fMRI patch fix
- Test status: **FAIL** (READY).
- Scale-to-zero: first request may incur cold-start delay.

## `caduceus`

> ⚠ Not currently serving — see `models.md` (NOT-READY).

**Bidirectional Mamba DNA model with 131k context (Cornell/Kuleshov)**

**Endpoint:** `POST /v1/embeddings` **Protocol:** OpenAI embeddings  
**Input:** `input`, `sequences` **Output:** model-specific JSON response  
**Model path:** `models/caduceus/`

### When to use

- genomics embeddings

### Avoid

- chat, generation, or unrelated modalities
- Production until cluster verification passes

### Example

```bash
curl -s -X POST "$GW/v1/embeddings" -H "Content-Type: application/json" \
  -d '{"model":"caduceus","input":"What is protein folding?"}'
```

### Quirks

- mamba_ssm/selective_scan_cuda torch-CUDA ABI mismatch
- Test status: **FAIL** (NOT-READY).
- Scale-to-zero: first request may incur cold-start delay.

## `chem-t5`

**Chem-T5**

**Endpoint:** `POST /v1/science/generate` **Protocol:** custom science JSON  
**Input:** `SMILES or text (task-dependent)` **Output:** model-specific JSON  
**Model path:** `models/chem-t5/`

### When to use

- chemistry-specific generation

### Avoid

- general chat or unrelated tasks

### Example

```bash
curl -s -X POST "$GW/v1/science/generate" -H "Content-Type: application/json" \
  -d '{"model":"chem-t5","smiles":"CCO"}'
```

### Quirks

- exact GT4SD prompt templates; caption+forward_synthesis correct (was wrong)
- Test status: **FIXED** (READY).
- Scale-to-zero: first request may incur cold-start delay.

## `chemberta`

**ChemBERTa**

**Endpoint:** `POST /v1/embeddings` **Protocol:** OpenAI embeddings  
**Input:** `SMILES string or [SMILES]` **Output:** 768-dim vectors  
**Model path:** `models/chemberta/`

### When to use

- chemistry embeddings (768-dim)
- Gateway model id: `chemberta-125m`

### Avoid

- chat, generation, or unrelated modalities

### Example

```bash
curl -s -X POST "$GW/v1/embeddings" -H "Content-Type: application/json" \
  -d '{"model":"chemberta-125m","input":"What is protein folding?"}'
```

### Quirks

- embeddings PASS dim=768 (id chemberta-125m)
- Test status: **PASS** (READY).
- Scale-to-zero: first request may incur cold-start delay.
- Use model id `chemberta-125m` in requests.

## `chemgpt`

**ChemGPT-1.2B**

**Endpoint:** `POST /v1/science/generate` **Protocol:** custom science JSON  
**Input:** task-specific fields (SMILES, formula, etc.) **Output:** generated text/structure  
**Model path:** `models/chemgpt/`

### When to use

- chemistry-specific generation
- Gateway model id: `chemgpt-1.2b`

### Avoid

- general chat or unrelated tasks

### Example

```bash
curl -s -X POST "$GW/v1/science/generate" -H "Content-Type: application/json" \
  -d '{"model":"chemgpt-1.2b","smiles":"CCO"}'
```

### Quirks

- id=chemgpt-1.2b; SELFIES molecule generation
- Test status: **PASS** (READY).
- Scale-to-zero: first request may incur cold-start delay.
- Use model id `chemgpt-1.2b` in requests.

## `chemgpt-19m`

**ChemGPT-19M, a lightweight GPT-Neo style model trained on SMILES for de-novo molecule generation.**

**Endpoint:** `POST /v1/science/generate` **Protocol:** custom science JSON  
**Input:** task-specific fields (SMILES, formula, etc.) **Output:** generated text/structure  
**Model path:** `models/chemgpt-19m/`

### When to use

- chemistry-specific generation

### Avoid

- general chat or unrelated tasks

### Example

```bash
curl -s -X POST "$GW/v1/science/generate" -H "Content-Type: application/json" \
  -d '{"model":"chemgpt-19m","smiles":"CCO"}'
```

### Quirks

- SELFIES molecule generation
- Test status: **PASS** (READY).
- Scale-to-zero: first request may incur cold-start delay.

## `chgnet`

**CHGNet universal neural network potential with magnetic moments and charge distribution for materials simulation.**

**Endpoint:** `POST /v1/science/energy` **Protocol:** custom science JSON  
**Input:** crystal structure (ASE dict) **Output:** energy, forces, stress  
**Model path:** `models/chgnet/`

### When to use

- molecular energy/force prediction
- Gateway model id: `chgnet-v0.3`

### Avoid

- NLP or vision

### Example

```bash
curl -s -X POST "$GW/v1/science/energy" -H "Content-Type: application/json" \
  -d '{"model":"chgnet-v0.3"}'
```

### Quirks

- DEEP-FIX: ported server.py was broken (manually built CrystalGraph w/ bad kwarg) -> rewrote to model.predict_structure(); added missing server.py+kustomization (never ported); CederGroupHub/chgnet HF repo removed (404) -> non-fatal, uses chgnet...
- Test status: **FIXED** (READY).
- Scale-to-zero: first request may incur cold-start delay.
- Use model id `chgnet-v0.3` in requests.

## `chronos-bolt`

**Chronos-Bolt zero-shot time-series forecasting (CPU)**

**Endpoint:** `POST /v1/forecast` **Protocol:** time-series forecast JSON  
**Input:** `values`/`series` + `horizon` **Output:** mean/quantiles/samples  
**Model path:** `models/chronos-bolt/`

### When to use

- time-series / weather forecasting

### Avoid

- chat, static embeddings

### Example

```bash
curl -s -X POST "$GW/v1/forecast" -H "Content-Type: application/json" \
  -d '{"model":"chronos-bolt","values":[1,2,3,4,5,6,7,8],"horizon":12}'
```

### Quirks

- quantile forecast on 16-pt series
- Test status: **PASS** (READY).
- Scale-to-zero: first request may incur cold-start delay.

## `clap`

**CLAP**

**Endpoint:** `POST /v1/embeddings` **Protocol:** OpenAI embeddings  
**Input:** `input` string or array **Output:** 512-dim vectors  
**Model path:** `models/clap/`

### When to use

- audio embeddings (512-dim)

### Avoid

- chat, generation, or unrelated modalities

### Example

```bash
curl -s -X POST "$GW/v1/embeddings" -H "Content-Type: application/json" \
  -d '{"model":"clap","input":"What is protein folding?"}'
```

### Quirks

- text emb 512-dim + zero-shot audio classify (dog 0.73)
- Test status: **PASS** (READY).
- Scale-to-zero: first request may incur cold-start delay.

## `clay`

**Clay Foundation Model ~330M geospatial MAE embeddings from satellite imagery. Apache 2.0.**

**Endpoint:** `POST /v1/science/embed` **Protocol:** custom science JSON  
**Input:** `pixels`, `waves`, `gsd`, `lat` **Output:** model-specific JSON response  
**Model path:** `models/clay/`

### When to use

- earth-observation embeddings

### Avoid

- chat, generation, or unrelated modalities

### Example

```bash
curl -s -X POST "$GW/v1/science/embed" -H "Content-Type: application/json" \
  -d '{"model":"clay","text":"sample input"}'
```

### Quirks

- rewrote to Clay v1.5 datacube dict API; cls embedding PASS
- Test status: **FIXED** (READY).
- Scale-to-zero: first request may incur cold-start delay.

## `climatebert`

**ClimateBERT**

**Endpoint:** `POST /v1/science/classify` **Protocol:** custom science JSON  
**Input:** `text (for /v1/embeddings)` **Output:** 768-dim vectors  
**Model path:** `models/climatebert/`

### When to use

- climate classification

### Avoid

- generation or embedding-only pipelines

### Example

```bash
curl -s -X POST "$GW/v1/science/classify" -H "Content-Type: application/json" \
  -d '{"model":"climatebert","text":"We will reach net zero by 2050."}'
```

### Quirks

- net-zero 0.9988
- Test status: **PASS** (READY).
- Scale-to-zero: first request may incur cold-start delay.

## `climax`

**Microsoft ClimaX 108M climate/weather foundation model pre-trained on CMIP6, fine-tuned on ERA5.**

**Endpoint:** `POST /v1/science/forecast` **Protocol:** custom science JSON  
**Input:** `variables`, `data`, `lead_time` **Output:** model-specific JSON response  
**Model path:** `models/climax/`

### When to use

- time-series / weather forecasting

### Avoid

- chat, static embeddings

### Example

```bash
curl -s -X POST "$GW/v1/science/forecast" -H "Content-Type: application/json" \
  -d '{"model":"climax","demo":true}'
```

### Quirks

- needs valid ERA5 var names (e.g. 2m_temperature)
- Test status: **PASS** (READY).
- Scale-to-zero: first request may incur cold-start delay.

## `clinical-longformer`

> ⚠ Not currently serving — see `models.md` (NOT-READY).

**Clinical-Longformer**

**Endpoint:** `POST /v1/science/embed` **Protocol:** custom science JSON  
**Input:** `input` string or array **Output:** embedding vectors  
**Model path:** `models/clinical-longformer/`

### When to use

- clinical embeddings

### Avoid

- chat, generation, or unrelated modalities
- Production until cluster verification passes

### Example

```bash
curl -s -X POST "$GW/v1/science/embed" -H "Content-Type: application/json" \
  -d '{"model":"clinical-longformer","text":"sample input"}'
```

### Quirks

- hangs on CPU (gpu=true but no CUDA use); needs GPU/attention fix
- Test status: **FAIL** (NOT-READY).
- Scale-to-zero: first request may incur cold-start delay.

## `clinicalbert`

**Bio_ClinicalBERT**

**Endpoint:** `POST /v1/embeddings` **Protocol:** OpenAI embeddings  
**Input:** `clinical text str or [str]` **Output:** 768-dim vectors  
**Model path:** `models/clinicalbert/`

### When to use

- biomedical embeddings (768-dim)
- Gateway model id: `clinicalbert-110m`

### Avoid

- chat, generation, or unrelated modalities

### Example

```bash
curl -s -X POST "$GW/v1/embeddings" -H "Content-Type: application/json" \
  -d '{"model":"clinicalbert-110m","input":"What is protein folding?"}'
```

### Quirks

- embeddings PASS dim=768 (id clinicalbert-110m)
- Test status: **PASS** (READY).
- Scale-to-zero: first request may incur cold-start delay.
- Use model id `clinicalbert-110m` in requests.

## `command-r-7b`

**Cohere Command R 7B, RAG-optimized chat (multilingual)**

**Endpoint:** `POST /v1/chat/completions` **Protocol:** OpenAI chat  
**Input:** `messages[]` **Output:** assistant message (+ reasoning if enabled)  
**Model path:** `models/command-r-7b/`

### When to use

- instruction-following chat in nlp domain

### Avoid

- embedding-only workloads, batch offline inference without chat API

### Example

```bash
curl -s -X POST "$GW/v1/chat/completions" -H "Content-Type: application/json" \
  -d '{"model":"command-r-7b","messages":[{"role":"user","content":"Hello"}]}'
```

### Quirks

- OpenAI + Anthropic
- Test status: **PASS** (READY).

## `croma`

**CROMA cross-modal remote sensing foundation model. SAR + optical paired satellite imagery. ~300M.**

**Endpoint:** `POST /v1/embeddings` **Protocol:** OpenAI embeddings  
**Input:** `sar_images`, `optical_images`, `modality` **Output:** model-specific JSON response  
**Model path:** `models/croma/`

### When to use

- image/medical segmentation

### Avoid

- text generation

### Example

```bash
curl -s -X POST "$GW/v1/embeddings" -H "Content-Type: application/json" \
  -d '{"model":"croma"}'
```

### Quirks

- dict output extraction (joint/optical/SAR GAP)
- Test status: **FIXED** (READY).
- Scale-to-zero: first request may incur cold-start delay.

## `crysta-llm`

**CrystaLLM GPT-2-based crystal structure generation model that outputs CIF-format structures from formula prompts.**

**Endpoint:** `POST /v1/science/generate` **Protocol:** custom science JSON  
**Input:** `formula`, `temperature`, `max_new_tokens`, `num_samples` **Output:** model-specific JSON response  
**Model path:** `models/crysta-llm/`

### When to use

- crystal structure generation from chemical formulas (CIF output)

### Avoid

- chat, general NLP, protein folding

### Example

```bash
curl -s -X POST "$GW/v1/science/generate" -H "Content-Type: application/json" \
  -d '{"model":"crysta-llm","smiles":"CCO"}'
```

### Quirks

- crystal structure gen from formula (progress-deadline fix)
- Test status: **PASS** (READY).
- Scale-to-zero: first request may incur cold-start delay.

## `deepseek-v2-lite-16b`

**DeepSeek V2 Lite 16B MoE (2.4B active), MLA attention**

**Endpoint:** `POST /v1/chat/completions` **Protocol:** OpenAI chat  
**Input:** `messages[]` **Output:** assistant message (+ reasoning if enabled)  
**Model path:** `models/deepseek-v2-lite-16b/`

### When to use

- instruction-following chat in nlp domain

### Avoid

- embedding-only workloads, batch offline inference without chat API

### Example

```bash
curl -s -X POST "$GW/v1/chat/completions" -H "Content-Type: application/json" \
  -d '{"model":"deepseek-v2-lite-16b","messages":[{"role":"user","content":"Hello"}]}'
```

### Quirks

- v0.20.2 (std); gpumem 45GB + max-model-len 8192; correct answers
- Test status: **PASS** (READY).

## `depth-anything`

**Depth Anything V2 Small**

**Endpoint:** `POST /v1/vision/depth` **Protocol:** vision JSON (base64 image)  
**Input:** base64 `image` **Output:** depth PNG/array  
**Model path:** `models/depth-anything/`

### When to use

- Depth Anything V2 Small — monocular depth estimation
- Gateway model id: `depth-anything-v2`

### Avoid

- unrelated modalities or production if FAIL

### Example

```bash
curl -s -X POST "$GW/v1/vision/depth" -H "Content-Type: application/json" \
  -d '{"model":"depth-anything-v2"}'
```

### Quirks

- fixed k8s_name 404 + PNG output; PASS
- Test status: **FIXED** (READY).
- Scale-to-zero: first request may incur cold-start delay.
- Use model id `depth-anything-v2` in requests.

## `diffdock`

**DiffDock-L diffusion-based protein-ligand docking**

**Endpoint:** `POST /v1/dock` **Protocol:** custom JSON  
**Input:** protein PDB + ligand SMILES **Output:** poses  
**Model path:** `models/diffdock/`

### When to use

- DiffDock-L diffusion-based protein-ligand docking
- Gateway model id: `diffdock-l`

### Avoid

- unrelated modalities or production if FAIL

### Example

```bash
curl -s -X POST "$GW/v1/dock" -H "Content-Type: application/json" \
  -d '{"model":"diffdock-l"}'
```

### Quirks

- SMILES passed direct (not .smi file); conf regex fixed; 11 poses on 1CRN+aspirin
- Test status: **FIXED** (READY).
- Scale-to-zero: first request may incur cold-start delay.
- Use model id `diffdock-l` in requests.

## `dino-vit-b8`

**DINO ViT-B/8**

**Endpoint:** `POST /v1/vision/embed` **Protocol:** vision JSON (base64 image)  
**Input:** `input` string or array **Output:** embedding vectors  
**Model path:** `models/dino-vit-b8/`

### When to use

- computer-vision embeddings

### Avoid

- chat, generation, or unrelated modalities

### Example

```bash
curl -s -X POST "$GW/v1/vision/embed" -H "Content-Type: application/json" \
  -d '{"model":"dino-vit-b8"}'
```

### Quirks

- image embedding
- Test status: **PASS** (READY).
- Scale-to-zero: first request may incur cold-start delay.

## `dnabert-2`

**DNABERT-2**

**Endpoint:** `POST /v1/embeddings` **Protocol:** OpenAI embeddings  
**Input:** `input` string or array **Output:** embedding vectors  
**Model path:** `models/dnabert-2/`

### When to use

- genomics embeddings
- Gateway model id: `dnabert-2-117m`

### Avoid

- chat, generation, or unrelated modalities

### Example

```bash
curl -s -X POST "$GW/v1/embeddings" -H "Content-Type: application/json" \
  -d '{"model":"dnabert-2-117m","input":"ACGTACGTACGTACGT"}'
```

### Quirks

- embeddings PASS dim=768 (id dnabert-2-117m)
- Test status: **PASS** (READY).
- Scale-to-zero: first request may incur cold-start delay.
- Use model id `dnabert-2-117m` in requests.

## `dnabert-s`

**Species-aware genome foundation model with contrastive learning**

**Endpoint:** `POST /v1/embeddings` **Protocol:** OpenAI embeddings  
**Input:** `input` **Output:** model-specific JSON response  
**Model path:** `models/dnabert-s/`

### When to use

- genomics embeddings

### Avoid

- chat, generation, or unrelated modalities

### Example

```bash
curl -s -X POST "$GW/v1/embeddings" -H "Content-Type: application/json" \
  -d '{"model":"dnabert-s","input":"ACGTACGTACGTACGT"}'
```

### Quirks

- embeddings PASS dim=768 (id dnabert-s)
- Test status: **PASS** (READY).
- Scale-to-zero: first request may incur cold-start delay.

## `dust3r`

**DUSt3R (CVPR 2024): unconstrained 3D reconstruction from 2+ uncalibrated images without known camera intrinsics.**

**Endpoint:** `POST /v1/science/reconstruct` **Protocol:** custom science JSON  
**Input:** `images`, `output_format` **Output:** model-specific JSON response  
**Model path:** `models/dust3r/`

### When to use

- DUSt3R (CVPR 2024): unconstrained 3D reconstruction from 2+ uncalibrated images 

### Avoid

- unrelated modalities or production if FAIL

### Example

```bash
curl -s -X POST "$GW/v1/science/reconstruct" -H "Content-Type: application/json" \
  -d '{"model":"dust3r"}'
```

### Quirks

- downsample pointcloud (was 31MB>gateway); bbox+loss; 2 imgs OK
- Test status: **FIXED** (READY).
- Scale-to-zero: first request may incur cold-start delay.

## `earthpt`

**EarthPT 700M EO time-series autoregressive foundation model. 18-channel pixel time-series prediction.**

**Endpoint:** `POST /v1/science/predict` **Protocol:** custom science JSON  
**Input:** `time_series`, `predict_steps` **Output:** model-specific JSON response  
**Model path:** `models/earthpt/`

### When to use

- earth-observation embeddings

### Avoid

- chat, generation, or unrelated modalities

### Example

```bash
curl -s -X POST "$GW/v1/science/predict" -H "Content-Type: application/json" \
  -d '{"model":"earthpt","demo":true}'
```

### Quirks

- CPU ckpt load + RAM 24Gi (was GPU+host OOM); predicts OK
- Test status: **FIXED** (READY).
- Scale-to-zero: first request may incur cold-start delay.

## `efficientnet-b0`

**EfficientNet-B0 ImageNet classifier (1000 classes)**

**Endpoint:** `POST /v1/vision/classify` **Protocol:** vision JSON (base64 image)  
**Input:** base64 `image` **Output:** top-k labels  
**Model path:** `models/efficientnet-b0/`

### When to use

- computer-vision classification

### Avoid

- generation or embedding-only pipelines

### Example

```bash
curl -s -X POST "$GW/v1/vision/classify" -H "Content-Type: application/json" \
  -d '{"model":"efficientnet-b0"}'
```

### Quirks

- lite4: fixed preproc+double-softmax+labels; minibus 0.63
- Test status: **FIXED** (READY).
- Scale-to-zero: first request may incur cold-start delay.

## `enformer`

> ⚠ Not currently serving — see `models.md` (NOT-READY).

**Gene expression prediction from 196kb DNA sequences (DeepMind/EleutherAI)**

**Endpoint:** `POST /v1/science/predict` **Protocol:** custom science JSON  
**Input:** `sequence`, `organism`, `return_tracks` **Output:** model-specific JSON response  
**Model path:** `models/enformer/`

### When to use

- Gene expression prediction from 196kb DNA sequences (DeepMind/EleutherAI)

### Avoid

- unrelated modalities or production if FAIL
- Production until cluster verification passes

### Example

```bash
curl -s -X POST "$GW/v1/science/predict" -H "Content-Type: application/json" \
  -d '{"model":"enformer","demo":true}'
```

### Quirks

- isvc never deployed (READY=False 11h); needs recreate
- Test status: **FAIL** (NOT-READY).
- Scale-to-zero: first request may incur cold-start delay.

## `ernierna`

> ⚠ Not currently serving — see `models.md` (NOT-READY).

**Structure-aware RNA foundation model from Baidu/multimolecule (~86M)**

**Endpoint:** `POST /v1/science/embed` **Protocol:** custom science JSON  
**Input:** `sequence`, `sequences` **Output:** model-specific JSON response  
**Model path:** `models/ernierna/`

### When to use

- genomics embeddings

### Avoid

- chat, generation, or unrelated modalities
- Production until cluster verification passes

### Example

```bash
curl -s -X POST "$GW/v1/science/embed" -H "Content-Type: application/json" \
  -d '{"model":"ernierna","text":"sample input"}'
```

### Quirks

- isvc never deployed (READY=False 10h); needs recreate/fix
- Test status: **FAIL** (NOT-READY).
- Scale-to-zero: first request may incur cold-start delay.

## `esm1b`

**ESM-1b 650M protein language model from Meta**

**Endpoint:** `POST /v1/embeddings` **Protocol:** OpenAI embeddings  
**Input:** `input`, `sequences` **Output:** model-specific JSON response  
**Model path:** `models/esm1b/`

### When to use

- proteomics embeddings

### Avoid

- chat, generation, or unrelated modalities

### Example

```bash
curl -s -X POST "$GW/v1/embeddings" -H "Content-Type: application/json" \
  -d '{"model":"esm1b","input":"MKTVRQERLKSIVRILERSKEPVSGAQ"}'
```

### Quirks

- 1280-dim protein (recreated)
- Test status: **PASS** (READY).
- Scale-to-zero: first request may incur cold-start delay.

## `esm2-150m`

**ESM2 150M compact protein encoder from Meta**

**Endpoint:** `POST /v1/embeddings` **Protocol:** OpenAI embeddings  
**Input:** `input`, `sequences` **Output:** model-specific JSON response  
**Model path:** `models/esm2-150m/`

### When to use

- proteomics embeddings

### Avoid

- chat, generation, or unrelated modalities

### Example

```bash
curl -s -X POST "$GW/v1/embeddings" -H "Content-Type: application/json" \
  -d '{"model":"esm2-150m","input":"MKTVRQERLKSIVRILERSKEPVSGAQ"}'
```

### Quirks

- 640-dim protein (recreated)
- Test status: **PASS** (READY).
- Scale-to-zero: first request may incur cold-start delay.

## `esm2-35m`

**Meta ESM-2 35M, the smallest ESM-2 protein encoder.**

**Endpoint:** `POST /v1/embeddings` **Protocol:** OpenAI embeddings  
**Input:** `protein sequence str or [str] (1-letter AA, <=1024)` **Output:** 480-dim vectors  
**Model path:** `models/esm2-35m/`

### When to use

- proteomics embeddings (480-dim)

### Avoid

- chat, generation, or unrelated modalities

### Example

```bash
curl -s -X POST "$GW/v1/embeddings" -H "Content-Type: application/json" \
  -d '{"model":"esm2-35m","input":"MKTVRQERLKSIVRILERSKEPVSGAQ"}'
```

### Quirks

- 480-dim protein
- Test status: **PASS** (READY).
- Scale-to-zero: first request may incur cold-start delay.

## `esm2-3b`

**ESM-2 3B protein language model embeddings**

**Endpoint:** `POST /v1/embeddings` **Protocol:** OpenAI embeddings  
**Input:** `input` string or array **Output:** embedding vectors  
**Model path:** `models/esm2-3b/`

### When to use

- proteomics embeddings

### Avoid

- chat, generation, or unrelated modalities

### Example

```bash
curl -s -X POST "$GW/v1/embeddings" -H "Content-Type: application/json" \
  -d '{"model":"esm2-3b","input":"MKTVRQERLKSIVRILERSKEPVSGAQ"}'
```

### Quirks

- 2560-dim protein (recreate cleared)
- Test status: **PASS** (READY).
- Scale-to-zero: first request may incur cold-start delay.

## `esm2-650m`

**ESM-2 650M protein language model (per-protein embeddings)**

**Endpoint:** `POST /v1/embeddings` **Protocol:** OpenAI embeddings  
**Input:** `protein sequence string or list of sequences (1-letter AA codes, <=1022 residues)` **Output:** 1280-dim vectors  
**Model path:** `models/esm2-650m/`

### When to use

- proteomics embeddings (1280-dim)

### Avoid

- chat, generation, or unrelated modalities

### Example

```bash
curl -s -X POST "$GW/v1/embeddings" -H "Content-Type: application/json" \
  -d '{"model":"esm2-650m","input":"MKTVRQERLKSIVRILERSKEPVSGAQ"}'
```

### Quirks

- 1280-dim protein
- Test status: **PASS** (READY).
- Scale-to-zero: first request may incur cold-start delay.

## `esmc-300m`

**ESM Cambrian 300M next-gen protein LM from EvolutionaryScale**

**Endpoint:** `POST /v1/embeddings` **Protocol:** OpenAI embeddings  
**Input:** `input`, `sequences` **Output:** model-specific JSON response  
**Model path:** `models/esmc-300m/`

### When to use

- proteomics embeddings

### Avoid

- chat, generation, or unrelated modalities

### Example

```bash
curl -s -X POST "$GW/v1/embeddings" -H "Content-Type: application/json" \
  -d '{"model":"esmc-300m","input":"MKTVRQERLKSIVRILERSKEPVSGAQ"}'
```

### Quirks

- 960-dim (recreated)
- Test status: **PASS** (READY).
- Scale-to-zero: first request may incur cold-start delay.

## `esmfold`

**ESMfold protein structure prediction from sequence**

**Endpoint:** `POST /v1/structure` **Protocol:** structure JSON  
**Input:** protein `sequence` **Output:** PDB string  
**Model path:** `models/esmfold/`

### When to use

- protein/structure prediction

### Avoid

- chat, fast approximate folds at scale

### Example

```bash
curl -s -X POST "$GW/v1/structure" -H "Content-Type: application/json" \
  -d '{"model":"esmfold"}'
```

### Quirks

- folds protein -> PDB
- Test status: **PASS** (READY).
- Scale-to-zero: first request may incur cold-start delay.

## `fengwu`

**Shanghai AI Lab FengWu v2 global weather forecast model. ONNX, 0.25-degree, 83 ERA5 variables.**

**Endpoint:** `POST /v1/science/forecast` **Protocol:** custom science JSON  
**Input:** `surface`, `upper`, `demo` **Output:** model-specific JSON response  
**Model path:** `models/fengwu/`

### When to use

- time-series / weather forecasting

### Avoid

- chat, static embeddings

### Example

```bash
curl -s -X POST "$GW/v1/science/forecast" -H "Content-Type: application/json" \
  -d '{"model":"fengwu","demo":true}'
```

### Quirks

- summarize grid (was 286MB>gateway); demo+real ONNX OK
- Test status: **FIXED** (READY).
- Scale-to-zero: first request may incur cold-start delay.

## `finbert`

**FinBERT financial sentiment classification (positive/negative/neutral)**

**Endpoint:** `POST /v1/science/classify` **Protocol:** custom science JSON  
**Input:** `text` **Output:** label + confidence  
**Model path:** `models/finbert/`

### When to use

- finance classification

### Avoid

- generation or embedding-only pipelines

### Example

```bash
curl -s -X POST "$GW/v1/science/classify" -H "Content-Type: application/json" \
  -d '{"model":"finbert","text":"We will reach net zero by 2050."}'
```

### Quirks

- sentiment positive 0.96
- Test status: **PASS** (READY).
- Scale-to-zero: first request may incur cold-start delay.

## `fourcastnet3`

**NVIDIA FourCastNet3 Spherical Fourier Neural Operator for global weather. 73 ERA5 variables, 0.25-degree.**

**Endpoint:** `POST /v1/science/forecast` **Protocol:** custom science JSON  
**Input:** `variables`, `steps`, `demo` **Output:** model-specific JSON response  
**Model path:** `models/fourcastnet3/`

### When to use

- time-series / weather forecasting

### Avoid

- chat, static embeddings

### Example

```bash
curl -s -X POST "$GW/v1/science/forecast" -H "Content-Type: application/json" \
  -d '{"model":"fourcastnet3","demo":true}'
```

### Quirks

- demo OK; real FCN3 blocked (makani+torch-harmonics CUDA matrix needs dedicated image)
- Test status: **DEMO** (READY).
- Scale-to-zero: first request may incur cold-start delay.

## `galileo`

> ⚠ Not currently serving reliably — see `models.md` (FAIL).

**NASA Harvest Galileo ~90M agricultural monitoring model. Multi-spectral Sentinel-2 time-series.**

**Endpoint:** `POST /v1/embeddings` **Protocol:** OpenAI embeddings  
**Input:** `pixels`, `months`, `latlons` **Output:** model-specific JSON response  
**Model path:** `models/galileo/`

### When to use

- earth-observation classification

### Avoid

- generation or embedding-only pipelines
- Production until cluster verification passes

### Example

```bash
curl -s -X POST "$GW/v1/embeddings" -H "Content-Type: application/json" \
  -d '{"model":"galileo"}'
```

### Quirks

- numpy fixed; model loads as raw state_dict - needs deep fix
- Test status: **FAIL** (READY).
- Scale-to-zero: first request may incur cold-start delay.

## `gemma-3-4b-it`

**Google Gemma 3 4B instruction-tuned, multimodal (text + image, multilingual)**

**Endpoint:** `POST /v1/chat/completions` **Protocol:** OpenAI chat  
**Input:** `messages[]` **Output:** assistant message (+ reasoning if enabled)  
**Model path:** `models/gemma-3-4b-it/`

### When to use

- instruction-following chat in nlp domain

### Avoid

- embedding-only workloads, batch offline inference without chat API

### Example

```bash
curl -s -X POST "$GW/v1/chat/completions" -H "Content-Type: application/json" \
  -d '{"model":"gemma-3-4b-it","messages":[{"role":"user","content":"Hello"}]}'
```

### Quirks

- OpenAI + Anthropic
- Test status: **PASS** (READY).
- Scale-to-zero: first request may incur cold-start delay.

## `gemma-4-26b-a4b`

**Google Gemma 4 26B A4B MoE, reasoning + vision, FP8**

**Endpoint:** `POST /v1/chat/completions` **Protocol:** OpenAI chat  
**Input:** `messages[]` **Output:** assistant message (+ reasoning if enabled)  
**Model path:** `models/gemma-4-26b-a4b/`

### When to use

- instruction-following chat in nlp domain

### Avoid

- embedding-only workloads, batch offline inference without chat API

### Example

```bash
curl -s -X POST "$GW/v1/chat/completions" -H "Content-Type: application/json" \
  -d '{"model":"gemma-4-26b-a4b","messages":[{"role":"user","content":"Hello"}]}'
```

### Quirks

- 26B MoE fp8 (progress-deadline fix); correct answers
- Test status: **PASS** (READY).

## `gena-lm`

**BERT-style DNA language model trained on T2T human genome (AIRI)**

**Endpoint:** `POST /v1/embeddings` **Protocol:** OpenAI embeddings  
**Input:** `input`, `sequences` **Output:** model-specific JSON response  
**Model path:** `models/gena-lm/`

### When to use

- genomics embeddings

### Avoid

- chat, generation, or unrelated modalities

### Example

```bash
curl -s -X POST "$GW/v1/embeddings" -H "Content-Type: application/json" \
  -d '{"model":"gena-lm","input":"ACGTACGTACGTACGT"}'
```

### Quirks

- 768-dim DNA (recreated)
- Test status: **PASS** (READY).
- Scale-to-zero: first request may incur cold-start delay.

## `gena-lm-large`

**Large DNA BERT for long genomic sequences (340M, AIRI)**

**Endpoint:** `POST /v1/science/embed` **Protocol:** custom science JSON  
**Input:** `sequence`, `sequences` **Output:** model-specific JSON response  
**Model path:** `models/gena-lm-large/`

### When to use

- genomics embeddings

### Avoid

- chat, generation, or unrelated modalities

### Example

```bash
curl -s -X POST "$GW/v1/science/embed" -H "Content-Type: application/json" \
  -d '{"model":"gena-lm-large","text":"sample input"}'
```

### Quirks

- output_hidden_states (was returning vocab logits); 1024-dim
- Test status: **FIXED** (READY).
- Scale-to-zero: first request may incur cold-start delay.

## `geneformer`

**Single-cell gene expression foundation model from NIH NCI (104M)**

**Endpoint:** `POST /v1/embed` **Protocol:** custom JSON  
**Input:** `gene_ids` **Output:** model-specific JSON response  
**Model path:** `models/geneformer/`

### When to use

- genomics embeddings

### Avoid

- chat, generation, or unrelated modalities

### Example

```bash
curl -s -X POST "$GW/v1/embed" -H "Content-Type: application/json" \
  -d '{"model":"geneformer"}'
```

### Quirks

- needs gene_ids token IDs (recreated)
- Test status: **PASS** (READY).
- Scale-to-zero: first request may incur cold-start delay.

## `geogalactica`

> ⚠ Not currently serving — see `models.md` (NOT-READY).

**GeoGalactica 30B geoscience LLM**

**Endpoint:** `POST /v1/chat/completions` **Protocol:** OpenAI chat  
**Input:** `messages`, `max_tokens`, `stream` **Output:** model-specific JSON response  
**Model path:** `models/geogalactica/`

### When to use

- instruction-following chat in earth-science domain

### Avoid

- embedding-only workloads, batch offline inference without chat API
- Production until cluster verification passes

### Example

```bash
curl -s -X POST "$GW/v1/chat/completions" -H "Content-Type: application/json" \
  -d '{"model":"geogalactica","messages":[{"role":"user","content":"Hello"}]}'
```

### Quirks

- gated HF repo geobrain-ai/geogalactica (403); needs access approval
- Test status: **FAIL** (NOT-READY).
- Scale-to-zero: first request may incur cold-start delay.

## `glm-4-32b`

**GLM-4-32B-0414 instruct: strong function calling + agentic workflows.**

**Endpoint:** `POST /v1/chat/completions` **Protocol:** OpenAI chat  
**Input:** `messages[]` **Output:** assistant message (+ reasoning if enabled)  
**Model path:** `models/glm-4-32b/`

### When to use

- instruction-following chat in nlp domain

### Avoid

- embedding-only workloads, batch offline inference without chat API

### Example

```bash
curl -s -X POST "$GW/v1/chat/completions" -H "Content-Type: application/json" \
  -d '{"model":"glm-4-32b","messages":[{"role":"user","content":"Hello"}]}'
```

### Quirks

- org moved THUDM->zai-org; haiku ok
- Test status: **PASS** (READY).
- Scale-to-zero: first request may incur cold-start delay.

## `glm-z1-32b`

**GLM-Z1-32B-0414 reasoning variant: R1-style thinking, distinct lineage.**

**Endpoint:** `POST /v1/chat/completions` **Protocol:** OpenAI chat  
**Input:** `messages[]` **Output:** assistant message (+ reasoning if enabled)  
**Model path:** `models/glm-z1-32b/`

### When to use

- instruction-following chat in nlp domain

### Avoid

- embedding-only workloads, batch offline inference without chat API

### Example

```bash
curl -s -X POST "$GW/v1/chat/completions" -H "Content-Type: application/json" \
  -d '{"model":"glm-z1-32b","messages":[{"role":"user","content":"Hello"}]}'
```

### Quirks

- dropped deepseek_r1 parser (no <think> special tokens); 8!=40320
- Test status: **FIXED** (READY).
- Scale-to-zero: first request may incur cold-start delay.

## `glm-z1-rumination-32b`

**GLM-Z1-Rumination-32B deep-research model: multi-step synthesis.**

**Endpoint:** `POST /v1/chat/completions` **Protocol:** OpenAI chat  
**Input:** `messages[]` **Output:** assistant message (+ reasoning if enabled)  
**Model path:** `models/glm-z1-rumination-32b/`

### When to use

- instruction-following chat in nlp domain

### Avoid

- embedding-only workloads, batch offline inference without chat API

### Example

```bash
curl -s -X POST "$GW/v1/chat/completions" -H "Content-Type: application/json" \
  -d '{"model":"glm-z1-rumination-32b","messages":[{"role":"user","content":"Hello"}]}'
```

### Quirks

- dropped deepseek_r1 parser; agentic finish-call format; Tokyo ok
- Test status: **FIXED** (READY).
- Scale-to-zero: first request may incur cold-start delay.

## `gpt-oss-120b`

**OpenAI GPT-OSS 120B MoE, configurable reasoning + native tool calling**

**Endpoint:** `POST /v1/chat/completions` **Protocol:** OpenAI chat  
**Input:** `messages[]` **Output:** assistant message (+ reasoning if enabled)  
**Model path:** `models/gpt-oss-120b/`

### When to use

- instruction-following chat in nlp domain

### Avoid

- embedding-only workloads, batch offline inference without chat API

### Example

```bash
curl -s -X POST "$GW/v1/chat/completions" -H "Content-Type: application/json" \
  -d '{"model":"gpt-oss-120b","messages":[{"role":"user","content":"Hello"}]}'
```

### Quirks

- TP2 ~200tok/s; whole GPUs + `--disable-custom-all-reduce` (HAMi custom-AR stall fix).
- Reasoning effort + OpenAI + Anthropic verified.
- Test status: **FIXED** (READY).
- Scale-to-zero: first request may incur cold-start delay.

## `gpt-oss-20b`

**OpenAI GPT-OSS 20B MoE, configurable reasoning + native tools (lightweight)**

**Endpoint:** `POST /v1/chat/completions` **Protocol:** OpenAI chat  
**Input:** `messages[]` **Output:** assistant message (+ reasoning if enabled)  
**Model path:** `models/gpt-oss-20b/`

### When to use

- instruction-following chat in nlp domain

### Avoid

- embedding-only workloads, batch offline inference without chat API

### Example

```bash
curl -s -X POST "$GW/v1/chat/completions" -H "Content-Type: application/json" \
  -d '{"model":"gpt-oss-20b","messages":[{"role":"user","content":"Hello"}]}'
```

### Quirks

- OpenAI + Anthropic
- Test status: **PASS** (READY).
- Scale-to-zero: first request may incur cold-start delay.

## `granite-geospatial-biomass`

**IBM Granite Geospatial Biomass**

**Endpoint:** `POST /v1/science/predict` **Protocol:** custom science JSON  
**Input:** `image`, `demo` **Output:** model-specific JSON response  
**Model path:** `models/granite-geospatial-biomass/`

### When to use

- earth-observation classification

### Avoid

- generation or embedding-only pipelines

### Example

```bash
curl -s -X POST "$GW/v1/science/predict" -H "Content-Type: application/json" \
  -d '{"model":"granite-geospatial-biomass","demo":true}'
```

### Quirks

- add gcc/g++ to init (terratorch->stringzilla build); demo OK
- Test status: **FIXED** (READY).
- Scale-to-zero: first request may incur cold-start delay.

## `granite-geospatial-ocean`

**IBM Granite Geospatial Ocean**

**Endpoint:** `POST /v1/science/embed` **Protocol:** custom science JSON  
**Input:** `image`, `bands`, `demo` **Output:** model-specific JSON response  
**Model path:** `models/granite-geospatial-ocean/`

### When to use

- earth-observation classification

### Avoid

- generation or embedding-only pipelines

### Example

```bash
curl -s -X POST "$GW/v1/science/embed" -H "Content-Type: application/json" \
  -d '{"model":"granite-geospatial-ocean","text":"sample input"}'
```

### Quirks

- add gcc/g++ to init; demo embeddings OK; slow cold-start
- Test status: **FIXED** (READY).
- Scale-to-zero: first request may incur cold-start delay.

## `graphcast`

**DeepMind GraphCast-Small weather model. 1-degree resolution, 13 pressure levels, JAX-based.**

**Endpoint:** `POST /v1/science/predict` **Protocol:** custom science JSON  
**Input:** `demo`, `future_era5` **Output:** model-specific JSON response  
**Model path:** `models/graphcast/`

### When to use

- time-series / weather forecasting

### Avoid

- chat, static embeddings

### Example

```bash
curl -s -X POST "$GW/v1/science/predict" -H "Content-Type: application/json" \
  -d '{"model":"graphcast","demo":true}'
```

### Quirks

- demo mode (real ERA5 not via API by design)
- Test status: **PASS** (READY).
- Scale-to-zero: first request may incur cold-start delay.

## `hyenadna`

**HyenaDNA**

**Endpoint:** `POST /v1/embeddings` **Protocol:** OpenAI embeddings  
**Input:** `input` string or array **Output:** embedding vectors  
**Model path:** `models/hyenadna/`

### When to use

- genomics embeddings
- Gateway model id: `hyenadna-6.5m`

### Avoid

- chat, generation, or unrelated modalities

### Example

```bash
curl -s -X POST "$GW/v1/embeddings" -H "Content-Type: application/json" \
  -d '{"model":"hyenadna-6.5m","input":"ACGTACGTACGTACGT"}'
```

### Quirks

- embeddings PASS dim=256 (id hyenadna-6.5m)
- Test status: **PASS** (READY).
- Scale-to-zero: first request may incur cold-start delay.
- Use model id `hyenadna-6.5m` in requests.

## `ithaca`

**Ithaca**

**Endpoint:** `POST /v1/science/predict` **Protocol:** custom science JSON  
**Input:** `sequence`/`text`/`demo` **Output:** prediction JSON  
**Model path:** `models/ithaca/`

### When to use

- Ithaca — ancient Greek inscription restoration, dating, and geolocation

### Avoid

- unrelated modalities or production if FAIL

### Example

```bash
curl -s -X POST "$GW/v1/science/predict" -H "Content-Type: application/json" \
  -d '{"model":"ithaca","demo":true}'
```

### Quirks

- DEEP-FIX: jax[cuda12] (was CPU-fallback -> 3min); contextualize() retrieval made opt-in (req.contextualize); gap char is ? (uppercase Greek, 50-750 chars). Warm ~8s on GPU (first call ~90s JIT). Returns restoration + attribution (date/geo)
- Test status: **FIXED** (READY).
- Scale-to-zero: first request may incur cold-start delay.

## `k2-v2`

**LLM360 K2-V2 70B: fully open (weights + data + code + evals). Citable.**

**Endpoint:** `POST /v1/chat/completions` **Protocol:** OpenAI chat  
**Input:** `messages[]` **Output:** assistant message (+ reasoning if enabled)  
**Model path:** `models/k2-v2/`

### When to use

- instruction-following chat in nlp domain

### Avoid

- embedding-only workloads, batch offline inference without chat API

### Example

```bash
curl -s -X POST "$GW/v1/chat/completions" -H "Content-Type: application/json" \
  -d '{"model":"k2-v2","messages":[{"role":"user","content":"Hello"}]}'
```

### Quirks

- ships FP32 ~290GB (not 140GB); --dtype=bfloat16 to fit 4xL40S; Xet stalled -> HF_HUB_DISABLE_XET; still downloading
- Test status: **PENDING** (READY).
- Scale-to-zero: first request may incur cold-start delay.

## `kandinsky-3`

**Kandinsky 3 text-to-image and image-to-image generation**

**Endpoint:** `POST /v1/images/generations` **Protocol:** OpenAI images  
**Input:** `prompt` **Output:** base64 PNG  
**Model path:** `models/kandinsky-3/`

### When to use

- text-to-image and image edit at 1024px

### Avoid

- chat, vision understanding, low-latency without Ray cold start

### Example

```bash
curl -s -X POST "$GW/v1/images/generations" -H "Content-Type: application/json" \
  -d '{"model":"kandinsky-3","prompt":"a red cube on a table","size":"1024x1024"}'
```

### Quirks

- RayService with in-tree autoscaler; head pinned to CPU node, GPU workers scale 0→3.
- Verified: scale-up on request, ~24s PNG at 1024, scale-down releases L40S after idle.
- Test status: **PASS** (READY).

## `labram`

> ⚠ Not currently serving reliably — see `models.md` (FAIL).

**LaBraM Large Brain Model for EEG signals. BSD-3-Clause, braindecode/Tsinghua.**

**Endpoint:** `POST /v1/science/embed` **Protocol:** custom science JSON  
**Input:** `eeg`, `sfreq` **Output:** model-specific JSON response  
**Model path:** `models/labram/`

### When to use

- neuroscience embeddings

### Avoid

- chat, generation, or unrelated modalities
- Production until cluster verification passes

### Example

```bash
curl -s -X POST "$GW/v1/science/embed" -H "Content-Type: application/json" \
  -d '{"model":"labram","text":"sample input"}'
```

### Quirks

- needs 128 canonical channels or ch_names - needs deep fix
- Test status: **FAIL** (READY).
- Scale-to-zero: first request may incur cold-start delay.

## `lag-llama`

**Lag-Llama probabilistic time-series foundation model (~30M params) for zero-shot forecasting with lag features.**

**Endpoint:** `POST /v1/science/forecast` **Protocol:** custom science JSON  
**Input:** `context`, `prediction_length`, `num_samples`, `freq` **Output:** model-specific JSON response  
**Model path:** `models/lag-llama/`

### When to use

- time-series / weather forecasting

### Avoid

- chat, static embeddings

### Example

```bash
curl -s -X POST "$GW/v1/science/forecast" -H "Content-Type: application/json" \
  -d '{"model":"lag-llama","demo":true}'
```

### Quirks

- torch2.6 weights_only + create_predictor(module=) API
- Test status: **FIXED** (READY).
- Scale-to-zero: first request may incur cold-start delay.

## `leandojo`

**LeanDojo Lean 4 premise retriever (ByT5-small, 125M) for retrieval-augmented automated theorem proving.**

**Endpoint:** `POST /v1/science/retrieve` **Protocol:** custom science JSON  
**Input:** `goal`, `num_premises` **Output:** model-specific JSON response  
**Model path:** `models/leandojo/`

### When to use

- mathematics embeddings

### Avoid

- chat, generation, or unrelated modalities

### Example

```bash
curl -s -X POST "$GW/v1/science/retrieve" -H "Content-Type: application/json" \
  -d '{"model":"leandojo"}'
```

### Quirks

- premise retrieval w/ scores
- Test status: **PASS** (READY).
- Scale-to-zero: first request may incur cold-start delay.

## `ligandmpnn`

**Ligand-aware protein sequence design from Baker Lab (UW)**

**Endpoint:** `POST /v1/design` **Protocol:** custom JSON  
**Input:** `pdb`, `num_sequences`, `temperature`, `model_type` **Output:** model-specific JSON response  
**Model path:** `models/ligandmpnn/`

### When to use

- Ligand-aware protein sequence design from Baker Lab (UW)

### Avoid

- unrelated modalities or production if FAIL

### Example

```bash
curl -s -X POST "$GW/v1/design" -H "Content-Type: application/json" \
  -d '{"model":"ligandmpnn"}'
```

### Quirks

- checkpoints+args+optional-openfold; 1CRN design near-native PASS
- Test status: **FIXED** (READY).
- Scale-to-zero: first request may incur cold-start delay.

## `mace-mh-1`

**MACE-MH-1 multi-head foundation force field for cross-domain atomistic simulation (inorganic, molecular, surfaces, reactive chemistry).**

**Endpoint:** `POST /v1/science/predict` **Protocol:** custom science JSON  
**Input:** `elements`, `positions`, `lattice`, `head` **Output:** model-specific JSON response  
**Model path:** `models/mace-mh-1/`

### When to use

- molecular energy/force prediction

### Avoid

- NLP or vision

### Example

```bash
curl -s -X POST "$GW/v1/science/predict" -H "Content-Type: application/json" \
  -d '{"model":"mace-mh-1","demo":true}'
```

### Quirks

- water -14.22 eV + forces (omat_pbe head)
- Test status: **PASS** (READY).
- Scale-to-zero: first request may incur cold-start delay.

## `mace-mp`

**MACE-MP-0 universal ML interatomic potential covering 89 elements with small/medium/large model variants.**

**Endpoint:** `POST /v1/science/predict` **Protocol:** custom science JSON  
**Input:** `elements`, `positions`, `lattice`, `model` **Output:** model-specific JSON response  
**Model path:** `models/mace-mp/`

### When to use

- molecular energy/force prediction
- Gateway model id: `mace-mp-0`

### Avoid

- NLP or vision

### Example

```bash
curl -s -X POST "$GW/v1/science/predict" -H "Content-Type: application/json" \
  -d '{"model":"mace-mp-0","demo":true}'
```

### Quirks

- water -14.01 eV + forces; mace-mp-0 medium
- Test status: **PASS** (READY).
- Scale-to-zero: first request may incur cold-start delay.
- Use model id `mace-mp-0` in requests.

## `mace-mp-0`

**MACE-MP-0 universal ML force field (medium variant) for materials energy/forces/stress prediction.**

**Endpoint:** `POST /v1/science/energy` **Protocol:** custom science JSON  
**Input:** crystal structure (ASE dict) **Output:** energy, forces, stress  
**Model path:** `models/mace-mp-0/`

### When to use

- molecular energy/force prediction

### Avoid

- NLP or vision

### Example

```bash
curl -s -X POST "$GW/v1/science/energy" -H "Content-Type: application/json" \
  -d '{"model":"mace-mp-0"}'
```

### Quirks

- fixed pbc-zero-cell garbage + PVC model cache; water -14.15eV PASS
- Test status: **FIXED** (READY).
- Scale-to-zero: first request may incur cold-start delay.

## `maskrcnn`

**Mask R-CNN ResNet-50 FPN v2**

**Endpoint:** `POST /v1/vision/segment` **Protocol:** vision JSON (base64 image)  
**Input:** base64 `image` + optional boxes **Output:** masks  
**Model path:** `models/maskrcnn/`

### When to use

- image/medical segmentation
- Gateway model id: `maskrcnn-resnet50`

### Avoid

- text generation

### Example

```bash
curl -s -X POST "$GW/v1/vision/segment" -H "Content-Type: application/json" \
  -d '{"model":"maskrcnn-resnet50"}'
```

### Quirks

- id=maskrcnn-resnet50; person 0.999 + mask
- Test status: **PASS** (READY).
- Scale-to-zero: first request may incur cold-start delay.
- Use model id `maskrcnn-resnet50` in requests.

## `mast3r`

**MASt3R (ECCV 2024): grounding image matching in 3D with metric depth and feature matching for visual localization.**

**Endpoint:** `POST /v1/science/match` **Protocol:** custom science JSON  
**Input:** `images` **Output:** model-specific JSON response  
**Model path:** `models/mast3r/`

### When to use

- MASt3R (ECCV 2024): grounding image matching in 3D with metric depth and feature

### Avoid

- unrelated modalities or production if FAIL

### Example

```bash
curl -s -X POST "$GW/v1/science/match" -H "Content-Type: application/json" \
  -d '{"model":"mast3r"}'
```

### Quirks

- use /v1/science/match; numpy (not tensor) fix; 473 matches
- Test status: **FIXED** (READY).
- Scale-to-zero: first request may incur cold-start delay.

## `matscibert`

**MatSciBERT, BERT pre-trained on materials-science literature.**

**Endpoint:** `POST /v1/science/embed` **Protocol:** custom science JSON  
**Input:** `input` string or array **Output:** 768-dim vectors  
**Model path:** `models/matscibert/`

### When to use

- materials-science embeddings (768-dim)

### Avoid

- chat, generation, or unrelated modalities

### Example

```bash
curl -s -X POST "$GW/v1/science/embed" -H "Content-Type: application/json" \
  -d '{"model":"matscibert","text":"sample input"}'
```

### Quirks

- 768-dim (field: text)
- Test status: **PASS** (READY).
- Scale-to-zero: first request may incur cold-start delay.

## `mattergen`

> ⚠ No InferenceService — not routable via gateway; see `models.md`.

**Microsoft MatterGen diffusion model for generating novel crystal structures conditioned on composition or properties.**

**Endpoint:** `POST /v1/science/generate` **Protocol:** custom science JSON  
**Input:** `chemical_system`, `num_structures`, `checkpoint` **Output:** model-specific JSON response  
**Model path:** `models/mattergen/`

### When to use

- materials-science-specific generation

### Avoid

- general chat or unrelated tasks
- Production until cluster verification passes

### Example

```bash
curl -s -X POST "$GW/v1/science/generate" -H "Content-Type: application/json" \
  -d '{"model":"mattergen","smiles":"CCO"}'
```

### Quirks

- Knative rejects ISVC: timeoutSeconds 1500 > max 600; predictor never created; gateway 404
- Test status: **FAIL** (NO-ISVC).
- Scale-to-zero: first request may incur cold-start delay.

## `mattersim`

**Microsoft MatterSim universal atomistic ML force field for energy/forces/stress prediction and structure relaxation.**

**Endpoint:** `POST /v1/science/predict` **Protocol:** custom science JSON  
**Input:** `sequence`/`text`/`demo` **Output:** prediction JSON  
**Model path:** `models/mattersim/`

### When to use

- molecular energy/force prediction

### Avoid

- NLP or vision

### Example

```bash
curl -s -X POST "$GW/v1/science/predict" -H "Content-Type: application/json" \
  -d '{"model":"mattersim","demo":true}'
```

### Quirks

- water -14.07 eV + forces + per-atom
- Test status: **PASS** (READY).
- Scale-to-zero: first request may incur cold-start delay.

## `medcpt-article`

**MedCPT Article Encoder**

**Endpoint:** `POST /v1/embeddings` **Protocol:** OpenAI embeddings  
**Input:** `input` string or array **Output:** embedding vectors  
**Model path:** `models/medcpt-article/`

### When to use

- biomedical embeddings

### Avoid

- chat, generation, or unrelated modalities

### Example

```bash
curl -s -X POST "$GW/v1/embeddings" -H "Content-Type: application/json" \
  -d '{"model":"medcpt-article","input":"What is protein folding?"}'
```

### Quirks

- 768-dim PubMed article (recreated)
- Test status: **PASS** (READY).
- Scale-to-zero: first request may incur cold-start delay.

## `medcpt-query`

**MedCPT Query Encoder**

**Endpoint:** `POST /v1/embeddings` **Protocol:** OpenAI embeddings  
**Input:** `input` string or array **Output:** embedding vectors  
**Model path:** `models/medcpt-query/`

### When to use

- biomedical embeddings

### Avoid

- chat, generation, or unrelated modalities

### Example

```bash
curl -s -X POST "$GW/v1/embeddings" -H "Content-Type: application/json" \
  -d '{"model":"medcpt-query","input":"What is protein folding?"}'
```

### Quirks

- 768-dim PubMed query (recreated)
- Test status: **PASS** (READY).
- Scale-to-zero: first request may incur cold-start delay.

## `medgemma-27b-it`

**Google MedGemma 27B, medical multimodal (text + radiology images)**

**Endpoint:** `POST /v1/chat/completions` **Protocol:** OpenAI chat  
**Input:** `messages[]` **Output:** assistant message (+ reasoning if enabled)  
**Model path:** `models/medgemma-27b-it/`

### When to use

- instruction-following chat in biomedical domain

### Avoid

- embedding-only workloads, batch offline inference without chat API

### Example

```bash
curl -s -X POST "$GW/v1/chat/completions" -H "Content-Type: application/json" \
  -d '{"model":"medgemma-27b-it","messages":[{"role":"user","content":"Hello"}]}'
```

### Quirks

- 27B dense TP2 ~20tok/s; v0.20.2 (fixed --limit-mm-per-prompt JSON); full GPUs + --disable-custom-all-reduce; correct medical answers
- Test status: **PASS** (READY).
- Scale-to-zero: first request may incur cold-start delay.

## `medsam`

**MedSAM medical image segmentation model (SAM-based) for segmenting structures from bounding box prompts.**

**Endpoint:** `POST /v1/science/segment` **Protocol:** custom science JSON  
**Input:** `image`, `boxes` **Output:** model-specific JSON response  
**Model path:** `models/medsam/`

### When to use

- image/medical segmentation

### Avoid

- text generation

### Example

```bash
curl -s -X POST "$GW/v1/science/segment" -H "Content-Type: application/json" \
  -d '{"model":"medsam"}'
```

### Quirks

- image as HxWx3 pixel array + boxes -> masks
- Test status: **PASS** (READY).
- Scale-to-zero: first request may incur cold-start delay.

## `megadetector`

**Microsoft MegaDetector v5 wildlife camera trap detector for animals, humans, and vehicles.**

**Endpoint:** `POST /v1/detect` **Protocol:** custom JSON  
**Input:** `images`, `threshold` **Output:** model-specific JSON response  
**Model path:** `models/megadetector/`

### When to use

- object detection in images

### Avoid

- text/NLP tasks

### Example

```bash
curl -s -X POST "$GW/v1/detect" -H "Content-Type: application/json" \
  -d '{"model":"megadetector"}'
```

### Quirks

- bbox detections w/ conf
- Test status: **PASS** (READY).
- Scale-to-zero: first request may incur cold-start delay.

## `moirai`

**Salesforce Moirai base universal time-series forecasting model with zero-shot capabilities.**

**Endpoint:** `POST /v1/forecast` **Protocol:** time-series forecast JSON  
**Input:** `values`, `input`, `horizon` **Output:** model-specific JSON response  
**Model path:** `models/moirai/`

### When to use

- time-series / weather forecasting

### Avoid

- chat, static embeddings

### Example

```bash
curl -s -X POST "$GW/v1/forecast" -H "Content-Type: application/json" \
  -d '{"model":"moirai","values":[1,2,3,4,5,6,7,8],"horizon":12}'
```

### Quirks

- Salesforce Moirai base; values+horizon -> mean/quantiles; sensible forecast
- Test status: **PASS** (READY).
- Scale-to-zero: first request may incur cold-start delay.

## `moirai-large`

**Salesforce Moirai 1.1-R-Large (311M) universal zero-shot time-series forecasting model.**

**Endpoint:** `POST /v1/science/forecast` **Protocol:** custom science JSON  
**Input:** `context`, `prediction_length`, `freq`, `patch_size` **Output:** model-specific JSON response  
**Model path:** `models/moirai-large/`

### When to use

- time-series / weather forecasting

### Avoid

- chat, static embeddings

### Example

```bash
curl -s -X POST "$GW/v1/science/forecast" -H "Content-Type: application/json" \
  -d '{"model":"moirai-large","demo":true}'
```

### Quirks

- mean+samples forecast
- Test status: **PASS** (READY).
- Scale-to-zero: first request may incur cold-start delay.

## `moirai-moe`

> ⚠ Not currently serving reliably — see `models.md` (FAIL).

**Salesforce Moirai-MoE mixture-of-experts universal time-series forecasting model.**

**Endpoint:** `POST /v1/forecast` **Protocol:** time-series forecast JSON  
**Input:** `time_series`, `prediction_length`, `freq` **Output:** model-specific JSON response  
**Model path:** `models/moirai-moe/`

### When to use

- time-series / weather forecasting

### Avoid

- chat, static embeddings
- Production until cluster verification passes

### Example

```bash
curl -s -X POST "$GW/v1/forecast" -H "Content-Type: application/json" \
  -d '{"model":"moirai-moe","values":[1,2,3,4,5,6,7,8],"horizon":12}'
```

### Quirks

- handler bug: MoiraiMoEForecast.forward() missing past_observed_target/past_is_pad args - needs handler fix
- Test status: **FAIL** (READY).
- Scale-to-zero: first request may incur cold-start delay.

## `molformer`

**MoLFormer-XL molecular embeddings from SMILES (chemistry)**

**Endpoint:** `POST /v1/science/embed` **Protocol:** custom science JSON  
**Input:** `input` string or array **Output:** 768-dim vectors  
**Model path:** `models/molformer/`

### When to use

- chemistry embeddings (768-dim)

### Avoid

- chat, generation, or unrelated modalities

### Example

```bash
curl -s -X POST "$GW/v1/science/embed" -H "Content-Type: application/json" \
  -d '{"model":"molformer","text":"sample input"}'
```

### Quirks

- 768-dim (field: smiles)
- Test status: **PASS** (READY).
- Scale-to-zero: first request may incur cold-start delay.

## `moment`

**MOMENT-1-large (385M) open time-series foundation model from CMU for forecasting, classification, and anomaly detection.**

**Endpoint:** `POST /v1/forecast` **Protocol:** time-series forecast JSON  
**Input:** `time_series`, `prediction_length` **Output:** model-specific JSON response  
**Model path:** `models/moment/`

### When to use

- time-series / weather forecasting

### Avoid

- chat, static embeddings

### Example

```bash
curl -s -X POST "$GW/v1/forecast" -H "Content-Type: application/json" \
  -d '{"model":"moment","values":[1,2,3,4,5,6,7,8],"horizon":12}'
```

### Quirks

- output indexing (chan vs horizon); needs 512-len input; 96-step horizon
- Test status: **FIXED** (READY).
- Scale-to-zero: first request may incur cold-start delay.

## `multilingual-e5-small`

**Multilingual E5 Small 100-language text embeddings**

**Endpoint:** `POST /v1/embeddings` **Protocol:** OpenAI embeddings  
**Input:** `input` string or array **Output:** embedding vectors  
**Model path:** `models/multilingual-e5-small/`

### When to use

- nlp embeddings

### Avoid

- chat, generation, or unrelated modalities

### Example

```bash
curl -s -X POST "$GW/v1/embeddings" -H "Content-Type: application/json" \
  -d '{"model":"multilingual-e5-small","input":"What is protein folding?"}'
```

### Quirks

- 384-dim text embedding
- Test status: **PASS** (READY).

## `naturecode-earth`

**Naturecode Earth 10.9M forest monitoring model. Sentinel-2 time-series, forest segmentation + biomass + soil.**

**Endpoint:** `POST /v1/science/predict` **Protocol:** custom science JSON  
**Input:** `images`, `timestamps`, `latitude`, `longitude` **Output:** model-specific JSON response  
**Model path:** `models/naturecode-earth/`

### When to use

- earth-observation embeddings

### Avoid

- chat, generation, or unrelated modalities

### Example

```bash
curl -s -X POST "$GW/v1/science/predict" -H "Content-Type: application/json" \
  -d '{"model":"naturecode-earth","demo":true}'
```

### Quirks

- demo OK (seg probs); weights GATED (naturecodeproject/earth 403); needs HF access
- Test status: **DEMO** (READY).
- Scale-to-zero: first request may incur cold-start delay.

## `neuralgcm`

**Google DeepMind NeuralGCM hybrid physics/ML atmospheric model. 2.8-degree deterministic.**

**Endpoint:** `POST /v1/science/predict` **Protocol:** custom science JSON  
**Input:** `demo` **Output:** model-specific JSON response  
**Model path:** `models/neuralgcm/`

### When to use

- time-series / weather forecasting

### Avoid

- chat, static embeddings

### Example

```bash
curl -s -X POST "$GW/v1/science/predict" -H "Content-Type: application/json" \
  -d '{"model":"neuralgcm","demo":true}'
```

### Quirks

- demo mode (real ERA5 not via API by design)
- Test status: **PASS** (READY).
- Scale-to-zero: first request may incur cold-start delay.

## `nucleotide-transformer`

**InstaDeep Nucleotide Transformer v2 (500M), a DNA foundation model trained on 3,200+ genomes across multiple species.**

**Endpoint:** `POST /v1/embeddings` **Protocol:** OpenAI embeddings  
**Input:** `DNA sequence str or [str] (ACGT)` **Output:** 1024-dim vectors  
**Model path:** `models/nucleotide-transformer/`

### When to use

- genomics embeddings (1024-dim)

### Avoid

- chat, generation, or unrelated modalities

### Example

```bash
curl -s -X POST "$GW/v1/embeddings" -H "Content-Type: application/json" \
  -d '{"model":"nucleotide-transformer","input":"What is protein folding?"}'
```

### Quirks

- 1024-dim DNA
- Test status: **PASS** (READY).
- Scale-to-zero: first request may incur cold-start delay.

## `oceangpt-30b`

**OceanGPT 30B MoE, ocean science (marine biology, oceanography)**

**Endpoint:** `POST /v1/chat/completions` **Protocol:** OpenAI chat  
**Input:** `messages[]` **Output:** assistant message (+ reasoning if enabled)  
**Model path:** `models/oceangpt-30b/`

### When to use

- instruction-following chat in science domain

### Avoid

- embedding-only workloads, batch offline inference without chat API

### Example

```bash
curl -s -X POST "$GW/v1/chat/completions" -H "Content-Type: application/json" \
  -d '{"model":"oceangpt-30b","messages":[{"role":"user","content":"Hello"}]}'
```

### Quirks

- 30B-A3B MoE TP2 ~73tok/s; v0.20.2; full GPUs + --disable-custom-all-reduce (no CUDA_DISABLE_CONTROL); OpenAI+Anthropic
- Test status: **FIXED** (READY).
- Scale-to-zero: first request may incur cold-start delay.

## `omnigenome`

**RNA foundation model with sequence-structure alignment (186M)**

**Endpoint:** `POST /v1/science/predict` **Protocol:** custom science JSON  
**Input:** `sequence`, `task`, `input` **Output:** model-specific JSON response  
**Model path:** `models/omnigenome/`

### When to use

- genomics embeddings
- Gateway model id: `omnigenome-186m`

### Avoid

- chat, generation, or unrelated modalities

### Example

```bash
curl -s -X POST "$GW/v1/science/predict" -H "Content-Type: application/json" \
  -d '{"model":"omnigenome-186m","demo":true}'
```

### Quirks

- id=omnigenome-186m; RNA embedding
- Test status: **PASS** (READY).
- Scale-to-zero: first request may incur cold-start delay.
- Use model id `omnigenome-186m` in requests.

## `openbiollm-70b`

**Llama3-OpenBioLLM-70B biomedical fine-tune. Strong on bio benchmarks.**

**Endpoint:** `POST /v1/chat/completions` **Protocol:** OpenAI chat  
**Input:** `messages[]` **Output:** assistant message (+ reasoning if enabled)  
**Model path:** `models/openbiollm-70b/`

### When to use

- instruction-following chat in nlp domain

### Avoid

- embedding-only workloads, batch offline inference without chat API

### Example

```bash
curl -s -X POST "$GW/v1/chat/completions" -H "Content-Type: application/json" \
  -d '{"model":"openbiollm-70b","messages":[{"role":"user","content":"Hello"}]}'
```

### Quirks

- hemoglobin answer correct; tokenizer already Fast
- Test status: **PASS** (READY).
- Scale-to-zero: first request may incur cold-start delay.

## `pangu-weather`

**Huawei Pangu-Weather 3D neural network for global medium-range weather forecasting. ONNX, 0.25-degree.**

**Endpoint:** `POST /v1/science/forecast` **Protocol:** custom science JSON  
**Input:** `input_upper`, `input_surface`, `demo` **Output:** model-specific JSON response  
**Model path:** `models/pangu-weather/`

### When to use

- time-series / weather forecasting

### Avoid

- chat, static embeddings

### Example

```bash
curl -s -X POST "$GW/v1/science/forecast" -H "Content-Type: application/json" \
  -d '{"model":"pangu-weather","demo":true}'
```

### Quirks

- demo+real ONNX; summarized upper/surface stats (not raw 721x1440 grids)
- Test status: **FIXED** (READY).
- Scale-to-zero: first request may incur cold-start delay.

## `phi-4-reasoning`

**Microsoft Phi-4 Reasoning 14B, chain-of-thought math/science/code**

**Endpoint:** `POST /v1/chat/completions` **Protocol:** OpenAI chat  
**Input:** `messages[]` **Output:** assistant message (+ reasoning if enabled)  
**Model path:** `models/phi-4-reasoning/`

### When to use

- instruction-following chat in nlp domain

### Avoid

- embedding-only workloads, batch offline inference without chat API

### Example

```bash
curl -s -X POST "$GW/v1/chat/completions" -H "Content-Type: application/json" \
  -d '{"model":"phi-4-reasoning","messages":[{"role":"user","content":"Hello"}]}'
```

### Quirks

- Gateway budget mode maps effort→`thinking_token_budget` (0=skip CoT).
- v0.20.2 whole L40S; verified 2026-06-06.
- Test status: **PASS** (READY).
- Scale-to-zero: first request may incur cold-start delay.

## `presto`

> ⚠ Not currently serving reliably — see `models.md` (FAIL).

**Presto NASA Harvest crop mapping model**

**Endpoint:** `POST /v1/embeddings` **Protocol:** OpenAI embeddings  
**Input:** `model` + payload fields **Output:** JSON response  
**Model path:** `models/presto/`

### When to use

- earth-observation classification

### Avoid

- generation or embedding-only pipelines
- Production until cluster verification passes

### Example

```bash
curl -s -X POST "$GW/v1/embeddings" -H "Content-Type: application/json" \
  -d '{"model":"presto"}'
```

### Quirks

- band-layout mismatch - needs correct presto format
- Test status: **FAIL** (READY).
- Scale-to-zero: first request may incur cold-start delay.

## `prithvi-eo`

> ⚠ Not currently serving — see `models.md` (NOT-READY).

**IBM/NASA Prithvi-EO-2.0-300M earth observation foundation model. 6-band HLS, 3D ViT MAE.**

**Endpoint:** `POST /v1/embed` **Protocol:** custom JSON  
**Input:** `image`, `bands` **Output:** model-specific JSON response  
**Model path:** `models/prithvi-eo/`

### When to use

- earth-observation embeddings

### Avoid

- chat, generation, or unrelated modalities
- Production until cluster verification passes

### Example

```bash
curl -s -X POST "$GW/v1/embed" -H "Content-Type: application/json" \
  -d '{"model":"prithvi-eo"}'
```

### Quirks

- ISVC BlockedByFailedLoad; revision ProgressDeadlineExceeded; never scales (terratorch init)
- Test status: **FAIL** (NOT-READY).
- Scale-to-zero: first request may incur cold-start delay.

## `prithvi-wxc`

**NASA-IBM Prithvi-WxC 2.3B weather-climate foundation model. MERRA-2, 160 variables, 0.5-degree.**

**Endpoint:** `POST /v1/science/forecast` **Protocol:** custom science JSON  
**Input:** `state`, `lead_time`, `demo` **Output:** model-specific JSON response  
**Model path:** `models/prithvi-wxc/`

### When to use

- weather-climate embeddings

### Avoid

- chat, generation, or unrelated modalities

### Example

```bash
curl -s -X POST "$GW/v1/science/forecast" -H "Content-Type: application/json" \
  -d '{"model":"prithvi-wxc","demo":true}'
```

### Quirks

- demo forecast OK after unstop+cold-start (~6min); real MERRA-2 state not exercised
- Test status: **PASS** (READY).
- Scale-to-zero: first request may incur cold-start delay.

## `progen2`

> ⚠ Not currently serving — see `models.md` (NOT-READY).

**ProGen2-XLarge (6.4B) protein sequence generation model from Salesforce Research.**

**Endpoint:** `POST /v1/completions` **Protocol:** OpenAI completions  
**Input:** `prompt`, `max_tokens`, `temperature`, `num_sequences` **Output:** model-specific JSON response  
**Model path:** `models/progen2/`

### When to use

- biology-specific generation

### Avoid

- general chat or unrelated tasks
- Production until cluster verification passes

### Example

```bash
curl -s -X POST "$GW/v1/completions" -H "Content-Type: application/json" \
  -d '{"model":"progen2","prompt":"The mitochondria is"}'
```

### Quirks

- ProgressDeadlineExceeded; init download too slow, needs progress-deadline bump
- Test status: **FAIL** (NOT-READY).
- Scale-to-zero: first request may incur cold-start delay.

## `prokbert`

**ProkBERT-mini, a compact prokaryotic DNA language model for bacterial/phage genomics.**

**Endpoint:** `POST /v1/embeddings` **Protocol:** OpenAI embeddings  
**Input:** `bacterial DNA sequence str (ACGT)` **Output:** 384-dim vectors  
**Model path:** `models/prokbert/`

### When to use

- genomics embeddings (384-dim)

### Avoid

- chat, generation, or unrelated modalities

### Example

```bash
curl -s -X POST "$GW/v1/embeddings" -H "Content-Type: application/json" \
  -d '{"model":"prokbert","input":"What is protein folding?"}'
```

### Quirks

- 384-dim DNA
- Test status: **PASS** (READY).
- Scale-to-zero: first request may incur cold-start delay.

## `prostt5`

**Protein sequence to 3Di structure token translation (Rostlab)**

**Endpoint:** `POST /v1/translate` **Protocol:** custom translate JSON  
**Input:** `input`, `direction` **Output:** model-specific JSON response  
**Model path:** `models/prostt5/`

### When to use

- proteomics embeddings

### Avoid

- chat, generation, or unrelated modalities

### Example

```bash
curl -s -X POST "$GW/v1/translate" -H "Content-Type: application/json" \
  -d '{"model":"prostt5"}'
```

### Quirks

- AA->3Di structural alphabet (recreated)
- Test status: **PASS** (READY).
- Scale-to-zero: first request may incur cold-start delay.

## `proteinmpnn`

**ProteinMPNN fixed-backbone protein sequence design (Baker Lab, Science 2022)**

**Endpoint:** `POST /v1/design` **Protocol:** custom JSON  
**Input:** PDB + constraints **Output:** designed sequences  
**Model path:** `models/proteinmpnn/`

### When to use

- ProteinMPNN fixed-backbone protein sequence design (Baker Lab, Science 2022)

### Avoid

- unrelated modalities or production if FAIL

### Example

```bash
curl -s -X POST "$GW/v1/design" -H "Content-Type: application/json" \
  -d '{"model":"proteinmpnn"}'
```

### Quirks

- designs sequences from PDB w/ scores
- Test status: **PASS** (READY).
- Scale-to-zero: first request may incur cold-start delay.

## `protgpt2`

**ProtGPT2 protein sequence generation model**

**Endpoint:** `POST /v1/completions` **Protocol:** OpenAI completions  
**Input:** `prompt`, `max_tokens`, `temperature`, `num_sequences` **Output:** model-specific JSON response  
**Model path:** `models/protgpt2/`

### When to use

- biology-specific generation

### Avoid

- general chat or unrelated tasks

### Example

```bash
curl -s -X POST "$GW/v1/completions" -H "Content-Type: application/json" \
  -d '{"model":"protgpt2","prompt":"The mitochondria is"}'
```

### Quirks

- de novo protein generation (recreated)
- Test status: **PASS** (READY).
- Scale-to-zero: first request may incur cold-start delay.

## `pubmedbert`

**PubMedBERT**

**Endpoint:** `POST /v1/embeddings` **Protocol:** OpenAI embeddings  
**Input:** `input` string or array **Output:** embedding vectors  
**Model path:** `models/pubmedbert/`

### When to use

- biomedical embeddings

### Avoid

- chat, generation, or unrelated modalities

### Example

```bash
curl -s -X POST "$GW/v1/embeddings" -H "Content-Type: application/json" \
  -d '{"model":"pubmedbert","input":"What is protein folding?"}'
```

### Quirks

- embeddings PASS dim=768 (id pubmedbert)
- Test status: **PASS** (READY).
- Scale-to-zero: first request may incur cold-start delay.

## `qwen25-coder-32b`

**Qwen2.5-Coder-32B coding specialist: code gen, completion, repair.**

**Endpoint:** `POST /v1/chat/completions` **Protocol:** OpenAI chat  
**Input:** `messages[]` **Output:** assistant message (+ reasoning if enabled)  
**Model path:** `models/qwen25-coder-32b/`

### When to use

- instruction-following chat in nlp domain

### Avoid

- embedding-only workloads, batch offline inference without chat API

### Example

```bash
curl -s -X POST "$GW/v1/chat/completions" -H "Content-Type: application/json" \
  -d '{"model":"qwen25-coder-32b","messages":[{"role":"user","content":"Hello"}]}'
```

### Quirks

- is_prime() correct/idiomatic
- Test status: **PASS** (READY).
- Scale-to-zero: first request may incur cold-start delay.

## `qwen25-vl-3b`

**Qwen2.5-VL 3B, vision-language (images + video)**

**Endpoint:** `POST /v1/chat/completions` **Protocol:** OpenAI chat  
**Input:** `messages[]` **Output:** assistant message (+ reasoning if enabled)  
**Model path:** `models/qwen25-vl-3b/`

### When to use

- instruction-following chat in nlp domain

### Avoid

- embedding-only workloads, batch offline inference without chat API

### Example

```bash
curl -s -X POST "$GW/v1/chat/completions" -H "Content-Type: application/json" \
  -d '{"model":"qwen25-vl-3b","messages":[{"role":"user","content":"Hello"}]}'
```

### Quirks

- v0.20.2 (std; fixed --limit-mm-per-prompt JSON); gpumem 24GB; chat OK
- Test status: **PASS** (READY).
- Scale-to-zero: first request may incur cold-start delay.

## `qwen25-vl-72b`

**Qwen2.5-VL-72B large vision-language model for imagery/spectra/microscopy.**

**Endpoint:** `POST /v1/chat/completions` **Protocol:** OpenAI chat  
**Input:** `messages[]` **Output:** assistant message (+ reasoning if enabled)  
**Model path:** `models/qwen25-vl-72b/`

### When to use

- instruction-following chat in nlp domain

### Avoid

- embedding-only workloads, batch offline inference without chat API

### Example

```bash
curl -s -X POST "$GW/v1/chat/completions" -H "Content-Type: application/json" \
  -d '{"model":"qwen25-vl-72b","messages":[{"role":"user","content":"Hello"}]}'
```

### Quirks

- vision OK (ID image color); TP4
- Test status: **PASS** (READY).
- Scale-to-zero: first request may incur cold-start delay.

## `qwen25-vl-7b`

**Qwen2.5-VL 7B vision-language: images, video, OCR, charts, docs (multimodal)**

**Endpoint:** `POST /v1/chat/completions` **Protocol:** OpenAI chat  
**Input:** `messages[]` **Output:** assistant message (+ reasoning if enabled)  
**Model path:** `models/qwen25-vl-7b/`

### When to use

- instruction-following chat in nlp domain

### Avoid

- embedding-only workloads, batch offline inference without chat API

### Example

```bash
curl -s -X POST "$GW/v1/chat/completions" -H "Content-Type: application/json" \
  -d '{"model":"qwen25-vl-7b","messages":[{"role":"user","content":"Hello"}]}'
```

### Quirks

- OpenAI + Anthropic + vision (image_url)
- Test status: **PASS** (READY).
- Scale-to-zero: first request may incur cold-start delay.

## `qwen3-235b`

**Qwen3 235B A22B MoE (AWQ int4), tools + multilingual (4x L40S)**

**Endpoint:** `POST /v1/chat/completions` **Protocol:** OpenAI chat  
**Input:** `messages[]` **Output:** assistant message (+ reasoning if enabled)  
**Model path:** `models/qwen3-235b/`

### When to use

- instruction-following chat in nlp domain

### Avoid

- embedding-only workloads, batch offline inference without chat API

### Example

```bash
curl -s -X POST "$GW/v1/chat/completions" -H "Content-Type: application/json" \
  -d '{"model":"qwen3-235b","messages":[{"role":"user","content":"Hello"}]}'
```

### Quirks

- 235B-A22B AWQ-int4 MoE TP4 ~67tok/s; v0.20.2; ported from 232 (tclf90 repo deleted -> QuantTrio); whole node (4 GPUs, no gpumem) + --disable-custom-all-reduce + awq_marlin; correct math + tool-calling (hermes)
- Test status: **PASS** (READY).
- Scale-to-zero: first request may incur cold-start delay.

## `qwen3-32b`

**Qwen3-32B dense flagship: thinking mode, tool calling, 100+ languages.**

**Endpoint:** `POST /v1/chat/completions` **Protocol:** OpenAI chat  
**Input:** `messages[]` **Output:** assistant message (+ reasoning if enabled)  
**Model path:** `models/qwen3-32b/`

### When to use

- instruction-following chat in nlp domain

### Avoid

- embedding-only workloads, batch offline inference without chat API

### Example

```bash
curl -s -X POST "$GW/v1/chat/completions" -H "Content-Type: application/json" \
  -d '{"model":"qwen3-32b","messages":[{"role":"user","content":"Hello"}]}'
```

### Quirks

- dense flagship; thinking (qwen3 parser) + tools; 17*23=391
- Test status: **PASS** (READY).
- Scale-to-zero: first request may incur cold-start delay.

## `qwen35-122b`

**Qwen3.5 122B MoE FP8, toggleable thinking + native tools (4x L40S)**

**Endpoint:** `POST /v1/chat/completions` **Protocol:** OpenAI chat  
**Input:** `messages[]` **Output:** assistant message (+ reasoning if enabled)  
**Model path:** `models/qwen35-122b/`

### When to use

- instruction-following chat in nlp domain

### Avoid

- embedding-only workloads, batch offline inference without chat API

### Example

```bash
curl -s -X POST "$GW/v1/chat/completions" -H "Content-Type: application/json" \
  -d '{"model":"qwen35-122b","messages":[{"role":"user","content":"Hello"}]}'
```

### Quirks

- 122B FP8 MoE TP4 ~65tok/s; v0.20.2; whole node (4 GPUs, no gpumem) + --disable-custom-all-reduce; unpinned; reasoning-parser=qwen3; correct answers
- Test status: **FIXED** (READY).
- Scale-to-zero: first request may incur cold-start delay.

## `qwen36-27b`

**Qwen3.6-27B dense, novel Gated-DeltaNet hybrid arch (needs newer vLLM).**

**Endpoint:** `POST /v1/chat/completions` **Protocol:** OpenAI chat  
**Input:** `messages[]` **Output:** assistant message (+ reasoning if enabled)  
**Model path:** `models/qwen36-27b/`

### When to use

- instruction-following chat in nlp domain

### Avoid

- embedding-only workloads, batch offline inference without chat API

### Example

```bash
curl -s -X POST "$GW/v1/chat/completions" -H "Content-Type: application/json" \
  -d '{"model":"qwen36-27b","messages":[{"role":"user","content":"Hello"}]}'
```

### Quirks

- Jupiter+Ganymede; Gated-DeltaNet on vllm:latest
- Test status: **PASS** (READY).
- Scale-to-zero: first request may incur cold-start delay.

## `qwen36-35b-a3b`

**Qwen3.6-35B-A3B MoE (3B active), Gated-DeltaNet hybrid (needs newer vLLM).**

**Endpoint:** `POST /v1/chat/completions` **Protocol:** OpenAI chat  
**Input:** `messages[]` **Output:** assistant message (+ reasoning if enabled)  
**Model path:** `models/qwen36-35b-a3b/`

### When to use

- instruction-following chat in nlp domain

### Avoid

- embedding-only workloads, batch offline inference without chat API

### Example

```bash
curl -s -X POST "$GW/v1/chat/completions" -H "Content-Type: application/json" \
  -d '{"model":"qwen36-35b-a3b","messages":[{"role":"user","content":"Hello"}]}'
```

### Quirks

- s[::-1]; MoE Gated-DeltaNet on vllm:latest
- Test status: **PASS** (READY).
- Scale-to-zero: first request may incur cold-start delay.

## `qwq-32b`

**Qwen QwQ-32B reasoning model. Strong STEM, distinct style from R1 distills.**

**Endpoint:** `POST /v1/chat/completions` **Protocol:** OpenAI chat  
**Input:** `messages[]` **Output:** assistant message (+ reasoning if enabled)  
**Model path:** `models/qwq-32b/`

### When to use

- instruction-following chat in nlp domain

### Avoid

- embedding-only workloads, batch offline inference without chat API

### Example

```bash
curl -s -X POST "$GW/v1/chat/completions" -H "Content-Type: application/json" \
  -d '{"model":"qwq-32b","messages":[{"role":"user","content":"Hello"}]}'
```

### Quirks

- deepseek_r1 parser ok (QwQ has <think>); sqrt144=12
- Test status: **PASS** (READY).
- Scale-to-zero: first request may incur cold-start delay.

## `r1-distill-llama-70b`

**DeepSeek-R1 reasoning distilled into Llama-70B. Strong open chain-of-thought.**

**Endpoint:** `POST /v1/chat/completions` **Protocol:** OpenAI chat  
**Input:** `messages[]` **Output:** assistant message (+ reasoning if enabled)  
**Model path:** `models/r1-distill-llama-70b/`

### When to use

- instruction-following chat in nlp domain

### Avoid

- embedding-only workloads, batch offline inference without chat API

### Example

```bash
curl -s -X POST "$GW/v1/chat/completions" -H "Content-Type: application/json" \
  -d '{"model":"r1-distill-llama-70b","messages":[{"role":"user","content":"Hello"}]}'
```

### Quirks

- tokenizer_class patch (was Ġ/Ċ garbled); 40km/h correct; max-len 65536
- Test status: **FIXED** (READY).
- Scale-to-zero: first request may incur cold-start delay.

## `r1-distill-qwen-32b`

**DeepSeek-R1 reasoning distilled into Qwen-32B. Faster R1-grade reasoning.**

**Endpoint:** `POST /v1/chat/completions` **Protocol:** OpenAI chat  
**Input:** `messages[]` **Output:** assistant message (+ reasoning if enabled)  
**Model path:** `models/r1-distill-qwen-32b/`

### When to use

- instruction-following chat in nlp domain

### Avoid

- embedding-only workloads, batch offline inference without chat API

### Example

```bash
curl -s -X POST "$GW/v1/chat/completions" -H "Content-Type: application/json" \
  -d '{"model":"r1-distill-qwen-32b","messages":[{"role":"user","content":"Hello"}]}'
```

### Quirks

- 12^2=144; deepseek_r1 parser; max-len 65536 (KV fit)
- Test status: **PASS** (READY).
- Scale-to-zero: first request may incur cold-start delay.

## `retinanet`

**RetinaNet ResNet-50 FPN v2**

**Endpoint:** `POST /v1/vision/detect` **Protocol:** vision JSON (base64 image)  
**Input:** base64 `image` **Output:** detections[]  
**Model path:** `models/retinanet/`

### When to use

- object detection in images
- Gateway model id: `retinanet-resnet50`

### Avoid

- text/NLP tasks

### Example

```bash
curl -s -X POST "$GW/v1/vision/detect" -H "Content-Type: application/json" \
  -d '{"model":"retinanet-resnet50"}'
```

### Quirks

- id=retinanet-resnet50; bus 0.95
- Test status: **PASS** (READY).
- Scale-to-zero: first request may incur cold-start delay.
- Use model id `retinanet-resnet50` in requests.

## `rita`

**Protein generative language model (1.2B) from LightOn**

**Endpoint:** `POST /v1/science/generate` **Protocol:** custom science JSON  
**Input:** `prompt`, `max_length`, `num_sequences`, `temperature` **Output:** model-specific JSON response  
**Model path:** `models/rita/`

### When to use

- proteomics embeddings
- Gateway model id: `rita-xl`

### Avoid

- chat, generation, or unrelated modalities

### Example

```bash
curl -s -X POST "$GW/v1/science/generate" -H "Content-Type: application/json" \
  -d '{"model":"rita-xl","smiles":"CCO"}'
```

### Quirks

- protein generation: greedy + sampling produce valid sequences
- Test status: **PASS** (READY).
- Scale-to-zero: first request may incur cold-start delay.
- Use model id `rita-xl` in requests.

## `rnabert`

**RNA BERT pre-trained on structured alignments from Rfam (~86M)**

**Endpoint:** `POST /v1/science/embed` **Protocol:** custom science JSON  
**Input:** `sequence`, `sequences` **Output:** model-specific JSON response  
**Model path:** `models/rnabert/`

### When to use

- genomics embeddings

### Avoid

- chat, generation, or unrelated modalities

### Example

```bash
curl -s -X POST "$GW/v1/science/embed" -H "Content-Type: application/json" \
  -d '{"model":"rnabert","text":"sample input"}'
```

### Quirks

- 120-dim RNA (recreated)
- Test status: **PASS** (READY).
- Scale-to-zero: first request may incur cold-start delay.

## `rnafm`

**RNA foundation model for non-coding RNA (100M, RNAcentral)**

**Endpoint:** `POST /v1/science/embed` **Protocol:** custom science JSON  
**Input:** `sequence`, `sequences` **Output:** model-specific JSON response  
**Model path:** `models/rnafm/`

### When to use

- genomics embeddings

### Avoid

- chat, generation, or unrelated modalities

### Example

```bash
curl -s -X POST "$GW/v1/science/embed" -H "Content-Type: application/json" \
  -d '{"model":"rnafm","text":"sample input"}'
```

### Quirks

- 640-dim RNA (recreated)
- Test status: **PASS** (READY).
- Scale-to-zero: first request may incur cold-start delay.

## `rnamsm`

**RNA MSA transformer for secondary structure prediction (~96M)**

**Endpoint:** `POST /v1/science/embed` **Protocol:** custom science JSON  
**Input:** `sequence`, `sequences` **Output:** model-specific JSON response  
**Model path:** `models/rnamsm/`

### When to use

- genomics embeddings

### Avoid

- chat, generation, or unrelated modalities

### Example

```bash
curl -s -X POST "$GW/v1/science/embed" -H "Content-Type: application/json" \
  -d '{"model":"rnamsm","text":"sample input"}'
```

### Quirks

- 768-dim RNA (field: sequence)
- Test status: **PASS** (READY).
- Scale-to-zero: first request may incur cold-start delay.

## `sapbert`

**SapBERT**

**Endpoint:** `POST /v1/science/embed` **Protocol:** custom science JSON  
**Input:** `input` string or array **Output:** embedding vectors  
**Model path:** `models/sapbert/`

### When to use

- biomedical embeddings

### Avoid

- chat, generation, or unrelated modalities

### Example

```bash
curl -s -X POST "$GW/v1/science/embed" -H "Content-Type: application/json" \
  -d '{"model":"sapbert","text":"sample input"}'
```

### Quirks

- 768-dim biomedical
- Test status: **PASS** (READY).
- Scale-to-zero: first request may incur cold-start delay.

## `saprot-650m`

**Structure-aware protein LM combining amino acids and 3Di tokens (Westlake)**

**Endpoint:** `POST /v1/embeddings` **Protocol:** OpenAI embeddings  
**Input:** `input`, `sequences` **Output:** model-specific JSON response  
**Model path:** `models/saprot-650m/`

### When to use

- proteomics embeddings

### Avoid

- chat, generation, or unrelated modalities

### Example

```bash
curl -s -X POST "$GW/v1/embeddings" -H "Content-Type: application/json" \
  -d '{"model":"saprot-650m","input":"What is protein folding?"}'
```

### Quirks

- 1280-dim (AA+3Di tokens; recreated)
- Test status: **PASS** (READY).
- Scale-to-zero: first request may incur cold-start delay.

## `satmae`

**SatMAE ViT-Large masked autoencoder pretrained on fMoW satellite imagery. Apache 2.0.**

**Endpoint:** `POST /v1/science/embed` **Protocol:** custom science JSON  
**Input:** `image` **Output:** model-specific JSON response  
**Model path:** `models/satmae/`

### When to use

- earth-observation embeddings

### Avoid

- chat, generation, or unrelated modalities

### Example

```bash
curl -s -X POST "$GW/v1/science/embed" -H "Content-Type: application/json" \
  -d '{"model":"satmae","text":"sample input"}'
```

### Quirks

- HxW RGB -> cls embedding
- Test status: **PASS** (READY).
- Scale-to-zero: first request may incur cold-start delay.

## `scgpt`

**scGPT single-cell gene expression embeddings**

**Endpoint:** `POST /v1/embeddings` **Protocol:** OpenAI embeddings  
**Input:** `input` string or array **Output:** embedding vectors  
**Model path:** `models/scgpt/`

### When to use

- transcriptomics embeddings

### Avoid

- chat, generation, or unrelated modalities

### Example

```bash
curl -s -X POST "$GW/v1/embeddings" -H "Content-Type: application/json" \
  -d '{"model":"scgpt","input":"What is protein folding?"}'
```

### Quirks

- _encode needs src_key_padding_mask; 512-dim
- Test status: **FIXED** (READY).
- Scale-to-zero: first request may incur cold-start delay.

## `scibert`

**SciBERT**

**Endpoint:** `POST /v1/embeddings` **Protocol:** OpenAI embeddings  
**Input:** `input` string or array **Output:** embedding vectors  
**Model path:** `models/scibert/`

### When to use

- nlp embeddings
- Gateway model id: `scibert-110m`

### Avoid

- chat, generation, or unrelated modalities

### Example

```bash
curl -s -X POST "$GW/v1/embeddings" -H "Content-Type: application/json" \
  -d '{"model":"scibert-110m","input":"What is protein folding?"}'
```

### Quirks

- embeddings PASS dim=768 (id scibert-110m)
- Test status: **PASS** (READY).
- Scale-to-zero: first request may incur cold-start delay.
- Use model id `scibert-110m` in requests.

## `science-embed`

> ⚠ Not deployed — superseded or cancelled; see `models.md`.

**Legacy shared embedding backend (ESM2/NT); superseded by per-model ISVCs**

**Endpoint:** `POST /v1/embeddings` **Protocol:** OpenAI embeddings  
**Input:** `model`, `input` **Output:** model-specific JSON response  
**Model path:** `models/science-embed/`

### When to use

- internal multi-model embed backend (historical)

### Avoid

- any client use — use esm2-*/nucleotide-transformer ISVCs directly
- Production until cluster verification passes

### Example

```bash
curl -s -X POST "$GW/v1/embeddings" -H "Content-Type: application/json" \
  -d '{"model":"science-embed","input":"What is protein folding?"}'
```

### Quirks

- CANCELLED — superseded by individual esm2-*/nucleotide-transformer ISVCs.
- Was shared Deployment (not ISVC); not routable via gateway.
- Test status: **CANCELLED** (NO-ISVC).
- Scale-to-zero: first request may incur cold-start delay.

## `scincl`

**ScINCL**

**Endpoint:** `POST /v1/embeddings` **Protocol:** OpenAI embeddings  
**Input:** `input` string or array **Output:** embedding vectors  
**Model path:** `models/scincl/`

### When to use

- scientific-nlp embeddings

### Avoid

- chat, generation, or unrelated modalities

### Example

```bash
curl -s -X POST "$GW/v1/embeddings" -H "Content-Type: application/json" \
  -d '{"model":"scincl","input":"What is protein folding?"}'
```

### Quirks

- 768-dim scientific paper
- Test status: **PASS** (READY).
- Scale-to-zero: first request may incur cold-start delay.

## `seisbench`

**SeisBench PhaseNet seismic phase detection for P/S wave arrival identification in earthquake seismology.**

**Endpoint:** `POST /v1/science/detect` **Protocol:** custom science JSON  
**Input:** `waveforms`, `sampling_rate` **Output:** model-specific JSON response  
**Model path:** `models/seisbench/`

### When to use

- ecology classification

### Avoid

- generation or embedding-only pipelines

### Example

```bash
curl -s -X POST "$GW/v1/science/detect" -H "Content-Type: application/json" \
  -d '{"model":"seisbench"}'
```

### Quirks

- phasenet runs (P/S detection)
- Test status: **PASS** (READY).
- Scale-to-zero: first request may incur cold-start delay.

## `speaches`

**Speaches: STT (Whisper Large v3) + TTS (Kokoro-82M) combined deployment**

**Endpoint:** `POST /v1/audio/speech`, `POST /v1/audio/transcriptions` **Protocol:** OpenAI audio  
**Input:** `input` text + `voice` **Output:** audio bytes  
**Model path:** `models/speaches/`

### When to use

- Speaches: STT (Whisper Large v3) + TTS (Kokoro-82M) combined deployment

### Avoid

- unrelated modalities or production if FAIL

### Example

```bash
curl -s -X POST "$GW/v1/audio/speech, /v1/audio/transcriptions" -H "Content-Type: application/json" \
  -d '{"model":"speaches"}'
```

### Quirks

- DEEP-FIX: chmod HF cache (root init -> non-root container PermissionError on whisper refs). TTS Kokoro-82M (af_heart/am_michael, wav+mp3 ~9s); STT faster-whisper-large-v3 ~6s. Round-trip transcription exact (x2). Always-on Deployment (heavily used)
- Test status: **PASS** (READY).

## `specter2`

**SPECTER2**

**Endpoint:** `POST /v1/embeddings` **Protocol:** OpenAI embeddings  
**Input:** `input` string or array **Output:** embedding vectors  
**Model path:** `models/specter2/`

### When to use

- nlp embeddings
- Gateway model id: `specter2-110m`

### Avoid

- chat, generation, or unrelated modalities

### Example

```bash
curl -s -X POST "$GW/v1/embeddings" -H "Content-Type: application/json" \
  -d '{"model":"specter2-110m","input":"What is protein folding?"}'
```

### Quirks

- embeddings PASS dim=768 (id specter2-110m)
- Test status: **PASS** (READY).
- Scale-to-zero: first request may incur cold-start delay.
- Use model id `specter2-110m` in requests.

## `splicebert`

**SpliceBERT**

**Endpoint:** `POST /v1/embeddings` **Protocol:** OpenAI embeddings  
**Input:** `input` string or array **Output:** embedding vectors  
**Model path:** `models/splicebert/`

### When to use

- genomics embeddings
- Gateway model id: `splicebert-86m`

### Avoid

- chat, generation, or unrelated modalities

### Example

```bash
curl -s -X POST "$GW/v1/embeddings" -H "Content-Type: application/json" \
  -d '{"model":"splicebert-86m","input":"What is protein folding?"}'
```

### Quirks

- embeddings PASS dim=768 (id splicebert-86m)
- Test status: **PASS** (READY).
- Scale-to-zero: first request may incur cold-start delay.
- Use model id `splicebert-86m` in requests.

## `stanford-deidentifier`

**Stanford Deidentifier**

**Endpoint:** `POST /v1/science/deidentify` **Protocol:** custom science JSON  
**Input:** `model` + payload fields **Output:** JSON response  
**Model path:** `models/stanford-deidentifier/`

### When to use

- Stanford Deidentifier — clinical PHI removal via NER

### Avoid

- unrelated modalities or production if FAIL

### Example

```bash
curl -s -X POST "$GW/v1/science/deidentify" -H "Content-Type: application/json" \
  -d '{"model":"stanford-deidentifier"}'
```

### Quirks

- PHI entities (PATIENT/DATE/HOSPITAL)
- Test status: **PASS** (READY).
- Scale-to-zero: first request may incur cold-start delay.

## `sundial`

**Sundial**

**Endpoint:** `POST /v1/science/forecast` **Protocol:** custom science JSON  
**Input:** `values`/`series` + `horizon` **Output:** mean/quantiles/samples  
**Model path:** `models/sundial/`

### When to use

- time-series / weather forecasting

### Avoid

- chat, static embeddings

### Example

```bash
curl -s -X POST "$GW/v1/science/forecast" -H "Content-Type: application/json" \
  -d '{"model":"sundial","demo":true}'
```

### Quirks

- fixed input shape + pinned transformers 4.40.2; forecast+quantiles PASS
- Test status: **FIXED** (READY).
- Scale-to-zero: first request may incur cold-start delay.

## `surya`

**Surya 1.0**

**Endpoint:** `POST /v1/science/forecast` **Protocol:** custom science JSON  
**Input:** `values`/`series` + `horizon` **Output:** mean/quantiles/samples  
**Model path:** `models/surya/`

### When to use

- time-series / weather forecasting
- Gateway model id: `surya-366m`

### Avoid

- chat, static embeddings

### Example

```bash
curl -s -X POST "$GW/v1/science/forecast" -H "Content-Type: application/json" \
  -d '{"model":"surya-366m","demo":true}'
```

### Quirks

- demo forecast+flare_risk via gateway 2026-06-06; id=surya-366m
- Test status: **PASS** (READY).
- Scale-to-zero: first request may incur cold-start delay.
- Use model id `surya-366m` in requests.

## `terramind-flood`

> ⚠ Not currently serving — see `models.md` (NOT-READY).

**IBM/ESA TerraMind-base-Flood multi-sensor flood detection. Sentinel-1 + Sentinel-2 + DEM, 256x256.**

**Endpoint:** `POST /v1/science/classify` **Protocol:** custom science JSON  
**Input:** `S2L2A`, `S1RTC`, `DEM`, `demo` **Output:** model-specific JSON response  
**Model path:** `models/terramind-flood/`

### When to use

- earth-observation classification

### Avoid

- generation or embedding-only pipelines
- Production until cluster verification passes

### Example

```bash
curl -s -X POST "$GW/v1/science/classify" -H "Content-Type: application/json" \
  -d '{"model":"terramind-flood","text":"We will reach net zero by 2050."}'
```

### Quirks

- revision ProgressDeadlineExceeded; initial scale never achieved
- Test status: **FAIL** (NOT-READY).
- Scale-to-zero: first request may incur cold-start delay.

## `thor`

> ⚠ Not currently serving — see `models.md` (NOT-READY).

**Norwegian Computing Center THOR 1.0-base multi-sensor geospatial foundation model. FlexiViT-Base.**

**Endpoint:** `POST /v1/science/embed` **Protocol:** custom science JSON  
**Input:** `image`, `bands`, `patch_size`, `ground_cover` **Output:** model-specific JSON response  
**Model path:** `models/thor/`

### When to use

- time-series / weather forecasting

### Avoid

- chat, static embeddings
- Production until cluster verification passes

### Example

```bash
curl -s -X POST "$GW/v1/science/embed" -H "Content-Type: application/json" \
  -d '{"model":"thor","text":"sample input"}'
```

### Quirks

- ProgressDeadlineExceeded; init too slow (+terratorch lib check)
- Test status: **FAIL** (NOT-READY).
- Scale-to-zero: first request may incur cold-start delay.

## `time-moe`

**TimeMoE-50M mixture-of-experts universal time-series forecasting model from Tsinghua.**

**Endpoint:** `POST /v1/forecast` **Protocol:** time-series forecast JSON  
**Input:** `time_series`, `prediction_length` **Output:** model-specific JSON response  
**Model path:** `models/time-moe/`

### When to use

- time-series / weather forecasting

### Avoid

- chat, static embeddings

### Example

```bash
curl -s -X POST "$GW/v1/forecast" -H "Content-Type: application/json" \
  -d '{"model":"time-moe","values":[1,2,3,4,5,6,7,8],"horizon":12}'
```

### Quirks

- TimeMoE-50M MoE; forecast_len matches prediction_length (must be 1/96/192/336/720; 12 returns empty)
- Test status: **PASS** (READY).
- Scale-to-zero: first request may incur cold-start delay.

## `timer`

**Timer-base-84M universal time-series forecasting model (Tsinghua THUML, decoder-only transformer).**

**Endpoint:** `POST /v1/forecast` **Protocol:** time-series forecast JSON  
**Input:** `time_series`, `prediction_length` **Output:** model-specific JSON response  
**Model path:** `models/timer/`

### When to use

- time-series / weather forecasting

### Avoid

- chat, static embeddings

### Example

```bash
curl -s -X POST "$GW/v1/forecast" -H "Content-Type: application/json" \
  -d '{"model":"timer","values":[1,2,3,4,5,6,7,8],"horizon":12}'
```

### Quirks

- pinned transformers==4.40.2 (remote code uses DynamicCache.seen_tokens removed in >=4.41); forecast_len 96 PASS
- Test status: **FIXED** (READY).
- Scale-to-zero: first request may incur cold-start delay.

## `timer-xl-1b`

> ⚠ Not currently serving — see `models.md` (NOT-READY).

**Timer-XL-1B large universal time-series forecasting model (Tsinghua THUML, 1B params).**

**Endpoint:** `POST /v1/forecast` **Protocol:** time-series forecast JSON  
**Input:** `time_series`, `prediction_length` **Output:** model-specific JSON response  
**Model path:** `models/timer-xl-1b/`

### When to use

- time-series / weather forecasting

### Avoid

- chat, static embeddings
- Production until cluster verification passes

### Example

```bash
curl -s -X POST "$GW/v1/forecast" -H "Content-Type: application/json" \
  -d '{"model":"timer-xl-1b","values":[1,2,3,4,5,6,7,8],"horizon":12}'
```

### Quirks

- repo thuml/Timer-XL-1B 404 (wrong id); needs correct repo
- Test status: **FAIL** (NOT-READY).
- Scale-to-zero: first request may incur cold-start delay.

## `timesfm`

> ⚠ Not currently serving — see `models.md` (NOT-READY).

**TimesFM 2.0 500M zero-shot time series forecasting**

**Endpoint:** `POST /v1/forecast` **Protocol:** time-series forecast JSON  
**Input:** `values`/`series` + `horizon` **Output:** mean/quantiles/samples  
**Model path:** `models/timesfm/`

### When to use

- time-series / weather forecasting
- Gateway model id: `timesfm-500m`

### Avoid

- chat, static embeddings
- Production until cluster verification passes

### Example

```bash
curl -s -X POST "$GW/v1/forecast" -H "Content-Type: application/json" \
  -d '{"model":"timesfm-500m","values":[1,2,3,4,5,6,7,8],"horizon":12}'
```

### Quirks

- TimesFmModelForPrediction not importable; transformers lacks TimesFm support - needs version pin/upgrade
- Test status: **FAIL** (NOT-READY).
- Scale-to-zero: first request may incur cold-start delay.
- Use model id `timesfm-500m` in requests.

## `tinyllama`

**TinyLlama 1.1B GGUF Q4_K_M, CPU inference via llama.cpp**

**Endpoint:** `POST /v1/chat/completions` **Protocol:** OpenAI chat  
**Input:** `messages[]` **Output:** assistant message (+ reasoning if enabled)  
**Model path:** `models/tinyllama/`

### When to use

- instruction-following chat in nlp domain
- Gateway model id: `tinyllama-1.1b`

### Avoid

- embedding-only workloads, batch offline inference without chat API

### Example

```bash
curl -s -X POST "$GW/v1/chat/completions" -H "Content-Type: application/json" \
  -d '{"model":"tinyllama-1.1b","messages":[{"role":"user","content":"Hello"}]}'
```

### Quirks

- OpenAI + Anthropic PASS; streaming 500 (gateway SSE, cross-cutting)
- Test status: **PASS** (READY).
- Use model id `tinyllama-1.1b` in requests.

## `totalsegmentator`

> ⚠ Not currently serving reliably — see `models.md` (FAIL).

**TotalSegmentator: automated segmentation of 117 anatomical structures in CT scans.**

**Endpoint:** `POST /v1/science/segment` **Protocol:** custom science JSON  
**Input:** `ct_array`, `spacing`, `fast` **Output:** model-specific JSON response  
**Model path:** `models/totalsegmentator/`

### When to use

- image/medical segmentation

### Avoid

- text generation
- Production until cluster verification passes

### Example

```bash
curl -s -X POST "$GW/v1/science/segment" -H "Content-Type: application/json" \
  -d '{"model":"totalsegmentator"}'
```

### Quirks

- pod runs; POST 16³ CT → 500 `operator torchvision::nms does not exist` (torch/torchvision ABI)
- Test status: **FAIL** (READY).
- Scale-to-zero: first request may incur cold-start delay.

## `ttm`

**IBM TinyTimeMixer (TTM-R2) lightweight multi-variate time-series forecasting model (1-5M params).**

**Endpoint:** `POST /v1/science/forecast` **Protocol:** custom science JSON  
**Input:** `context`, `prediction_length`, `context_length` **Output:** model-specific JSON response  
**Model path:** `models/ttm/`

### When to use

- time-series / weather forecasting

### Avoid

- chat, static embeddings

### Example

```bash
curl -s -X POST "$GW/v1/science/forecast" -H "Content-Type: application/json" \
  -d '{"model":"ttm","demo":true}'
```

### Quirks

- past_values shape [batch,time,chan]; 96-step forecast
- Test status: **FIXED** (READY).
- Scale-to-zero: first request may incur cold-start delay.

## `uma-m`

> ⚠ Blocked (gated access / credentials) — see `models.md`.

**Universal Materials Architecture from Meta FAIR (EquiformerV2, ~1.1B params)**

**Endpoint:** `POST /v1/science/predict` **Protocol:** custom science JSON  
**Input:** `elements`, `positions`, `lattice`, `task` **Output:** model-specific JSON response  
**Model path:** `models/uma-m/`

### When to use

- molecular energy/force prediction

### Avoid

- NLP or vision
- Production until cluster verification passes

### Example

```bash
curl -s -X POST "$GW/v1/science/predict" -H "Content-Type: application/json" \
  -d '{"model":"uma-m","demo":true}'
```

### Quirks

- gated repo facebook/UMA (401) - needs Meta access grant on HF token
- Test status: **FAIL** (BLOCKED).
- Scale-to-zero: first request may incur cold-start delay.

## `xtts-v2`

**Coqui XTTS-v2 multilingual TTS + voice cloning (17 langs, GPU)**

**Endpoint:** `POST /v1/audio/speech` **Protocol:** OpenAI audio  
**Input:** `input` text + `voice` **Output:** audio bytes  
**Model path:** `models/xtts-v2/`

### When to use

- speech synthesis/transcription

### Avoid

- text-only chat

### Example

```bash
curl -s -X POST "$GW/v1/audio/speech" -H "Content-Type: application/json" \
  -d '{"model":"xtts-v2"}'
```

### Quirks

- text->WAV 155KB audio
- Test status: **PASS** (READY).

## `yolov8n`

**YOLOv8 Nano**

**Endpoint:** `POST /v1/vision/detect` **Protocol:** vision JSON (base64 image)  
**Input:** base64 `image` **Output:** detections[]  
**Model path:** `models/yolov8n/`

### When to use

- object detection in images

### Avoid

- text/NLP tasks

### Example

```bash
curl -s -X POST "$GW/v1/vision/detect" -H "Content-Type: application/json" \
  -d '{"model":"yolov8n"}'
```

### Quirks

- person 0.89 on bus.jpg
- Test status: **PASS** (READY).
- Scale-to-zero: first request may incur cold-start delay.

## `yolov8s`

**YOLOv8 Small**

**Endpoint:** `POST /v1/vision/detect` **Protocol:** vision JSON (base64 image)  
**Input:** base64 `image` **Output:** detections[]  
**Model path:** `models/yolov8s/`

### When to use

- object detection in images

### Avoid

- text/NLP tasks

### Example

```bash
curl -s -X POST "$GW/v1/vision/detect" -H "Content-Type: application/json" \
  -d '{"model":"yolov8s"}'
```

### Quirks

- person 0.91 on bus.jpg
- Test status: **PASS** (READY).
- Scale-to-zero: first request may incur cold-start delay.

## `zoobot`

**Zoobot galaxy morphology encoder (ConvNext-Nano, 640-dim)**

**Endpoint:** `POST /v1/vision/embed` **Protocol:** vision JSON (base64 image)  
**Input:** base64 `image` **Output:** embedding vector  
**Model path:** `models/zoobot/`

### When to use

- astronomy classification
- Gateway model id: `zoobot-15m`

### Avoid

- generation or embedding-only pipelines

### Example

```bash
curl -s -X POST "$GW/v1/vision/embed" -H "Content-Type: application/json" \
  -d '{"model":"zoobot-15m"}'
```

### Quirks

- id=zoobot-15m; galaxy embedding
- Test status: **PASS** (READY).
- Scale-to-zero: first request may incur cold-start delay.
- Use model id `zoobot-15m` in requests.
