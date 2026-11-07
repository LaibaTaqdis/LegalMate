-- The analysis job needs to remember which documents to read. 002 was first applied to a database before this column was added to it,
-- and an applied migration is never edited, so the column is added here. A no-op where 002 already created it.
alter table app.analyses add column if not exists input jsonb not null default '{}'::jsonb;
