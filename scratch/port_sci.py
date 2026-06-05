#!/usr/bin/env python3
"""One-off: adapt fetched 232 sub-GPU model manifests for cluster 230 + write
our-schema cards. Idempotent-ish; run from repo root."""
import json, re, os

MODELS = "models"

SPEC = {
    "esm2-35m": dict(gpumem=3072, type="embedding", endpoint="/v1/embeddings",
        source="facebook/esm2_t12_35M_UR50D", license="MIT", params="35M", ctx=1024,
        emb=480, domain="proteomics", subdomain="protein-language-model",
        owned_by="Meta AI (FAIR)",
        desc="Meta ESM-2 35M, the smallest ESM-2 protein encoder. Mean-pooled 480-dim embeddings of amino-acid sequences for fast protein featurization. Served fp16 on a HAMi sub-GPU slice.",
        tags=["embedding","science","proteomics","protein","tiny","gpu"],
        infmt={"model":"esm2-35m","input":"protein sequence str or [str] (1-letter AA, <=1024)"}),
    "biobert": dict(gpumem=3072, type="embedding", endpoint="/v1/embeddings",
        source="dmis-lab/biobert-base-cased-v1.1", license="Apache-2.0", params="110M", ctx=512,
        emb=768, domain="biomedical", subdomain="biomedical-nlp", owned_by="DMIS Lab",
        desc="BioBERT base (v1.1), BERT pre-trained on PubMed abstracts + PMC full text. Produces 768-dim biomedical text embeddings for NER, relation extraction and search. Served on a HAMi sub-GPU slice.",
        tags=["embedding","science","biomedical","nlp","bert","gpu"],
        infmt={"model":"biobert","input":"biomedical text str or [str]"}),
    "nucleotide-transformer": dict(gpumem=4096, type="embedding", endpoint="/v1/embeddings",
        source="InstaDeepAI/nucleotide-transformer-v2-500m-multi-species", license="Apache-2.0",
        params="500M", ctx=1024, emb=1024, domain="genomics", subdomain="dna-language-model",
        owned_by="InstaDeepAI",
        desc="InstaDeep Nucleotide Transformer v2 (500M), a DNA foundation model trained on 3,200+ genomes across multiple species. Embeds nucleotide (ACGT) sequences (6-mer tokens) into 1024-dim vectors for genomics tasks. Served on a HAMi sub-GPU slice.",
        tags=["embedding","science","genomics","dna","gpu"],
        infmt={"model":"nucleotide-transformer","input":"DNA sequence str or [str] (ACGT)"}),
    "prokbert": dict(gpumem=3072, type="embedding", endpoint="/v1/embeddings",
        source="neuralbioinfo/prokbert-mini", license="MIT", params="20.6M", ctx=512,
        emb=768, domain="genomics", subdomain="dna-language-model", owned_by="neuralbioinfo",
        desc="ProkBERT-mini, a compact prokaryotic DNA language model for bacterial/phage genomics. Embeds nucleotide sequences into 768-dim vectors. Tiny (~20M params). Served on a HAMi sub-GPU slice.",
        tags=["embedding","science","genomics","dna","bacteria","tiny","gpu"],
        infmt={"model":"prokbert","input":"bacterial DNA sequence str (ACGT)"}),
    "matscibert": dict(gpumem=3072, type="embedding", endpoint="/v1/science/embed",
        source="m3rg-iitd/matscibert", license="MIT", params="110M", ctx=512,
        emb=768, domain="materials-science", subdomain="scientific-nlp", owned_by="m3rg-iitd",
        desc="MatSciBERT, BERT pre-trained on materials-science literature. Produces 768-dim embeddings of materials text and supports masked-token prediction. Served on a HAMi sub-GPU slice.",
        tags=["embedding","science","materials-science","nlp","bert","gpu"],
        infmt={"model":"matscibert","text":"materials-science text (str or [str])"}),
    "chemgpt-19m": dict(gpumem=3072, type="generate", endpoint="/v1/science/generate",
        source="ncfrey/ChemGPT-19M", license="MIT", params="19M", ctx=512,
        emb=0, domain="chemistry", subdomain="molecule-generation", owned_by="ncfrey",
        desc="ChemGPT-19M, a lightweight GPT-Neo style model trained on SMILES for de-novo molecule generation. Given a SMILES prefix it samples novel molecules. Tiny (~19M params). Served on a HAMi sub-GPU slice.",
        tags=["generate","science","chemistry","molecules","smiles","tiny","gpu"],
        infmt={"model":"chemgpt-19m","smiles":"SMILES prefix, e.g. 'CC'","num_return_sequences":"int (default 5)"}),
}

