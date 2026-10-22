# Adapting OpenScrutiny to your rulebook

This tutorial builds a second, tiny ruleset from scratch and runs it: a proposed **product name** checked against a **brand naming guideline**. Two agents, three tasks, one local-data tool, about 150 lines of YAML. The finished example lives in [`examples/brand-name-check/`](../examples/brand-name-check/), so you can read along or diff against it.

The point is the shape, not the brand rules. Once you have done this once, retargeting the full bundled example (the ICANN one in [`crewai_service/evaluation/config/`](../crewai_service/evaluation/config/)) is the same four files at larger scale.

## 0. What a ruleset is to the engine

`CrewBuilder` reads one directory, a **config tree**, holding four YAML files:

| File | Holds |
|---|---|
| `agents.yaml` | The expert roles and which tools each may call |
| `tasks.yaml` | The ruleset: one instruction and one rubric-shaped output template per step |
| `tools.yaml` | How to import each tool and who owns it |
| `workflows.yaml` | Which tasks run, in what order, with which agents |

Optionally a fifth, `environment.yaml`, overrides the shared runtime knobs. The engine knows nothing about domains; the item vocabulary is just the placeholder names you choose for your tasks. [ARCHITECTURE.md](ARCHITECTURE.md) explains what the builder does with each file.

```
examples/brand-name-check/
├── config/            agents.yaml · tasks.yaml · tools.yaml · workflows.yaml
├── brand_tools/       guideline_lookup.py   (the tool)
├── data/              brand_guideline.json  (the rulebook, as data)
└── run.py
```

## 1. Decide the item and the rulebook

Write one sentence of the form "evaluate **X** against **Y** along dimensions **Z**". Here: evaluate a *product name* against *the Northwind Goods naming guideline* for *rule compliance, distinctiveness, tone, and unfortunate meanings*.

Then split the dimensions into two kinds:

- **Mechanical rules** with data behind them (length, prohibited words, clashes with existing products). These become a **tool**, so the agent reports facts instead of guessing.
- **Interpretive judgement** (does it sound like the brand, could it be confused with a sibling product). These become task prompts with a qualitative rubric.

The ICANN example does the same split: syntax, similarity, collision, and precedent are tools; geographic, cultural, and safeguard judgement are prompts.

## 2. Put the rulebook in a data file

[`examples/brand-name-check/data/brand_guideline.json`](../examples/brand-name-check/data/brand_guideline.json) holds the mechanical rules and the product list:

```json
{
  "naming_rules": {
    "min_length": 3, "max_length": 12,
    "letters_only": true, "single_word": true,
    "must_not_start_with": ["i", "e"],
    "forbidden_suffixes": ["ly", "ify", "io"],
    "prohibited_terms": ["pro", "max", "ultra", "plus", "ai", "smart", "cloud", "lite", "premium"],
    "tone": "Warm and concrete. Names should sound like an object you could hold ..."
  },
  "existing_products": ["Atlas", "Compass", "Harbor", "Beacon", "Lantern", "Kettle"],
  "reserved_names": ["Northwind", "Nordwind", "Tradewind"]
}
```

Keeping rules in data rather than in the prompt means a brand manager can change them without touching a prompt, and the tool's output cites the guideline version.

## 3. Write the tool

A tool is a CrewAI `BaseTool` subclass with a `name`, a `description` the agent reads, an input schema, and a `_run` method. [`brand_tools/guideline_lookup.py`](../examples/brand-name-check/brand_tools/guideline_lookup.py) loads the JSON, runs each rule, and returns a JSON string with a status and a per-rule table:

```python
class BrandGuidelineLookupTool(BaseTool):
    name: str = "Brand Guideline Lookup"
    description: str = "Checks a proposed product name against the brand naming guideline ... Call with product_name."
    args_schema: type[BaseModel] = GuidelineLookupInput

    def _run(self, product_name: str) -> str:
        guideline = self._load_guideline()
        checks = []
        # ... one check per rule: {"rule", "result": "PASS"|"FAIL", "detail", "blocking"}
        status = "BLOCKED" if any(c["blocking"] and c["result"] == "FAIL" for c in checks) else ...
        return json.dumps({"product_name": product_name, "status": status, "checks": checks, ...}, indent=2)
```

Three habits from the bundled example are worth copying:

