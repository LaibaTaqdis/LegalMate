# LegalMate backend

Python backend for the LegalMate AI legal chatbot (RAG over Pakistani federal + Punjab law, DeepSeek Flash for generation).

Status: **Phases 0-3 done** (scaffold, corpus pipeline, embeddings + hybrid retrieval loaded in Supabase, chat engine with verification). The API and frontend wiring (Phase 4) come next.

## Who runs what

| Job | Who | Needs |
|---|---|---|
| Corpus pipeline (this README) | **one person, once** (the one with the dataset) | `requirements-ingest.txt` |
| Embedding + loading into Supabase (Phase 2) | same person, once | + `fastembed`, Supabase URL |
| Running the app / chat engine (Phase 3+) | **everyone** | `requirements.txt` (added in Phase 3; ~1 GB, no PyTorch, no GPU) |

Teammates never touch the 290 MB of PDFs; they use the shared index in Supabase.

## Build-time vs runtime (what a deployment needs)

| | Build the knowledge base (one person, occasionally) | Run / deploy the app |
|---|---|---|
| Code | `ingest/`, `retrieval/embed_chunks.py`, `db/`, `evals/` | `retrieval/` (runtime: `kb.py`, `search.py`, `lexical.py`) + the API (Phase 4) |
| Settings | `LEGALMATE_DATASET_DIR`, `LEGALMATE_CHECKLIST` (machine-specific paths to the raw PDFs) | `DATABASE_URL`, `DEEPSEEK_API_KEY`, `JWT_SECRET` |
| Data | raw PDFs (290 MB, not in git) -> `backend/data/` (gitignored) | nothing local: the knowledge base lives in Supabase |

The two path variables exist only because the raw PDFs are not in git, so each machine that builds the index must say where they are. They live in the gitignored `backend/.env`, so they are never deployed, and the running app never reads them (checked: `retrieval.kb` imports with no `.env` and without the `ingest/` package). The knowledge base is built once, loaded into Supabase with `python -m db.load`, and the deployed server only talks to Supabase and DeepSeek.

## Corpus pipeline

Run from the `backend/` folder:

```powershell
python -m venv C:\Users\<you>\venvs\legalmate        # keep the venv OUTSIDE OneDrive
C:\Users\<you>\venvs\legalmate\Scripts\pip install -r requirements-ingest.txt
copy .env.example .env                                # then set LEGALMATE_DATASET_DIR (the dataset is not in git)
C:\Users\<you>\venvs\legalmate\Scripts\python -m ingest.run_all
```

`run_all` takes about 35 minutes the first time (30 min is the OCR repair of garbled gazette pages). `--from s2` re-runs only the cheap stages (~30 seconds) and needs the `data/extract` folder from an earlier full run.

The API contract the frontend expects is `../frontend/BACKEND_API.md`.

| Stage | Module | What it does |
|---|---|---|
| s1 | `s1_extract` | PDF -> per-page text (PyMuPDF), content hash, flags image-only pages |
| s1b | `s1b_ocr` | OCR (RapidOCR, CPU) for the ~21 image-only pages |
| s2 | `s2_manifest` | Cleans text; decides each document's **true** title/year/type/jurisdiction from content (filenames are unreliable); merges the curated CSV; near-duplicate detection; links amendments/repeals to base laws |
| s3 | `s3_chunk` | Parses Part/Chapter/Order -> Section/Article/Rule (numbering-chain DP), splits into legal-section chunks with a context header |
| s4 | `s4_qa` | Writes `reports/corpus_qa.md` |

Outputs (all in `data/`, gitignored, regenerable): `extract/` raw page text, `interim/manifest.json`, `interim/paras/`, `interim/parse_stats.json`, **`processed/chunks.jsonl`**.

## Results (current run, re-verified)

