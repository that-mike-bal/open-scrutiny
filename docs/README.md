# Documentation

Start with the root [README](../README.md) for what the platform does, the quick start, and how to retarget it to your own domain.

| Document | What it covers |
|---|---|
| [`API_REFERENCE.md`](API_REFERENCE.md) | Every HTTP endpoint: evaluation submission and status, reports, applicants, applications, RAG, chat |
| [`CLIENT_ARCHITECTURE.md`](CLIENT_ARCHITECTURE.md) | React frontend: client-side binary gates, submission queue, direct Supabase reads, report rendering |
| [`DEPLOY.md`](DEPLOY.md) | Deploying as a single web service (Render reference), Docker, macOS dev notes, troubleshooting |
| [`SUPABASE_CLIENT_USAGE.md`](SUPABASE_CLIENT_USAGE.md) | The two Supabase client wrappers and when to use each |
| [`../crewai_service/README.md`](../crewai_service/README.md) | The evaluation engine: agents, tasks, tools, workflows, and how a crew is assembled |
| [`../db/README.md`](../db/README.md) | Schema, deploy order, migrations, and the shape of stored results |
| [`../data/README.md`](../data/README.md) | The bundled example's reference datasets and where they come from |

Credentials are environment variables only; see `env.example` at the repo root.
