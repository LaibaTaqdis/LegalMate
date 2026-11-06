-- LegalMate knowledge base schema (Supabase Postgres + pgvector).
-- Apply with:  python -m db.load --schema-only      (or paste into the Supabase SQL editor)
-- Embedding model: BAAI/bge-small-en-v1.5 (384 dimensions). Change the dimension here if the model changes.

create extension if not exists vector;

-- ------------------------------------------------------------------ documents (one row per unique law)
create table if not exists law_documents (
    doc_id         text primary key,
    title          text not null,
    year           int,
    doc_type       text,                 -- act | ordinance | order | code | rules | constitution
    jurisdiction   text not null,        -- Federal | Punjab | ICT
    applies_to     text[] not null default '{}',
    tier           text not null,        -- curated | gazette | publisher
    is_amendment   boolean not null default false,
    legal_status   text not null default 'unverified',   -- unverified | repealed
    status_scope   text,                 -- where the status applies (e.g. Punjab)
    status_note    text,
    source_urls    text[] not null default '{}',
    amends         text[] not null default '{}',          -- doc_ids this instrument amends
    amended_by     text[] not null default '{}',          -- doc_ids that amend this law
    n_pages        int,
    source_path    text
);

-- ------------------------------------------------------------------ chunks (one row per retrievable passage)
create table if not exists law_chunks (
    chunk_id        text primary key,
    doc_id          text not null references law_documents(doc_id) on delete cascade,
    ordinal         int not null,
    act_title       text not null,
    year            int,
    doc_type        text,
    jurisdiction    text not null,
    applies_to      text[] not null default '{}',
    tier            text not null,
    legal_status    text not null default 'unverified',
    status_scope    text,
    status_note     text,
    unit_type       text not null,       -- section | article | rule | preamble | tail | passage
    section_no      text,
    section_nums    text[] not null default '{}',          -- every section number covered (exact "section 379" lookups)
    section_label   text,
    heading         text,
    part            text,
    chapter         text,
    order_name      text,
    schedule        text,
    page_start      int,
    page_end        int,
    part_index      int,
    parts_total     int,
    header          text not null,       -- "Act > Chapter > Section - Heading" (embedded with the body)
    body            text not null,       -- exact law wording; this is what gets quoted
    amendment_notes text,
    chunk_hash      text not null,       -- identical text across Federal/Punjab copies shares a hash
    embedding       vector(384),
    fts             tsvector generated always as (
                        setweight(to_tsvector('english', coalesce(header, '')), 'A') ||
                        setweight(to_tsvector('english', coalesce(body, '')), 'B')
                    ) stored
);

-- ------------------------------------------------------------------ indexes (created after the bulk load by db.load)
-- vector search
--   create index law_chunks_embedding_idx on law_chunks using hnsw (embedding vector_cosine_ops) with (m = 16, ef_construction = 64);
-- keyword search
--   create index law_chunks_fts_idx on law_chunks using gin (fts);
create index if not exists law_chunks_doc_idx      on law_chunks (doc_id);
create index if not exists law_chunks_juris_idx    on law_chunks (jurisdiction);
create index if not exists law_chunks_hash_idx     on law_chunks (chunk_hash);
create index if not exists law_chunks_sections_idx on law_chunks using gin (section_nums);

-- ------------------------------------------------------------------ hybrid search (pure-SQL FALLBACK)
-- PRODUCTION uses retrieval.kb.KnowledgeBase: pgvector here + BM25 in the app (see retrieval/lexical.py). Measured on the
-- gold questions Postgres ts_rank_cd is much weaker than BM25 (keyword-only hit@10 75% vs 90%) and ~4x slower, so this
-- function is only a fallback for when the app-side keyword index is unavailable (hybrid hit@10 89% vs 94%).
-- Weighted reciprocal-rank fusion of vector similarity and keyword rank, with a soft jurisdiction preference and
-- de-duplication of identical texts. `lex_query` is a ready tsquery string such as 'landlord | evict | tenant'
-- (OR semantics: long natural-language questions would match nothing under AND).
create or replace function hybrid_search(
    query_embedding   vector(384),
    lex_query         text,
    user_jurisdiction text    default null,
    match_count       int     default 10,
    depth             int     default 50,
    w_vec             float8  default 1.0,
    w_lex             float8  default 1.0,
    rrf_k             int     default 60,
    juris_boost       float8  default 1.15,
    juris_penalty     float8  default 0.70
)
returns table (
    chunk_id text, doc_id text, act_title text, jurisdiction text, section_label text, heading text, header text,
    body text, page_start int, page_end int, legal_status text, status_scope text, amendment_notes text,
    year int, tier text, score float8, cosine float8, rank_vec int, rank_lex int
)
language sql stable
as $$
    with vec as (
        select c.chunk_id,
               row_number() over (order by c.embedding <=> query_embedding)::int as r,
               1 - (c.embedding <=> query_embedding) as cos
        from law_chunks c
        order by c.embedding <=> query_embedding
        limit depth
    ),
    lex as (
        select c.chunk_id,
               row_number() over (order by ts_rank_cd(c.fts, q.tsq, 32) desc)::int as r
        from law_chunks c, (select to_tsquery('english', lex_query) as tsq) q
        where lex_query <> '' and c.fts @@ q.tsq
        order by ts_rank_cd(c.fts, q.tsq, 32) desc
        limit depth
    ),
    fused as (
        select coalesce(v.chunk_id, l.chunk_id) as chunk_id,
               coalesce(w_vec / (rrf_k + v.r), 0) + coalesce(w_lex / (rrf_k + l.r), 0) as rrf,
               v.cos, v.r as rv, l.r as rl
        from vec v full outer join lex l using (chunk_id)
    ),
    scored as (
        select c.*, f.cos, f.rv, f.rl,
               f.rrf * (case
                   when user_jurisdiction is null then 1.0
                   when c.jurisdiction = user_jurisdiction then juris_boost
                   when user_jurisdiction = any (c.applies_to) or c.jurisdiction = 'Federal' or 'Federal' = any (c.applies_to) then 1.0
                   else juris_penalty
               end) as final_score
        from fused f join law_chunks c on c.chunk_id = f.chunk_id
    ),
    deduped as (
        select distinct on (chunk_hash) *
        from scored
        order by chunk_hash, final_score desc
    )
    select d.chunk_id, d.doc_id, d.act_title, d.jurisdiction, d.section_label, d.heading, d.header, d.body,
           d.page_start, d.page_end, d.legal_status, d.status_scope, d.amendment_notes, d.year, d.tier,
           d.final_score, d.cos, d.rv, d.rl
    from deduped d
    order by d.final_score desc
    limit match_count;
$$;

-- Exact lookup when the user names a section: "section 379 PPC", "Article 10".
create or replace function lookup_section(act_like text, section text, match_count int default 5)
returns setof law_chunks
language sql stable
as $$
    select c.* from law_chunks c join law_documents d on d.doc_id = c.doc_id
    where c.act_title ilike '%' || act_like || '%' and c.section_nums @> array[section]
    -- base laws before the amending instruments that merely mention the same section number
    -- then titles that START with the query ("Constitution" -> the Constitution, not "Federal Constitutional Court ... Order")
    order by d.is_amendment, (c.act_title ilike act_like || '%') desc, length(c.act_title),
             case c.tier when 'curated' then 0 when 'publisher' then 1 else 2 end, c.ordinal
    limit match_count;
$$;
