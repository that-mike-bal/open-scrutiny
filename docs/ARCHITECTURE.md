# Architecture

OpenScrutiny has two halves that share one Postgres database: an **evaluate** half that runs YAML-defined CrewAI crews against each item and records what every task did, and a **generate** half that turns those findings plus a knowledge base into drafted deliverables. This document describes both, the data layer between them, the audit trail, how models are routed per agent, and the tool-ownership model the YAML declares.

![Architecture diagram](assets/architecture.svg)

For the bundled example in terms of the ICANN rulebook, see [examples/icann-gtld.md](examples/icann-gtld.md). To point the engine at a different rulebook, see [ADAPTING.md](ADAPTING.md).

## 1. The evaluate half

### Request flow

```
POST /api/evaluations/auto-submit  {"tld_string": "example", "use_case": "..."}
  │  get_server_status(): if an evaluation is RUNNING → HTTP 409, nothing is written
  │  upsert the item row in tld_strings
  ▼
run_sequential_workflows()                      (FastAPI background task)
  │  for each workflow in [technical, legal, policy]:
  │     workflow_executions.status = RUNNING
  │     crew = build_crew_for_workflow(name, inputs, config_dir=evaluation/config)
  │     clear_api_call_log(); kickoff_and_get_results(crew, inputs)
  │     extract_task_results(crew) → classify each task → task_executions rows
  │     workflow_executions.status = COMPLETED | FAILED
  ▼
generate_automatic_report()                     → tld_strings.generated_report
```