def transform_isvc(text, mib):
    # nodeSelector -> HAMi
    text = text.replace("nvidia.com/gpu.product: NVIDIA-L40S-SHARED", 'gpu: "on"')
    # idle retention -> 15m (both annotation spellings)
    text = re.sub(r'(scale-to-zero-pod-retention-period:\s*)"[^"]*"', r'\g<1>"15m"', text)
    text = re.sub(r'(scaleToZeroPodRetentionPeriod:\s*)"[^"]*"', r'\g<1>"15m"', text)
    # torch wheel -> cu121, drop torch>=2.6 pin
    text = text.replace("download.pytorch.org/whl/cpu", "download.pytorch.org/whl/cu121")
    text = text.replace("download.pytorch.org/whl/cu126", "download.pytorch.org/whl/cu121")
    text = text.replace("'torch>=2.6'", "torch").replace("torch>=2.6", "torch")
    # pin transformers only on pip-install lines (cu121 torch lacks float8_e8m0fnu that >=4.48 wants)
    out = []
    for line in text.split("\n"):
        if "pip install" in line and re.search(r'\btransformers\b(?![=<>])', line):
            line = re.sub(r'\btransformers\b(?![=<>])', "transformers==4.46.3", line)
        out.append(line)
    text = "\n".join(out)
    text = add_gpumem(text, mib)
    text = fix_pvc(text)
    return text

def add_gpumem(text, mib):
    out = []; in_limits = False; lim_indent = 0
    for line in text.split("\n"):
        s = line.strip()
        if s.startswith("limits:") and "{" in line and "nvidia.com/gpu" in line and "gpumem" not in line:
            out.append(line.replace('nvidia.com/gpu: "1" }', f'nvidia.com/gpu: "1", nvidia.com/gpumem: "{mib}" }}'))
            continue
        if s.startswith("limits:") and "{" not in line:
            in_limits = True; lim_indent = len(line) - len(line.lstrip()); out.append(line); continue
        if in_limits:
            ind = len(line) - len(line.lstrip()); out.append(line)
            if "nvidia.com/gpu:" in line and "gpumem" not in line:
                out.append(" " * ind + f'nvidia.com/gpumem: "{mib}"'); in_limits = False
            elif s and ind <= lim_indent:
                in_limits = False
            continue
        out.append(line)
    return "\n".join(out)

def fix_pvc(text):
    docs = text.split("\n---\n")
    for i, d in enumerate(docs):
        if "kind: PersistentVolumeClaim" not in d:
            continue
        d = d.replace("ReadWriteOnce", "ReadWriteMany")
        d = re.sub(r'storage:\s*\d+Gi', "storage: 15Gi", d)
        if "storageClassName" in d:
            d = re.sub(r'storageClassName:\s*\S+', "storageClassName: nfs-models", d)
        else:
            d = re.sub(r'(\nspec:\n)', r'\1  storageClassName: nfs-models\n', d, count=1)
        docs[i] = d
    return "\n---\n".join(docs)

def make_card(mid, sp):
    cat = {
        "description_short": sp["desc"].split(".")[0] + ".",
        "description": sp["desc"], "owned_by": sp["owned_by"], "source": sp["source"],
        "source_url": f"https://huggingface.co/{sp['source']}", "license": sp["license"],
        "parameters": sp["params"], "precision": "fp16" if mid == "esm2-35m" else "fp32",
        "framework": "transformers", "domain": sp["domain"], "subdomain": sp["subdomain"],
        "tags": sp["tags"], "gpu": True, "max_input_tokens": sp["ctx"],
        "input_format": sp["infmt"],
    }
    if sp["emb"]:
        cat["embedding_dimensions"] = sp["emb"]
        cat["pooling"] = "mean"
    card = {
        "id": mid, "type": sp["type"],
        "endpoints": {"primary": sp["endpoint"], "health": "/health"},
        "routing": {"k8s_name": mid, "no_stream": True, "upstream_model_id": None},
        "limits": {"context_window": sp["ctx"], "max_input_tokens": sp["ctx"]},
        "scaling": {"scale_to_zero": True, "min_replicas": 0, "idle_retention": "15m",
                    "cold_start_estimate": "1-2 minutes"},
        "behavior": {"supports_vision": False, "supports_tools": False,
                     "supports_system_prompt": False, "reasoning_model": False, "strips_thinking": False},
        "param_translation": {"thinking": {"mode": "none"}}, "defaults": {},
        "custom_params": {"passthrough": True}, "schema_version": 2, "catalog": cat,
    }
    body = json.dumps(card, indent=2)
    return (
        "apiVersion: v1\nkind: ConfigMap\nmetadata:\n"
        f"  name: {mid}-details\n  namespace: models\n  labels:\n    model-details: \"true\"\n"
        "data:\n  details.json: |\n" + "\n".join("    " + l for l in body.split("\n")) + "\n"
    )

for mid, sp in SPEC.items():
    p = os.path.join(MODELS, mid, "inferenceservice.yaml")
    with open(p) as f:
        t = f.read()
    with open(p, "w") as f:
        f.write(transform_isvc(t, sp["gpumem"]))
    with open(os.path.join(MODELS, mid, "details.yaml"), "w") as f:
        f.write(make_card(mid, sp))
    print(f"transformed {mid}")
print("done")