- 500 PDFs -> 494 unique laws (6 exact duplicates folded). 19 Federal-vs-Punjab-Code pairs are kept as separate variants because the texts differ (some pairs are simply different laws with similar structure, e.g. Punjab vs Pakistan Environmental Protection Act, 1997).
- **21,138 chunks**, median 827 chars (~210 tokens), p90 1,291; ~4.5M tokens of law text. 54 chunk texts occur twice (Federal/Punjab copies): dedupe at retrieval time by `chunk_hash`, preferring the user's jurisdiction.
- 449 documents parsed section-by-section; 45 (mostly 1-6 page gazette amendments) use paragraph windows.
- **Section completeness**: PPC 511/511 sections, QSO 166/166, Industrial Relations Act 2012 91/91, PECA 55/55, Punjab Rented Premises Act 36/36, Transfer of Property Act 132/137 (86-90 absent from the PDF). Gaps elsewhere are sections the PDF itself omits/repeals (e.g. Contract Act ss.76-123).
- **Text fidelity** (6-gram overlap of every chunk against the source PDF): median recall 0.93 (the rest is TOC, headers and footnotes, which are intentionally excluded); ~5% of chunks have <95% precision, almost all preambles (joined across a removed TOC) and table/schedule chunks.
- Team law checklist: all 20 P1 laws are in the corpus (the Constitution is present; the automatic matcher can't match its long checklist name, so the report shows 19/20). P2 19/20 (missing: Anti-Rape Act 2021). P3 18/20 (missing: Dowry and Bridal Gifts Act 1976, Right of Access to Information Act 2017).
- Verified by lookup: PPC s.302/375/379/489-F/500, CrPC s.154, Constitution Art. 8/10, CPC Order VII Rule 11, Transfer of Property Act s.107/123, Punjab Rented Premises Act s.15, PECA s.24, IR Act 2012 s.33.

See `reports/corpus_qa.md` for everything uncertain.

## Bugs found and fixed during re-verification (so nobody trips on them again)

- Soft hyphens (U+00AD) encode the visible hyphen of compounds ("house-trespass"); deleting them glued words together. Now mapped to `-`.
- A section whose heading said "Omitted/Repealed" was dropped together with everything after it (e.g. the whole Schedule of the President's Pension Act). Stubs are now only the stub itself.
- The TOC skip swallowed the preamble after the TOC; a run now only counts as a TOC if a later run repeats its numbers.
- Section headers hidden inside a paragraph (`*273.`, `[4.`, `1500.` = footnote 1 + s.500) were missed; a chain-guided repair pass now splits them.
- Garbled text layers in several official gazettes (e.g. NADRA Ordinance, Food Safety Authority Act 2026) are re-OCR'd and the better version kept per page (the OCR pass takes ~30 min once).
- Amendment links now respect the instrument type ("Police Order (Second Amendment) Act" amends the Police Order, not the Police Act) and never point at a later law.
- Repeal status carries a `status_scope`: the Trust Act and Canal and Drainage Act are repealed in **Punjab** only.

## Phase 2: index and retrieval

```powershell
python -m retrieval.embed_chunks                  # BAAI/bge-small-en-v1.5, 384-d, resumable. ~27 min on a 24-core CPU, once
python -m db.local_pg                             # (dev) throw-away local Postgres with pgvector; prints its URL
python -m db.load --url <postgres url>            # schema + replace all rows + HNSW/GIN indexes (or set DATABASE_URL in .env)
python -m evals.run_eval                          # offline evaluation, writes reports/retrieval_eval_<model>.md
python -m evals.run_eval_kb --url <postgres url>  # the same questions through the production path, with timings
```

**Design (all decided by measurement on 108 gold questions, `evals/gold.py`):**

- Chunks are embedded as `header + text` with `BAAI/bge-small-en-v1.5` (ONNX/CPU through fastembed). Queries use the bge query prefix (+5.5 points hit@10 over no prefix: 89.8% vs 84.3%).
- Retrieval = **pgvector** (cosine, HNSW) in Postgres **+ BM25 keyword search inside the app** (SQLite FTS5 built from the same table at startup, ~2 s, ~20 MB), fused with weighted reciprocal-rank fusion (1:1, k=60), then a soft jurisdiction preference (+15% for the user's province/ICT, -30% for another one) and de-duplication of identical Federal/Punjab texts.
- Postgres full-text search was tried and **rejected for ranking**: no BM25, keyword-only hit@10 75% vs 90%, and 4x slower. `db/schema.sql` keeps a pure-SQL `hybrid_search` as a fallback only.
- `lookup_section('Penal Code', '379')` gives exact section lookups (base laws first, amendments last).

| Setup (hit rate %, question already rewritten to English) | hit@1 | hit@5 | hit@10 | hit@20 | MRR |
|---|---|---|---|---|---|
| keyword only (BM25) | 55.6 | 81.5 | 89.8 | 96.3 | 0.667 |
| vector only | 50.9 | 82.4 | 89.8 | 91.7 | 0.646 |
| **hybrid + jurisdiction (chosen)** | **62.0** | **86.1** | **94.4** | **97.2** | **0.724** |
| production path (pgvector + BM25), measured | 61.1 | 85.2 | 94.4 | 97.2 | 0.716 |

- Production latency (this machine): query embedding ~87 ms, vector 7 ms, keyword 16 ms, fetch 6 ms; ~116 ms median end to end. Expect slower embedding on a 2018 i5.
- Database size with everything indexed: **~141 MB** (limit 500 MB). Use `db.load` in replace mode; upserting leaves dead rows and nearly doubles the size.
- Weight/`rrf_k` differences are within noise (see the grid in the report), so the standard 1:1, k=60 is used.

**What the evaluation says about Phase 3:**

1. **The analyser's English rewrite is the biggest lever**: the same search gets hit@10 of 94% on rewritten queries but only 58% on raw user questions. Prompts must produce a good search query (and, ideally, statutory hints such as "section 154 CrPC information in cognizable cases": "FIR" never finds s.154 by itself).
2. **A score threshold cannot decide "no source found"**: out-of-scope questions score as high as real ones (best cosine 0.74 vs real p10 0.71). That decision must come from the analyser's intent classification and the answer-time check, not from retrieval scores.
3. hit@10 (not hit@1) is what matters: the answer step sees the top 8-10 chunks.

Not done: an embedding-model comparison against `bge-base-en-v1.5` (about 65-130 min of CPU to embed; `python -m retrieval.embed_chunks --model BAAI/bge-base-en-v1.5` then `python -m evals.run_eval --model BAAI/bge-base-en-v1.5`; `db/schema.sql` would need `vector(768)`). The bottleneck measured above is query formulation, not the model, so `bge-small` stays. The knowledge base IS loaded into Supabase (494 documents, 21,138 chunks, 145 MB) and the production path was evaluated against it: same quality (hit@10 94.4%), median ~220 ms per search from Pakistan to the Mumbai region (50 ms network round trip per query; one fetch round trip per search).

## Phase 3: chat engine (`backend/chat`)

```powershell
python -m tests.test_chat_offline                 # 10 tests, fake LLM + fake search: ZERO DeepSeek calls
python -m chat.pilot --plan                       # the pilot scenarios, expected calls and cost. NO calls
python -m chat.pilot --dry                        # real retrieval + real prompt sizes from Supabase. NO calls
python -m chat.pilot --only S02 S07 --cap 6       # live, hard stop after 6 live calls; cached afterwards
python -m evals.run_eval_analyser --plan          # the 114-question analyser evaluation: how many calls
```

**One message in, one frontend-shaped message out, at most TWO DeepSeek calls:**

| Message | Calls | What happens |
|---|---|---|
| greeting / thanks | 0 | answered locally |
| vague ("I need help with my property") | 1 | analyser -> up to 2 questions with tappable options (`kind: clarify`); never asks twice |
| out of scope / prompt injection | 1 | analyser -> polite redirect (`kind: info`) |
| legal question | 2 | **analyser** (intent, language, jurisdiction, emergency, title/tag, THREE English search queries) -> retrieval (code) -> **answerer** (JSON, cites passages as `[[n]]`) -> verification (code) |

- **Analyser output is the lever**: three queries (plain issue / statutory phrasing + Act name / section-heading style, e.g. "What agreements are contracts"). Merged by reciprocal-rank fusion, max 3 passages per Act and 2 per section, 8 passages sent to the answerer.
- **Verification is code, not an LLM** (`chat/verify.py`): every `[[n]]` must be a supplied passage (others are stripped); every quote must be a verbatim substring (otherwise replaced by the closest real sentence and flagged); section numbers and figures in the answer must appear in the sources (number words like "fifty per centum" count as 50). Confidence (`chat/confidence.py`) = 0.5 relevance + 0.3 agreement + 0.2 recency, capped at 45 when the model says the sources are insufficient. It is a heuristic, not a probability.
- **Privacy** (`chat/pii.py`): CNIC, phone, email, IBAN and card numbers are replaced with placeholders before anything leaves for DeepSeek; the profile sent to the model contains only non-identifying fields (province, city, user type...).
- **Answer shape** matches `frontend/BACKEND_API.md` (`intro`, `lawTitle`, `law`, `steps`, `important`, `outro`, `sources`, `confidence`) plus extras for the UI to adopt: `kind` (answer | clarify | info), `questions[]`, `followUps`, `sufficient`, per-source `pages`, `status`, `note` (repealed / amended-later warnings), `quoteVerified`, and an `emergency` note in `important`.

**Keeping DeepSeek usage (and cost) low, on purpose** (`chat/llm.py`):

| Safeguard | Detail |
|---|---|
| Disk cache | identical request = never paid twice (`data/llm_cache/`); `LLM_MODE=replay` never touches the network |
| Hard caps | `LLM_MAX_CALLS_PER_RUN` (default 30) and `LLM_DAILY_CALL_CAP` (default 200, counted from the ledger); over the cap raises `BudgetExceeded`, and the engine turns it into a friendly message |
| Ledger | every live call: tokens, seconds, tag (`data/llm_ledger.jsonl`); never the key or the question |
| Thinking off | `DeepSeek thinking` is ON by default and bills hidden reasoning tokens (57 of 68 output tokens for "hello"); we send `thinking: disabled` (`DEEPSEEK_THINKING=on` to change) |
| Prompt caching | the long static system prompts come first and are identical on every call, so DeepSeek's automatic prefix cache bills them at the cached rate |
| Evaluate offline | retrieval variants are recomputed from the CACHED analyser outputs, so trying a new retrieval design costs nothing |

Measured (prices are **estimates** from third-party reports, check DeepSeek's pricing page): about 2 calls and **0.2-0.3 US cents per answered message**, 6-9 s end to end (two sequential model calls). All development, testing and evaluation of this phase used about 155 live calls, roughly **6 US cents**.

**Evaluation of the real analyser on the 114 gold questions** (`reports/analyser_eval.md`, 111 calls, 2.3 cents):

| Queries used | hit@1 | hit@8 (what the answerer sees) | MRR |
|---|---|---|---|
| plain query only | 40.7 | 70.4 | 0.511 |
| statutory query only | 52.8 | 74.1 | 0.613 |
| section-heading query only | 56.5 | 78.7 | 0.652 |
| **all three merged (production)** | **58.3** | **88.9** | **0.687** |
| my hand-written reference queries | 61.1 | 89.8 | 0.709 |

0 of 108 real questions triggered a needless clarification; 5 of 6 out-of-scope questions were declined; the analyser never contradicted a profile's province. Many of the remaining "misses" are narrow gold labels (a specific chunk), not wrong answers.

**Bugs found and fixed through the pilot:** table-of-contents chunks (25, mostly CrPC and the Contract Act) were being retrieved instead of law (now labelled `toc` and skipped); the verifier counted an invalid citation as a citation, flagged years inside Act titles, and could not match "fifty per centum" to "50"; the model's "X is not listed" claims needed hedging ("in the text available to me"), now in the prompt.

**Experiment, kept switched off:** routing a query that names an Act to a search inside that Act (`route_acts`) gave no measurable gain on the gold set.

**Known limits:** the verifier checks that citations, quotes, sections and figures exist in the sources, not that the conclusion follows from them (an optional cheap third "entailment" call could); negative claims depend on a possibly outdated corpus; confidence cannot capture that; the emergency numbers (15, 1122) are static text to be replaced by the verified Emergency directory; the API and streaming are Phase 4 (below); document attachments come in Phase 5.

## Phase 4: the API (`backend/app`) and the frontend wiring

```powershell
pip install -r requirements.txt                       # adds fastapi, uvicorn, argon2, pyjwt, psycopg-pool
python -m uvicorn app.asgi:app --port 8000            # from backend/. Needs backend/.env (DATABASE_URL, JWT_SECRET, DEEPSEEK_API_KEY)
python -m pytest tests -q                             # 35 tests: 25 API + 10 engine. Local Postgres, fake model: ZERO DeepSeek calls
python -m app.migrations_check                        # proves every table is protected by Row Level Security (run against Supabase)
python -m app.create_admin --email you@example.com --name "Your Name"     # admins/lawyers cannot self-register
```

Frontend (`frontend/.env.local`, copy of `.env.example`): `VITE_REAL_SERVICES=auth,chat,profile` and `VITE_PROXY_TARGET=http://localhost:8000`, then `npm install` and `npm run dev`. Services not listed keep running on mocks.

**What it does**

| Part | Detail |
|---|---|
| Accounts | Own JWT login (no OTP). Argon2id passwords. Access token 15 min; refresh token is random, stored only as a SHA-256, rotated on every use; replaying an old one signs the whole login session out. Wrong email and wrong password look identical (and take equally long). 8 failed sign-ins per account per 15 minutes then 429. |
| Authorisation | Every request re-reads the user from the database, so a suspended account loses access immediately. Every conversation query filters by the signed-in user; another user's id answers 404 (tested). |
| Profile | `PUT /users/me/profile` stores the onboarding answers (fixed choices; the only free text is the city, restricted to letters and digits). They are given to the chatbot as context. Name, CNIC, phone, email and address are never sent to the model. |
| Chat | `POST /chat/conversations/:id/messages` streams Server-Sent Events: `status` (thinking, searching_sources, writing_answer), `conversation` (generated title and tag), `answer` (the message: answer, clarify or info). The user message and the answer are saved by the worker, not the stream, so an answer is not lost if the browser disconnects. A failed turn leaves no half conversation (the question is removed, the user retries). |
| Limits | Per-user question limits are OFF by default (`CHAT_MSGS_PER_HOUR` / `CHAT_MSGS_PER_DAY`, 0 = none; when set, the daily count comes from the database so restarts do not reset it). Always on: one answer at a time per user, at most 4 answers computed at once, and a safety ceiling of 2000 live DeepSeek calls per day (`LLM_DAILY_CALL_CAP`, 0 = none; about 1000 answers, a few US dollars). Over a limit the user sees a plain message, not an error page. |
| Database | Tables `users`, `refresh_tokens`, `conversations`, `messages`, `source_reports` in their own schema `app` (not exposed by Supabase's REST API), applied automatically by `app/migrations/*.sql` at start-up. Row Level Security is on for all of them with no policies, and also on the law tables, which were open to the public anon key before. |
| Engine | One shared `KnowledgeBase` + `ChatEngine` built in the background at start-up (about 30 s: it streams 21,113 chunks into the in-memory keyword index). If Supabase is unreachable the API keeps running and chat answers 503 with a retry every 30 s; the keyword index is thread-safe and the Supabase connection reconnects itself after the pooler drops it. |
| Privacy of the server itself | The DeepSeek disk cache is OFF in the API (`LLM_CACHE=on` to enable): it would keep users' scrubbed questions on disk. Engine diagnostics saved with each answer are timings and verification results, never the question. Errors shown to the browser never include internals (tested). |

**Not built yet (the API answers clearly, the UI says so):** password reset by email (needs a mail service), Google sign-in, Save to Vault (501), document upload and attachments (501, Phase 5), account deletion and data export, the settings tabs other than profile, and every other module. The frontend keeps those on mocks.

**Frontend changes:** per-service mock switch (`isMock('chat')`; `VITE_USE_MOCKS=false` still means everything real); sign-up has no OTP step and CNIC and phone are optional; new `/profile-setup` page (offered right after sign-up, skippable); the chat shows clarifying questions as tappable chips, plain replies, a progress label while thinking, follow-up suggestions, source warnings (quote not matched word for word, repealed or amended law) and auto-generated conversation titles; the Google button and the fake "reset email sent" message are hidden or made honest while the backend is real.

**Found and fixed while testing the phase**

| Issue | Fix |
|---|---|
| The keyword index (SQLite) raises an error when a request thread uses a connection made by another thread, so every chat would have failed | `check_same_thread=False` plus a lock around searches |
| Supabase's pooler closes idle connections; the next question would fail | `KnowledgeBase._run` reconnects once and retries |
| A crashed engine left the user's question in the conversation with no answer | any failure after saving the question removes it again (test `test_failed_turns_leave_no_half_conversation`) |
| The engine reported a spent daily budget as a generic error | now a distinct `busy` reason with a plain message; the API maps it to 429 |
| The chat composer asked for Urdu answers by default when the interface was English (invisible with mocks) | defaults to the interface language |
| `Info` component name clashed with the `Info` icon import (caught by the production build) | renamed `PlainReply` |
| CNIC "last digit group" is one digit, a useless mask | store and show the last 4 digits |
| The static per-run cap of 30 calls (meant for scripts) would stop a server within minutes | the API uses the daily cap unless `LLM_MAX_CALLS_PER_RUN` is set on purpose |

**Measured end to end** (real browser, real Supabase, real DeepSeek, 5 live calls in total): sign-up, profile, greeting (0 calls), a legal question with a Punjab tenant profile (2 calls, 13 s including Urdu output, 3 sources, 87% confidence, conversation auto-titled), a vague question that asked two clarifying questions and then answered (1 + 2 calls, 11 s), reload (conversation restored), silent token refresh, wrong-password message.

**Before deploying:** set `TRUST_PROXY=1` only when running behind a proxy you control (Cloudflare tunnel, Render); otherwise every user looks like one address to the rate limiter. Set `APP_ENV=production` (hides `/docs`) and `CORS_ORIGINS` to the real frontend address. The in-memory rate limiter and the DeepSeek ledger live on the server's disk: a host with an ephemeral disk resets them on restart (the per-user daily limit survives, it is counted in the database).

## Phase 5: documents (`backend/app/extract.py`, `analysis.py`, `docs_service.py`, `routers/documents.py`)

```powershell
pip install -r requirements.txt                    # adds pymupdf, python-docx, rapidocr-onnxruntime, pillow
python -m pytest tests -q                          # 53 tests (28 API + 15 documents + 10 engine); zero DeepSeek calls
```

**Flow**

| Step | Who | What happens |
|---|---|---|
| 1. Upload | browser -> `POST /documents` | File type is decided from the file's bytes (not its name), size is capped while reading, the text is extracted at once and stored; **the original file is not kept** |
| 2. Extract | backend | PDF and Word: text read directly (Word tables too). Scanned pages and photos: OCR (RapidOCR, CPU). Password-protected, damaged, too many pages, zip bombs, huge images, blank images: a plain message |
| 3a. Ask in chat | browser -> `POST .../messages` with `attachmentIds` | The pieces of each document that best match the question (a short document goes in whole) are shown to the assistant as untrusted data, after identity numbers are masked |
| 3b. Analyse | browser -> `POST /analyses`, then polls `GET /analyses/:id` | A background job makes ONE DeepSeek call: summary, key clauses, risks, obligations, dates, what is missing, suggested actions |
| 4. Check | backend (code) | Every quoted clause must be the document's exact words (else replaced by the closest real sentence and flagged); figures in the explanation must exist in the text; counts, risk distribution and overall risk are computed, not trusted from the model |
| 5. Show | browser | Analysis page with notes about anything that could not be verified; attachments appear as file chips in the conversation |

**Database** (`app.documents`, `app.analyses`, migrations `002` and `003`, RLS on, no policies): the document row holds the extracted text, page count, OCR facts and an expiry; the analysis row holds status, progress, the job input and the result. Deleting a document keeps a finished analysis. Expired documents and analyses are deleted, and jobs left "running" by a restart are marked failed, at start-up and on each upload.

**Every tunable is an environment variable** (full list with defaults in `backend/.env.example`): `MAX_UPLOAD_MB`, `MAX_PAGES`, `MAX_TEXT_CHARS`, `OCR_ENABLED`, `OCR_DPI`, `OCR_CONCURRENCY`, `OCR_MIN_CONFIDENCE`, `DOCS_PER_USER`, `UPLOADS_PER_HOUR`, `DOC_RETENTION_DAYS`, `ANALYSIS_RETENTION_DAYS`, `ATTACHMENTS_PER_MESSAGE`, `CHAT_DOC_CHARS`, `ANALYSIS_QUICK_CHARS` / `_DETAILED_CHARS`, `ANALYSIS_QUICK_TOKENS` / `_DETAILED_TOKENS`, `ANALYSIS_MAX_DOCS`, `ANALYSIS_CONCURRENCY`, `ANALYSIS_PER_USER_RUNNING`, `ANALYSIS_PER_DAY`. Frontend: `VITE_REAL_SERVICES` now includes `documents`, and `VITE_MAX_UPLOAD_MB` (keep equal to `MAX_UPLOAD_MB`).

**Analysis history** (`GET /analyses`, `DELETE /analyses/:id`; page `frontend/src/pages/AnalysisHistory.jsx`): the sidebar item is now **Analysis** and opens the user's history (search, risk, status, period and sort filters kept in the address bar, paging, in-progress rows that update themselves, failed rows with the reason and "Try again", delete confirmed inline). **New Analysis** opens the upload page. Everything is inline: no pop-up windows and no native dropdowns. New addresses: `/analysis`, `/analysis/new`, `/analysis/:id`; the old `/documents/...` addresses redirect. Deleting an analysis also deletes the stored text of its document.

**Speed fix found while testing this page (affects every endpoint):** measured against Supabase, one round trip is ~96 ms but every pooled query cost ~353 ms (a transaction commit and a health-check ping on top of the query), so the history list took 1.5 s. Single statements now run in autocommit (one round trip), the pool health check is skipped for a connection used in the last 20 s, and the list's three queries go in one pipelined trip. Now: list ~0.25 s, `/auth/me` 558 -> 124 ms. `Database.tx()` still gives a real transaction where work must succeed or fail together (refresh tokens, saving an answer, deleting an analysis).

**Urdu** (`app/urdu.py`, `app/extract.py`): two OCR readers share one picture. The English reader always runs; the Urdu reader (PaddleOCR Arabic-script model through `rapidocr`) runs only when the English reader left more than 20% of the page's ink unread, so English pages cost nothing extra. Each line is kept from the reader right for its script, symbol-soup the English reader invents from Urdu is dropped, and lines are put back in reading order (top to bottom; right to left for Urdu). Digital Urdu PDFs are folded from old "presentation form" letters to normal Urdu, and broken text layers (private-use characters, runs of odd symbols, as in old InPage files) fall back to OCR. Quote and figure checks understand Urdu (Arabic or Urdu letter forms, Urdu full stop, Urdu digits); a CNIC or phone written in Urdu digits is scrubbed before anything leaves. Answers and quotes display right to left. `python -m app.ocr_warmup` pre-downloads the model (about 10 MB); `OCR_LANGS=en` switches Urdu off.
**Measured** on rendered Urdu text in three fonts: English reader alone 0%; Urdu reader 85-94% of each line correct, mean about 90% through the real extractor, 7-10 s per image. Digital Urdu PDF: 99%. Mixed English and Urdu page: both kept in order. **Not tested and expected to be worse: Nastaliq print (the usual Pakistani style; no such font was available to test), handwriting, photos at an angle.** Known weakness: the model often reads ہ as ب. The user is always told that Urdu read from an image can contain mistakes.

**Photo speed** (`app/extract.py`): a phone photo of an English page used to take 20 s or more; it now takes about 4-6 s. Three causes were measured and fixed. (1) The Urdu reader started on English photos, because shadows and the paper's edge were counted as unread writing (5-7 s wasted): "ink" is now a pixel darker than its own neighbourhood, and long structures such as the paper edge or table rules are ignored; Urdu and mixed pages still start it (tests with shaded photos both ways). (2) The English recognizer paid a 10 s set-up for every picture of a new size, because its batch width changed with the longest line: widths are now rounded to multiples of 160 px and lines are read one at a time, so only a handful of shapes exist (new sizes read in about 4 s, same text). (3) The first photo after a restart paid for model loading: the server now loads and primes both readers in the background at start (`OCR_WARM=0` switches that off; about 10 s, `OCR ready in ...s` appears in the log). The chat attachment chip says "reading the picture…" while it works. A text-heavy photo still costs about 0.1 s per line of text; this is the CPU-only limit of the reader.

**Supabase egress and the optional local copy of the law text** (`retrieval/kb_cache.py`, tests `tests/test_kb_cache.py`): every time the chat engine starts it downloads the text of all 21,138 law chunks (about 22 MB) from Supabase to build the keyword index, and the free plan allows about 5 GB of egress a month, so many restarts add up (a day of testing used more than 1 GB). With `KB_CACHE=on` the first start saves those rows to `backend/data/kb_cache` (git-ignored) and later starts read the file: a tiny query returns a fingerprint of the law table (row count plus an md5 over each chunk's id, hash, legal status, jurisdiction and scope, computed inside Postgres, so nothing is downloaded for it); if a file for that fingerprint exists it is used, otherwise the rows are downloaded again and the file replaced, so a stale copy can never be served. Measured on the real database: first start 13.7 s (download), later starts 6.0 s, identical search results; a damaged or half-written file is ignored, and a full disk never stops the engine. **It is OFF by default** and meant for test runs: set `KB_CACHE=on` (and optionally `KB_CACHE_DIR`) in the environment to use it. The log shows `local copy: hit|miss|off`. A teammate who wants it sets the same variable on their own machine.

**Security and encryption** (what protects stored data, and what does not). The stack choice already encrypts: Supabase encrypts its Postgres disks and its file Storage at rest (AES-256, applied by Supabase, nothing for us to switch on) and all traffic is TLS (browser to API, API to database, API to Storage, and the signed file links). On top of that, the application adds: a private bucket (checked: the public address of a stored object answers an error), generated object names (`<user id>/<random>.<ext>`, never a name the user chose), signed links that live `VAULT_LINK_SECONDS` (300) and are made only after the file is proved to belong to the caller, Row Level Security on every table in the `app` schema and on the law tables (`python -m app.migrations_check` proves it), every query scoped to the user (another user's id is a plain 404), argon2id password hashes, refresh tokens stored as sha256 with reuse detection, identity numbers (CNIC, phone, email, IBAN, card) removed before anything reaches the model, and the service key kept server-side in `backend/.env` (never sent to the browser, never in git). **Not done:** our own encryption of file contents before upload (so someone with the Supabase service key or project access can read the files; a database dump holds the extracted text of documents in a normal column), end-to-end encryption (impossible while the server reads files for search and analysis), a virus scan of uploads, and removal of a user's stored objects on account deletion (account deletion itself is not built). An application-level layer is possible (AES-GCM with a key only the server holds, applied before upload): the cost is that previews would have to stream through our server instead of a signed link, and losing the key makes the files unrecoverable, so it needs a key-backup plan first.

**Legal Vault, part A: saved answers and analyses** (migration `005_vault_items.sql`, `app/vault.py`, `app/routers/vault.py`, tests `tests/test_vault.py`): "Save to Vault" now works under a chat answer and on an analysis. What is saved is a snapshot (a chat answer with its question and sources; the full analysis result), so it stays readable after the chat or the analysis is deleted or expires. Saving the same thing twice is one item. The Vault page lists them (search, All / Chat answers / Analyses / Favourites / Trash, sort, pages), an item opens as it was, and it can be renamed, starred, given notes and has an activity log. Delete moves an item to the Trash, which empties itself after `VAULT_TRASH_DAYS` (30; run with the expiry clean-up). Starting an analysis with "Save to Legal Vault" ticked saves it automatically when it completes. Limits: `VAULT_MAX_ITEMS` 500 per user, `VAULT_MAX_NOTES` 50, `VAULT_NOTE_CHARS` 2000, `VAULT_PAGE_SIZE` 24. Every table has Row Level Security and every query is scoped to the user (another user's id is a plain 404). The frontend needs `vault` in `VITE_REAL_SERVICES`. Part B is described just below.

**Legal Vault, part B: your own files** (migration `006_vault_files.sql`, `app/storage.py`, `app/vault_files.py`, `app/routers/vault_files.py`, tests `tests/test_vault_files.py`, 19 tests with an in-memory storage): contracts, notices and photos are uploaded to the Vault's **My Files** tab. The original is kept in a PRIVATE Supabase Storage bucket (`VAULT_BUCKET`, created on first start); the database holds the name, folder, category, size and the text read from the file. Object names are generated (`<user id>/<random>.<ext>`), the type is decided by the file's bytes, and the browser only ever gets a signed link that works for `VAULT_LINK_SECONDS` (300) after the file was proved to be the caller's (checked on the real bucket: the public address of an object answers an error). Text for search comes from the file at upload (PDF, Word); a photo or a scanned PDF is stored at once and read by OCR in the background (`textStatus: pending` then `ready`), so search finds what is inside. Folders (create, rename, colour, delete keeps the files), categories, favourites, notes, an activity log, a preview page (PDF and pictures from the signed link, Word as extracted text), download, search, sort, pages and a Trash that empties itself after `VAULT_TRASH_DAYS`. The Trash and delete-forever remove the stored original first and the row second, so a storage failure keeps the file for a retry instead of orphaning it. Limits: `VAULT_QUOTA_MB` 50 per user (the Trash counts until emptied), `VAULT_MAX_FILES` 200, `VAULT_MAX_FOLDERS` 30, `VAULT_UPLOADS_PER_HOUR` 60, and the file size limit is `MAX_UPLOAD_MB`. Without `SUPABASE_URL` and `SUPABASE_SERVICE_KEY` the server still runs; the My Files tab says storage is not set up. An upload takes about 1 s (one storage call and a few database round trips). Not built: virus scanning (only the content type is checked), copy, one-click "analyse this file", sharing, removing a user's stored objects when the account is deleted (account deletion itself is not built).

**Photos in chat are read during the answer, not at upload** (migration `004_deferred_ocr.sql`): attaching a JPG or PNG in chat now takes about a second (type and openability are checked, a big photo is shrunk to at most 3000 px / about 1 MB, and it is stored in `app.documents.raw` with `status = 'pending'`). When the question is sent, the turn first reads the photo, and the chat shows "Analyzing the image…" (SSE `status` state `reading_image`) before "Searching Pakistani laws…" and "Writing and checking the answer…". The text is stored, `raw` is emptied (the original is still not kept), and a second question about the same photo does not read it again. A photo with no readable text is deleted and reported in plain words, and the question is taken back like any failed turn. A photo that is attached but never sent is removed after `PENDING_DOC_HOURS` (24). The Analysis page upload and PDFs/Word files are unchanged (read at upload; a scanned PDF in chat is still read at upload). `OCR_DEFER_CHAT=0` goes back to reading at upload. The expiry clean-up on upload now runs at most once a minute per server (it was four database round trips on every upload).

**Answer language in chat** (`chat/lang.py`, `chat/strings.py`): the answer is in the language the user wrote in: English, Urdu script, or Roman Urdu (Urdu in Latin letters, "kiraya kitna barh sakta hai"). Code decides this, not the model: Urdu letters mean Urdu; Latin text with Roman Urdu words (a list of words that are not English, such as kya, hai, mujhe, kiraya) means Roman Urdu; a bare reply ("ok", "1", a tapped one-word option) keeps the language of the conversation; the analyser's guess can only turn short English-looking text into Roman Urdu. The composer's language menu is Auto (default) / English / اردو / Roman Urdu, and a forced choice wins; the interface language (the globe in the top bar) no longer decides the chat language. The model writes every field of the answer in that language; everything the app itself says (greeting, "no law found", errors, the clarifying prompt, headings, disclaimer, emergency numbers, "amended later" notes) comes from `chat/strings.py` in all three languages, and the frontend labels (`utils/answerText.js`: "Steps you can take", "Sources", "Confidence", buttons, toasts) follow the message's `language`. A model reply in the wrong script is replaced by the fixed text, and a drift in a full answer is recorded as `language_mismatch` in the message meta. No extra model call. The Urdu and Roman Urdu wording of the fixed texts was written by us and should be read once by a native speaker. `python -m pytest tests/test_language.py`.

**Related laws on an analysis** (`app/law_refs.py`): searching the law library from a loosely worded clause is not reliable enough to show people, so the model only CLASSIFIES (category, jurisdiction, 0-2 topics per clause from a fixed list) and a reviewed table maps each topic to exact Acts and sections (58 entries, for example penalty clause -> Contract Act s.74, non-compete -> s.27, loan interest -> the Punjab and Islamabad Prohibition of Interest on Private Loans Acts, eviction -> Punjab Rented Premises Act s.15 or Islamabad Rent Restriction Ordinance s.17). Code fetches the REAL section text from the law library (`KnowledgeBase.get_section`, exact title), cuts out the right section of a combined chunk, and shows it with the province and any "amended later" or "repealed" warning. Province-specific laws are used only when the document or the user's profile says where it applies. Topics with no governing section show nothing (the Punjab tenancy Act has no rent-increase or deposit section; blank-cheque clauses have no entry). Nothing shown is written by the model, and the box never says whether the document complies. `python -m app.law_refs --check` resolves every entry against the real library; `LEGALMATE_LIVE_TESTS=1 pytest -k real_library` does the same as a test.
**Measured** on four live analyses (employment, plot sale, loan, Urdu tenancy): classification and jurisdiction were right in all four, every clause that had a law in the table got it, clauses without one got none. One clause (non-compete) was first cut by the box limit; now a clause's main law is always kept.

**Not built / limits (the UI says so)**
- **No virus scan.** Mitigation: the file is parsed in-process, never executed (no macros or scripts), size/page/pixel/zip limits apply before heavy work, and the file is discarded. A scanner (ClamAV) is a deployment task for Phase 6.
- **OCR can misread digits** (seen: "45,000" read as "45,0o0"), so any document read from an image carries a warning to double-check amounts. Urdu OCR: see above (Nastaliq and handwriting untested).
- **No PDF report, no Legal Vault save, no share link** (they answer 501 with a plain message). The related-laws table covers 26 topics for tenancy, employment, property, loans, business and contracts; court documents and notices get none yet.
- Analysis takes 10-60 s (one long structured answer, 1,700-2,300 tokens; the default cap is now 2,800 because 1,800 cut answers off). If an answer is still cut off, the parts that arrived are kept and a note says so. DeepSeek returned 503 twice during testing, which the app reports plainly.

**Found and fixed while building**

| Issue | Fix |
|---|---|
| OCR silently dropped a whole line that sat near the picture's edge (found by a failing test) | white margin around every image before reading; verified on 4 sizes |
| I edited migration 002 after it had been applied to Supabase, so the live table lacked a column and the first analysis failed | never edit an applied migration: new migration `003` adds the column (a no-op on fresh databases) |
| Test engine and test client both wanted port 8000/5173, already used by your running servers | tested on other ports; your servers were not touched |
| A quote the model invented ("throw you out whenever he likes") | replaced by the closest real sentence and flagged (test) |

## Known data issues (also in the QA report)

- **Mislabelled files**: three `Pakistan Ordnance Factories Board Ordinance 1961.pdf (n)` files are really the Companies Act 2017, the ICT Senior Citizens Act 2021 and the Anand Marriage Act 1909; `THE PUNJAB CRIMINAL PROSECUTION SERVICE Act 2025.pdf` is actually the Punjab Agriculture, Food and Drug Authority (Amendment) Act 2025. Titles are taken from content.
- **No currency verification.** 45/47 curated records are `UNVERIFIED` in the source CSV; `publisher_versions_unverified` files are treated as tier "publisher". Gazette amendments are linked to base laws (42 of 57) but **not merged into their text**. 15 amending instruments have no base law in the corpus (e.g. Income Tax Ordinance 2001, Civil Servants Act 1973). The link "Criminal Laws (Amendment) Act 2025 -> Criminal Law Amendment Act 1908" is probably wrong (an omnibus amendment).
- **Missing from the checklist**: Anti-Rape (Investigation and Trial) Act 2021, Dowry and Bridal Gifts Act 1976, Right of Access to Information Act 2017. No case law/judgments at all.
- **No Urdu text** in the corpus; Urdu questions are handled by translating the query to English before retrieval.
- Footnote text (amendment history) is split off the body and kept in `amendment_notes` (not embedded); heavily footnoted Acts such as the Punjab Katchi Abadis Act are ~40% footnotes.
- ~105 chunks are "Schedule/appendix material after Section X" (tables/forms that the PDF text attaches to the last section); they are labelled as such instead of being attributed to the section.

## `chunks.jsonl` fields

`chunk_id, doc_id, ordinal, act_title, year, doc_type, jurisdiction (Federal|Punjab|ICT), applies_to[], tier (curated|gazette|publisher), legal_status (unverified|repealed), status_scope, status_note, unit_type (section|article|rule|preamble|tail|passage), section_no, section_nums[], section_label, heading, part, chapter, order, schedule, page_start, page_end (1-based PDF pages), part_index, parts_total, header, text, embed_text, n_chars, amendment_notes, source_urls, chunk_hash`

`embed_text` = `header` + text (what gets embedded); `text` is the exact law wording shown to the user and quoted in citations.

## Conventions

- Use real regex escapes in source files; the pipeline was bitten once by an editor turning `\b` into a backspace character.
- Do not commit `.env`, `data/` or the dataset.
