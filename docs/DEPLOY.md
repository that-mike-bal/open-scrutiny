# Deployment

The app deploys as a **single web service**: FastAPI serves the API and the built React frontend from `client/dist/`. The reference target is [Render](https://render.com); any host that can run `pip install` + `npm run build` + `uvicorn` works the same way. A local Docker option is in `docker-compose.yml`.

## Render (reference)

`render.yaml` at the repo root defines the service:

```yaml
services:
  - type: web
    name: crewai-assistant        # rename freely
    env: python
    buildCommand: |
      pip install -r requirements.txt &&
      cd client && npm install && npm run build
    startCommand: cd crewai_service && uvicorn app:app --host 0.0.0.0 --port $PORT
```

Files that matter for the build:

| File | Why |
|---|---|
| `.python-version` | Pins Python 3.12. Render defaults to 3.13, which CrewAI's pinned deps don't support. |
| `requirements.txt` | `crewai[tools,google-genai]>=0.175.0` — the `google-genai` extra is **required**; without it every evaluation fails with `Google Gen AI native provider not available`. |
| `client/` | Built during deploy; the backend serves `client/dist/`. |

Build takes roughly 4–5 minutes (Python deps ~3 min, Node build ~1–2 min).

### Environment variables

Set these in the Render dashboard (or your host's secret store). Nothing is read from files.

Required:

```
GEMINI_API_KEY          # primary model
SUPABASE_URL
SUPABASE_SERVICE_KEY    # backend only — never expose as VITE_*
SUPABASE_ANON_KEY
VITE_SUPABASE_URL       # baked into the frontend build
VITE_SUPABASE_ANON_KEY
CORS_ALLOW_ORIGINS      # your public origin, e.g. https://your-app.onrender.com
```

Optional (features degrade gracefully without them):

```
OPENAI_API_KEY          # report-generation fallback + RAG embeddings
BRAVE_API_KEY           # web search tool
SERPER_API_KEY          # alternative web search
FIRECRAWL_API_KEY       # Firecrawl MCP tool
ANTHROPIC_API_KEY       # unused by the bundled example
```

Non-secret config (already in `render.yaml`): `ENVIRONMENT=production`, `DEBUG_MODE=false`, `LOG_LEVEL=INFO`.

### Health checks

```bash
curl https://<your-service>.onrender.com/health
curl https://<your-service>.onrender.com/api/server-status   # busy with an evaluation?
```

## Docker (local)

```bash
cp env.example .env     # fill in keys
docker compose up --build
# backend  http://localhost:8000
# frontend http://localhost:8080
```

## Local development on macOS

CrewAI pins `lancedb`, which only ships Linux wheels. The code doesn't use lancedb directly (it backs CrewAI memory/knowledge features this project disables), so skip it:

```bash
python3.12 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
pip install "crewai==1.13.0" "crewai-tools==1.13.0" --no-deps
pip install "google-genai>=1.65.0"
```

## Troubleshooting

**Evaluations fail with "Google Gen AI native provider not available"** — the `crewai[google-genai]` extra is missing. Fix `requirements.txt` and redeploy.

**Server always reports busy; new submissions are rejected with 409** — a stuck `tld_strings` row is left in `RUNNING`. Reset it:

```sql
UPDATE tld_strings SET overall_status = 'FAILED'
WHERE overall_status = 'RUNNING' AND updated_at < NOW() - INTERVAL '30 minutes';
```

**Build fails resolving lancedb** — the host is not Linux or `.python-version` is not `3.12`.

## Notes on CrewAI ≥ 1.1

CrewAI removed LiteLLM as a core dependency in 1.1.0 and routes `gemini/<model>` through the native `google-genai` provider. The model string (`gemini/gemini-2.5-flash`) and `GEMINI_API_KEY` are unchanged; only the extra is new. Reference: https://docs.crewai.com/en/learn/litellm-removal-guide
