# details.yaml Templates (v2 Schema)

Three patterns cover every model on the cluster. Copy the right one, fill in the `CHANGEME` fields.

All templates use the **v2 compact schema** — gateway reads only `id`, `type`, `endpoints`, `routing`, `limits`, `scaling`, `behavior`, `param_translation`, `defaults`. Everything else goes in `catalog` (ignored by gateway, used by UI/catalog).

- **Template A — vLLM chat/embedding LLM** (gemma-4, qwen, deepseek, etc.)
- **Template B — Custom science server** (diffdock, aurora, esmfold, etc.)
- **Template C — Embedding/rerank/audio/classification** (bge, scibert, dnabert, birdnet, etc.)

## Exemplars (real production details.yaml to study)

| Pattern | Best example | Notes |
|---|---|---|
| vLLM chat (simple) | `command-r-7b/details.yaml` | Clean v2, 6 input_map params |
| vLLM chat (tools) | `oceangpt-30b/details.yaml` | tool_choice + hermes parser |
| vLLM chat (no_stream) | `astrosage/details.yaml` | Custom transformers server |
| vLLM chat (science) | `openbiollm-70b/details.yaml` | Biomedical, temperature note |
| Completions-only | `progen2/details.yaml` | Protein gen, no chat endpoint |
| Reasoning | `phi-4-reasoning/details.yaml` | Full thinking/effort mapping |
| Complex (tools+vision) | `gpt-oss-120b/details.yaml` | Max features |
| Science (typed I/O) | `diffdock/details.yaml` | Pattern 1 input_map |
| Embedding | `esm2-150m/details.yaml` | Standard embed card |

## Gateway field reference

The gateway reads these fields from cards. Everything else is catalog/documentation:

| Field | Used for | Required |
|---|---|---|
| `id` | Model name in API requests | Yes |
| `type` | Routing: `"chat"` gates Anthropic endpoint, `"completions"` for non-chat LLMs | Yes |
| `endpoints` | Primary + health paths | Yes |
| `routing.k8s_name` | ISVC name lookup (defaults to model ID) | No |
| `routing.no_stream` | Force stream=false upstream | No |
| `routing.upstream_model_id` | Rewrite model name for backend | No |
| `behavior.*` | Feature gates (vision, tools, reasoning, system prompts) | Yes for LLMs |
| `limits.context_window` | Hard context cap | Yes |
| `limits.max_completion_tokens` | Hard output cap | Yes for LLMs |
| `scaling.scale_to_zero` | Cold-start guard (503 + ETA) | Yes |
| `scaling.idle_retention` | How long to keep pod alive | Recommended |
| `scaling.cold_start_estimate` | Human-readable ETA in 503; the **0→1 wake time after the first start** (weights/venv already cached), NOT the first-ever deploy time | Recommended |
| `defaults.chat.*` | Auto-fill missing params (temperature, max_tokens) | Recommended for LLMs |
| `defaults.meta_tasks.*` | OpenWebUI title/tags/followups | Recommended for LLMs |
| `param_translation.thinking.*` | Effort → budget mapping | Yes for reasoning models |
| `param_translation.max_tokens` | Map max_tokens field name | No |
| `custom_params.*` | Per-model param schema + passthrough | No |
| `catalog.*` | Display metadata (ignored by gateway) | Recommended |

**Important:** The gateway reads `behavior.*` (not `compatibility.*`). Do NOT use `compatibility`.

---

## Template A — vLLM Chat LLM

For models served by `vllm/vllm-openai`. This is the template used for the 8 tested models.

```yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: CHANGEME-details
  namespace: models
  labels:
    model-details: "true"
data:
  details.json: |
    {
      "id": "CHANGEME",
      "status": "production",
      "type": "chat",
      "endpoints": {
        "primary": "/v1/chat/completions",
        "health": "/v1/models"
      },
      "routing": {
        "k8s_name": "CHANGEME",
        "serialize": false,
        "no_stream": false,
        "upstream_model_id": null
      },
      "limits": {
        "context_window": CHANGEME,
        "max_completion_tokens": CHANGEME
      },
      "scaling": {
        "scale_to_zero": true,
        "min_replicas": 0,
        "idle_retention": "15m",
        "cold_start_estimate": "2-5 minutes"
      },
      "behavior": {
        "supports_vision": false,
        "supports_tools": false,
        "supports_system_prompt": true,
        "reasoning_model": false,
        "strips_thinking": false
      },
      "param_translation": {
        "thinking": {
          "mode": "none"
        }
      },
      "defaults": {
        "chat": {
          "temperature": CHANGEME,
          "max_tokens": CHANGEME
        },
        "meta_tasks": {
          "title": {"max_tokens": 80},
          "tags": {"max_tokens": 60},
          "followups": {"max_tokens": 220}
        }
      },
      "custom_params": {
        "passthrough": true
      },
      "schema_version": 2,
      "input_map": {
        "messages": {
          "type": "array",
          "required": true,
          "description": "Chat messages [{role: 'user'|'system'|'assistant', content: str}]"
        },
        "max_tokens": {
          "type": "integer",
          "required": false,
          "default": CHANGEME,
          "max": CHANGEME,
          "description": "Maximum tokens to generate"
        },
        "temperature": {
          "type": "float",
          "required": false,
          "default": CHANGEME,
          "min": 0.0,
          "max": 2.0,
          "description": "Sampling temperature"
        },
        "top_p": {
          "type": "float",
          "required": false,
          "default": 1.0,
          "description": "Nucleus sampling threshold"
        },
        "stream": {
          "type": "boolean",
          "required": false,
          "default": false,
          "description": "Enable streaming responses"
        },
        "frequency_penalty": {
          "type": "float",
          "required": false,
          "default": 0.0,
          "description": "Frequency penalty (0-2)"
        }
      },
      "output_map": {
        "id": {"type": "string", "description": "Chat completion ID"},
        "object": {"type": "string", "description": "\"chat.completion\""},
        "model": {"type": "string", "description": "Model name"},
        "choices": {"type": "array", "items": {"message": "object", "finish_reason": "string"}, "description": "Response choices"},
        "usage": {"type": "object", "description": "Token usage (prompt_tokens, completion_tokens, total_tokens)"}
      },
      "catalog": {
        "description_short": "ONE LINE — what it is, who made it, key features",
        "description": "2-4 sentences. Architecture, parameter count, quantization, context window, capabilities. License.",
        "owned_by": "CHANGEME-org",
        "source": "CHANGEME-org/CHANGEME-model",
        "source_url": "https://huggingface.co/CHANGEME-org/CHANGEME-model",
        "license": "CHANGEME",
        "parameters": "CHANGEME",
        "precision": "CHANGEME (bfloat16, fp8, awq_int4, etc.)",
        "framework": "vllm",
        "domain": "nlp",
        "subdomain": "large-language-model",
        "tags": ["chat", "llm", "CHANGEME-extra-tags"]
      }
    }
```

### Optional: Add tool calling

```json
"behavior": {
  "supports_tools": true,
  ...
},
"catalog": {
  ...
  "tags": ["chat", "llm", "tools", ...]
}
```

### Optional: Add vision/multimodal

```json
"behavior": {
  "supports_vision": true,
  ...
},
"input_map": {
  ...
  "image": {
    "type": "string",
    "required": false,
    "description": "Base64-encoded image or URL"
  }
},
"output_map": {
  "choices": {
    "description": "Response choices (may include image analysis)"
  }
}
```

### Optional: Completions-only (non-chat LLM)

For protein/sequence generation models (progen2, protgpt2) that use `/v1/completions` not `/v1/chat/completions`:

```json
"type": "completions",
"endpoints": {
  "primary": "/v1/completions",
  "health": "/v1/models"
},
"defaults": {
  "completions": {
    "temperature": 1.0,
    "max_tokens": 256
  }
},
"input_map": {
  "prompt": {
    "type": "string",
    "required": true,
    "description": "Input sequence"
  },
  "max_tokens": { ... },
  "temperature": { ... }
},
"output_map": {
  "id": {"type": "string", "description": "Completion ID"},
  "object": {"type": "string", "description": "\"text_completion\""},
  "model": {"type": "string", "description": "Model name"},
  "choices": {"type": "array", "items": {"text": "string", "finish_reason": "string"}, "description": "Generated sequences"}
}
```

