# Model deployment guidance

Follow [the deployment workflow](../docs/ADD-A-MODEL.md) and
[repository conventions](../AGENTS.md).

Read the reference for the file being prepared:

- [pvc.yaml](pvc.md): persistent storage, caches and environments.
- [inferenceservice.yaml](inferenceservice.md): runtime, setup, resources and lifecycle.
- [details.yaml](details.md): model-card fields and current gateway behavior.
- [test.py](test.md): select and adapt the existing test battery.
- [README and CLAUDE notes](model-notes.md): current status and research continuity.

Start with existing patterns and verify them for the model. Other runtimes and
layouts are possible when research establishes a need; document and test the
variation. Read the affected model's README and notes before changing it.

Keep each model's README current with deployment instructions, dated test results,
known limitations and work in progress. Preserve its PVC during service updates.
