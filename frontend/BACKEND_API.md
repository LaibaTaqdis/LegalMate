# LegalMate - Backend API Specification

This document lists every backend API the LegalMate frontend needs to run fully dynamically. The frontend already calls these endpoints through `src/api/services/*`. Set `VITE_USE_MOCKS=false` and `VITE_API_BASE_URL` (see `.env.example`) and the app switches from mock data to your backend with no page changes.

- Base URL: `{VITE_API_BASE_URL}`, for example `https://api.legalmate.pk/api/v1`. Every path below is relative to it.
- Route constants: `src/api/endpoints.js`
- Mock responses (exact shapes the UI expects): `src/api/mocks/*`

---

## Implementation status (what the FastAPI backend in `backend/app` does today)

The frontend switches services to the real backend one by one (`VITE_REAL_SERVICES=auth,chat,profile,documents,vault,calculators,dashboard`, see `frontend/.env.example`). Everything else keeps running on mocks until it is built.

| Area | Status |
|---|---|
| Auth: `register`, `login`, `refresh`, `logout`, `me`, `forgot-password` | **Done.** No OTP step (accounts are usable at once). `forgot-password` always answers 204 but sends no email yet (no mail service). Google sign-in is not built. |
| Account: `GET/PATCH /users/me`, `POST /users/me/password` | **Done.** Email and phone changes are not re-verified yet. |
| Onboarding profile: `GET/PUT /users/me/profile` | **Done** (new, see section 13). It gives the chatbot context about the user. |
| Chat: conversations, streaming messages, feedback, source reports | **Done** (section 5). |
| Chat: `POST /chat/messages/:id/save` (Legal Vault) | **Done** (section 7, part A). |
| Documents: `POST/DELETE /documents`, `POST /analyses`, `GET /analyses/:id`, chat attachments | **Done** (section 6). Text is extracted and stored, the original file is not kept. |
| Analysis: `/analyses/:id/save` | **Done** (section 7, part A). |
| Analysis: `/analyses/:id/report`, `/share` | Answer `501 NOT_IMPLEMENTED` (PDF report and share links are later). |
| Legal Vault part A: saved answers and analyses (`/vault/items`, notes, activity, Trash, `/vault/stats`) | **Done** (section 7). |
| Legal Vault part B: your own uploaded files (`/vault/files`, `/vault/folders`, storage quota) | **Done** (section 7, part B). Originals are kept in private Supabase Storage. |
| Settings: security, sessions, preferences, avatar, export, delete account, integrations | Not built (mock). |
| Dashboard: `GET /dashboard` | **Done** (section 4). Real Vault storage, real recent activity, court holidays and vacations, official links. |
| Legal calculators: limitation, inheritance, compensation, stamp duty, property transfer; court holidays `GET /calendar/court-holidays` | **Done** (section 9). Every result says whether it rests on the law (`law`) or on news reports (`reported`). Court fee is deliberately not offered. |
| Briefs, legal aid, lawyers, bookings, admin, community, emergency, offline, WhatsApp | Not built (mock). |

Limits that exist today: 30 questions per hour and 100 per day per user, one answer at a time per user, 8 failed sign-ins per account per 15 minutes, 6 sign-ups per hour per address, 4000 characters per message.

---

## 1. Conventions

### 1.1 Format
- JSON request and response bodies (`Content-Type: application/json`), except uploads (multipart) and file downloads.
- Field names are **camelCase**.
- Dates are **ISO 8601** strings. Date-only values use `YYYY-MM-DD` (e.g. `dueDate`). The UI formats them for display, so send raw values, not labels.
- File sizes are in bytes (`sizeBytes`). Money is a plain number in PKR.
- The frontend sends `Accept-Language: en` or `ur`, based on the interface language picker. It does NOT decide the chat answer language: that follows what the user writes (see `language` on the chat message request).

### 1.2 Authentication
- JWT bearer tokens: `Authorization: Bearer <accessToken>`.
- Login and register return `{ user, accessToken, refreshToken }`; refresh returns `{ accessToken, refreshToken }`. Register signs the user in immediately (no OTP step).
- The access token should be short-lived (about 15 min). The refresh token is long-lived and rotated on each refresh.
- On `401`, the frontend calls `POST /auth/refresh` once and retries the request. If the refresh fails, the user is sent to `/login`.
- All endpoints require auth except the ones under `/auth/*` marked **public**.

### 1.3 Errors
Every non-2xx response uses this shape:
```json
{ "error": { "code": "VALIDATION_ERROR", "message": "Email is already registered.", "details": { "field": "email" } } }
```
The frontend shows `error.message` to the user, so write it in plain, user-friendly language.

| Status | When |
|---|---|
| 400 | Validation error (`VALIDATION_ERROR`) |
| 401 | Missing/expired token (`UNAUTHORIZED`) |
| 403 | Not allowed (`FORBIDDEN`) |
| 404 | Not found (`NOT_FOUND`) |
| 409 | Conflict, e.g. duplicate (`CONFLICT`) |
| 413 | File too large (`FILE_TOO_LARGE`, limit 10 MB) |
| 415 | Unsupported file type (`UNSUPPORTED_TYPE`) |
| 422 | Business rule failed (`UNPROCESSABLE`) |
| 429 | Rate limited (`RATE_LIMITED`) |
| 500 | Server error (`INTERNAL`) |

### 1.4 Lists and pagination
```json
{ "items": [ ... ], "total": 19, "page": 1, "pageSize": 50 }
```
Query params: `page` (1-based) and `pageSize` (default 50).

### 1.5 Uploads
`multipart/form-data` with the file in a field named **`file`**, plus the extra form fields listed per endpoint. Accepted types: PDF, DOCX, JPG, PNG (vault uploads also accept XLSX). Max size: 10 MB. The frontend shows upload progress, so do not buffer the whole request behind a proxy.

### 1.6 Downloads
File endpoints return the binary with `Content-Type` and `Content-Disposition: attachment; filename="..."`. They are called with the bearer token.

### 1.7 Streaming (AI chat)
`POST /chat/conversations/:id/messages` responds with **Server-Sent Events** (`text/event-stream`). See section 5.

---

## 2. Endpoint summary

