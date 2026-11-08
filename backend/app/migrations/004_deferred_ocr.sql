-- A photo attached in chat is stored as soon as it is uploaded (so the upload is instant) and read later, while the answer is prepared.
-- Until then the row is 'pending' and holds the picture in `raw`; once read, `raw` is emptied again: the original file is still never kept.
alter table app.documents add column if not exists status text not null default 'ready' check (status in ('pending', 'ready'));
alter table app.documents add column if not exists raw bytea;
create index if not exists documents_pending_idx on app.documents (created_at) where status = 'pending';