The gateway rejects chat requests to `type: "completions"` models with 400.

### Optional: Reasoning/thinking with effort mapping

```json
"behavior": {
  "reasoning_model": true,
  "strips_thinking": true,
  ...
},
"param_translation": {
  "thinking": {
    "mode": "budget",
    "budget_support": true,
    "answer_reserve": 512,
    "default_effort": "medium",
    "disabled_effort": "none",
    "effort_aliases": {
      "none": "none", "minimal": "none", "disabled": "none",
      "low": "low", "medium": "medium", "med": "medium",
      "high": "high", "xhigh": "xhigh", "max": "max"
    },
    "effort_map": {
      "none":  {"thinking_token_budget": 0},
      "low":   {"thinking_token_budget": 1024},
      "medium":{"thinking_token_budget": 4096},
      "high":  {"thinking_token_budget": 12288},
      "xhigh": {"thinking_token_budget": 24576},
      "max":   {"thinking_token_budget": null}
    }
  }
},
"defaults": {
  "chat": {
    "temperature": 0.6,
    "max_tokens": 8192,
    "thinking": {"enabled": true, "effort": "medium"}
  },
  "meta_tasks": {
    "title": {"max_tokens": 80, "thinking": {"effort": "none"}},
    "tags": {"max_tokens": 60, "thinking": {"effort": "none"}},
    "followups": {"max_tokens": 220, "thinking": {"effort": "none"}}
  }
}
```

The `mode` can be:
- `"budget"` — maps effort → vLLM `thinking_token_budget` (most common)
- `"effort"` — direct `reasoning_effort` passthrough to vLLM
- `"toggle"` — inject params on/off (for models with chat_template_kwargs)
- `"none"` — no thinking support (default for non-reasoning models)

To **disable thinking** on a per-request basis, the gateway uses `disabled_effort` (typically `"none"`). Setting effort to `"none"` sets `thinking_token_budget: 0`. See `phi-4-reasoning/details.yaml` for a full working example.

### Optional: no_stream models

For models using custom transformers/llama.cpp servers that don't support streaming:

```json
"routing": {
  "no_stream": true,
  ...
}
```

The gateway forces `stream=false` upstream and returns a normal non-streaming response to the client.

### Optional: Multi-GPU (TP≥2)

Add to the ISVC `inferenceservice.yaml`, not the card. The card doesn't need `gpu_count` — that's ISVC config.

ISVC needs: `nvidia.com/gpu: "N"` (whole devices, NOT `nvidia.com/gpumem`), `shared_memory: "16Gi"`, `--tensor-parallel-size`, `--disable-custom-all-reduce`.

---

## Template B — Custom Science Server

For models with a custom FastAPI/Flask server (not vLLM). Biology, chemistry, weather, physics, etc.

```yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: CHANGEME-details
  namespace: models
  labels:
    model-details: "true"
data:
  details.json: |
    {
      "id": "CHANGEME",
      "status": "production",
      "type": "CHANGEME (predict, forecast, dock, embed, segment, classify, design, generate, detect, etc.)",
      "endpoints": {
        "primary": "/v1/science/CHANGEME",
        "health": "/health"
      },
      "routing": {
        "k8s_name": "CHANGEME",
        "no_stream": true,
        "upstream_model_id": null
      },
      "limits": {
        "context_window": 0,
        "max_input_tokens": CHANGEME
      },
      "scaling": {
        "scale_to_zero": true,
        "min_replicas": 0,
        "idle_retention": "15m",
        "cold_start_estimate": "2-5 minutes"
      },
      "behavior": {
        "supports_vision": false,
        "supports_tools": false,
        "supports_system_prompt": false,
        "reasoning_model": false,
        "strips_thinking": false
      },
      "param_translation": {
        "thinking": {"mode": "none"}
      },
      "defaults": {},
      "custom_params": {
        "passthrough": true
      },
      "schema_version": 2,
      "input_map": {CHANGEME — see input_map patterns below},
      "output_map": {CHANGEME — see output_map patterns below},
      "catalog": {
        "description_short": "ONE LINE — what it does, what domain",
        "description": "2-4 sentences. What the model predicts/classifies/generates. Input format. Key architecture. Paper reference.",
        "owned_by": "CHANGEME-org",
        "source": "CHANGEME-org/CHANGEME-model",
        "source_url": "https://huggingface.co/CHANGEME-org/CHANGEME-model",
        "license": "CHANGEME",
        "parameters": "CHANGEME",
        "precision": "CHANGEME",
        "framework": "CHANGEME (custom, transformers, torch, jax, etc.)",
        "domain": "CHANGEME (structural-biology, weather-climate, genomics, etc.)",
        "subdomain": "CHANGEME (molecular-docking, forecasting, etc.)",
        "tags": ["science", "CHANGEME-domain-tags"]
      }
    }
```

### input_map / output_map patterns

Science models have wildly different I/O. **The input_map must document exactly what the server's POST body expects**, and output_map must document what it returns. The gateway passes these through to the upstream server unchanged.

Here are the 5 real patterns used on this cluster:

#### Pattern 1 — Typed params with required/optional (most common)

Used by: diffdock, ligandmpnn, seisbench, esmfold, most prediction models.

```json
"input_map": {
  "protein_pdb": {
    "type": "string",
    "required": true,
    "description": "Protein structure in PDB format"
  },
  "ligand_smiles": {
    "type": "string",
    "required": true,
    "description": "Ligand as SMILES string"
  },
  "num_poses": {
    "type": "integer",
    "required": false,
    "default": 10,
    "description": "Number of docked poses to generate"
  }
},
"output_map": {
  "model": {"type": "string", "description": "Model name"},
  "poses": {"type": "array", "description": "Ranked poses with rank, confidence, and SDF content"}
}
```

#### Pattern 2 — Nested objects with description strings (weather/climate)

Used by: aurora, graphcast, pangu-weather, climax, neuralgcm.

```json
"input_map": {
  "surf_vars": {
    "2t": "2m temperature (K), shape [lat, lon]",
    "10u": "10m u-wind (m/s), shape [lat, lon]",
    "msl": "mean sea-level pressure (Pa), shape [lat, lon]"
  },
  "lat": "[90, ..., -90] float array",
  "lon": "[0, ..., 359.75] float array",
  "time": "ISO datetime string e.g. 2024-01-01T00:00:00"
},
"output_map": {
  "surf_vars": "same structure as input, 6h ahead",
  "step": "6h"
}
```

#### Pattern 3 — Crystal/material structure (chemistry, physics)

Used by: chgnet, mace-mp, mace-mp-0, mace-mh-1, mattersim.

```json
"input_map": {
  "structure": {
    "elements": "array of element symbols e.g. [\"Li\", \"Fe\", \"P\", \"O\"]",
    "positions": "array of [x,y,z] positions in Angstroms",
    "cell": "3x3 cell vectors",
    "pbc": "[bool, bool, bool] periodic boundary conditions"
  }
},
"output_map": {
  "energy_eV": "total potential energy in eV",
  "forces_eV_A": "per-atom forces in eV/Angstrom",
  "stress_eV_A3": "Voigt stress tensor"
}
```

#### Pattern 4 — Binary/image inputs (vision, 3D reconstruction, medical)

Used by: dust3r, mast3r, medsam, totalsegmentator, depth-anything.

```json
"input_map": {
  "images": "array of 2+ base64-encoded JPEG/PNG images",
  "output_format": "\"pointcloud\" (default) or \"depth\""
},
"output_map": {
  "pointclouds": [{"pts3d": "[[x,y,z], ...]", "confidence": "[float, ...]"}],
  "model": "dust3r"
}
```

#### Pattern 5 — Text/sequence input (restoration, classification, generation)