| # | Method | Path | Used by (page) |
|---|---|---|---|
| **Auth** |||
| 1 | POST | `/auth/login` | Login |
| 2 | GET | `/auth/google` | Login (redirect) |
| 3 | POST | `/auth/register` | Signup (signs in at once, no OTP) |
| 6 | POST | `/auth/forgot-password` | Login |
| 7 | POST | `/auth/refresh` | API client (automatic) |
| 8 | POST | `/auth/logout` | Top bar, Settings |
| 9 | GET | `/auth/me` | App start (session restore) |
| **Dashboard and notifications** |||
| 10 | GET | `/dashboard` | Dashboard |
| 11 | GET | `/notifications` | Top bar bell |
| 12 | POST | `/notifications/read-all` | Top bar bell |
| 13 | POST | `/notifications/:id/read` | Top bar bell |
| **Legal Chat** |||
| 14 | GET | `/chat/conversations` | Chat sidebar |
| 15 | POST | `/chat/conversations` | Chat (new question, topic cards, top-bar search) |
| 16 | GET | `/chat/conversations/:id` | Chat conversation |
| 17 | PATCH | `/chat/conversations/:id` | Chat (rename) |
| 18 | DELETE | `/chat/conversations/:id` | Chat sidebar menu |
| 19 | PUT | `/chat/conversations/:id/pin` | Chat sidebar menu |
| 20 | POST | `/chat/conversations/:id/messages` (SSE) | Chat composer |
| 21 | POST | `/chat/messages/:id/feedback` | Answer thumbs, Sources panel |
| 22 | POST | `/chat/messages/:id/save` | "Save to Vault" chip |
| 23 | POST | `/chat/sources/report` | Sources panel |
| **Documents and analysis** |||
| 24 | POST | `/documents` (multipart) | Upload page, chat attachments |
| 25 | DELETE | `/documents/:id` | Upload queue (remove) |
| 26 | POST | `/analyses` | Upload page "Analyse Document" |
| 27 | GET | `/analyses/:id` | Analysis result (polled) |
| 28 | GET | `/analyses/:id/report` | "Download Report" |
| 29 | POST | `/analyses/:id/save` | "Save to Vault" |
| 30 | POST | `/analyses/:id/share` | "Share" |
| **Legal Vault** (both parts are BUILT: `/vault/items...` is part A, `/vault/files...` and `/vault/folders` are part B; section 7 has the current API. Rows 32-45 below are the original design) |||
| 31 | GET | `/vault/stats` | Vault sidebar, Settings (part A: counts; part B adds storage) |
| 32 | GET | `/vault/folders` | Vault, Document view (move) |
| 33 | POST | `/vault/folders` | Vault "New Folder" |
| 34 | GET | `/vault/documents` | Vault list |
| 35 | POST | `/vault/documents` (multipart) | Vault "Upload Document" |
| 36 | GET | `/vault/documents/:id` | Document view |
| 37 | PATCH | `/vault/documents/:id` | Rename, move, tags |
| 38 | DELETE | `/vault/documents/:id` | Delete (to Trash) |
| 39 | PUT | `/vault/documents/:id/favourite` | Star |
| 40 | POST | `/vault/documents/:id/copy` | "Make a Copy" |
| 41 | GET | `/vault/documents/:id/file` | Download |
| 42 | GET | `/vault/documents/:id/content` | Document viewer pages |
| 43 | GET | `/vault/documents/:id/notes` | Notes tab |
| 44 | POST | `/vault/documents/:id/notes` | Notes tab |
| 45 | GET | `/vault/documents/:id/activity` | Activity tab |
| **Case briefs** |||
| 46 | GET | `/case-briefs/draft` | Create AI Case Brief |
| 47 | PUT | `/case-briefs/draft` | Autosave / Save Draft |
| 48 | POST | `/case-briefs/attachments` (multipart) | Attach documents |
| 49 | DELETE | `/case-briefs/attachments/:id` | Remove attachment |
| 50 | POST | `/case-briefs` | "Generate Brief" |
| 51 | GET | `/case-briefs/:id` | Brief view (polled while generating) |
| 52 | POST | `/case-briefs/:id/regenerate` | "Regenerate" |
| 53 | GET | `/case-briefs/:id/export?format=pdf\|docx` | Download / Export |
| 54 | POST | `/case-briefs/:id/save` | "Add to Legal Vault" |
| 55 | POST | `/case-briefs/:id/invites` | Share → Invite People |
| 56 | PUT | `/case-briefs/:id/share-link` | Share → Secure Link |
| **Legal calculator** |||
| 57 | POST | `/calculators/:type/calculate` | Calculator |
| 58 | POST | `/calculators/saved` | "Save Calculation" |
| 59 | GET | `/calculators/saved/:id/summary` | "Download Summary" |
| **Legal aid** |||
| 61 | GET | `/legal-aid/providers` | Find a Lawyer search (list/map) |
| 63 | PUT | `/legal-aid/providers/:id/save` | Heart (save) |
| 64 | GET | `/legal-aid/emergency-contacts` | Find a Lawyer (emergency banner) |
| **Offline** |||
| 65 | GET | `/offline/manifest` | Offline cache |
| 66 | POST | `/sync` | Offline "Try Again" / auto-sync |
| **WhatsApp** |||
| 67 | GET | `/whatsapp` | WhatsApp page |
| 68 | POST | `/whatsapp/connect` | "Connect WhatsApp" |
| 69 | DELETE | `/whatsapp` | Disconnect |
| 70 | GET | `/whatsapp/qr` | QR code |
| 71 | GET | `/whatsapp/commands` | Example commands |
| 72 | POST | `/whatsapp/test-message` | "Send Test Message" |
| 73 | POST | `/whatsapp/preview` | Phone preview replies |
| 74 | POST | `/webhooks/whatsapp` | WhatsApp Business API (server-to-server) |
| **Settings** |||
| 75 | GET | `/users/me` | Settings → Profile |
| 76 | PATCH | `/users/me` | Save profile |
| 76a | GET, PUT | `/users/me/profile` | Profile setup (onboarding questions that give the chatbot context) |
| 77 | POST | `/users/me/avatar` (multipart) | Change photo |
| 78 | POST | `/users/me/password` | Change password |
| 79 | GET | `/users/me/security` | 2FA / login alerts |
| 80 | PATCH | `/users/me/security` | Toggle 2FA / alerts |
| 81 | GET | `/users/me/sessions` | Active sessions |
| 82 | DELETE | `/users/me/sessions/:id` | Sign out a device |
| 83 | GET | `/users/me/preferences` | Notifications, region, privacy, appearance, offline |
| 84 | PATCH | `/users/me/preferences` | Any preference toggle |
| 85 | POST | `/users/me/export` | "Request Export" |
| 86 | DELETE | `/users/me` | "Delete Account" |
| 87 | GET | `/users/me/integrations` | Connected Apps |
| 88 | POST | `/users/me/integrations/:provider` | Connect Google |
| 89 | DELETE | `/users/me/integrations/:provider` | Disconnect |
| **Emergency Mode** |||
| 90 | GET | `/emergency/contacts` | Emergency Mode |
| 91 | GET | `/emergency/personal-contacts` | Emergency Mode |
| 92 | POST | `/emergency/personal-contacts` | Emergency Mode "Add Contact" |
| 93 | DELETE | `/emergency/personal-contacts/:id` | Emergency Mode "Remove" |
| 94 | POST | `/emergency/alert` | Emergency Mode "Send Emergency Alert" |
| **Find a Lawyer marketplace** |||
| 95 | GET | `/lawyers` | Find a Lawyer |
| 96 | GET | `/lawyers/:id` | Lawyer Profile |
| 97 | POST | `/bookings` | Booking "Confirm & Continue to Payment" |
| 98 | GET | `/bookings/:id` | Payment |
| 99 | GET | `/bookings/mine` | (client bookings; also lawyer portal) |
| 100 | POST | `/bookings/:id/pay` | Payment "Confirm Booking" / "I've Sent the Payment" |
| 117 | POST | `/lawyers/apply` | "Apply to join LegalMate" (lawyer onboarding) |
| **Admin** |||
| 101 | GET | `/admin/stats` | Admin Dashboard |
| 102 | GET | `/admin/lawyers` | Admin Lawyers directory + Pending Applications (same response, filtered client-side) |
| 103 | PUT | `/admin/lawyers/:id` | Admin Lawyers "View" actions / Pending Applications "Approve" / "Reject" |
| 104 | GET | `/admin/users` | Admin Users |
| 105 | PUT | `/admin/users/:id` | Admin Users "Suspend" / "Activate" |
| 106 | GET | `/admin/bookings` | Admin Bookings & Payments |
| 107 | POST | `/admin/bookings/:id/paid` | Admin Bookings & Payments "Mark Received" |
| **Community Q&A** |||
| 108 | GET | `/community/categories` | Community Q&A |
| 109 | GET | `/community/questions` | Community Q&A |
| 110 | GET | `/community/questions/:id` | Question view |
| 111 | POST | `/community/questions` | Ask a Question "Post Question" |
| 112 | POST | `/community/questions/:id/answers` | Question view "Post Answer" |
| **Lawyer portal** |||
| 113 | PATCH | `/lawyers/:id` | Lawyer Profile "Save Changes" |
| 114 | GET | `/bookings?lawyerId=` | Consultations |
| 115 | POST | `/bookings/:id/complete` | Consultations "Mark Completed" |
| 116 | GET | `/lawyers/:id/earnings` | Payments |

---

## 3. Auth

### User object
```json
{
  "id": "usr_arfah",
  "name": "Arfah Rizwan",
  "email": "arfah@example.com",
  "phone": "300 1234567",
  "phoneCountryCode": "+92",
  "cnic": "35202-1234567-1",
  "cnicVerified": true,
  "city": "Islamabad",
  "address": "House 12, Street 4, G-11/2, Islamabad",
  "avatarUrl": null,
  "role": "client",
  "roleLabel": "Citizen Account",
  "preferredLanguage": "en", "profileCompleted": true, "joinedAt": "2026-11-06T10:00:00+00:00"
}
```
The frontend derives `initials` and `firstName` itself if you do not send them. `role` is one of `client`, `lawyer`, `admin` and decides which app shell (nav + routes) the frontend renders after login — see `src/context/AuthContext.jsx`'s `homeFor()`. A `lawyer` user's response should also include `lawyerId`, the id of their row in `/lawyers` (so the lawyer portal can load "my profile").

### POST `/auth/login` (public)
```json
// request
{ "identifier": "arfah@example.com or 03001234567", "password": "••••••••", "remember": true, "role": "client|lawyer|admin" }
// 200
{ "user": { ...User }, "accessToken": "jwt", "refreshToken": "opaque" }
```
`role` is the tab the person picked on the sign-in screen (Client/Lawyer/Admin); reject the login with `403 FORBIDDEN` if the account's actual role does not match it, rather than silently logging them into the wrong portal. `401 INVALID_CREDENTIALS` for a wrong email/phone or password. Too many failed attempts: `429 RATE_LIMITED` with `Retry-After`.

### GET `/auth/google?redirect=<url>` (public)
Starts Google OAuth. After the callback, redirect to `redirect` with tokens delivered securely (e.g. a short-lived one-time `code` that the frontend exchanges, or HttpOnly cookies).

### POST `/auth/register` (public)
```json
// request
{ "fullName": "Arfah Rizwan", "email": "arfah@example.com", "password": "Str0ng!pass", "acceptedTerms": true,
  "phone": "+923001234567", "cnic": "35202-1234567-1", "preferredLanguage": "en|ur|both" }
// 201
{ "user": { ...User }, "accessToken": "jwt", "refreshToken": "opaque" }
```
`phone`, `cnic` and `preferredLanguage` are optional. Validation: valid email; password of at least 8 characters with one uppercase letter, one number and one special character; `acceptedTerms` must be true; phone is a Pakistani mobile number in any common form (stored as `+923001234567`); CNIC format `XXXXX-XXXXXXX-X`. `409 CONFLICT` (with `details.field` = `email` or `phone`) if already registered. Only the last 4 digits of the CNIC are stored, and `User.cnic` comes back masked (`*****-***567-1`). Rate limited per address. Public registration only creates `client` accounts; admins and lawyers are created with `python -m app.create_admin`.

