# Neuvon AI Calling Platform

White-label AI calling platform built by Neuvon Software. Multi-tenant voice agent management, outbound campaigns, live call monitoring, and usage-based billing — powered by self-hosted Dograh.

## Tech Stack

| Layer | Tool |
|---|---|
| Frontend | React 18 + Vite + TypeScript + Tailwind CSS + shadcn/ui |
| Backend | FastAPI (Python 3.12+) + SQLModel + Celery |
| Auth/DB/Storage | InsForge |
| Voice Engine | Dograh (self-hosted) |
| Task Queue | Celery + Redis (AWS) |
| Billing | Razorpay |
| Analytics | PostHog |

## Project Structure

```
/
├── src/           ← React frontend (Vite)
├── backend/       ← FastAPI backend
├── context/       ← Architecture docs & build plan
└── AGENTS.md      ← AI agent rules
```

## Context Files

Read these before any implementation work:

1. `context/project-overview.md` — What the product does
2. `context/architecture.md` — System design, DB schema, data flows
3. `context/code-standards.md` — Coding conventions and patterns
4. `context/library-docs.md` — Library usage and Dograh API reference
5. `context/build-plan.md` — Phased implementation plan
6. `context/progress-tracker.md` — Current build status

## Getting Started

```bash
# Frontend
npm install
npm run dev

# Backend (coming soon)
cd backend
pip install -r requirements.txt
uvicorn main:app --reload
```
