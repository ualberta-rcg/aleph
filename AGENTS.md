# Working on Aleph

Aleph is a Warewulf/RKE2 inference platform with a FastAPI gateway and KServe
model deployments. Keep repository guidance portable; site access details,
credentials, inventories, and operating history belong in private working notes.

## Read what applies

- Overview and deployment: [README.md](README.md), [QUICKSTART.md](QUICKSTART.md).
- Models: [ADD-A-MODEL.md](docs/ADD-A-MODEL.md), the card templates it links to,
  and the affected model's README and implementation notes.
- Gateway: [gateway/README.md](gateway/README.md) and
  [gateway/CLAUDE.md](gateway/CLAUDE.md).
- Infrastructure: [Warewulf](docs/WW-OVERLAYS.md),
  [Kubernetes](docs/KUBERNETES.md), and [System](docs/SYSTEM.md).

Check code and manifests before trusting prose. Treat dated validation results
as evidence for that tested configuration, not a current fleet guarantee.

Read [CLAUDE.md](CLAUDE.md) for the shared operator procedures: environment, Tyk
keys, model deployment, parking/scaling, HAMi diagnostics, and usage reporting.

## Make changes

- Keep changes within the requested scope. Repository work does not by itself
  authorize production deployment, fleet tests, or node maintenance. Continue
  work already authorized in the conversation without requesting it again.
- Adapt existing model patterns and verify runtime compatibility. Describe
  capabilities and limits from tests, not assumptions.
- Never patch an InferenceService spec. For authorized updates, delete the
  service, wait for old predictors/revisions to clear, and reapply its YAML.
  Never delete model PVCs. Hiding a card and stopping a service are separate acts.
- Keep secrets out of source, output, and examples. Do not inspect private key
  files or raw user usage records to write documentation; use synthetic examples.
- Preserve site tokens in committed overlays. Static storage bindings need
  explicit review for the target data; they are not generic fresh-install values.
- Pin gateway releases to an explicit image version/digest. A production change
  must also reach its boot sources so a reboot does not revert it.
- Keep public docs brief and task-oriented. Put reusable details in `docs/` and
  link them. Do not add cluster snapshots, local addresses, or unrelated host
  software setup to the README or quickstart.

## Validate and report

- Documentation changes: check relative links, example syntax, and claims against
  the relevant implementation. Do not deploy or run inference for prose edits.
- Gateway behavior: run the relevant tests under `gateway/tests/` using the
  container workflow in `.github/workflows/deploy-gateway.yml`; add a focused
  regression check when behavior changes.
- Model changes: follow the deploy/test/recreate loop in the model guide within
  the authorized environment. Record limitations in that model's README.
- Every repository change, including documentation, comments, and typos, requires
  a dated `CHANGELOG.md` entry before committing. Include it in the same commit. Report what
  changed, validation performed, and anything still unverified. Do not describe
  source changes as deployed or live checks as broader validation than they are.

## Preserve README customizations

Keep the README's original header and branding: logos, title, badges, tagline,
institutional attribution, and maintainer names/links. Preserve the boxed text
architecture diagram and the closing References, Support, License, and About
University of Alberta Research Computing sections, including their exact wording
and links. Update technical sections around these customizations; do not replace
the README wholesale. Change a protected part only when the user explicitly
requests that particular change. The historical baseline is commit e8e6777
(2026-09-10) for the branding and closing sections; retain the subsequently added
Aleph logo. Keep the original boxed text architecture style, including the added
provisioning and serving components; do not replace it with Mermaid or an image
unless the user explicitly requests that format.

## Advanced documentation

Record reusable infrastructure findings in the guide that owns the topic:

- `docs/WW-OVERLAYS.md`: Warewulf, overlay settings, site tokens, and storage bindings.
- `docs/KUBERNETES.md`: serving components, scheduling, networking, and model lifecycle.
- `docs/SYSTEM.md`: node image integration, boot, systemd, kernel, GPU, and RDMA behavior.

Extend these guides instead of adding a separate document for each setting or
expanding the README. Link the owning source file and explain what the setting
does, why it matters, and how it was checked. Date measured findings and state
the tested scope; do not present proposals or old snapshots as verified live state.
Keep addresses, credentials, user records, and site-specific recovery details in
private operating notes. Add a dated changelog entry for documentation changes.
