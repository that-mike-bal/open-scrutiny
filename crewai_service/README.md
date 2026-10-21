# Evaluation engine (`crewai_service/`)

FastAPI service that builds CrewAI crews from YAML and runs them against each submitted item. In the bundled example the item is a proposed gTLD string and the rulebook is the ICANN New gTLD Program; the engine itself does not know that.

## How a crew is assembled

`crew.py` (`CrewBuilder`) reads four files from a config tree and turns them into a `Crew`:

| File | Defines |
|---|---|
| `agents.yaml` | The expert roles: role, goal, backstory, which tools each may call, time/iteration limits |
| `tasks.yaml` | **The ruleset.** One entry per evaluation step: the instruction (`description`) and the rubric-shaped report the agent must produce (`expected_output`), plus which agent runs it |
| `tools.yaml` | Tool catalogue: a `class` + `module` per tool, which agent owns it, and its access pattern (`exclusive`, `primary`, `shared_context_with_validation`, …) |
| `workflows.yaml` | Named workflows: the ordered list of tasks and the agent for each, process type, memory/rate-limit settings |

Two config trees exist:

- `evaluation/config/` — the evaluation ruleset. **This is what `CrewBuilder()` loads by default** and what the evaluation endpoints run.
- `application/config/` — the generation half (turning evaluation output plus a knowledge base into drafted deliverables).

`environment.yaml` (one level up, shared by both trees) holds per-environment runtime knobs: memory on/off, rate limits, timeouts. A tree can override it with its own `environment.yaml`.

Task descriptions may use `{tld_string}` and `{use_case}`; only those two placeholders are substituted, so JSON examples with braces are safe.

## The bundled example: three evaluation workflows

Each workflow is a sequential crew. Memory is disabled everywhere so one item's context never leaks into the next.

| Workflow | Tasks | Agents | Tools |
|---|---|---|---|
| `technical_risk_assessment` | DNS stability review → similarity analysis → name-collision assessment → technical gut check | string analyst, collision analyst, validator | string analyzer, similarity analyzer, magnitude collision checker, guidebook search |
| `legal_risk_assessment` | deep-research legal assessment → legal risk validation → legal gut check | legal & IP risk analyst | Deep Research legal analyzer (Gemini Deep Research), guidebook search |
| `policy_safeguard_review` | geographic name assessment → safeguard assessment → GAC risk analysis → policy gut check | GAC safeguard risk analyst | web search, GAC precedent database, similarity analyzer, guidebook search |

Every workflow ends in a **gut check**: a short task whose only job is to catch contradictions, unsupported claims, and missing sections in the preceding analysis. A dedicated **validator** agent cross-references technical findings against the local datasets.

Results are classified (`_classify_result_status` in `app.py`) into `CLEAR` / `PASS` / `FLAGGED` / `FAIL` / `REVIEW_REQUIRED`, given a 0–1 confidence score from the tool-execution record, and stored per task in `task_executions` with the full API-call log.

## Request flow

```
POST /api/evaluations/auto-submit  {"tld_string": "example", "use_case": "..."}
        │  409 if an evaluation is already running (single-threaded by design)
        ▼
run_sequential_workflows()  → technical → legal → policy   (one crew each)
        │  each task result written to task_executions as it completes
        ▼
report generation (Gemini, GPT-4o fallback) → tld_strings.generated_report
```

Status and results: `GET /evaluations/{id}/workflows`, `GET /evaluations/{tld_string}`, `GET /api/evaluations/{id}/audit`. Full list in [docs/API_REFERENCE.md](../docs/API_REFERENCE.md).

## Running it

```bash
cp env.example .env          # Gemini + Supabase keys; everything is env-only
python3 -m uvicorn crewai_service.app:app --reload --port 8000
curl http://localhost:8000/health
```

## Layout

```
crewai_service/
├── app.py                        # HTTP API + workflow orchestration
├── crew.py                       # CrewBuilder: YAML → Crew
├── environment.yaml              # shared runtime settings
├── evaluation/config/            # agents / tasks / tools / workflows (the ruleset)
├── application/config/           # generation-side agents / tasks / workflows
├── answer_generation_service.py  # generation half (entity / selection / substantive handlers)
├── tools/                        # custom tools (string, similarity, collision, GAC, deep research, search, RAG)
├── utils/                        # model routing, API-call logging, result classification, Supabase client
└── prompts/                      # report-synthesis prompt
```

To retarget the engine, grep for `CUSTOMIZE:`; see the root README's Customize section.
