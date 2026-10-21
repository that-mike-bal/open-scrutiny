# Example: brand name check

A deliberately tiny second ruleset that proves the engine is config-driven: a proposed product name is checked against a fictional brand naming guideline by two agents, three tasks, and one local-data tool.

```
config/        agents.yaml · tasks.yaml · tools.yaml · workflows.yaml
brand_tools/   the one tool (reads data/brand_guideline.json)
data/          the guideline
run.py         builds the crew and runs it
```

```bash
python examples/brand-name-check/run.py Lumen --category "desk lamp"
```

[docs/ADAPTING.md](../../docs/ADAPTING.md) builds this example step by step and explains how to point `CrewBuilder` at it. The build (no network) is covered by `tests/backend/crew/test_brand_name_example.py`.
