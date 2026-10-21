# Documentation

Start with the root [README](../README.md): what the engine does, the bundled example, the quick start, and how to adapt it.

## Understand it

| Document | What it covers |
|---|---|
| [`ARCHITECTURE.md`](ARCHITECTURE.md) | The evaluate half, the generate half, the data layer, the audit trail (classification, confidence, API-call attribution), per-agent model routing, and the tool-ownership model |
| [`examples/icann-gtld.md`](examples/icann-gtld.md) | The bundled example end to end: the public ICANN rulebook, each workflow, agent, task rubric, and tool, and how the crew is assembled |
| [`../crewai_service/README.md`](../crewai_service/README.md) | The evaluation engine's layout and request flow |
| [`CLIENT_ARCHITECTURE.md`](CLIENT_ARCHITECTURE.md) | React frontend: client-side binary gates, submission queue, direct Supabase reads, report rendering |

## Adapt it

| Document | What it covers |
|---|---|
| [`ADAPTING.md`](ADAPTING.md) | Step-by-step tutorial that builds a second ruleset (product name vs. brand guideline) and runs it |
| [`../examples/brand-name-check/`](../examples/brand-name-check/) | That second ruleset: two agents, three tasks, one local-data tool, a runner, and a build test |

## Run it

| Document | What it covers |
|---|---|
| [`API_REFERENCE.md`](API_REFERENCE.md) | Every HTTP endpoint: evaluation submission and status, reports, audit logs, applicants, applications, RAG, chat |
| [`DEPLOY.md`](DEPLOY.md) | Deploying as a single web service (Render reference), Docker, macOS dev notes, troubleshooting |
| [`../db/README.md`](../db/README.md) | Schema, deploy order, migrations, and the shape of stored results |
| [`SUPABASE_CLIENT_USAGE.md`](SUPABASE_CLIENT_USAGE.md) | The two Supabase client wrappers and when to use each |
| [`../data/SOURCES.md`](../data/SOURCES.md) | Where every bundled dataset came from and what was derived |
| [`../data/README.md`](../data/README.md) | The DNS magnitude dataset in detail |

## Project

| Document | What it covers |
|---|---|
| [`../CONTRIBUTING.md`](../CONTRIBUTING.md) | How to set up, test, and submit changes |
| [`../SECURITY.md`](../SECURITY.md) | Reporting vulnerabilities; how credentials are handled |
| [`../CHANGELOG.md`](../CHANGELOG.md) | Release history |
| [`../LICENSE`](../LICENSE) | MIT |

Credentials are environment variables only; see `env.example` at the repo root.
