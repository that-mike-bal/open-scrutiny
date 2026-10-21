# Frontend (`client/`)

React 19 + Vite + TypeScript + Tailwind (shadcn/ui). Submits items for evaluation, shows live progress, renders reports and audit trails, and hosts the generation UI.

## Run it

```bash
cp env.example .env     # VITE_SUPABASE_URL, VITE_SUPABASE_ANON_KEY, VITE_CREWAI_ENDPOINT
npm install
npm run dev             # http://localhost:5173
```

The frontend only ever holds the Supabase **anon** key; writes and AI work go through the backend.

Scripts: `npm run build` (Vite), `npm run build-strict` (type-check + build), `npm run lint`, `npm test` (Vitest).

## How it fits

```
UI ──submit──▶ backend POST /api/evaluations/auto-submit
UI ◀──reads─── Supabase (PostgREST, RLS)   # status, task results, reports
UI ──poll────▶ backend GET /api/server-status   # client-side queue
```

Reads go straight to Supabase for responsiveness; the backend returns `409` while an evaluation is running and the client queue retries automatically.

## Pieces worth knowing

| Area | Files |
|---|---|
| Client-side binary gates (fast rejects before any AI spend) | `src/lib/binaryCompliance.ts`, `public/data/*` |
| Submission + queue | `components/NewEvaluationModal.tsx`, `components/QueuedStrings.tsx`, `components/QueueStatus.tsx` |
| Dashboard and comparison | `components/SimpleDashboard.tsx`, `components/Scoreboard.tsx` |
| Evaluation detail, report, audit log | `components/StringEvaluation.tsx`, `components/EvaluationReportViewer.tsx`, `components/WorkflowProgressTracker.tsx` |
| Generation UI (applications, applicants, answers) | `components/ApplicationDetail.tsx`, `components/ApplicantManagement.tsx`, `components/RAGAnswerGenerator.tsx` |
| Data access | `src/lib/supabase-api.ts`, `src/hooks/useTldEvaluations.ts` |
| Auth (Supabase Auth) | `src/contexts/AuthContext.tsx`, `components/Auth/*`; setup notes in `AUTHENTICATION_SETUP.md`, `SUPABASE_AUTH_CONFIG.md` |

The bundled example's gates and labels are TLD-specific; `CUSTOMIZE:` markers in `src/lib/section-utils.ts` and `components/CreateApplicationModal.tsx` show where to retarget output types and sections. More detail in [docs/CLIENT_ARCHITECTURE.md](../docs/CLIENT_ARCHITECTURE.md).
