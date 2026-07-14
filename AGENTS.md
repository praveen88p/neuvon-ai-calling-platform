# Neuvon AI Calling Platform — Agent Rules

## Read Before Anything Else

Read in this exact order before any implementation:

1. context/project-overview.md
2. context/architecture.md
3. context/code-standards.md
4. context/library-docs.md
5. context/build-plan.md
6. context/progress-tracker.md

## Rules That Never Change

- Never use hardcoded hex values or raw Tailwind color classes in frontend components — use CSS variables
- Update `progress-tracker.md` after every completed feature
- Before any third party library — load its installed skill first,
  then read `context/library-docs.md` for project-specific rules
- Before any Dograh API integration — load the Dograh skill first,
  then verify endpoints against `context/library-docs.md`
- Every database query must be scoped by `organization_id` — no exceptions
- All Dograh communication goes through `DograhClient` — never call Dograh directly
- Backend follows RORO pattern — Pydantic schemas in, Pydantic schemas out
- Frontend never talks to Dograh — all calls go through the FastAPI backend
- If the same problem persists after one corrective prompt —
  stop immediately and run /recover

## Tech Stack

- **Frontend:** React 18 + Vite + TypeScript + Tailwind CSS + shadcn/ui
- **Backend:** FastAPI (Python 3.12+) + SQLModel + Celery + Redis
- **Auth/DB/Storage:** InsForge (BaaS)
- **Voice:** Self-hosted Dograh at `dograh.neuvonsoftware.com`
- **Billing:** Razorpay
- **Analytics:** PostHog (server-side)

## Available Skills

- `/architect` — before any complex feature. Think before building.
- `/imprint` — after any new UI component. Capture patterns.
- `/review` — before demo or when something feels off.|
- `/recover` — when something breaks after one failed correction.
- `/remember save` — when a feature spans multiple sessions.
- `/remember restore` — when returning after a multi-session feature.