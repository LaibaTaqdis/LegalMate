-- Uploaded documents (extracted text only: the original file is NOT kept) and their analyses. Same lock-down as 001: RLS on, no policies.

create table if not exists app.documents (
    id           uuid primary key default gen_random_uuid(),
    user_id      uuid not null references app.users (id) on delete cascade,
    name         text not null,
    file_type    text not null check (file_type in ('pdf', 'docx', 'jpg', 'png')),
    size_bytes   bigint not null,
    pages        int not null default 1,
    purpose      text not null default 'analysis' check (purpose in ('analysis', 'chat')),
    text         text not null,                       -- what was read from the file, cut to MAX_TEXT_CHARS
    char_count   int not null,
    ocr_pages    int not null default 0,              -- pages that had to be read from an image
    ocr_conf     real,                                -- average OCR confidence (0-1), null when no OCR was needed
    truncated    boolean not null default false,
    created_at   timestamptz not null default now(),
    expires_at   timestamptz                          -- null = kept until the user deletes it
);
create index if not exists documents_user_idx on app.documents (user_id, created_at desc);
create index if not exists documents_expiry_idx on app.documents (expires_at) where expires_at is not null;

create table if not exists app.analyses (
    id           uuid primary key default gen_random_uuid(),
    user_id      uuid not null references app.users (id) on delete cascade,
    document_id  uuid references app.documents (id) on delete set null,     -- the result outlives the stored text
    status       text not null default 'queued' check (status in ('queued', 'processing', 'completed', 'failed')),
    progress     int not null default 0,
    input        jsonb not null default '{}'::jsonb,                 -- {"documentIds": [...]}
    language     text not null default 'auto',
    depth        text not null default 'quick' check (depth in ('quick', 'detailed')),
    result       jsonb,
    error        text,
    created_at   timestamptz not null default now(),
    finished_at  timestamptz,
    expires_at   timestamptz
);
create index if not exists analyses_user_idx on app.analyses (user_id, created_at desc);

alter table app.documents enable row level security;
alter table app.analyses  enable row level security;

do $$
begin
    if exists (select 1 from pg_roles where rolname = 'anon') then
        revoke all on all tables in schema app from anon;
    end if;
    if exists (select 1 from pg_roles where rolname = 'authenticated') then
        revoke all on all tables in schema app from authenticated;
    end if;
end
$$;
