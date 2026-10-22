# Changelog

All notable changes to this project are documented here. The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/) and the project uses [Semantic Versioning](https://semver.org/).

## [Unreleased]

### Fixed
- Tasks that declared no `context` were built with an empty list, which CrewAI treats as "no prior output". Gut checks and the legal validation pass therefore reviewed nothing. The builder now leaves `context` unset unless declared, and the validation and gut-check tasks declare the outputs they review.
- The validation-mode agent now runs the legal validation pass and every gut check; previously those tasks were bound to the specialist whose work they were meant to check.
- `guidebook_search` is loaded for every agent whose prompts cite it (string analyst, legal analyst, validator, as well as the GAC analyst), and the tool's name matches the prompts.

### Added
- `docs/KNOWLEDGE_BASE.md`: what is in the rulebook index, who reads it, how to load the Applicant Guidebook, and how to swap in another corpus.

### Removed
- The last file-based credential fallback (`scripts/setup_rag_database.py` reading `secrets/openai_api_key.txt`).

## [0.1.0] - 2026-10-21

Initial public release.

### Added
- Evaluation engine: `CrewBuilder` assembles CrewAI crews from a config tree of `agents.yaml`, `tasks.yaml`, `tools.yaml`, and `workflows.yaml`, with per-environment runtime settings in `environment.yaml`.
- Bundled example: three workflows (technical, legal, policy) that evaluate proposed gTLD strings against the public ICANN New gTLD Program rulebook, with specialist agents, seven custom tools, validator and gut-check layers, and a qualitative risk rubric.
- Audit trail: per-task API-call attribution, tool-execution summaries, pattern-based result classification, and a 0–1 confidence score stored with every task; narrative audit log endpoints.
- Per-agent model routing (`crewai_service/utils/model_config.py`) with Gemini 2.5 models and a GPT-4o fallback.
- Generation half: three-tier answer generation (entity, selection, substantive) with RAG over a reference corpus and an applicant knowledge base.
- FastAPI HTTP API with a single-threaded evaluation queue (HTTP 409 when busy) and a React + Vite + TypeScript client with client-side binary gates, live progress, report and audit-log views, and a scoreboard.
- Supabase schema with Row Level Security and migrations; setup and seeding scripts.
- Second example ruleset, `examples/brand-name-check/`: two agents, three tasks, one local-data tool, with a build test. `CrewBuilder` can now import a config tree's tools from the tree's own directory.
- Documentation: README product page, `docs/ARCHITECTURE.md`, `docs/examples/icann-gtld.md`, `docs/ADAPTING.md`, `docs/API_REFERENCE.md`, `docs/DEPLOY.md`, `data/SOURCES.md`, `CONTRIBUTING.md`, `SECURITY.md`.
- CI: backend tests (110 passing with placeholder keys) and a strict TypeScript build.

### Security
- All credentials are environment variables; the Supabase service-role key is backend-only.

[Unreleased]: https://github.com/that-mike-bal/open-scrutiny/compare/v0.1.0...HEAD
[0.1.0]: https://github.com/that-mike-bal/open-scrutiny/releases/tag/v0.1.0
