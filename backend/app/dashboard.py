"""The dashboard: everything on it comes from the user's own data or from the court calendar, in one call (a single database round trip).

Recent activity = conversations, analyses, saved Vault items and Vault files, newest first. The Vault card shows the REAL storage used by the user's
files. Court holidays come from app/reference/court_calendar.json (collected from news reports of official notifications, with a status and source
per entry). The resource links are official websites that were checked to answer.
"""
from __future__ import annotations

from datetime import date

from . import calendar_service, personas, vault, vault_files
from .db import Database
from .config import DocSettings
from .users_repo import iso

RESOURCES = [
    {"id": "res_laws", "title": "Pakistan Code", "summary": "The official collection of federal laws and ordinances.", "category": "laws", "link": "https://pakistancode.gov.pk"},
    {"id": "res_punjab", "title": "Punjab Laws", "summary": "Provincial Acts, ordinances and rules from the Government of the Punjab.", "category": "laws", "link": "https://punjablaws.gov.pk"},
    {"id": "res_sc", "title": "Supreme Court of Pakistan", "summary": "Judgments, cause lists, rules and notices.", "category": "courts", "link": "https://www.supremecourt.gov.pk"},
    {"id": "res_lhc", "title": "Lahore High Court", "summary": "Cause lists, judgments and notifications, including court calendars.", "category": "courts", "link": "https://www.lhc.gov.pk"},
    {"id": "res_land", "title": "Punjab Land Records Authority", "summary": "Land records, fard and mutation services in the Punjab.", "category": "property", "link": "https://punjab-zameen.gov.pk"},
    {"id": "res_fbr", "title": "Federal Board of Revenue", "summary": "Tax rules, rate cards and circulars, including property taxes.", "category": "tax", "link": "https://www.fbr.gov.pk"},
]

ACTIVITY_SQL = """
(select 'chat' as type, c.id::text as id, c.title as title, coalesce(c.tag, 'Legal chat') as subtitle, c.updated_at as at, 'completed' as status, '/chat/' || c.id as link
   from app.conversations c where c.user_id = %(u)s order by c.updated_at desc limit 6)
union all
(select 'document', a.id::text, coalesce(a.result->'document'->>'name', a.input->>'name', 'Document'), 'Document analysis', coalesce(a.finished_at, a.created_at),
        case a.status when 'completed' then 'analysed' when 'failed' then 'failed' else 'processing' end, '/analysis/' || a.id
   from app.analyses a where a.user_id = %(u)s order by a.created_at desc limit 6)
union all
(select 'saved', i.id::text, i.title, case i.kind when 'answer' then 'Answer saved to your Vault' when 'analysis' then 'Analysis saved to your Vault' when 'calculation' then 'Calculation saved to your Vault' else 'Saved to your Vault' end,
        i.created_at, 'saved', '/vault/item/' || i.id
   from app.vault_items i where i.user_id = %(u)s and i.trashed_at is null order by i.created_at desc limit 6)
union all
(select 'file', f.id::text, f.name, 'File in your Vault', f.created_at, 'saved', '/vault/file/' || f.id
   from app.vault_files f where f.user_id = %(u)s and f.trashed_at is null order by f.created_at desc limit 6)
order by at desc limit 8
"""
RISK_SQL = ("select a.id::text as id, coalesce(a.result->'document'->>'name', a.input->>'name', 'Document') as name, a.result->'overallRisk'->>'level' as level, "
            "coalesce(a.finished_at, a.created_at) as at from app.analyses a where a.user_id = %s and a.status = 'completed' and a.result is not null "
            "order by coalesce(a.finished_at, a.created_at) desc limit 3")
VAULT_SQL = ("select coalesce(sum(size_bytes) filter (where file_type in ('pdf', 'docx')), 0) as docs, coalesce(sum(size_bytes) filter (where file_type in ('jpg', 'png')), 0) as images, "
             "coalesce(sum(size_bytes), 0) as used, count(*) filter (where trashed_at is null) as files from app.vault_files where user_id = %s")


def build(db: Database, cfg: DocSettings, user_id: str, files_enabled: bool, today: date | None = None, user_type: str | None = None) -> dict:
    activity, (v,), (c,), risks = db.batch([(ACTIVITY_SQL, {"u": user_id}), (VAULT_SQL, [user_id]), (vault.COUNTS_SQL, [user_id]), (RISK_SQL, [user_id])])
    used = int(v["used"])
    quota = cfg.vault_quota_mb * 1024 * 1024
    saved = vault.counts_out(c)
    return {
        "activity": [{"id": r["id"], "type": r["type"], "title": r["title"], "subtitle": r["subtitle"], "occurredAt": iso(r["at"]), "status": r["status"], "link": r["link"]} for r in activity],
        "vault": {"usedBytes": used, "quotaBytes": quota, "filesEnabled": files_enabled, "fileCount": int(v["files"]), "savedCount": saved["all"],
                  "breakdown": [{"category": "documents", "label": "Documents (PDF, Word)", "bytes": int(v["docs"])}, {"category": "images", "label": "Photos", "bytes": int(v["images"])}]},
        "resources": RESOURCES,
        "forYou": personas.for_you(user_type),
        "riskPreview": [{"id": r["id"], "name": r["name"], "level": r["level"], "occurredAt": iso(r["at"]), "link": "/analysis/" + r["id"]} for r in risks],
        "holidays": {"items": calendar_service.upcoming(today, limit=6), **calendar_service.meta()},
    }