- Return **structured JSON**, and tell the agent in the task prompt to report it verbatim. Agents are good at formatting and bad at remembering numbers.
- Make the tool decide **blocking vs. soft** failures. That decision is a rule, so it belongs in code, not in the model.
- Keep tools **side-effect free** and local where possible. A tool that reads a file cannot fail because an API key is missing. Tools that call out should go through the `logged_get` / `logged_post` wrappers in `crewai_service/utils/logged_requests.py` so the audit trail can attribute the calls.
- When the rulebook is too long to put in a prompt, give agents a **lookup tool over an index** of it instead. [KNOWLEDGE_BASE.md](KNOWLEDGE_BASE.md) shows how the bundled example does that with the Applicant Guidebook and how to load your own corpus.

The tool lives in a package next to the config (`brand_tools/`). When the builder cannot import a tool module from the current `sys.path`, it retries with the config tree's parent directory added, so `module: brand_tools.guideline_lookup` resolves without any `PYTHONPATH` setup.

## 4. Declare the tool

[`config/tools.yaml`](../examples/brand-name-check/config/tools.yaml):

```yaml
brand_guideline_lookup:
  name: "Brand Guideline Lookup"
  class: "BrandGuidelineLookupTool"
  module: "brand_tools.guideline_lookup"
  primary_agent: brand_guardian
  access_pattern: "exclusive"
  data_sources: ["data/brand_guideline.json"]
```

Only `module` and `class` (and an optional `args` mapping passed to the constructor) are enforced. `primary_agent`, `access_pattern`, and `data_sources` are declarative: they record who owns the tool so the ownership model is reviewable in a diff.

## 5. Declare the agents

[`config/agents.yaml`](../examples/brand-name-check/config/agents.yaml) has two roles. The guardian owns the tool and reports facts; the reviewer has no tools and judges:

```yaml
brand_guardian:
  role: "Brand Guideline Guardian"
  goal: "Check the proposed name '{product_name}' against every mechanical rule ... and report the tool's findings exactly."
  backstory: |
    You keep the Northwind Goods naming guideline. You never guess: you run the
    Brand Guideline Lookup tool and report what it returns, rule by rule. ...
  tool_ownership: "exclusive"
  tools: [brand_guideline_lookup]
  context_producer: ["guideline_check_results"]
  memory: false
  max_rpm: 10

naming_reviewer:
  role: "Naming Reviewer"
  goal: "Judge whether '{product_name}' is distinctive, pronounceable, on-tone for the brand, ..."
  backstory: |
    You have named consumer products for years. You take the guideline check as given ...
  tool_ownership: "none"
  tools: []
  context_consumer: ["guideline_check_results"]
  memory: false
  max_rpm: 10
```

`tools` is the enforced list. `tool_ownership`, `context_producer`, and `context_consumer` document the dependency graph; keep them accurate because they are what a reviewer reads. Set `memory: false` unless you have a reason to let one item's findings influence the next; the shared `environment.yaml` also forces memory off per environment.

Every agent gets a model from `get_model_for_agent(agent_key)` in [`crewai_service/utils/model_config.py`](../crewai_service/utils/model_config.py). Unknown keys get the default (Gemini 2.5 Flash, or GPT-4o when no Gemini key is set), so a new tree runs as-is. Add a mapping entry when a role needs a stronger or cheaper model.

## 6. Write the tasks

[`config/tasks.yaml`](../examples/brand-name-check/config/tasks.yaml) is the ruleset. Each task has a `description` (what to do), an `expected_output` (the rubric-shaped template to fill), the `agent` that runs it, and the earlier tasks whose output it should see as `context`.

The first task is tool-backed and strict about provenance:

```yaml
guideline_compliance_check:
  description: |
    Check the proposed product name '{product_name}' (a {category}) against the
    brand naming guideline.
    1. Call the "Brand Guideline Lookup" tool with product_name '{product_name}'.
    2. Report every check the tool returns, with its PASS/FAIL result and detail.
    3. Do not add rules of your own and do not soften a FAIL.
  expected_output: |
    # Guideline Compliance: {product_name}
    **STATUS:** PASS / FLAGGED / BLOCKED  (copy the tool's status)
    ## Rule-by-rule results
    | Rule | Result | Detail |
    ...
  agent: brand_guardian
```

The second is interpretive and uses a qualitative scale with an explicit tie-break rule:

