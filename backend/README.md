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

**Known limits:** the verifier checks that citations, quotes, sections and figures exist in the sources, not that the conclusion follows from them (an optional cheap third "entailment" call could); negative claims depend on a possibly outdated corpus; confidence cannot capture that; the emergency numbers (15, 1122) are static text to be replaced by the verified Emergency directory; streaming, document attachments and the API come in Phases 4-5.

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
