# LegalMate

AI-powered legal assistance platform for Pakistan (Riphah International University FYP): an AI legal assistant grounded in
federal and Punjab law (RAG), document understanding, a legal vault, lawyer marketplace and more.

## Repository layout

| Folder | What | Stack |
|---|---|---|
| [`frontend/`](frontend/) | Web app. Auth, chat, profile, documents and the Legal Vault run on the real backend; the other modules still use mock data | React + Vite |
| [`backend/`](backend/) | Legal-corpus pipeline, the chat/RAG engine, the REST API (auth, chat, documents and OCR, analysis, Legal Vault) | Python, FastAPI, Supabase Postgres + pgvector + Storage, DeepSeek |

The API contract between the two is [`frontend/BACKEND_API.md`](frontend/BACKEND_API.md).

## Tech stack and security

| Part | Choice |
|---|---|
| Web app | React + Vite |
| API | FastAPI (Python), own JWT login (argon2id password hashing, short-lived access tokens, rotating refresh tokens) |
| Database | Supabase Postgres with pgvector (law search) and full-text search |
| File storage | Supabase Storage, one PRIVATE bucket for the Legal Vault's files |
| AI | DeepSeek (answers and document analysis; the only paid part), `bge-small` embeddings and OCR run locally on CPU |

**Encryption comes with this stack.** Supabase encrypts the database and the file storage at rest (AES-256, applied by Supabase) and every connection
is HTTPS/TLS (browser to API, API to Supabase, and the file links). On top of that we add access control: the Storage bucket is private, files get
names we generate, a file is only reachable through a signed link that lasts a few minutes and is made after the server proved the file is the
caller's, every table has Row Level Security and every query is scoped to the signed-in user. What we do **not** add is our own encryption layer on
the file bytes: anyone holding the Supabase service key or admin access to the project could read stored files, and the text read from files (used for
search) sits in a normal database column. See "Security and encryption" in [`backend/README.md`](backend/README.md) for the details and the option to add one.

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
