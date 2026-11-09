-- A saved calculation is another kind of Vault item (part A): the inputs and the result as they were.
alter table app.vault_items drop constraint if exists vault_items_kind_check;
alter table app.vault_items add constraint vault_items_kind_check check (kind in ('answer', 'analysis', 'brief', 'calculation'));
