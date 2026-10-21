# Security

## Reporting a vulnerability

Please do not open a public issue for a security problem. Use GitHub's private reporting instead: on the repository page, open the **Security** tab and choose **Report a vulnerability**. You will get an acknowledgement within seven days and a fix or a response plan within thirty.

Include the version or commit, the endpoint or component, and steps to reproduce. If the issue involves a model prompt or output, include the exact text.

## Supported versions

Only the latest release on `main` receives fixes.

## How credentials are handled

- **Environment only.** Every credential (Gemini, OpenAI, Supabase, Brave, Serper, Firecrawl) is read from environment variables by `crewai_service/utils/config.py`. There is no file-based fallback and nothing is hardcoded. `env.example` lists the variables; `.env*` is git-ignored.
- **The Supabase service-role key never reaches the browser.** The backend holds it. The React client receives only the anon key, via `VITE_SUPABASE_ANON_KEY`, and reads under Row Level Security policies defined in `db/schema.sql`.
- **CORS is explicit.** Allowed origins come from `CORS_ALLOW_ORIGINS`; the default covers local development only.
- **Logs name credentials, never values.** `ensure_env_secrets()` logs which variables are present at startup.

If you find a credential in the repository or its history, treat it as the highest-severity report.

## Things to know before deploying

- The evaluation endpoint runs model calls with external tools (web search, deep research). Task outputs are stored verbatim in `task_executions`. Treat them as untrusted text: do not feed them to a shell, and render them as Markdown, not HTML, in any UI you add.
- The MCP server in `crewai_service/mcp_server.py` is a development convenience and is not started by the web service.
- The generation half stores applicant data you provide. The bundled knowledge base is fictional; replace it with care and keep your database's RLS enabled.
- `tests/live/` exercises a running backend with real keys and is excluded from the default test run and from CI.

## Out of scope

Prompt-injection through the reference corpus or web search results is a known limitation of tool-using agents. Reports that demonstrate a concrete, exploitable consequence in this codebase (for example, a tool result that changes a stored status without passing through the classifier) are welcome; general demonstrations of model steering are not.