```yaml
distinctiveness_review:
  description: |
    ... Rate each dimension on the qualitative scale Minimal / Low / Moderate /
    Concerning / High risk. Do not compute an overall number. When in doubt
    between two adjacent levels, choose the more cautious one and say why.
  expected_output: |
    # Distinctiveness Review: {product_name}
    **STATUS:** CLEAR / FLAGGED / HIGH RISK
    ## Findings
    - **Distinctiveness**: [level] — [specific products or reasons]
    ...
  agent: naming_reviewer
  context:
    - guideline_compliance_check
```

The third is the gut check: a tiny rubric that reviews the other two for logic, consistency, and completeness and is told not to redo the analysis.

Placeholders are whatever you name them: `{product_name}` and `{category}` here. Only the keys you pass as `inputs` are substituted, so JSON examples in prompts are safe. `context` is optional: a task that declares none receives every earlier task's output in a sequential crew, so declare it when a task should see only specific outputs. Two rubric rules carried over from the bundled example: open every output with a `STATUS:` line from a fixed vocabulary, and let a tool decide anything a tool can decide.

## 7. Define the workflow

[`config/workflows.yaml`](../examples/brand-name-check/config/workflows.yaml):

```yaml
brand_name_check:
  name: "Brand Name Check"
  agents: [brand_guardian, naming_reviewer]
  tasks: [guideline_compliance_check, distinctiveness_review, naming_gut_check]
  process: "sequential"
  memory: false
  max_rpm: 10
  max_execution_time: 300
```

Order the tasks cheapest first. A blocking failure in the tool-backed step is visible before any judgement work happens; the ICANN example runs technical before legal for the same reason.

## 8. Build it and run it

Point the builder at the tree. From the repo root, with placeholder keys, this builds without any network call:

```python
from crewai_service.crew import CrewBuilder

builder = CrewBuilder("examples/brand-name-check/config")
print(builder.validate_workflow("brand_name_check"))   # {'valid': True, 'errors': [], 'warnings': []}

crew = builder.build_crew("brand_name_check", {"product_name": "Lumen", "category": "desk lamp"})
len(crew.agents), len(crew.tasks)                       # (2, 3)
[t.name for t in crew.agents[0].tools]                  # ['Brand Guideline Lookup']
```

To run it for real, set `GEMINI_API_KEY` and use the example's runner, which calls `kickoff_and_get_results` and prints each task's output:

```bash
python examples/brand-name-check/run.py Lumen --category "desk lamp"
```

Try `AtlasPro` to see the tool block on a prohibited term and an overlap with an existing product, or `Emberly` to see soft rules produce a `FLAGGED` status that the reviewer then has to weigh.

[`tests/backend/crew/test_brand_name_example.py`](../tests/backend/crew/test_brand_name_example.py) checks the build and the tool and runs in the default `pytest -q`. Copy it when you add a tree of your own: a ruleset that cannot build is the most common way an adaptation breaks.

## 9. Going further

The tutorial above covers the engine. The rest of the repository has a few seams marked `CUSTOMIZE:` where the bundled example's vocabulary appears:

```bash
grep -rn "CUSTOMIZE:" crewai_service scripts client/src
```

| To get | Change |
|---|---|
| Your workflows through the HTTP API and the single-threaded queue | `run_sequential_workflows` in `crewai_service/app.py`: the workflow names and the input keys it passes (`tld_string`, `use_case`) |
| Your tasks in the narrative audit log | `TASK_METADATA` in `crewai_service/utils/audit_log_generator.py` |
| Different models per role | the mapping in `crewai_service/utils/model_config.py` |
| A synthesised report over all workflows | `crewai_service/prompts/gemini_report_prompt.txt` (categories and levels) |
| Drafted deliverables from the findings | the handlers and field routing in `crewai_service/answer_generation_service.py`, and the item schema seeded by `scripts/categorize_questions.py` |
| Fast client-side gates and UI labels | `client/src/lib/binaryCompliance.ts`, `client/src/lib/section-utils.ts`, `client/src/components/CreateApplicationModal.tsx` |

Result classification (`_classify_result_status`) and the confidence score are vocabulary-based: if your rubrics use `STATUS: PASS / FLAGGED / BLOCKED` and the risk words `LOW RISK` / `MEDIUM RISK` / `HIGH RISK`, they work unchanged.
