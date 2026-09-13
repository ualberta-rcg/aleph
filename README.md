<p align="center"><img src="./assets/aleph.png" alt="Aleph logo" width="20%" /></p>

# Aleph

Aleph serves scientific and language models through one HTTP API. Researchers can
call a model from a notebook, a batch job, or an existing API client without
managing its weights, software environment, or GPU allocation.

The model definitions cover protein structure, genomics, materials, weather,
medical imaging, and other scientific tasks, alongside chat, embeddings, vision,
and audio. The [live catalog](https://inference.vulcan.alliancecan.ca/) lists what
is available on the hosted Vulcan service. A model directory in this repository
is a deployment definition, not a guarantee that the model is currently served.

## Use Aleph

- **Browse models and examples:** [inference.vulcan.alliancecan.ca](https://inference.vulcan.alliancecan.ca/)
- **Chat in your browser:** [llm.vulcan.alliancecan.ca](https://llm.vulcan.alliancecan.ca/)
- **Get an API key and make your first request:** [Alliance Aleph guide](https://docs.alliancecan.ca/wiki/aleph)

Aleph supports OpenAI-compatible chat and embedding requests, Anthropic-compatible
messages, and model-specific science APIs. Client support depends on the selected
model's capabilities; check its card for endpoints, inputs, and limits.

Some models stay loaded; others start on demand and release GPU resources when
idle. A cold start can return a `503` with retry guidance. Capacity is shared, and
the hosted service is a proof of concept without an SLA.

## How it works

```text
Client → Traefik (TLS) → Tyk (API keys) → Aleph gateway
                                            ↓
                                  KServe / Knative → model runtime
                                            ↓
                                     HAMi GPU scheduling
```

The gateway discovers model cards from Kubernetes and routes requests to the
appropriate runtime. KServe and Knative manage serving and scaling; HAMi provides
GPU sharing. Model weights and platform data use persistent NFS storage.

The platform is provisioned with Warewulf and RKE2. This repository contains the
gateway, per-model definitions, and overlays that install the serving stack.
To deploy your own instance, start with [QUICKSTART.md](QUICKSTART.md).

## Repository guide

| Path | Contents |
|---|---|
| [gateway/](gateway/) | API gateway source, container build, and tests |
| [models/](models/) | Model manifests, cards, tests, and per-model notes |
| [ww-overlays/](ww-overlays/) | Warewulf overlays and RKE2 deployment manifests |
| [docs/](docs/) | Configuration and API reference |
| [CHANGELOG.md](CHANGELOG.md) | Change history |

| Guide | Purpose |
|---|---|
| [Quickstart](QUICKSTART.md) | Deployment requirements and setup sequence |
| [Endpoints](docs/ENDPOINTS.md) | API paths and client configuration |
| [API keys](docs/TYK-USERS.md) | Authentication and identity |
| [Logging and metrics](docs/LOGGING.md) | What is recorded, retention, and how to request usage information |
| [Overlays](docs/WW-OVERLAYS.md) | Deployment layout |
| [Site values](docs/SITE-VALUES.md) | Configure an instance |
| [Storage](docs/STORAGE-RECOVERY.md) | Fresh storage versus recovery bindings |
| [Gateway reference](gateway/README.md) | Routing and model-card behavior |
| [Add a model](docs/ADD-A-MODEL.md) | Our deployment and validation workflow |

## Support and license

For the hosted service or model requests, contact
[support@tech.alliancecan.ca](mailto:support@tech.alliancecan.ca) and mention
**Aleph on Vulcan**. For repository bugs, [open an issue](https://github.com/ualberta-rcg/aleph/issues).

Developed for research computing at the University of Alberta and AMII, within
the Digital Research Alliance of Canada. Released under the [MIT license](LICENSE).
