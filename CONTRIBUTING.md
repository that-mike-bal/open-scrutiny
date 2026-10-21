# Contributing

Thanks for looking. OpenScrutiny is a small project with one maintainer, so the bar is "clear, tested, and in keeping with the design". Issues and pull requests are welcome.

## What helps most

- **New example rulesets.** A config tree under `examples/<name>/` with its own tool and a build test, following [docs/ADAPTING.md](docs/ADAPTING.md). Each one proves the engine is config-driven better than any sentence in the README.
- **Tools** that read local data or well-documented public APIs, with their HTTP calls routed through `crewai_service/utils/logged_requests.py` so the audit trail can attribute them.
- **Documentation fixes**, especially anything that contradicts the code.
- Items on the roadmap in the [README](README.md#status-and-roadmap).

## Setup

```bash
cp env.example .env           # placeholder values are fine for the test suite
pip install -r requirements.txt pytest pytest-mock
cd client && npm install
```

Python 3.12 is required (CrewAI's pinned dependencies). The backend tests mock every database and model call.

## Before you open a pull request

```bash
pytest -q                            # backend + integration, must pass
cd client && npm run build-strict    # tsc -b && vite build, must pass
```

Then check:

- No credentials, project identifiers, or personal data in the diff. Credentials are environment variables only (see [SECURITY.md](SECURITY.md)).
- Rulebook changes live in YAML and data, not Python. If you had to change `crew.py` to make a config work, say why in the PR; that is usually a sign the engine needs a feature rather than the config needing a workaround.
- A new config tree has a build test next to `tests/backend/crew/test_brand_name_example.py`.
- Every doc link resolves. `docs/README.md` indexes every document.
- `CHANGELOG.md` has a line under "Unreleased".

Keep commits small and the messages in the imperative ("add", "fix"). One topic per pull request.

## Conventions

- `CUSTOMIZE:` comments mark the places an adopter edits to retarget the engine. Keep them accurate when you move code.
- Task rubrics open with a `STATUS:` line from a fixed vocabulary; `_classify_result_status` in `crewai_service/app.py` depends on it.
- Agents and crews run with `memory: false` unless a workflow has a documented reason otherwise.
- The frontend only ever holds the Supabase anon key.

## Reporting bugs

Open an issue with the workflow name, the item you submitted, and the relevant lines from the backend log. Do not paste `.env` contents or task outputs that include third-party data you cannot share.

By contributing you agree that your contributions are licensed under the [MIT License](LICENSE).