All of this lives in [`crewai_service/app.py`](../crewai_service/app.py). The queue is deliberately single-threaded: one evaluation at a time, a 409 for anyone else, and a client-side queue that retries. See the design decisions in the [README](../README.md#design-decisions).

### CrewBuilder: YAML to Crew

[`crewai_service/crew.py`](../crewai_service/crew.py) turns a config tree into a CrewAI `Crew`. A config tree is a directory holding four files:

| File | What it declares |
|---|---|
| `agents.yaml` | One entry per expert role: `role`, `goal`, `backstory`, the `tools` it may call, rate and time limits, and ownership metadata (below) |
| `tasks.yaml` | **The ruleset.** One entry per evaluation step: the `description` the agent follows, the `expected_output` template it must fill, the `agent` that runs it, and optional `context` task names |
| `tools.yaml` | The tool catalogue: a `module` and `class` to import per tool, optional constructor `args`, plus ownership metadata |
| `workflows.yaml` | Named workflows: an ordered `tasks` list, the `agents` roster, `process` (`sequential` or `hierarchical`), and crew-level `memory`, `share_crew`, `max_rpm` |

A fifth file, `environment.yaml`, holds per-environment runtime knobs (memory on or off, default rate limits, timeouts). A config tree may ship its own; otherwise the shared [`crewai_service/environment.yaml`](../crewai_service/environment.yaml) is used. Its `current_environment` key selects the active block.

`CrewBuilder(config_dir=...)` loads all of them at construction. `build_crew(workflow_name, inputs)` then:

1. **Builds agents** from the workflow's roster. Each gets an LLM from `get_model_for_agent(name)` (section 5), the tools its `agents.yaml` entry lists, `memory` from the environment override, and `max_rpm`.
2. **Validates tools.** `_validate_agent_tools` raises `ValueError` if an agent declares tools and none of them imported, since that agent could not do its job. A partial load is logged as a warning.
3. **Builds tasks** in workflow order. `{placeholders}` in `description` and `expected_output` are replaced for exactly the keys in `inputs`; other braces, such as JSON examples, are left alone. Each task binds to its `agent` by config key or role. A task that declares `context` receives exactly those earlier tasks' outputs; one that declares none is left at CrewAI's default and, in a sequential crew, receives every earlier output.
4. **Decorates binary gates** when a workflow sets `binary_gates: true` and lists `blocking_tasks`: the task description gains a "return `BINARY_GATE_RESULT: BLOCKED`" instruction and `check_for_blocking` can halt the run on that signal.
5. **Assembles the crew** with the process type, memory and sharing settings, and rate limit. Hierarchical workflows get a `manager_llm` from `get_model_by_name`.

The bundled ICANN tree is the default (`crewai_service/evaluation/config/`). Nothing in `crew.py` knows about domains; the one place the item vocabulary appears is the input keys the app passes (`tld_string`, `use_case`).

### After kickoff

`kickoff_and_get_results` runs the crew and collects each task's raw output. `extract_task_results` then reads every task's `_task_name` (set by the builder from the YAML key) and classifies the output with `_classify_result_status` (section 4). The result, the raw report, the per-task slice of the API-call log, and a confidence score are written to `task_executions`.

### Report synthesis

After the last workflow, `generate_automatic_report` sends the concatenated task outputs to Gemini with [`crewai_service/prompts/gemini_report_prompt.txt`](../crewai_service/prompts/gemini_report_prompt.txt). The prompt is alert-first and forbids an overall numeric score: each category (technical compliance, name collision, string similarity, legal and trademark, safeguard policy, geopolitical, cultural and linguistic) gets a qualitative level and its flags carry the specific conflicting string, mark, jurisdiction, or magnitude. GPT-4o is the fallback when Gemini fails.

## 2. The generate half

The generation half drafts deliverables from the evaluation findings and an applicant knowledge base. In the bundled example the deliverable is a set of answers to the ICANN application questions. It is implemented as a three-tier handler in [`crewai_service/answer_generation_service.py`](../crewai_service/answer_generation_service.py) rather than as a crew, because most fields do not need a model at all:

| Tier | Handler | What it does |
|---|---|---|
| Entity fields | `EntityFieldHandler` | Maps a question to a column on the applicant record. Zero model calls. |
| Selection fields | `SelectionFieldHandler` | Returns the allowed options plus contextual tips. Zero model calls. |
| Substantive fields | `SubstantiveAnswerGenerator` | One Gemini call per batch, with the applicant profile and the relevant evaluation task outputs as context. Questions are grouped by the task names they depend on so related answers share one call. |

`AnswerGenerationService.generate_multiple` runs the tiers in order, reports progress as it goes, and records a confidence value per answer. Retrieval over the reference corpus and knowledge base goes through `rag_search_tool.py`, which embeds the query with OpenAI `text-embedding-ada-002` and calls the `similarity_search` Postgres function over the `rag_content` table (pgvector); `scripts/setup_rag_database.py` creates both. The evaluation agents' `guidebook_search` tool reads the same table's `guidebook_section` rows with `text-embedding-3-small`; [KNOWLEDGE_BASE.md](KNOWLEDGE_BASE.md) covers loading and swapping that corpus. The YAML under `crewai_service/application/config/` documents the earlier crew-based pipeline and is kept for reference; `workflows.yaml` there says so.

The item schema the generator fills (questions, categories, field mappings) is seeded by [`scripts/categorize_questions.py`](../scripts/categorize_questions.py).

## 3. The data layer

Postgres on Supabase. [`db/schema.sql`](../db/schema.sql) creates every table; [`db/README.md`](../db/README.md) has the deploy order and column notes. The tables the engine touches most:

| Table | Role |
|---|---|
| `tld_strings` | One row per item: the string, use case, overall status, and the synthesised `generated_report` |
| `workflow_executions` | One row per item per workflow with status and timestamps |
| `task_executions` | One row per task run: `result_status`, `confidence_score`, timings, and `result_data` JSONB holding the full output, `api_call_log`, and `tool_execution_summary` |
| `task_definitions` | The task catalogue the UI joins against |
| `applicants`, `tld_applications`, `application_questions_enhanced`, `application_answers_enhanced` | The generation half's entities, questions, and drafted answers |
| `rag_content` | The knowledge base: guidebook sections for the `guidebook_search` tool, plus applicant data, question guidance, and answer templates for generation. See [KNOWLEDGE_BASE.md](KNOWLEDGE_BASE.md) |
| `rag_embeddings` | Evaluation outputs embedded for the chat panel |

Two access patterns, by design:

- **Writes and model work go through FastAPI**, which holds the service-role key.
- **The React client reads directly from Supabase** over PostgREST with the anon key. Row Level Security on `tld_strings`, `workflow_executions`, and `task_executions` scopes rows to the signed-in user, so the client can poll status and render reports without a backend round trip.

The backend has two client wrappers; [SUPABASE_CLIENT_USAGE.md](SUPABASE_CLIENT_USAGE.md) explains when to use each.

## 4. The audit trail

Every stored task answers three questions: what did the agent conclude, which external calls backed it, and how much should a reader trust it.

### API-call attribution

[`crewai_service/utils/api_call_logger.py`](../crewai_service/utils/api_call_logger.py) keeps a `ContextVar` list of call records. Tools make HTTP calls through the `logged_get` and `logged_post` wrappers in `utils/logged_requests.py`, which append `{tool_name, endpoint, method, status_code, response_time_ms, success, error, timestamp}` to the current context. `clear_api_call_log()` resets it before each workflow kicks off.

After a workflow completes:

- `compute_tool_execution_summary` aggregates calls per tool and derives an overall `data_reliability` of `FULL` (no failures), `PARTIAL`, or `NONE`.
- `partition_api_calls_by_task` splits the workflow-level log into per-task slices. Tools used by exactly one task are attributed directly. Tools shared by several tasks are split by timestamp-gap clustering, which works because tasks run sequentially. The `TOOL_CLASS_TO_SHORT_NAME` map ties a tool class to the names used in `TASK_METADATA`.

### Result classification

`_classify_result_status` in `app.py` reads the raw task output and returns one of `PASS`, `FAIL`, `BLOCKED`, `REVIEW_REQUIRED`, `CLEAR`, `LOW_RISK`, `MEDIUM_RISK`, `HIGH_RISK`. Patterns are checked in priority order:

1. Explicit failure phrases such as "unable to complete" or "I do not have access to tools" → `FAIL`.
2. Risk levels (`HIGH RISK`, `MEDIUM RISK`, `LOW RISK`).
3. `BLOCKED`.
4. Degraded-run phrases ("search bypassed", "model knowledge only", "expert review required") → `REVIEW_REQUIRED`.
5. Explicit clear signals (`RISK LEVEL: CLEAR`, `RECOMMENDATION: PROCEED`).
6. Contextual `STATUS: FAIL` / `STATUS: PASS` so "bypass" never matches "pass".
7. Substantive output with no error language → `CLEAR`; anything short and ambiguous → `REVIEW_REQUIRED`.

The ordering is the point: a run whose tool failed and whose agent then wrote a confident-sounding report is caught by step 1 or 4 before it can be marked clear.

### Confidence score

`_compute_confidence_score(result_status, tool_summary)` produces a 0–1 value stored on each task row:

| Signal | Adjustment |
|---|---|
| Baseline | 0.50 |
| Tool data reliability `FULL` / `PARTIAL` / `NONE` | +0.30 / +0.15 / −0.10 |
| Definitive status (`CLEAR`, `PASS`, `LOW_RISK`) | +0.10 |
| Definitive adverse status (`FAIL`, `HIGH_RISK`, `CRITICAL`) | +0.05 |
| `REVIEW_REQUIRED` | −0.15 |
| Every API call failed | −0.20 |

Clamped to [0, 1]. A confident adverse finding scores well; an answer produced with no working tools does not.

### Narrative audit log

[`crewai_service/utils/audit_log_generator.py`](../crewai_service/utils/audit_log_generator.py) holds `TASK_METADATA` (display name, purpose, agent, tools, expected API calls, and the checks each task performs) and renders a task-by-task narrative from the stored rows. `POST /api/evaluations/{id}/audit` generates it; `GET .../audit` and `.../audit/markdown` return it. The client's evaluation detail view renders the same data as a timeline with per-task confidence, timings, and data-reliability indicators.

## 5. Per-agent model routing

[`crewai_service/utils/model_config.py`](../crewai_service/utils/model_config.py) decides which model each agent runs on. `get_model_for_agent(agent_name)` looks the agent's config key up in a mapping and returns a configured CrewAI `LLM`:

- Two Gemini models are prepared: `gemini/gemini-2.5-flash` for extraction, analysis, and synthesis, and `gemini/gemini-2.5-pro` for heavier reasoning. The shipped mapping routes every bundled agent to Flash after Pro produced intermittent 503s under load; Pro stays wired so a single line moves an agent back.
- If no `GEMINI_API_KEY` is set, every agent falls back to `gpt-4o` and a warning is logged.
- Unknown agent names get the `default` entry, so a new config tree works without touching this file; add an entry when you want a different model for a role.
- `get_model_by_name` resolves the `manager_llm` for hierarchical workflows.
- `get_model_costs` and `estimate_workflow_cost` give rough per-workflow cost estimates from a token budget and the model split.

Credentials come only from the environment via `utils/config.py`; there is no file-based fallback.

## 6. The tool-ownership model

The YAML declares who may call what, and the audit trail reports against those declarations.

**In `agents.yaml`:**

| Key | Meaning |
|---|---|
| `tools` | The tools the builder actually loads for this agent. This list is enforced. |
| `tool_ownership` | `exclusive` (only this agent calls its tools), `primary` (owns them, may share results), `enhanced` (broad toolset for interpretive work), `validation` (uses tools only to check others), `none` (synthesiser, consumes context only) |
| `context_producer` / `context_consumer` | Named outputs this agent creates and the upstream outputs it relies on. These document the dependency graph the task `context` lists implement. |
| `conservative_bias`, `validation_mode`, `contradiction_detection`, `decision_authority` | Behavioural flags that shape the role prompt and the audit narrative |

**In `tools.yaml`:**

| Key | Meaning |
|---|---|
| `module`, `class`, `args` | How the builder imports and constructs the tool. Enforced. |
| `primary_agent`, `secondary_agents`, `validation_agent` | Who owns the tool and who checks its output |
| `access_pattern` | `exclusive`, `shared_context_with_validation` (results flow to a validator), or `shared_reference` (a read-only reference any listed agent may consult) |
| `data_sources`, `api_keys_required` | What the tool reads and what it needs configured |

The distinction worth knowing: only `tools` in `agents.yaml` and `module`/`class`/`args` in `tools.yaml` change what runs. The ownership keys are declarative. They make the intent reviewable in a diff, they drive `TASK_METADATA` and the audit narrative, and they are what a reader checks when a report cites a tool the agent should not have had. Keep the two in step: a `secondary_agents` entry in `tools.yaml` should have a matching `tools` entry in `agents.yaml`, and a task prompt should only name tools its agent loads.

Tools that do not exist in `tools.yaml` are skipped with an error in the log, and an agent whose declared tools all fail to import makes `build_crew` raise. If a config tree's tools cannot be imported from the current `sys.path`, the builder retries with the tree's parent directory added, so an example can ship its tools next to its config (see [ADAPTING.md](ADAPTING.md)).

## 7. Where the domain leaks into the engine

Being honest about the seams helps adopters. Outside the YAML and data, the bundled example shows up in:

- `app.py`: the three workflow names in `run_sequential_workflows`, the `tld_string` and `use_case` input keys, and the trademark audit log attached to the legal task.
- `utils/audit_log_generator.py`: `TASK_METADATA` is keyed by the example's task names.
- `utils/model_config.py`: the routing map lists the example's agent names (unknown names fall back to `default`).
- `client/`: labels, the local gate datasets, and the application sections.

Each is marked with a `CUSTOMIZE:` comment. [ADAPTING.md](ADAPTING.md) walks through them.