### POST `/auth/forgot-password` (public)
`{ "identifier": "email or phone" }` → `204`. Always returns 204, even when no account exists, so the endpoint cannot be used to check whether an account exists. **No email is sent yet** (no mail service in this version).

### POST `/auth/refresh` (public)
`{ "refreshToken": "..." }` → `{ "accessToken": "...", "refreshToken": "..." }`. The old refresh token stops working. Presenting a rotated token again (after a 10 second grace for two tabs racing) signs that whole login session out. `401 INVALID_REFRESH` or `TOKEN_EXPIRED`.

### POST `/auth/logout`
`{ "refreshToken": "..." }` → `204` (ends that login session; works even when the access token has expired).

### GET `/auth/me`
→ `User`

---

## 4. Dashboard and notifications

### GET `/dashboard` (built)
One call, one database round trip. Everything comes from the user's own data or from the court calendar.
```json
{
  "activity": [
    { "id": "...", "type": "chat|document|saved|file", "title": "Tenancy rights in Pakistan",
      "subtitle": "Chat with LegalMate", "occurredAt": "2026-09-23T10:24:00+00:00",
      "status": "completed|analysed|processing|failed|saved", "link": "/chat/<id>" }
  ],
  "vault": {
    "usedBytes": 2516582, "quotaBytes": 52428800, "filesEnabled": true, "fileCount": 3, "savedCount": 5,
    "breakdown": [ { "category": "documents|images", "label": "Documents (PDF, Word)", "bytes": 1500000 } ]
  },
  "resources": [ { "id": "res_laws", "category": "laws|courts|property|tax", "title": "Pakistan Code", "summary": "...", "link": "https://pakistancode.gov.pk" } ],
  "holidays": {
    "items": [ { "id": "...", "title": "Quaid-e-Azam Day", "kind": "holiday|vacation|optional", "courts": ["all"], "courtNames": ["All courts (public holiday)"],
                 "start": "2026-12-25", "end": "2026-12-25", "days": 1, "status": "notified|reported|expected", "source": "ARY News, 19 Jan 2026 (...)",
                 "url": null, "ongoing": false, "daysUntil": 46 } ],
    "verifiedOn": "2026-11-09", "note": "...", "notYetAnnounced": "...", "courts": { "lhc": "Lahore High Court and Punjab courts" }
  }
}
```
* `usedBytes` is the real total of the user's stored Vault files (including those in the Trash, which still use storage until purged). `quotaBytes` is `VAULT_QUOTA_MB`.
* `activity` is the 8 newest of: chats, document analyses, items saved to the Vault, and Vault files. `link` is a frontend route.
* `resources` are official websites (external links). `holidays.items` are the 6 nearest court holidays and vacations that have not finished yet.
* The calendar data is in `backend/app/reference/court_calendar.json`. Each entry has a status: `notified` (reported with its notification date), `reported` (one or two outlets) or `expected` (worked out from a published rule or a fixed national day). It was collected from news reports because the courts' own notifications could not be fetched, and it is dated (`verifiedOn`). Update the file when a new notification is issued.
* The WhatsApp card on the dashboard is static until the WhatsApp module is built.

### GET `/calendar/court-holidays?limit=&court=&all=` (built)
`court` = `lhc` | `ihc` | `sc` | `fcc` (also returns the public holidays). `all=true` returns past entries too. Same item shape as `holidays` above, plus the notes.

### GET `/notifications?limit=10`
```json
{ "unreadCount": 3, "items": [
  { "id": "ntf_1", "type": "deadline|analysis|chat", "title": "Court Hearing - Civil Case",
    "text": "Hearing on 25 Sep at District Court, Islamabad.", "createdAt": "...", "read": false, "link": "/dashboard" }
] }
```
### POST `/notifications/read-all` → `204`
### POST `/notifications/:id/read` → `204`

---

## 5. Legal Chat (AI assistant with citations and confidence)

### Conversation
```json
{ "id": "conv_1", "title": "Tenant rights in Pakistan", "tag": "Property Law",
  "preview": "What are my rights if the landlord...", "icon": "chat|briefcase|doc|home|message|file|person",
  "pinned": false, "updatedAt": "2026-09-24T10:24:00+05:00" }
```
The frontend groups conversations into Today, Previous 7 Days and Older using `updatedAt`. Pinned conversations go under Today.

