-- Legal Vault, part A: things the user SAVES from the app (a chat answer, a document analysis, later a case brief).
-- Each item is a snapshot, so it stays readable after the chat or the analysis it came from is deleted or expires.
-- (Uploaded files are part B and get their own tables.) Same lock-down as 001: RLS on, no policies.

create table if not exists app.vault_items (
    id           uuid primary key default gen_random_uuid(),
    user_id      uuid not null references app.users (id) on delete cascade,
    kind         text not null check (kind in ('answer', 'analysis', 'brief')),
    title        text not null,
    summary      text not null default '',                 -- a short preview for the list
    content      jsonb not null,                           -- the snapshot (answer: {question, answer}; analysis: the full result)
    meta         jsonb not null default '{}'::jsonb,       -- {tag, risk, language, conversationId, sources, confidence ...}
    source_id    uuid,                                     -- the message or analysis it was saved from (no foreign key: the source may go away)
    favourite    boolean not null default false,
    trashed_at   timestamptz,                              -- in the Trash until this + VAULT_TRASH_DAYS
    created_at   timestamptz not null default now(),
    updated_at   timestamptz not null default now()
);
-- saving the same thing twice is one item
create unique index if not exists vault_items_source_idx on app.vault_items (user_id, kind, source_id) where source_id is not null;
create index if not exists vault_items_user_idx on app.vault_items (user_id, trashed_at, updated_at desc);
create index if not exists vault_items_trash_idx on app.vault_items (trashed_at) where trashed_at is not null;

create table if not exists app.vault_notes (
    id           uuid primary key default gen_random_uuid(),
    item_id      uuid not null references app.vault_items (id) on delete cascade,
    user_id      uuid not null references app.users (id) on delete cascade,
    text         text not null,
    created_at   timestamptz not null default now()
);
create index if not exists vault_notes_item_idx on app.vault_notes (item_id, created_at desc);

create table if not exists app.vault_activity (
    id           bigserial primary key,
    item_id      uuid not null references app.vault_items (id) on delete cascade,
    user_id      uuid not null references app.users (id) on delete cascade,
    action       text not null,                            -- saved, renamed, favourited, unfavourited, noted, trashed, restored
    created_at   timestamptz not null default now()
);
create index if not exists vault_activity_item_idx on app.vault_activity (item_id, created_at desc);

alter table app.vault_items    enable row level security;
alter table app.vault_notes    enable row level security;
alter table app.vault_activity enable row level security;

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
