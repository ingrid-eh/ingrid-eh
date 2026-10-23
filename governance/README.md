# EditHealth governance registry

This folder holds the records the governance agent (`.claude/agents/governance.md`) checks work against. They are written as YAML so that `tools/govcheck.py` and CI can test them.

| Record | Holds |
|---|---|
| [workflows/template-creation.yaml](workflows/template-creation.yaml) | Template creation workflow: steps, checks, rulings, events, open items, change history. Read it as [template-creation.md](workflows/template-creation.md), which is generated from the YAML |
| [rulings/filing-rulings-index.yaml](rulings/filing-rulings-index.yaml) | Governance rulings, each with who, when, standing and source (the `filing-rulings-index.yaml` named in EH-STD-MODS) |
| [vocabularies.yaml](vocabularies.yaml) | Controlled vocabularies |
| [naming.yaml](naming.yaml) | Naming patterns and forbidden forms |
| [locations.yaml](locations.yaml) | Where each kind of artifact lives |
| [events.yaml](events.yaml) | Events each step sets off |
| [tooling.yaml](tooling.yaml) | Which tool does which job: research in Rhizome AI, diagrams in Lucidchart, both filed in Notion |

## How a workflow change is recorded

1. Edit the step in the workflow YAML.
2. Run `python tools/govcheck.py record-change --summary "..." --ruled-by Ingrid --steps <step-id> --bump minor`. This appends a change record, raises the version, seals a hash of the steps and regenerates the page.
3. Run `python tools/govcheck.py validate`.

`validate` fails, locally and in CI, whenever the steps differ from what the last change record sealed. A workflow cannot change without the change being recorded.

## Commands

```
python tools/govcheck.py validate                 # check every record
python tools/govcheck.py show                     # print the workflow
python tools/govcheck.py names --as base-label IB-FIRST
python tools/govcheck.py block path/to/IB-FIRST.slots.md
python -m unittest discover -s tools              # tests
```

Requires Python 3.10+ and PyYAML.

## Standing

Every entry carries a standing. **Ruled** means recorded with Ingrid's name; it binds and blocks. **Proposed** means drafted but not ruled. **Observed** means a convention seen in the files. Proposed and observed entries warn and never block. The first version was rebuilt from Box on 23 October 2026, so most entries are observed until Ingrid rules on them.
