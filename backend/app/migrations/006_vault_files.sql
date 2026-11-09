-- Legal Vault, part B: the user's OWN files. The original is kept in private Supabase Storage (never in this database);
-- these tables hold what the app needs to list, search and organise them. Independent of part A (vault_items).
-- Same lock-down as 001: RLS on, no policies.

create table if not exists app.vault_folders (
    id           uuid primary key default gen_random_uuid(),
    user_id      uuid not null references app.users (id) on delete cascade,
    name         text not null,
    color        text not null default '#0ea5e9',
    created_at   timestamptz not null default now()
);
create unique index if not exists vault_folders_name_idx on app.vault_folders (user_id, lower(name));

create table if not exists app.vault_files (
    id            uuid primary key default gen_random_uuid(),
    user_id       uuid not null references app.users (id) on delete cascade,
    folder_id     uuid references app.vault_folders (id) on delete set null,      -- deleting a folder keeps its files
    name          text not null,
    file_type     text not null check (file_type in ('pdf', 'docx', 'jpg', 'png')),
    size_bytes    bigint not null,
    pages         int not null default 1,
    category      text not null default 'Other',
    storage_path  text not null unique,                                            -- <user id>/<random id>.<ext> in the private bucket
    text          text not null default '',                                        -- what was read from the file, for search and the text preview
    text_status   text not null default 'ready' check (text_status in ('ready', 'pending', 'none')),   -- pending: a photo or scan still being read
    favourite     boolean not null default false,
    trashed_at    timestamptz,
    created_at    timestamptz not null default now(),
    updated_at    timestamptz not null default now()
);
create index if not exists vault_files_user_idx on app.vault_files (user_id, trashed_at, updated_at desc);
create index if not exists vault_files_folder_idx on app.vault_files (folder_id) where folder_id is not null;
create index if not exists vault_files_trash_idx on app.vault_files (trashed_at) where trashed_at is not null;
create index if not exists vault_files_pending_idx on app.vault_files (created_at) where text_status = 'pending';

create table if not exists app.vault_file_notes (
    id           uuid primary key default gen_random_uuid(),
    file_id      uuid not null references app.vault_files (id) on delete cascade,
    user_id      uuid not null references app.users (id) on delete cascade,
    text         text not null,
    created_at   timestamptz not null default now()
);
create index if not exists vault_file_notes_idx on app.vault_file_notes (file_id, created_at desc);

create table if not exists app.vault_file_activity (
    id           bigserial primary key,
    file_id      uuid not null references app.vault_files (id) on delete cascade,
    user_id      uuid not null references app.users (id) on delete cascade,
    action       text not null,                     -- uploaded, renamed, moved, categorised, favourited, unfavourited, noted, trashed, restored, downloaded
    created_at   timestamptz not null default now()
);
create index if not exists vault_file_activity_idx on app.vault_file_activity (file_id, created_at desc);

alter table app.vault_folders       enable row level security;
alter table app.vault_files         enable row level security;
alter table app.vault_file_notes    enable row level security;
alter table app.vault_file_activity enable row level security;

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