Used by: ithaca, climatebert, finbert, scgpt, most text-based science models.

```json
"input_map": {
  "text": {
    "type": "string",
    "required": true,
    "description": "Input text (format depends on model)"
  },
  "task": {
    "type": "string",
    "required": false,
    "description": "Task to perform (model-specific)"
  }
},
"output_map": {
  "model": {"type": "string", "description": "Model name"},
  "result": {"type": "string", "description": "Model output"}
}
```

---

## Template C — Embedding/Rerank/Audio/Classification

For embedding models, rerankers, audio classifiers, and other non-LLM models with standard OpenAI-shaped endpoints.

```yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: CHANGEME-details
  namespace: models
  labels:
    model-details: "true"
data:
  details.json: |
    {
      "id": "CHANGEME",
      "status": "production",
      "type": "CHANGEME (embed, rerank, classify, audio-classification, etc.)",
      "endpoints": {
        "primary": "/v1/CHANGEME (embeddings, rerank, science/classify, science/identify, etc.)",
        "health": "/health"
      },
      "routing": {
        "k8s_name": "CHANGEME",
        "no_stream": true,
        "upstream_model_id": null
      },
      "limits": {
        "context_window": CHANGEME,
        "max_input_tokens": CHANGEME
      },
      "scaling": {
        "scale_to_zero": true,
        "min_replicas": 0,
        "idle_retention": "15m",
        "cold_start_estimate": "1-2 minutes"
      },
      "behavior": {
        "supports_vision": false,
        "supports_tools": false,
        "supports_system_prompt": false,
        "reasoning_model": false,
        "strips_thinking": false
      },
      "param_translation": {
        "thinking": {"mode": "none"}
      },
      "defaults": {},
      "custom_params": {
        "passthrough": true
      },
      "schema_version": 2,
      "input_map": {
        "input": {
          "type": "CHANGEME (string or array)",
          "required": true,
          "description": "Text, sequence, or audio to process"
        }
      },
      "output_map": {
        "object": {"type": "string", "description": "Response type (list, embedding_result, etc.)"},
        "data": {"type": "array", "description": "Results array"},
        "model": {"type": "string", "description": "Model name"}
      },
      "catalog": {
        "description_short": "ONE LINE — what it does, dimension, domain",
        "description": "2 sentences. What it embeds/classifies, dimension, training data.",
        "owned_by": "CHANGEME-org",
        "source": "CHANGEME-org/CHANGEME-model",
        "source_url": "https://huggingface.co/CHANGEME-org/CHANGEME-model",
        "license": "CHANGEME",
        "parameters": "CHANGEME",
        "precision": "CHANGEME",
        "framework": "CHANGEME (transformers, TEI, custom, etc.)",
        "domain": "CHANGEME",
        "subdomain": "CHANGEME",
        "tags": ["CHANGEME-type-tag", "CHANGEME-domain-tags"],
        "embedding_dimensions": CHANGEME,
        "pooling": "mean"
      }
    }
```

### Reranker variant

```json
"type": "rerank",
"endpoints": {
  "primary": "/v1/rerank",
  "health": "/health"
},
"input_map": {
  "query": {"type": "string", "required": true, "description": "Search query"},
  "documents": {"type": "array", "required": true, "description": "Documents to rank"},
  "top_n": {"type": "integer", "required": false, "default": 5, "description": "Number of results"}
},
"output_map": {
  "results": {"type": "array", "description": "Ranked documents with relevance scores"},
  "model": {"type": "string", "description": "Model name"}
}
```

### Audio classification variant

```json
"type": "audio-classification",
"endpoints": {
  "primary": "/v1/science/identify",
  "health": "/health"
},
"input_map": {
  "audio": {"type": "array", "required": true, "description": "Float audio samples at specified sample rate"},
  "sample_rate": {"type": "integer", "required": false, "default": 48000, "description": "Audio sample rate in Hz"}
},
"output_map": {
  "detections": {"type": "array", "description": "Detected classes with confidence scores"},
  "model": {"type": "string", "description": "Model name"}
}
```
