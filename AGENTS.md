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
- Provisioning: [WW-OVERLAYS.md](docs/WW-OVERLAYS.md) and
  [SITE-VALUES.md](docs/SITE-VALUES.md).

Check code and manifests before trusting prose. Treat dated validation results
as evidence for that tested configuration, not a current fleet guarantee.

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
- Update `CHANGELOG.md` before committing a substantive change. Report what
  changed, validation performed, and anything still unverified. Do not describe
  source changes as deployed or live checks as broader validation than they are.
