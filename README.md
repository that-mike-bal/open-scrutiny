# OpenScrutiny — a multi-agent evaluate-then-generate platform

OpenScrutiny is a general-purpose platform for **evaluating a list of items against complex rules and then generating deliverables from the results**. You feed it items, a crew of specialized AI agents assesses each one against a configurable ruleset, and a second stage turns those assessments into structured, copy-ready output.

It ships with one fully worked example: evaluating **gTLD (domain) application strings** against the public [ICANN New gTLD Program](https://newgtlds.icann.org/) requirements, then generating draft application answers. The domain layer is intentionally swappable — the engine itself knows nothing about domains.

**Stack:** CrewAI (multi-agent orchestration) · Google Gemini · FastAPI · React + Vite + TypeScript (shadcn/ui) · Supabase (Postgres).

---

## What it does

The platform has two halves that share one database:

1. **Evaluate** — a CrewAI crew runs a set of agents and tasks against each input item. In the bundled example this is risk assessment of a domain string (technical, legal, and policy/safeguard workflows), but the same machinery evaluates anything you can describe as agents + tasks + a ruleset.
2. **Generate** — a three-tier answer-generation service takes the evaluation output plus a structured knowledge base and produces drafted deliverables (in the example, ICANN application answers), routing each field to an entity / selection / substantive handler.

```
┌──────────────┐     ┌────────────┐     ┌─────────────────────┐
│ React client │ ──▶ │  Supabase  │ ──▶ │   CrewAI service     │
│  submit items│     │  (Postgres)│     │  evaluate → generate │
│  view results│ ◀── │  results   │ ◀── │  (FastAPI)           │
└──────────────┘     └────────────┘     └─────────────────────┘
```

---

## Quick start

### Prerequisites
- Python 3.12 (CrewAI dependency)
- Node.js 18+
- A Supabase project (free tier is fine)
- A Google Gemini API key (and optionally OpenAI/others — see `env.example`)

### 1. Configure environment
```bash
cp env.example .env                 # backend: fill in Gemini + Supabase keys
cp client/env.example client/.env   # frontend: Supabase URL + anon key only
```
Credentials are read only from the environment — nothing is hardcoded, and the
Supabase **service-role key is backend-only** (never a `VITE_` variable).

### 2. Set up the database (bring your own — Supabase recommended)
The app needs a PostgreSQL database; we recommend [Supabase](https://supabase.com)
(free tier). Deploy the empty schema to a fresh project, then seed the example.
The repo ships **no data** — you bring your own database.
```bash
# In the Supabase SQL editor (or psql), run, in order:
#   db/schema.sql                        -> creates all tables (empty, per-user RLS)
#   then db/migrations/*.sql in order    -> incremental updates (see db/README.md)
python scripts/categorize_questions.py   # seed the example ruleset/questions
python scripts/setup_rag_database.py     # build the RAG index from the sample knowledge base
```
See [db/README.md](db/README.md) for the full deploy order and recommendations.

### 3. Run it
```bash
# Backend
cd crewai_service && python3 app.py

# Frontend (separate terminal)
cd client && npm install && npm run dev
```

### 4. Run the tests
```bash
pytest -q                       # backend + integration (everything mocked; placeholder keys are fine)
cd client && npm run build-strict && npx vitest run
```
`tests/live/` needs a running backend and real keys; it is excluded from the default run.

> The bundled example's retrieval features use the public *ICANN Applicant Guidebook* PDF as a reference corpus. It is not included (it's large and user-supplied); RAG degrades gracefully without it. See [db/README.md](db/README.md) for where to place it.

---

## Customize it for your own domain

The engine is domain-agnostic; the ICANN example lives entirely in configuration and data. To retarget it, grep for the markers:

```bash
grep -rn "CUSTOMIZE:" crewai_service scripts client/src
```

Each marker explains what to change. The main surfaces:

| What | Where |
|------|-------|
| Evaluation agents (the expert roles) | `crewai_service/evaluation/config/agents.yaml` |
| The ruleset (prompts, inputs, outputs per step) | `crewai_service/evaluation/config/tasks.yaml` |
| Tools agents can call | `crewai_service/evaluation/config/tools.yaml` |
| Which agents/tasks run, in what order | `crewai_service/evaluation/config/workflows.yaml` |
| Runtime knobs (memory, rate limits per environment) | `crewai_service/environment.yaml` |
| Generation agents + tasks | `crewai_service/application/config/*.yaml` |
| Generation handlers + field routing | `crewai_service/answer_generation_service.py` |
| Item/question schema + categories | `scripts/categorize_questions.py` |
| UI output types and sections | `client/src/components/CreateApplicationModal.tsx`, `client/src/lib/section-utils.ts` |

Crew assembly (`crewai_service/crew.py`) reads the YAML above — you usually retarget by editing the config and data, not the Python. `CrewBuilder()` defaults to `evaluation/config/`; the generation half is built from `application/config/`.

---

## Project structure

```
.
├── crewai_service/          # FastAPI backend + CrewAI orchestration
│   ├── evaluation/config/   # evaluation agents / tasks / tools / workflows (YAML) — the ruleset
│   ├── application/config/  # generation agents / tasks / workflows (YAML)
│   ├── environment.yaml     # shared runtime settings (memory, rate limits)
│   ├── tools/               # custom agent tools
│   ├── crew.py              # builds crews from the YAML config
│   ├── app.py               # HTTP API
│   └── answer_generation_service.py   # the generation half
├── client/                  # React + Vite + TypeScript frontend
├── db/                      # schema, migrations, and data-access layer
├── data/                    # sample reference datasets + example knowledge base
├── scripts/                 # setup and seeding scripts
└── docs/                    # API reference, architecture, deployment, DB usage notes
```

---

## Documentation

- [docs/API_REFERENCE.md](docs/API_REFERENCE.md) — HTTP API
- [docs/CLIENT_ARCHITECTURE.md](docs/CLIENT_ARCHITECTURE.md) — frontend architecture
- [docs/DEPLOY.md](docs/DEPLOY.md) — deploying (Render reference, Docker, macOS dev notes)
- [docs/SUPABASE_CLIENT_USAGE.md](docs/SUPABASE_CLIENT_USAGE.md) — database client patterns
- [db/README.md](db/README.md) — schema and setup
- [crewai_service/README.md](crewai_service/README.md) — the evaluation engine (agents, tasks, tools, workflows)

---

## License

MIT — see [LICENSE](LICENSE).

This is a portfolio/sample project. The bundled gTLD example uses the public
ICANN program as a demonstration domain; all applicant data in the repo is
fictional.
