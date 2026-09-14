# Working on Aleph

Aleph is an inference platform built around a FastAPI gateway, KServe/Knative,
Tyk, and Warewulf-provisioned RKE2 nodes with HAMi GPU scheduling.

Read and follow [AGENTS.md](AGENTS.md) for shared repository instructions, then
read the relevant component guide below. Check implementation and manifests
before trusting old notes. Site addresses, access commands, credentials, fleet
inventories, and rollout history belong in the operator's private working directory.

## Where to look

| Work | Guide |
|---|---|
| Overview and installation | [README](README.md), [Quickstart](QUICKSTART.md) |
| Add or update a model | [Model workflow](docs/ADD-A-MODEL.md), [card templates](models/DETAILS-TEMPLATE-LLM.md), and the model's own README/CLAUDE notes |
| Gateway implementation and tests | [Gateway reference](gateway/README.md), [gateway instructions](gateway/CLAUDE.md) |
| API behavior | [Endpoints](docs/ENDPOINTS.md) |
| Authentication and key administration | [Tyk](docs/TYK-USERS.md) |
| Usage records, retention, and metrics | [Logging and metrics](docs/LOGGING.md) |
| Overlays, site tokens, and storage bindings/recovery | [Warewulf](docs/WW-OVERLAYS.md) |
| Serving components, networking, scheduling, and lifecycle | [Kubernetes](docs/KUBERNETES.md) |
| Images, boot, systemd, GPU drivers, and RDMA | [System](docs/SYSTEM.md) |

Extend the owning guide when recording reusable findings. Keep model-specific
behavior with that model and date tested results. Avoid duplicating operational
recipes or snapshots here; do not add unrelated Slurm or CVMFS setup to this repo.

## Working rules

- Work within the authorized scope. Repository edits do not themselves authorize
  production deployment, fleet tests, or node maintenance.
- For InferenceService spec updates, delete the service, wait for old predictors
  and revisions to clear, then reapply its YAML. Never patch its spec or delete
  model PVCs. Hiding a catalog card and stopping execution are separate actions.
- Follow the model guide's test/recreate workflow. Do not claim capabilities or
  successful deployment without validation of the final configuration.
- Pin gateway releases to an explicit image version/digest. Authorized deployment
  changes must also reach the boot sources so reprovisioning preserves them.
- Preserve site tokens. Keep credentials and private records out of committed
  files, tool output, and examples; use synthetic examples for documentation.
- Validate documentation links and claims. Use the relevant component tests for
  behavior changes; documentation edits do not require deployment or inference.

## Changelog before every commit

Every repository change—including documentation, comments, and typos—requires a
**dated entry in CHANGELOG.md before committing**, staged in the same commit.
There are no exceptions for small edits. Group related edits into one logical
change and keep entries newest first. Record what changed, why, operational
impact, validation performed, and any incomplete or unverified work. Distinguish
committed changes from deployed changes and historical tests from live checks.

## Preserve README customizations

Keep the README's original header and branding: logos, title, badges, tagline,
institutional attribution, and maintainer names/links. Preserve the boxed
architecture diagram and the closing References, Support, License, and About
University of Alberta Research Computing sections, including their exact wording
and links. Update technical sections around these customizations; do not replace
the README wholesale. Change a protected part only when the user explicitly
requests that particular change. The historical baseline is commit e8e6777
(2026-09-10); retain the subsequently added Aleph logo as well.
