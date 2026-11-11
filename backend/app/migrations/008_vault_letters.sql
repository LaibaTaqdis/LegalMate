-- A drafted letter is another kind of Vault item (part A): the template, the facts typed in and the finished text.
alter table app.vault_items drop constraint if exists vault_items_kind_check;
alter table app.vault_items add constraint vault_items_kind_check check (kind in ('answer', 'analysis', 'brief', 'calculation', 'letter'));
