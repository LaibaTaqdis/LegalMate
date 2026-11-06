# LegalMate

AI-powered legal assistance platform for Pakistan (Riphah International University FYP): an AI legal assistant grounded in
federal and Punjab law (RAG), document understanding, a legal vault, lawyer marketplace and more.

## Repository layout

| Folder | What | Stack |
|---|---|---|
| [`frontend/`](frontend/) | Web app (all screens, mock data until the backend is connected) | React + Vite |
| [`backend/`](backend/) | Legal-corpus pipeline today; chat/RAG API next | Python, FastAPI (planned), Supabase Postgres + pgvector, DeepSeek |

The API contract between the two is [`frontend/BACKEND_API.md`](frontend/BACKEND_API.md).

## Quick start

Frontend:

```bash
cd frontend
npm install
npm run dev
```

Backend: see [`backend/README.md`](backend/README.md). The legal dataset (~290 MB of PDFs) is **not** stored in git.

## This repository is public

Never commit secrets (`.env`, API keys, database URLs) or the raw dataset. The `.gitignore` already excludes them;
keep it that way and share keys privately.
