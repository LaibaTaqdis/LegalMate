-- LegalMate application tables (accounts, sessions, chat). Applied automatically by `python -m app.migrate` / API start-up.
--
-- Everything lives in its own schema `app`, which Supabase's public REST API (PostgREST) does not expose.
-- Row Level Security is switched on for every table with NO policies as a second lock: the browser-facing
-- `anon` / `authenticated` roles can read nothing. The API connects as the database owner, which bypasses RLS.

create table if not exists app.users (
    id                    uuid primary key default gen_random_uuid(),
    email                 text not null,
    name                  text not null,
    password_hash         text not null,
    phone                 text,                        -- normalised, e.g. +923001234567
    cnic_last4            text,                        -- only the last 4 digits are kept (data minimisation)
    city                  text,
    address               text,
    role                  text not null default 'client'   check (role in ('client', 'lawyer', 'admin')),
    status                text not null default 'active'   check (status in ('active', 'suspended')),
    preferred_language    text not null default 'en'       check (preferred_language in ('en', 'ur', 'both')),
    profile               jsonb not null default '{}'::jsonb,   -- onboarding answers that give the chatbot context
    profile_completed_at  timestamptz,
    accepted_terms_at     timestamptz,
    created_at            timestamptz not null default now(),
    updated_at            timestamptz not null default now(),
    last_login_at         timestamptz
);
create unique index if not exists users_email_uq on app.users (lower(email));
create unique index if not exists users_phone_uq on app.users (phone) where phone is not null;

-- Refresh tokens are random opaque strings; only their SHA-256 is stored. A rotated (used) token that shows up
-- again means it was stolen: the whole family is revoked.
create table if not exists app.refresh_tokens (
    id            uuid primary key default gen_random_uuid(),
    user_id       uuid not null references app.users (id) on delete cascade,
    family_id     uuid not null,
    token_hash    text not null unique,
    remember      boolean not null default true,
    user_agent    text,
    ip            text,
    created_at    timestamptz not null default now(),
    last_used_at  timestamptz,
    expires_at    timestamptz not null,
    revoked_at    timestamptz
);
create index if not exists refresh_tokens_user_idx on app.refresh_tokens (user_id);
create index if not exists refresh_tokens_family_idx on app.refresh_tokens (family_id);

create table if not exists app.conversations (
    id          uuid primary key default gen_random_uuid(),
    user_id     uuid not null references app.users (id) on delete cascade,
    title       text not null,
    title_auto  boolean not null default true,         -- true until the analyser has named the conversation
    tag         text not null default 'General',
    icon        text not null default 'chat',
    preview     text not null default '',
    pinned      boolean not null default false,
    created_at  timestamptz not null default now(),
    updated_at  timestamptz not null default now()
);
create index if not exists conversations_user_idx on app.conversations (user_id, updated_at desc);

create table if not exists app.messages (
    id                uuid primary key default gen_random_uuid(),
    seq               bigint generated always as identity,
    conversation_id   uuid not null references app.conversations (id) on delete cascade,
    user_id           uuid not null references app.users (id) on delete cascade,
    role              text not null check (role in ('user', 'assistant')),
    kind              text not null check (kind in ('user', 'answer', 'clarify', 'info')),
    content           text not null,                    -- plain text (what the model sees as history)
    payload           jsonb not null default '{}'::jsonb,   -- the full assistant message the UI renders
    attachment_ids    uuid[] not null default '{}',
    feedback          text check (feedback in ('up', 'down')),
    feedback_comment  text,
    meta              jsonb not null default '{}'::jsonb,   -- engine diagnostics (timings, verification); never raw user text
    created_at        timestamptz not null default now()
);
create index if not exists messages_conv_idx on app.messages (conversation_id, seq);
create index if not exists messages_user_day_idx on app.messages (user_id, created_at) where role = 'user';

create table if not exists app.source_reports (
    id          uuid primary key default gen_random_uuid(),
    user_id     uuid not null references app.users (id) on delete cascade,
    message_id  uuid not null references app.messages (id) on delete cascade,
    source_id   int not null,
    reason      text not null default 'user_report',
    created_at  timestamptz not null default now()
);

-- ---- lock-down -----------------------------------------------------------------------------------------
alter table app.users           enable row level security;
alter table app.refresh_tokens  enable row level security;
alter table app.conversations   enable row level security;
alter table app.messages        enable row level security;
alter table app.source_reports  enable row level security;

-- The law tables (public schema) were created without RLS: with Supabase's public API an `anon` key could edit them.
alter table if exists public.law_documents enable row level security;
alter table if exists public.law_chunks    enable row level security;

do $$
begin
    if exists (select 1 from pg_roles where rolname = 'anon') then
        revoke all on schema app from anon;
        revoke all on all tables in schema app from anon;
    end if;
    if exists (select 1 from pg_roles where rolname = 'authenticated') then
        revoke all on schema app from authenticated;
        revoke all on all tables in schema app from authenticated;
    end if;
end
$$;