### Messages
User message:
```json
{ "id": "msg_1", "role": "user", "content": "What are my rights if...", "attachmentIds": [], "createdAt": "..." }
```
Assistant message (structured answer):
```json
{
  "id": "msg_2", "role": "assistant", "createdAt": "...",
  "intro":   ["In general, your landlord cannot increase the rent ... unless ", { "b": "both parties" }, " agree. ", { "cite": 1 }],
  "lawTitle": "What the law generally says",
  "law":     ["Under the Rent Act, 2009, ... ", { "cite": 1 }, " ", { "cite": 2 }],
  "assumptions": "I assumed you are the tenant in Punjab.",          // optional: what the answer had to assume (empty string when nothing)
  "steps":   [["Review your rental agreement for any rent increase clause."], ["... ", { "cite": 3 }]],   // 3 to 6 steps
  "prepare": ["Your rent receipts", "The notice, with dates"],        // optional: up to 4 things to keep ready (plain text, no legal claims)
  "important": "Do not stop paying rent without legal advice...",
  "outro":   "If you share your city, I can also guide you on local rules.",
  "sources": [
    { "id": 1, "title": "The Rent Act, 2009", "section": "Section 4 - Tenancy Agreement", "type": "Act|Rule|Judgment",
      "quote": "“The terms of a written tenancy agreement shall be binding...”", "url": "https://..." }
  ],
  "confidence": { "score": 87, "relevance": 92, "agreement": 84, "recency": 86, "checked": 4, "verifiedAt": "..." },
  "followUps": ["Optional suggested next questions (0-2)"],
  "feedback": null
}
```
Extra fields on each source: `quoteVerified` (false when the quoted text could not be matched word for word in the law's text; show a warning), `pages` (`"p. 4"`), `jurisdiction` (`Federal|Punjab|ICT`), `status` and `note` (for example "Amended later by ..." or "Marked repealed in Punjab ...": show it next to the source). `kind` is `"answer"`.

Other assistant message kinds (the UI renders each differently):
```json
// kind "clarify": the question was too general. Show the options as tappable chips; the user's choice is sent as an ordinary next message.
{ "id": "msg_3", "role": "assistant", "kind": "clarify", "intro": "To give you accurate guidance I need a little more information...",
  "questions": [ { "id": "q1", "text": "Are you the tenant or the landlord?", "options": ["Tenant", "Landlord"] } ], "createdAt": "..." }
// Up to 3 questions with 2 to 5 options each. The options never include "Other": the UI adds its own "Other..." chip that opens a blank text box, and a
// "Skip the questions and answer anyway" link. The answers are sent as one ordinary user message ("<question> <answer> <question> <answer>").
// kind "info": a plain reply with no sources (greeting, out of scope, nothing found in the database).
{ "id": "msg_4", "role": "assistant", "kind": "info", "reason": "greeting|out_of_scope|unclear|no_source", "text": "Hello! I can explain Pakistani law...", "createdAt": "..." }
```
The assistant asks on a FIRST message that leaves out two or more decisive facts (who the user is in the matter, what happened, the stage, the place when the law differs). It asks at most one round per conversation; after the user answers (or skips), it always answers and states its assumptions.
**Rich text** (`intro`, `law`, each item in `steps`) is an array of plain strings, `{ "b": "bold text" }` and `{ "cite": <source id> }`. Citation numbers must match `sources[].id`. Clicking a citation opens the Sources panel on that source.

**Confidence** values are percentages (0-100). The UI labels 80 and above as "High Confidence" and 60-79 as "Medium Confidence". Compute them from your retrieval/verification pipeline:
- `relevance`: how well the retrieved sources match the question.
- `agreement`: how consistently the sources support the answer.
- `recency`: how current the sources are.
- `checked`: number of sources evaluated.

### GET `/chat/conversations`
→ `{ "items": Conversation[] }`, most recent first.

### POST `/chat/conversations`
```json
{ "firstMessage": "How do I file for divorce in Lahore?", "topic": "tenant-rights|employment|inheritance|consumer|null" }
// 201
{ "conversation": { ...Conversation } }
```
Creates the empty conversation with a provisional `title` (a topic card's own title, otherwise the start of the question) and `tag` `General`. The frontend then sends the first message with endpoint 20, and the stream's `conversation` event carries the real generated `title`/`tag` (once, until the user renames it).

### GET `/chat/conversations/:id`
→ `{ "conversation": Conversation, "messages": Message[] }` (oldest first)

### PATCH `/chat/conversations/:id`
`{ "title": "..." }` → `Conversation`
### DELETE `/chat/conversations/:id` → `204`
### PUT `/chat/conversations/:id/pin`
`{ "pinned": true }` → `204`

### POST `/chat/conversations/:id/messages` (SSE stream)
```json
// request
{ "content": "Can my landlord increase rent?", "attachmentIds": ["doc_1"], "language": "auto|en|ur|ur-roman" }
// language: omitted or "auto" = answer in the language the question is written in (English, Urdu script, or Roman Urdu = Urdu in Latin letters).
// "en" / "ur" / "ur-roman" force one. The answer message carries "language" (en|ur|ur-roman); the frontend uses it for headings and direction.
```
The response is `Content-Type: text/event-stream`:
```
event: status
data: {"state":"thinking"}

event: status
data: {"state":"searching_sources"}

event: status
data: {"state":"writing_answer"}

event: conversation
data: { ...Conversation (new title/tag/preview/updatedAt) }

event: answer
data: { ...assistant Message (full JSON, any kind) }
```
- Store both the user message and the assistant message.
- If something fails, the stream ends with `event: error` and `data: {"code":"UNAVAILABLE|RATE_LIMITED|INTERNAL","message":"..."}`; the unanswered user message is removed, so the user can simply send it again. A `: keep-alive` comment line is sent every 10 seconds on slow answers. Checks that fail before streaming starts (not your conversation, empty text, rate limits, attachments) are ordinary HTTP errors: `404`, `400`, `429`, `422`.
- Token streaming (`event: delta`) is not used: the answer is verified in full before it is sent, so the UI shows the progress labels instead.
- Update the conversation's `preview` and `updatedAt`.

### POST `/chat/messages/:id/feedback`
`{ "vote": "up|down", "comment": "optional" }` → `204`. `comment: "sources"` means the vote came from the Sources panel.

### POST `/chat/messages/:id/save`
Saves the answer to the Legal Vault as a snapshot (the question, the answer and its sources) → `{ "id": "<vault item id>", "alreadySaved": false }`. Saving the same answer again returns the same id with `alreadySaved: true` (and takes it out of the Trash if it was there). `422` if the message is not an answer, `404` if it is not the user's, `422 QUOTA_EXCEEDED` when the Vault is full. Same as `POST /vault/items` with `{ "kind": "answer", "messageId" }`. `GET /chat/conversations/:id` marks saved answers with `savedToVault: true`.

### POST `/chat/sources/report`
`{ "messageId": "msg_2", "sourceId": 1, "reason": "user_report" }` → `204`

---

## 6. Documents and analysis

### POST `/documents` (multipart)
Fields: `file`, `purpose` (`analysis` | `chat`), `saveToVault` (`true|false`)
```json
// 201
{ "id": "uuid", "name": "Rental_Agreement.pdf", "sizeBytes": 2516582, "fileType": "pdf", "pages": 12,
  "ocrUsed": false, "urdu": false, "truncated": false, "charCount": 18234, "warnings": [], "expiresAt": "2026-12-07T10:00:00+00:00" }
```
The type is decided from the file's bytes (PDF, Word `.docx`, JPG, PNG), not its name. Text is extracted at once; scans and photos are read with OCR in English and Urdu (`urdu: true` when Urdu was read; Urdu from an image carries a warning); **the original file is not kept**. `warnings` are plain sentences to show the user (for example "Part of this document was read from an image. Please double-check amounts, dates and names."). Errors: `415 UNSUPPORTED_TYPE`, `413 FILE_TOO_LARGE`, `422` with `code` `TOO_MANY_PAGES`, `PASSWORD_PROTECTED`, `UNREADABLE`, `NO_TEXT`, `TOO_LARGE_IMAGE`, `QUOTA_EXCEEDED`, `429 RATE_LIMITED`. Limits (size, pages, quota, retention) come from environment variables on the server. Not virus-scanned yet. `saveToVault` is accepted but ignored (a warning says so).

In chat, send the returned `id`s as `attachmentIds` of `POST /chat/conversations/:id/messages` (at most `ATTACHMENTS_PER_MESSAGE`, default 3). User messages come back with `attachments: [{ "id", "name" }]`.

### DELETE `/documents/:id`
Discards an uploaded, not-yet-analysed file → `204`.

### GET `/analyses` (analysis history)
Query: `q` (name search, max 80), `risk` (`all|High|Medium|Low`), `status` (`all|completed|running|failed`), `days` (0 = any time, otherwise only the last N days), `sort` (`newest|oldest|name|risk`), `page`, `pageSize` (default `ANALYSIS_PAGE_SIZE`, max 50). Only the signed-in user's analyses.
```json
{ "items": [ { "id": "uuid", "status": "completed|processing|failed", "progress": 100, "error": null, "name": "Rental Agreement.pdf", "fileType": "pdf",
               "documentType": "Tenancy Agreement", "risk": "High", "counts": { "clauses": 8, "deadlines": 2, "missing": 3 },
               "createdAt": "...", "finishedAt": "...", "expiresAt": "..." } ],
  "total": 12, "page": 1, "pageSize": 10,
  "counts": { "all": 12, "completed": 10, "running": 1, "failed": 1, "High": 3, "Medium": 3, "Low": 4 } }
```
`counts` are over everything the user has (they feed the filter chips), not just the current filter. `risk` is `null` until the analysis completes.

### DELETE `/analyses/:id` → `204`
Removes the analysis and the stored text of the document(s) it was made from (unless another analysis still uses them). `404` if it is not the user's.

### POST `/analyses`
```json
{ "documentIds": ["doc_1"], "language": "auto|en|ur", "depth": "quick|detailed", "saveToVault": true }
// 202
{ "id": "uuid", "status": "queued" }
```
Runs as a background job: one model call, about 20-60 s. Up to `ANALYSIS_MAX_DOCS` (default 3) documents are analysed together. `429` while the user already has `ANALYSIS_PER_USER_RUNNING` jobs running. No notification is sent yet.

### GET `/analyses/:id`
The frontend polls every 3 s while `status` is `queued` or `processing`.
```json
{
  "id": "ana_1", "status": "queued|processing|completed|failed", "progress": 100, "error": null,
  "document": { "id": "doc_1", "vaultDocumentId": "tenancy", "name": "Tenancy Agreement.pdf", "fileType": "pdf",
                "documentType": "Tenancy Agreement", "pages": 12, "sizeBytes": 2516582,
                "uploadedAt": "...", "thumbnailUrl": "https://... (optional)" },
  "overallRisk": { "level": "Low|Medium|High", "note": "Some important issues require attention." },
  "counts": { "clauses": 8, "deadlines": 2, "missing": 3 },
  "summary": "Plain-language summary...",
  "clauses": [ { "id": "c1", "title": "Tenancy Duration", "reference": "Clause 2.1", "risk": "Low|Medium|High",
                 "summary": "Fixed term of 12 months.", "detail": "Longer explanation..." } ],
  "risks": [ { "id": "r1", "title": "Early Termination Risk", "description": "...", "level": "High" } ],
  "riskDistribution": { "high": 2, "medium": 4, "low": 2 },
  "obligations": ["Pay rent by the 5th of each month."],
  "importantDates": ["1 Jan 2026 - Tenancy starts."],
  "missingInformation": ["Inventory list of furniture and fixtures."],
  "citations": [ { "id": "l1", "title": "The Rent Act, 2009", "reference": "Section 4 - Tenancy Agreement",
                   "type": "Act|Judgment|Rule", "url": null } ],
  "recommendedActions": ["Consider negotiating the termination clause."],
  "notes": ["Plain sentences about anything that could not be verified: quotes that did not match word for word, figures not found in the document, scans that were hard to read, text that was cut for length."]
}
```
Extra fields: each clause and risk carries `quote` (the document's exact words, or the closest real sentence) and `quoteVerified`. `counts`, `riskDistribution` and `overallRisk` are computed from the findings. `citations` are the laws that deal with the kinds of terms found (see below); the page hides the box when there are none.

**Related laws.** The model only classifies: `category` (tenancy, employment, property, loan, business, contract, notice, court, other), `jurisdictionHint` (`Punjab` or `ICT` when the document names a place there) and, per clause, `topics` (0 to 2 keys from a fixed list). Code then looks up the REAL text of the sections that a reviewed table (`backend/app/law_refs.py`) assigns to those topics. Province-specific laws are used only when the province is known (from the document, else the user's profile: `jurisdiction` in the result); otherwise a `notes` entry says so. A topic with no governing section (for example security deposits) shows no law.
```json
{ "citations": [ { "id": "l1", "title": "Punjab Rented Premises Act, 2009", "reference": "Section 15 - Grounds for eviction", "type": "Act|Rule",
                   "jurisdiction": "Punjab", "url": "https://... or null", "quote": "the law's own wording, cut at a sentence end",
                   "note": "Amended later by ... / Marked as repealed ... or null", "topics": ["Eviction and ending a tenancy"], "clauseIds": ["c2"] } ],
  "citationsNote": "These laws deal with the kind of terms in your document... they do not say whether your document follows them.",
  "clauses": [ { "id": "c2", "topics": ["eviction"], "lawRefs": ["l1"] } ], "category": "tenancy", "jurisdiction": "Punjab" }
```
A clause that has a matching law always keeps its main law in the list, even when the box limit would cut it. While running, `GET` returns `{ id, status, progress, error, document: { name } }`; on failure `status: "failed"` and `error` is a plain sentence.

### GET `/analyses/:id/report`
PDF report download. **Not built yet: answers `501 NOT_IMPLEMENTED`.**
### POST `/analyses/:id/save`
Saves the finished analysis to the Legal Vault as a snapshot → `{ "id": "<vault item id>", "alreadySaved": false }` (`422` while it is still running or failed). Same as `POST /vault/items` with `{ "kind": "analysis", "analysisId" }`. Starting an analysis with `saveToVault: true` saves it automatically when it completes. `GET /analyses/:id` returns `savedToVault: true|false` once it is complete.
### POST `/analyses/:id/share`
→ `{ "url": "https://legalmate.pk/s/analysis/abc" }` (read-only, expiring link)

---

## 7. Legal Vault

The Vault is built in two independent parts. **Part A (built)** keeps what the user saves from the app: chat answers and analyses, as snapshots that stay readable after the chat or the analysis is deleted. **Part B (built)** keeps the user's own uploaded files. They share only the Vault page (two tabs) and `GET /vault/stats`.

### Part A: saved items

```json
SavedItem = { "id": "uuid", "kind": "answer|analysis|brief", "title": "...", "summary": "first ~240 characters",
  "tag": "Property Law|Tenancy Agreement|null", "risk": "Low|Medium|High|null", "language": "en|ur|ur-roman|null", "confidence": 94,
  "conversationId": "uuid|null", "sourceId": "uuid|null (the message or analysis it came from)", "favourite": false, "noteCount": 2,
  "savedAt": "...", "updatedAt": "...", "trashedAt": "...|null" }
```
`GET /vault/items/:id` adds `content`: for an answer `{ "question": "...", "answer": <the assistant Message as it was> }`, for an analysis the analysis result (same shape as `GET /analyses/:id`).

| Method | Path | Notes |
|---|---|---|
| POST | `/vault/items` | `{ "kind": "answer", "messageId" }` or `{ "kind": "analysis", "analysisId" }` → `201 { id, alreadySaved }`. `kind: "brief"` is `422` until case briefs are real. |
| GET | `/vault/items` | Query: `category` (`all` default, `answer`, `analysis`, `brief`, `favourites`, `trash`), `q` (title, summary, question), `sort` (`updated_desc` default, `updated_asc`, `name_asc`, `name_desc`), `page`, `pageSize` (default 24, max 100) → `{ items, total, page, pageSize, counts }` |
| GET | `/vault/stats` | → `{ counts: { all, answer, analysis, brief, favourites, trash } }` (the Trash is not counted in `all`) |
| GET | `/vault/items/:id` | SavedItem + `content` (readable while in the Trash) |
| PATCH | `/vault/items/:id` | `{ "title" }` (1-160 characters) → SavedItem. `404` while in the Trash. |
| PUT | `/vault/items/:id/favourite` | `{ "favourite": true }` → `204` |
| DELETE | `/vault/items/:id` | Moves to the Trash → `204` (again when already there: `204`). `?permanent=true` deletes an item that is already in the Trash for good (`422` if it is not). |
| POST | `/vault/items/:id/restore` | `204` |
| DELETE | `/vault/trash` | Empties the Trash → `{ "deleted": 3 }` |
| GET/POST | `/vault/items/:id/notes` | `{ "text" }` (up to `VAULT_NOTE_CHARS`, 2000) → Note `{ id, text, createdAt }` (201). `422` in the Trash or past `VAULT_MAX_NOTES` (50). |
| DELETE | `/vault/items/:id/notes/:noteId` | `204` |
| GET | `/vault/items/:id/activity` | → `{ items: [ { action: saved\|renamed\|favourited\|unfavourited\|noted\|trashed\|restored, createdAt } ] }` newest first |

Limits (all environment variables, see `backend/.env.example`): `VAULT_MAX_ITEMS` 500 per user (`422 QUOTA_EXCEEDED`), `VAULT_TRASH_DAYS` 30 (the server removes older Trash items), `VAULT_PAGE_SIZE` 24. Every id that is not the caller's answers `404`.

### Part B: your own files (built)

The user's own contracts, notices and photos. The original is kept in a PRIVATE Supabase Storage bucket (`VAULT_BUCKET`, default `legalmate-vault`); the database holds the name, folder, category, size and the text read from the file (for search). The browser never gets a permanent address: it asks for a short-lived signed link. Accepted types (decided by the file's bytes, never its name): PDF, Word (.docx), JPG, PNG, up to `MAX_UPLOAD_MB` (10). `503 UNAVAILABLE` when `SUPABASE_URL` / `SUPABASE_SERVICE_KEY` are not set (`GET /vault/stats` then returns `filesEnabled: false`).

```json
VaultFile = { "id": "uuid", "name": "Tenancy Agreement.pdf", "fileType": "pdf|docx|jpg|png",
  "category": "Contracts|Notices|Court Documents|Property|Personal|Family|Other", "folderId": "uuid|null", "folderName": "Property|null",
  "sizeBytes": 2516582, "pages": 12, "favourite": false, "noteCount": 0,
  "textStatus": "ready|pending|none", "hasText": true,
  "uploadedAt": "...", "updatedAt": "...", "trashedAt": "...|null" }
Folder = { "id": "uuid", "name": "Property", "color": "#fbbf24", "fileCount": 6 }
```
`textStatus: "pending"` means a photo or scanned PDF is still being read in the background (the file is usable at once; poll `GET /vault/files/:id` until it is `ready` or `none`).

| Method | Path | Notes |
|---|---|---|
| POST | `/vault/files` | multipart `file`, optional `folderId`, `category` (default `Other`) → `201 VaultFile`. `415` wrong type, `413` too large, `422 QUOTA_EXCEEDED` (`VAULT_QUOTA_MB` 50 per user, the Trash counts until emptied; `VAULT_MAX_FILES` 200), `429` past `VAULT_UPLOADS_PER_HOUR`. |
| GET | `/vault/files` | Query: `category` (`all` default, `favourites`, `trash`, or one of the categories), `folderId`, `q` (file names AND the text inside), `sort` (`updated_desc` default, `updated_asc`, `name_asc`, `name_desc`, `size_desc`), `page`, `pageSize` (default 24) → `{ items, total, page, pageSize, counts: { all, favourites, trash, Contracts, ... }, storage: { usedBytes, quotaBytes } }` |
| GET | `/vault/files/:id` | VaultFile |
| GET | `/vault/files/:id/link` | `?download=true` → `{ url, expiresIn }`: a signed link valid `VAULT_LINK_SECONDS` (300) seconds. Without `download` it opens in place (PDF, image); with it the browser saves the file under its name. Readable while in the Trash. |
| GET | `/vault/files/:id/text` | → `{ text, truncated, status }` (the text read from the file; used for Word previews) |
| PATCH | `/vault/files/:id` | any of `{ "name", "folderId" (null = no folder), "category" }`; only what is sent changes → VaultFile. `404` while in the Trash. |
| PUT | `/vault/files/:id/favourite` | `{ "favourite": true }` → `204` |
| DELETE | `/vault/files/:id` | Moves to the Trash → `204`. `?permanent=true` deletes a file that is in the Trash for good: the stored original first, then the row (`503` if storage refuses, and the file stays so it can be retried; `422` if it is not in the Trash). |
| POST | `/vault/files/:id/restore` | `204` |
| DELETE | `/vault/files-trash` | Empties the file Trash → `{ "deleted": 3 }` |
| GET/POST | `/vault/files/:id/notes` | same shape as part A notes |
| DELETE | `/vault/files/:id/notes/:noteId` | `204` |
| GET | `/vault/files/:id/activity` | → `{ items: [ { action: uploaded\|renamed\|moved\|categorised\|favourited\|unfavourited\|noted\|trashed\|restored\|downloaded, createdAt } ] }` |
| GET | `/vault/folders` | → `{ items: Folder[] }` |
| POST | `/vault/folders` | `{ "name", "color"? }` → `201 Folder`. `409` if the name exists (any case), `422` past `VAULT_MAX_FOLDERS` (30). |
| PATCH | `/vault/folders/:id` | `{ "name"?, "color"? }` → Folder |
| DELETE | `/vault/folders/:id` | `204`. The files inside are kept and simply have no folder. |

`GET /vault/stats` returns part A's `counts` plus `files` (the counts above), `storage` and `filesEnabled`. Files that stay in the Trash for `VAULT_TRASH_DAYS` (30) are deleted for good (original included) by the server's clean-up. Every id that is not the caller's answers `404`. Not built: copying a file, analysing a Vault file with one click, virus scanning, a Word/Excel viewer (Word files show as extracted text), sharing.

---

## 8. AI case briefs

### GET `/case-briefs/draft?fromMessage=&fromAnalysis=`
Returns the user's current draft (create an empty one if none exists). `fromMessage` / `fromAnalysis` ask you to pre-fill it from a chat answer or document analysis.
```json
{ "id": "draft_1", "title": "Ahmad Khan vs State", "court": "Sessions Court, Islamabad",
  "caseNumber": "Criminal Appeal No. 123/2026", "parties": "Ahmad Khan (Appellant) vs State (Respondent)",
  "filingDate": "2026-03-12", "nextHearingDate": "2026-10-25",
  "facts": "...", "issues": "Issue one?\nIssue two?", "briefType": "summary|lawyer|personal|null",
  "attachments": [ { "id": "att_1", "name": "FIR_Copy.pdf", "sizeBytes": 2516582, "fileType": "pdf" } ],
  "savedAt": "..." }
```
Courts list currently used by the UI (can be moved to `GET /reference/courts`): Sessions Court Islamabad, Civil Court Lahore, High Court Islamabad, High Court Lahore, District Court Karachi, Supreme Court of Pakistan.

### PUT `/case-briefs/draft`
The frontend autosaves 1.5 s after each change.
```json
{ "title": "...", "court": "...", "caseNumber": "...", "parties": "...", "filingDate": "2026-03-12",
  "nextHearingDate": "2026-10-25", "facts": "...", "issues": "...", "briefType": "summary", "attachmentIds": ["att_1"] }
// 200
{ "savedAt": "..." }
```

### POST `/case-briefs/attachments` (multipart)
→ `{ "id", "name", "sizeBytes", "fileType" }`
### DELETE `/case-briefs/attachments/:id` → `204`

### POST `/case-briefs`
Body = draft payload + `"format": "A4 (PDF Style)|Letter|Plain text"`. Required: `title`, `court`, `parties`, `facts`, `issues`, `briefType`.
→ `{ "id": "brf_1", "status": "generating|completed" }` (the frontend polls endpoint 51 while `generating`).

### GET `/case-briefs/:id`
```json
{ "id": "brf_1", "status": "generating|completed|failed", "title": "Ahmad Khan vs State",
  "caseNumber": "Criminal Appeal No. 123/2026", "court": "Sessions Court, Islamabad", "briefType": "summary",
  "createdAt": "...", "updatedAt": "...", "pages": 8, "sizeBytes": 1258291,
  "nextHearing": { "date": "2026-10-25", "court": "Sessions Court, Islamabad" },
  "sections": [
    { "number": "II.", "title": "Parties", "blocks": [
      { "type": "kv", "label": "Appellant", "text": "Ahmad Khan" },
      { "type": "p", "text": "Paragraph" },
      { "type": "ol|ul", "items": ["one", "two"] } ] }
  ],
  "relatedDocuments": [ { "id": "doc_1", "name": "FIR Copy.pdf", "sizeBytes": 2516582, "fileType": "pdf" } ],
  "sharing": {
    "invites": [ { "id": "inv_1", "contact": "sara.ali@example.com", "permission": "View|Comment|Edit" } ],
    "link": { "enabled": true, "url": "https://legalmate.pk/s/brief/AK-2026-9f3k2", "expiresIn": "24 hours|7 days|30 days|Never", "requirePassword": false }
  } }
```
Standard sections: I. Case Title, II. Parties, III. Facts, IV. Issues, V. Applicable Law, VI. Arguments, VII. Evidence, VIII. Important Dates.

### POST `/case-briefs/:id/regenerate` → `CaseBrief`
### GET `/case-briefs/:id/export?format=pdf|docx` → file download
### POST `/case-briefs/:id/save` → `{ "vaultDocumentId": "..." }`
### POST `/case-briefs/:id/invites`
```json
{ "recipients": [ { "contact": "sara.ali@example.com or +923001234567", "permission": "View|Comment|Edit" } ],
  "message": "optional, max 500 chars" }
// 200
{ "invites": [ { "id": "inv_3", "contact": "...", "permission": "View" } ] }
```
Email or SMS each recipient a secure link.
### PUT `/case-briefs/:id/share-link`
`{ "enabled": true, "expiresIn": "7 days", "requirePassword": false }` → `{ "enabled", "url", "expiresIn", "requirePassword" }`

---

## 9. Legal calculator (built)

Every figure is worked out on the server (`backend/app/calculators.py`); the browser sends inputs only. Each result carries a `confidence`:

* `law`: the rule was checked against the text of the law in the law library, or is settled Hanafi law (limitation periods, inheritance shares, Standing Order 12 gratuity and notice).
* `reported`: official text or FBR rate card was not available, so the rate comes from news reports and commentary (Punjab stamp duty, property transfer taxes). The page shows a warning badge and the notes say which sources were used.

`:type` = `limitation` | `inheritance` | `compensation` | `stamp` | `property`. `court` (court fee) is deliberately **not offered**: its scales differ by province and could not be verified, and a wrong fee is worse than none. `POST /calculators/court/calculate` answers `422` with the reason.

### GET `/calculators`
```json
{ "verifiedOn": "2026-11-09",
  "items": [ { "key": "limitation", "name": "Limitation Period", "confidence": "law" } ],
  "unavailable": [ { "key": "court", "name": "Court Fee", "reason": "..." } ],
  "options": { "limitation": [ { "key": "residuary", "label": "...", "appeal": false } ], "courts": { "lhc": "Lahore High Court / Punjab courts" } } }
```

### POST `/calculators/:type/calculate`
| type | inputs |
|---|---|
| `limitation` | `kind` (key from `options.limitation`), `court` (`lhc`/`ihc`/`sc`/`fcc`), `date` (`YYYY-MM-DD`, the day time starts; that day is not counted), `copyDays` (appeals only: days to get the certified copy, not counted) |
| `inheritance` | `amount`, `spouse` (`Wife`/`Husband`/`None`), `wives` (1 to 4), `sons`, `daughters`, `father`, `mother` (`Yes`/`No`) |
| `compensation` | `salary`, `years`, `months`, `reason`, `workman` (`Permanent`/`Temporary / probationer`), `providentFund` (`Yes`/`No`) |
| `stamp` | `amount`, `instrument` (Punjab sale deed only) |
| `property` | `amount`, `sellerStatus`, `buyerStatus` (`Filer`/`Non-filer`) |

```json
// request
{ "inputs": { "kind": "contract_unregistered", "court": "lhc", "date": "2023-12-27" } }
// 200
{
  "total": 24500,                         // numeric result, or
  "text": "28 Dec 2026",                  // text result (the limitation date) instead of total
  "rows": [ { "label": "Period", "value": "3 years (Article 115)" } ],
  "notes": ["The last day was moved because the court is closed that day (section 4)."],
  "confidence": "law",                    // or "reported"
  "source": { "title": "Limitation Act, 1908", "reference": "First Schedule, Article 115", "url": "https://pakistancode.gov.pk/..." },
  "assumptions": ["..."],
  "verifiedOn": "2026-11-09", "calculatedAt": "...", "type": "limitation"
}
```
Wrong input answers `422` with a plain message such as `date: enter a date between 1900 and a year from now.`

How the rules were checked, and what stays open:
* Limitation: First Schedule Articles 115, 116, 113, 48, 142, 120, 152, 156, 151, 157 read from the Limitation Act in the law library (Pakistan's version; Azad Kashmir changed some periods, so web articles can be wrong). Section 12(1) (the starting day is not counted), 12(2) (certified copy time, appeals only), section 4 (a Sunday or public holiday on the last day moves it to the next open day; vacations do not move it, offices stay open) and leap-day handling are applied.
* Inheritance: Hanafi fixed shares with `'awl` (shares exceeding the estate) and `radd` (a return to heirs; never to the spouse), and the two cases where the mother takes a third of the remainder.
* Compensation: Standing Order 12 (one month's notice or wages in lieu, gratuity of 30 days' wages per completed year or part above six months, no gratuity for provident-fund service).
* Stamp duty and property transfer: Punjab stamp duty of 1% (Stamp (Amendment) Ordinance 2026, signed 10 April 2026) and the federal advance taxes for tax year 2027 (sections 236C and 236K) are from news reports and commentary. The non-filer rates come from one commentary source. Check with FBR or the sub-registrar before relying on them.
* The pakistancode.gov.pk links were not reachable from the development machine, so the PDF links are not verified from there.

### POST `/calculators/saved`
`{ "type": "limitation", "inputs": {...} }` → `201 { "id": "...", "alreadySaved": false }`. The server works the result out again from the inputs, so a result sent by the browser is never stored. The calculation becomes a Vault item of kind `calculation` (shown in the Vault under Calculations, with its own page and PDF).
### GET `/calculators/saved/:id/summary`
PDF download of a saved calculation (`:id` is the Vault item id). `404` if the item is not the user's own calculation.

---

## 10. Legal aid (Find a Lawyer search UI)

The "Find a Lawyer" page (`/legal-aid` route) keeps its original list/map/detail-panel UI, but its `Provider` cards are now the same lawyers from the marketplace (section 15), reshaped into this page's view-model — a lawyer's `id` is shared across `/legal-aid/providers` and `/lawyers`, not two separate directories.

### Provider (view-model)
```json
{ "id": "lw_Laiba", "kind": "lawyer", "name": "Laiba", "verified": true,
  "practiceAreas": ["Contract Law", "Corporate Law"], "languages": ["Urdu", "English"],
  "city": "Islamabad", "distanceKm": null, "modes": "Online & In-person|In-person|Online",
  "availability": { "label": "Available Today", "nextSlotLabel": "Next slot: 9:00 AM" },
  "fee": "paid", "rating": 4.9, "reviewCount": 128, "experienceLabel": "9 years experience",
  "bio": "...", "saved": false }
```
### GET `/legal-aid/providers`
Query: `q`, `area`, `city`, `language`, `mode`, `availability`, `sort` (`relevance`|`rating`|`distance`), `page`. → `{ "items": Provider[], "total": 14, "mapImageUrl": "optional static map" }`
### PUT `/legal-aid/providers/:id/save` `{ "saved": true }` → `204`
### GET `/legal-aid/emergency-contacts`
→ `{ "items": [ { "number": "15", "label": "Punjab Police Helpline", "icon": "phone|siren" } ] }`. Can vary by the user's province.

The page's two card actions are plain navigation, not API calls: "View Profile" goes to `/find-a-lawyer/:id` (`GET /lawyers/:id`, section 15) and "Book Consultation" starts the booking flow (`POST /bookings`, section 15).

---

## 11. Offline mode

The frontend keeps a local queue of writes made while offline (`src/api/services/offlineService.js`).

### GET `/offline/manifest`
Tells the app what to cache for offline use (respecting the user's `offline.autoDownload` preference):
```json
{ "documents": [ { "id": "doc_1", "updatedAt": "...", "url": "signed url" } ],
  "briefs": [ { "id": "brf_1", "updatedAt": "..." } ],
  "guides": [ { "id": "res_tenancy", "updatedAt": "..." } ] }
```

### POST `/sync`
Replays queued operations. Process them **idempotently by `id`**, because the same operation can be sent twice after a network failure.
```json
// request
{ "operations": [
  { "id": "op_1", "type": "note.create|brief.update|calculation.save|bookmark.create",
    "payload": { ...same body as the online endpoint... }, "createdAt": "..." } ] }
// 200
{ "results": [ { "id": "op_1", "status": "ok|conflict|error", "message": "optional" } ], "syncedAt": "..." }
```

---

## 12. WhatsApp bot

The WhatsApp Business Cloud API (Meta) is required on the backend.

### GET `/whatsapp`
→ `{ "connected": true, "phone": "300 1234567", "connectedAt": "..." }`

### POST `/whatsapp/connect`
`{ "phone": "+923001234567", "consent": true }` → `{ "status": "pending_verification|connected", "phone": "300 1234567" }`
Send an opt-in template message. The number becomes `connected` when the user replies. Store the consent record with a timestamp.

### DELETE `/whatsapp` → `204`

### GET `/whatsapp/qr`
→ `{ "qrImageUrl": "data:image/png;base64,... or https://...", "expiresAt": "...", "webUrl": "https://wa.me/92XXXXXXXXXX?text=LINK-abc123" }`
The QR encodes a `wa.me` link with a one-time linking code. The UI shows a countdown to `expiresAt` and a Refresh button.

### GET `/whatsapp/commands`
→ `{ "items": [ { "command": "/Ask", "description": "What is the notice period for tenancy?" } ] }`

### POST `/whatsapp/test-message` → `{ "sent": true }`

### POST `/whatsapp/preview`
`{ "text": "/status" }` → `{ "reply": "plain text reply" }`. This is the bot's answer for the on-page phone preview; no WhatsApp message is sent.

### POST `/webhooks/whatsapp` (server-to-server, not called by the frontend)
Receives incoming WhatsApp messages. Supported commands: `/ask <question>` (answers through the same AI pipeline as chat, with source links), `/status` (latest document analysis), `/legal-aid <city>`, `/support`. Save conversations to the user's chat history when `preferences.privacy.saveChatHistory` is true.

---

## 13. Settings (user account)

### GET `/users/me` → `User`
### PATCH `/users/me`
`{ "name", "email", "phone", "city", "address" }` → `User`. CNIC is read-only once verified. Re-verify an email or phone number when it changes.
### GET `/users/me/profile` and PUT `/users/me/profile`
The onboarding questions. The answers are given to the chatbot as context (where the user lives, their situation), so it can pick the right laws and explain at the right level. **No name, CNIC, phone, email or address is ever part of it or sent to the model.** Every field is optional; each choice must be one of the listed values (anything else is `400`).
```json
{
  "province": "Punjab|Sindh|Khyber Pakhtunkhwa|Balochistan|Islamabad Capital Territory|Gilgit-Baltistan|Azad Jammu & Kashmir",
  "city": "Lahore",
  "userType": "Citizen|Young adult|Business owner (SME)|Student",
  "employmentStatus": "Employed|Self-employed|Unemployed|Student|Retired",
  "roles": ["Tenant", "Landlord", "Employee", "Employer", "Business owner", "Property buyer or seller", "Parent or guardian"],
  "ageBand": "18-24|25-34|35-44|45-59|60+",
  "maritalStatus": "Single|Married|Divorced|Widowed|Prefer not to say",
  "language": "en|ur|both",
  "interests": ["Property and tenancy", "Family", "Criminal", "Employment", "Business and contracts", "Consumer", "Cyber and online", "Constitutional rights"],
  "completed": true
}
```
`PUT` replaces all answers (an empty body is a valid "skipped" form) and marks the profile completed; `GET` returns the same shape. `language` also updates `User.preferredLanguage`, `city` also updates `User.city`.
### POST `/users/me/avatar` (multipart, JPG/PNG ≤ 2 MB)
→ `{ "avatarUrl": "https://..." }`
### POST `/users/me/password`
`{ "currentPassword", "newPassword" }` → `204` (`422 WRONG_PASSWORD`). Signs out every other device; this one stays signed in.
### GET `/users/me/security`
→ `{ "twoFactorEnabled": true, "loginAlerts": true }`
### PATCH `/users/me/security`
Partial of the above → the same object.
### GET `/users/me/sessions`
→ `{ "items": [ { "id": "ses_1", "device": "Windows · Chrome", "deviceType": "laptop|phone|desktop", "location": "Islamabad, Pakistan", "lastActiveLabel": "Active now", "current": true } ] }`
### DELETE `/users/me/sessions/:id` → `204`

### GET `/users/me/preferences`
```json
{
  "notifications": { "email": true, "sms": false, "whatsapp": true, "deadlines": true, "analysis": true, "news": false },
  "region": { "language": "English|اردو", "province": "Islamabad Capital Territory", "dateFormat": "DD/MM/YYYY", "timezone": "(GMT+05:00) Pakistan Standard Time" },
  "privacy": { "saveChatHistory": true, "shareUsageData": false, "autoDeleteChats": "3 months|6 months|12 months|Never" },
  "appearance": { "theme": "light|dark|system", "density": "Comfortable|Compact" },
  "offline": { "autoDownload": true }
}
```
### PATCH `/users/me/preferences`
Deep-partial update, e.g. `{ "notifications": { "sms": true } }` → the full preferences object. `privacy.autoDeleteChats` needs a scheduled cleanup job.

### POST `/users/me/export`
→ `{ "requestId": "exp_1" }`. Build a ZIP of documents, briefs and chats, then email a download link.
### DELETE `/users/me`
Starts account deletion and emails a confirmation link → `204`.
### GET `/users/me/integrations`
→ `{ "items": [ { "provider": "whatsapp|google", "connected": true, "account": "+92 300 1234567" } ] }`
### POST `/users/me/integrations/:provider`
→ `{ "redirectUrl": "https://accounts.google.com/..." }` for OAuth providers; the frontend redirects the browser to it.
### DELETE `/users/me/integrations/:provider` → `204`

---

## 14. Emergency Mode

### GET `/emergency/contacts`
→ `{ "helpline": { "label": "LegalMate Legal Helpline", "number": "+92 21 111 000 000", "sub": "..." },`
`  "categories": [ { "key": "police", "label": "Police & Rescue", "icon": "shield|cross|flame|users|shield-alert|car", "numbers": [ { "label": "Police Helpline", "number": "15" } ] } ] }`
National numbers can vary by province — use the user's profile city/province if available, otherwise return the national defaults.

### GET `/emergency/personal-contacts` → `{ "items": [ { "id": "ec_1", "name": "...", "relation": "...", "phone": "...", "primary": true } ] }`
### POST `/emergency/personal-contacts`
`{ "name": "...", "relation": "...", "phone": "..." }` → created contact (`primary: false` unless it's the user's first contact).
### DELETE `/emergency/personal-contacts/:id` → `204`
### POST `/emergency/alert`
`{ "contactId": "ec_1", "shareLocation": true }` → `{ "sentAt": "...", "notifiedContact": PersonalContact }`. Sends an SMS/WhatsApp message to the contact with the user's situation and (if `shareLocation`) a live location link; also logs the alert for the user's own record.

---

## 15. Find a Lawyer marketplace

### Lawyer
```json
{ "id": "lw_Laiba", "name": "Laiba", "verified": "verified|pending", "title": "Advocate High Court",
  "specializations": ["Contract Law", "Corporate Law"], "city": "Islamabad", "fee": 3500,
  "rating": 4.9, "reviewCount": 128, "experienceYears": 9, "languages": ["Urdu", "English"],
  "modes": ["video", "phone", "in_person"], "bio": "...", "availableDays": [1, 2, 3, 4, 5], "slotTimes": ["9:00 AM", "2:00 PM"],
  "credentials": [ { "label": "LLB, Punjab University", "value": "2015" } ],
  "reviews": [ { "author": "Bilal H.", "rating": 5, "text": "..." } ] }
```
### Booking
```json
{ "id": "bkg_1", "lawyerId": "lw_Laiba", "lawyerName": "Laiba", "clientId": "usr_1", "clientName": "...",
  "date": "2026-10-02", "time": "2:00 PM", "type": "video|phone|in_person", "durationMin": 30,
  "status": "pending_payment|confirmed|completed|cancelled",
  "paymentMethod": null, "paymentStatus": "unpaid|cash_pending|bank_pending_verification|paid",
  "fee": 3500, "platformFee": 150, "total": 3650, "createdAt": "..." }
```

### GET `/lawyers`
Query: `q`, `specialization`, `city`, `fee` (`under2000`|`2000to4000`|`above4000`), `sort` (`relevance`|`rating`|`feeAsc`), `page`.
→ `{ "items": Lawyer[] (list fields only), "total": 14 }`. Only list lawyers whose account status is active (verified or pending review).
### GET `/lawyers/:id` → `Lawyer` (full profile, including `credentials`/`reviews`)
### PATCH `/lawyers/:id`
`{ "bio", "fee", "city", "specializations": string[], "languages": string[], "modes": string[], "availableDays": number[] (0=Sun..6=Sat), "slotTimes": string[] }` → updated `Lawyer`. Only the lawyer who owns `:id` (or an admin) may call this; `verified` is not settable here — see `PUT /admin/lawyers/:id`. `availableDays`/`slotTimes` are what the booking calendar reads, so an unverified lawyer with none set simply has no bookable slots yet.
### POST `/lawyers/apply` (public)
`{ "name", "email", "phone", "city", "fee", "experienceYears", "specializations": string[], "languages": string[], "modes": string[], "bio" }` → `Lawyer` (`verified: "pending"`) plus signs the applicant in as that lawyer account, same token shape as `/auth/login`. Their dashboard shows a "pending review" banner until an admin approves them via `PUT /admin/lawyers/:id`.
### POST `/bookings`
`{ "lawyerId": "lw_Laiba", "date": "2026-10-02", "time": "2:00 PM", "type": "video" }` → `Booking` (`status: "pending_payment"`). Reject if the slot is no longer available.
### GET `/bookings/:id` → `Booking`
### GET `/bookings/mine` → `{ "items": Booking[] }` for the signed-in client (or `?role=lawyer` scoping for the signed-in lawyer, used by the lawyer portal in a later phase)
### POST `/bookings/:id/pay`
`{ "method": "cash|bank_transfer" }` → updated `Booking`. `cash` → `paymentStatus: "cash_pending"`, `status: "confirmed"` immediately (collected in person). `bank_transfer` → `paymentStatus: "bank_pending_verification"`, `status: "confirmed"`; an admin/lawyer marks it `paid` once the transfer is verified (see the Admin phase). **No card fields exist in this flow by design.**

---

## 16. Admin

Every endpoint here requires the signed-in user's `role` to be `admin` (`403 FORBIDDEN` otherwise).

### GET `/admin/stats`
→ `{ "totals": { "users": 482, "pendingLawyers": 1, "activeBookings": 2, "revenueMonth": 186500 },`
`  "deltas": { "users": "+8% this month", "revenue": "+12% this month" },`
`  "trend": [ { "day": "Mon", "bookings": 3 } ], "recentActivity": [ { "id": "act_1", "text": "...", "timeLabel": "2h ago" } ] }`
### GET `/admin/lawyers` → `{ "items": Lawyer[] }` (every lawyer, any verification status). The frontend splits this one response into two views client-side: the **Lawyers** directory (`verified`/`rejected`, read-only "View" detail) and **Pending Applications** (`verified: "pending"`, with Approve/Reject) — no separate endpoint for the pending list.
### PUT `/admin/lawyers/:id` `{ "verified": "verified|pending|rejected" }` → updated `Lawyer`. This is both "Verify/Reject" on a pending application and "Approve/Reject" from the Pending Applications page.
### GET `/admin/users` → `{ "items": [ { "id": "usr_1", "name": "...", "email": "...", "role": "client|lawyer", "status": "active|suspended", "joinedAt": "2026-06-02" } ] }`
### PUT `/admin/users/:id` `{ "status": "active|suspended" }` → updated user. A suspended user's tokens should be rejected (`401`) until reactivated.
### GET `/admin/bookings` → `{ "items": Booking[] }` (every booking platform-wide)
### POST `/admin/bookings/:id/paid` → updated `Booking` (`paymentStatus: "paid"`). Used once a bank transfer is manually verified against the bank statement.

---

## 17. Community Q&A

### Question
```json
{ "id": "q_1", "title": "Is a verbal rental agreement legally binding in Pakistan?", "category": "Property Law",
  "body": "...", "authorName": "Bilal H.", "anonymous": false, "createdAt": "...", "viewCount": 412,
  "answers": [ { "id": "a_1", "authorName": "Zainab Farooq", "isExpert": true, "text": "...", "upvotes": 34, "createdAt": "..." } ] }
```
`authorName` is omitted/replaced with `"Anonymous"` server-side when `anonymous: true`, regardless of what the frontend is told — never trust the client to hide it. `isExpert` is true when the answerer is a verified lawyer account.

### GET `/community/categories` → `{ "items": [ { "key": "Family Law", "count": 12 } ] }`
### GET `/community/questions`
Query: `category`, `sort` (`trending`|`recent`), `q`, `page`. → `{ "items": Question[] (list fields, no `body`/`answers`), "total": 41 }`
### GET `/community/questions/:id` → `Question` (full, with `body` and `answers`). Increment `viewCount` server-side on each unique view.
### POST `/community/questions`
`{ "title": "...", "category": "Family Law", "body": "...", "privacy": "public|anonymous" }` → `Question`
### POST `/community/questions/:id/answers`
`{ "text": "..." }` → `Answer`. If the poster is a verified lawyer, set `isExpert: true`.

---

## 18. Lawyer portal

These reuse the marketplace's `Lawyer` and `Booking` shapes (section 15), scoped to the signed-in lawyer (`role: "lawyer"`, `user.lawyerId`). Profile edits (including the availability editor's `availableDays`/`slotTimes`) go through `PATCH /lawyers/:id` — see section 15.

### GET `/bookings?lawyerId=lw_Laiba` → `{ "items": Booking[] }` every booking for that lawyer (also used as `/admin/bookings`'s per-lawyer filter).
### POST `/bookings/:id/complete` → updated `Booking` (`status: "completed"`; if `paymentMethod` is `"cash"`, also set `paymentStatus: "paid"` since cash is collected in person at the session).
### GET `/lawyers/:id/earnings` → `{ "totalEarned": 5300, "pending": 3650, "completedCount": 1, "items": Booking[] }`. `totalEarned` sums `fee` (not `platformFee`, which is LegalMate's cut) across `paymentStatus: "paid"` bookings; `pending` sums `fee` across `cash_pending`/`bank_pending_verification` bookings.

---

## 19. Backend services needed behind these APIs

| Area | What is needed |
|---|---|
| Auth | JWT + refresh-token rotation, argon2 passwords (done); Google OAuth, mail service for password reset and email verification, optional NADRA CNIC verification (not built; SMS OTP is not used in this version) |
| AI chat | RAG over Pakistani laws (Acts, Rules, judgments) with a vector store, citation extraction, confidence scoring, Urdu + English support, SSE streaming |
| Document analysis | OCR for scans/images, clause/risk/deadline extraction, background jobs (done: text only is stored, the original is not kept); PDF report generation and virus scan (not built) |
| Case briefs | LLM generation into the section/block schema, PDF + DOCX export, share links with expiry/password, invite emails/SMS |
| Vault | Done (section 7): saved answers and analyses, folders, categories, favourites, 30-day Trash, 50 MB quota, signed links (5 min), notes, activity log. Originals live in a private Supabase Storage bucket. Not built: tags, virus scan, copy, sharing |
| Calculators | Configurable, province-specific rate tables with legal sources |
| Legal aid | Verified provider directory, geo search, help-request inbox for providers |
| Emergency Mode | Province-aware emergency number directory, SMS/WhatsApp alert dispatch, live-location link generation |
| Lawyer marketplace | Verified lawyer directory with credential checks, slot/availability management, booking + escrow-style payment status, bank-transfer verification workflow |
| Admin | Role-restricted operations dashboard, audit log for verification/suspension actions, reconciliation against actual bank statements for "mark paid" |
| Community Q&A | Question/answer storage, view-count tracking, spam/abuse moderation, server-side enforcement of anonymous posting |
| Lawyer portal | Ownership checks on profile edits, earnings ledger derived from booking payment events, payout/settlement process to actually pay lawyers their `fee` share |
| Notifications | In-app notifications + email/SMS/WhatsApp channels honouring preferences, deadline reminders |
| WhatsApp | WhatsApp Business Cloud API, webhook, opt-in templates, QR linking codes |
| Offline | Idempotent `/sync`, cache manifest |
| Privacy | Data export job, account deletion, chat auto-delete job, audit logging |

### Security checklist
- HTTPS only. Set CORS to allow the frontend origin, or use the Vite dev proxy locally (`VITE_PROXY_TARGET`).
- Rate-limit auth, OTP, chat and upload endpoints.
- Scope every resource to the authenticated user (return `404` for other users' ids).
- Sanitise any HTML returned by `/vault/documents/:id/content`.
- Never log document contents or CNIC numbers. Documents are encrypted at rest by the storage platform (Supabase encrypts Postgres and Storage with AES-256 and all traffic is TLS); the app adds a private bucket, signed short-lived links and per-user scoping. An extra application-level encryption layer is not built (see `backend/README.md`, "Security and encryption").
- Answers are general legal information, not legal advice. Keep the disclaimer in AI responses.
