# LegalMate - Backend API Specification

This document lists every backend API the LegalMate frontend needs to run fully dynamically. The frontend already calls these endpoints through `src/api/services/*`. Set `VITE_USE_MOCKS=false` and `VITE_API_BASE_URL` (see `.env.example`) and the app switches from mock data to your backend with no page changes.

- Base URL: `{VITE_API_BASE_URL}`, for example `https://api.legalmate.pk/api/v1`. Every path below is relative to it.
- Route constants: `src/api/endpoints.js`
- Mock responses (exact shapes the UI expects): `src/api/mocks/*`

---

## 1. Conventions

### 1.1 Format
- JSON request and response bodies (`Content-Type: application/json`), except uploads (multipart) and file downloads.
- Field names are **camelCase**.
- Dates are **ISO 8601** strings. Date-only values use `YYYY-MM-DD` (e.g. `dueDate`). The UI formats them for display, so send raw values, not labels.
- File sizes are in bytes (`sizeBytes`). Money is a plain number in PKR.
- The frontend sends `Accept-Language: en` or `ur`, based on the language picker. Use it for AI answers and any localised text.

### 1.2 Authentication
- JWT bearer tokens: `Authorization: Bearer <accessToken>`.
- Login, register+OTP and refresh return `{ user, accessToken, refreshToken }`.
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
| 3 | POST | `/auth/register` | Signup step 1 |
| 4 | POST | `/auth/verify-otp` | Signup step 2 |
| 5 | POST | `/auth/resend-otp` | Signup step 2 |
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
| **Legal Vault** |||
| 31 | GET | `/vault/stats` | Vault sidebar, Settings |
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
  "preferredLanguage": "en"
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
`role` is the tab the person picked on the sign-in screen (Client/Lawyer/Admin); reject the login with `403 FORBIDDEN` if the account's actual role does not match it, rather than silently logging them into the wrong portal. `401 INVALID_CREDENTIALS` for a wrong email/phone or password. If 2FA is enabled, you may return `{ "twoFactorRequired": true, "verificationId": "..." }` and reuse `/auth/verify-otp`.

### GET `/auth/google?redirect=<url>` (public)
Starts Google OAuth. After the callback, redirect to `redirect` with tokens delivered securely (e.g. a short-lived one-time `code` that the frontend exchanges, or HttpOnly cookies).

### POST `/auth/register` (public)
```json
// request
{ "fullName": "Arfah Rizwan", "cnic": "35202-1234567-1", "email": "arfah@example.com",
  "phone": "+923001234567", "preferredLanguage": "en|ur|both", "password": "Str0ng!pass", "acceptedTerms": true }
// 201
{ "verificationId": "ver_123", "channel": "sms", "maskedDestination": "+92 300 ***4567" }
```
Validate: CNIC format `XXXXX-XXXXXXX-X`, a unique email and phone, and a password with at least 8 characters, one uppercase letter, one number and one special character. Send a 6-digit OTP by SMS.

### POST `/auth/verify-otp` (public)
```json
{ "verificationId": "ver_123", "code": "123456" }
// 200 -> { "user": {...}, "accessToken": "...", "refreshToken": "..." }
```
`422 INVALID_OTP` or `OTP_EXPIRED`.

### POST `/auth/resend-otp` (public)
`{ "verificationId": "ver_123" }` → `204`. Rate-limit this (e.g. 1 per 30 s).

### POST `/auth/forgot-password` (public)
`{ "identifier": "email or phone" }` → `204`. Always returns 204, even when no account exists, so the endpoint cannot be used to check whether an account exists.

### POST `/auth/refresh` (public)
`{ "refreshToken": "..." }` → `{ "accessToken": "...", "refreshToken": "..." }`

### POST `/auth/logout`
`{ "refreshToken": "..." }` → `204` (revokes the refresh token).

### GET `/auth/me`
→ `User`

---

## 4. Dashboard and notifications

### GET `/dashboard`
```json
{
  "activity": [
    { "id": "act_1", "type": "chat|document|brief|calculator|resource", "title": "Tenancy rights in Pakistan",
      "subtitle": "Chat with LegalMate", "occurredAt": "2026-09-23T10:24:00+05:00",
      "status": "completed|analysed|viewed|processing", "link": "/chat/tenant-rights" }
  ],
  "vault": {
    "usedBytes": 1800000000, "quotaBytes": 5000000000,
    "breakdown": [
      { "category": "documents|briefs|images|other", "label": "Documents", "bytes": 842000000 }
    ]
  },
  "resources": [
    { "id": "res_tenancy", "category": "property|labour|family", "title": "Tenancy Laws in Pakistan",
      "summary": "Know your rights as a tenant...", "link": "/chat/tenant-rights" }
  ],
  "deadlines": [
    { "id": "dl_1", "title": "Court Hearing - Civil Case", "location": "District Court, Islamabad",
      "dueDate": "2026-09-25", "daysLeft": 3 }
  ],
  "whatsapp": { "connected": true }
}
```
`link` is a frontend route. Return the 5 latest activity items and the 3 nearest deadlines.

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
  "steps":   [["Review your rental agreement for any rent increase clause."], ["... ", { "cite": 3 }]],
  "important": "Do not stop paying rent without legal advice...",
  "outro":   "If you share your city, I can also guide you on local rules.",
  "sources": [
    { "id": 1, "title": "The Rent Act, 2009", "section": "Section 4 - Tenancy Agreement", "type": "Act|Rule|Judgment",
      "quote": "“The terms of a written tenancy agreement shall be binding...”", "url": "https://..." }
  ],
  "confidence": { "score": 87, "relevance": 92, "agreement": 84, "recency": 86, "checked": 4, "verifiedAt": "..." },
  "feedback": null
}
```
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
Generate `title` and `tag` (legal area) from the question. The frontend then sends the first message with endpoint 20.

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
{ "content": "Can my landlord increase rent?", "attachmentIds": ["doc_1"], "language": "en|ur" }
```
The response is `Content-Type: text/event-stream`:
```
event: status
data: {"state":"thinking"}

event: status
data: {"state":"searching_sources"}

event: answer
data: { ...assistant Message (full JSON) }
```
- Store both the user message and the assistant message.
- If something fails, send `event: error` with `data: {"message":"..."}`.
- Optional: `event: delta` with `{ "text": "..." }` chunks for token streaming (the current UI shows a typing indicator and waits for `answer`).
- Update the conversation's `preview` and `updatedAt`.

### POST `/chat/messages/:id/feedback`
`{ "vote": "up|down", "comment": "optional" }` → `204`. `comment: "sources"` means the vote came from the Sources panel.

### POST `/chat/messages/:id/save`
Saves the answer as a document in the Legal Vault → `{ "documentId": "doc_9" }`

### POST `/chat/sources/report`
`{ "messageId": "msg_2", "sourceId": 1, "reason": "user_report" }` → `204`

---

## 6. Documents and analysis

### POST `/documents` (multipart)
Fields: `file`, `purpose` (`analysis` | `chat`), `saveToVault` (`true|false`)
```json
// 201
{ "id": "doc_1", "name": "Rental_Agreement.pdf", "sizeBytes": 2516582, "fileType": "pdf", "pages": 12 }
```
Virus-scan files and reject password-protected or unreadable ones with a clear `message`.

### DELETE `/documents/:id`
Discards an uploaded, not-yet-analysed file → `204`.

### POST `/analyses`
```json
{ "documentIds": ["doc_1"], "language": "auto|en|ur", "depth": "quick|detailed", "saveToVault": true }
// 202
{ "id": "ana_1", "status": "queued" }
```
Run the analysis as a background job (quick takes about 1-2 min, detailed about 3-5 min). Notify the user when it finishes (notification `type: "analysis"`).

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
  "recommendedActions": ["Consider negotiating the termination clause."]
}
```

### GET `/analyses/:id/report`
PDF report download.
### POST `/analyses/:id/save`
→ `{ "vaultDocumentId": "..." }`
### POST `/analyses/:id/share`
→ `{ "url": "https://legalmate.pk/s/analysis/abc" }` (read-only, expiring link)

---

## 7. Legal Vault

### Document (vault)
```json
{ "id": "tenancy", "name": "Tenancy Agreement.pdf", "fileType": "pdf|docx|xlsx|jpg|png",
  "category": "Contracts|Notices|Court Documents|Case Briefs|Property|Personal|Family",
  "folderId": "fld_property", "folderName": "Property", "updatedAt": "...", "uploadedAt": "...",
  "sizeBytes": 2516582, "status": "analysed|secure", "favourite": true, "pages": 12,
  "verified": true, "tags": ["Tenancy", "Property"], "owner": "You", "analysisId": "ana_1|null" }
```

### GET `/vault/stats`
```json
{ "storage": { "usedBytes": 1800000000, "quotaBytes": 5000000000 },
  "counts": { "all": 24, "Contracts": 6, "Notices": 4, "Court Documents": 5, "Case Briefs": 3,
              "shared": 2, "favourites": 4, "trash": 1 } }
```

### GET `/vault/folders`
→ `{ "items": [ { "id": "fld_property", "name": "Property", "color": "#fbbf24", "fileCount": 6 } ] }`
### POST `/vault/folders`
`{ "name": "Tax", "color": "#0ea5e9" }` → `Folder` (`409` if the name already exists)

### GET `/vault/documents`
Query:

| Param | Values |
|---|---|
| `category` | `all` (default), a category name, `favourites`, `shared`, `trash` |
| `folderId` | folder id |
| `q` | search text (name, tags, content) |
| `status` | `analysed` \| `secure` |
| `sort` | `updated_desc` (default) \| `updated_asc` \| `name_asc` \| `name_desc` |
| `page`, `pageSize` | pagination |

→ `{ "items": Document[], "total": 19, "page": 1, "pageSize": 50 }`

### POST `/vault/documents` (multipart)
Fields: `file`, `folderId?`, `category?` → `Document` (201). Enforce the storage quota (`422 QUOTA_EXCEEDED`).

### GET `/vault/documents/:id` → `Document`
### PATCH `/vault/documents/:id`
Any of `{ "name", "folderId", "category", "tags": [] }` → `Document`
### DELETE `/vault/documents/:id`
Moves the document to Trash (restorable for 30 days) → `204`.
### PUT `/vault/documents/:id/favourite`
`{ "favourite": true }` → `204`
### POST `/vault/documents/:id/copy` → `Document` (the copy)
### GET `/vault/documents/:id/file`
Original file download (or `302` to a short-lived signed storage URL).

### GET `/vault/documents/:id/content`
Used by the document viewer:
```json
{ "pageCount": 12, "fileUrl": "https://signed-url (for images)",
  "pages": [ { "number": 1, "html": "<h2 class=\"doc-h\">TENANCY AGREEMENT</h2><p>... <mark>highlighted clause</mark> ...</p>" } ] }
```
The frontend renders `html` directly, so **it must be sanitised server-side** (allow only `h2, p, b, i, ol, ul, li, mark, span, div` plus `class`). Use `<mark>` for clauses highlighted by the analysis.

### GET `/vault/documents/:id/notes`
→ `{ "items": [ { "id": "n1", "text": "...", "createdAt": "..." } ] }`
### POST `/vault/documents/:id/notes`
`{ "text": "..." }` → `Note` (201)
### GET `/vault/documents/:id/activity`
→ `{ "items": [ { "id": "a1", "type": "analysed|verified|viewed|uploaded|renamed|moved|shared", "text": "Analysis completed", "createdAt": "..." } ] }`

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

## 9. Legal calculator

`:type` = `court` | `stamp` | `inheritance` | `compensation` | `limitation` | `property`

### POST `/calculators/:type/calculate`
Inputs per type:

| type | inputs |
|---|---|
| `court` | `province`, `caseType`, `amount` (PKR) |
| `stamp` | `province`, `instrument`, `amount` |
| `inheritance` | `amount`, `spouse` (`Wife`/`Husband`/`None`), `sons`, `daughters` |
| `compensation` | `salary`, `years`, `reason` |
| `limitation` | `kind`, `date` (`YYYY-MM-DD`) |
| `property` | `province`, `amount`, `filer` (`Filer`/`Non-filer`) |

```json
// request
{ "inputs": { "province": "Punjab", "caseType": "Civil Suit (Money Claim)", "amount": 1000000 } }
// 200
{
  "total": 24500,                         // numeric result, or
  "text": "10 Mar 2029",                  // text result (e.g. limitation date) instead of total
  "rows": [ { "label": "Claim Amount", "value": "PKR 1,000,000" },
            { "label": "Applicable Rate (2.5%)", "value": "PKR 25,000" } ],
  "source": { "title": "Court Fees Act, 1870 (As Amended)", "reference": "Schedule I - Article 1A (Civil Suits)", "url": null },
  "assumptions": ["Standard civil court fee structure applies."],
  "calculatedAt": "..."
}
```
The formulas currently in `src/pages/Calculator.jsx` (`compute`) are mock estimates. Replace them with the officially notified rates per province, and keep those rates configurable on the server.

### POST `/calculators/saved`
`{ "type": "court", "inputs": {...}, "result": {...} }` → `{ "id": "calc_1" }`
### GET `/calculators/saved/:id/summary`
PDF download.

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
### POST `/users/me/avatar` (multipart, JPG/PNG ≤ 2 MB)
→ `{ "avatarUrl": "https://..." }`
### POST `/users/me/password`
`{ "currentPassword", "newPassword" }` → `204` (`422 WRONG_PASSWORD`). Revoke other sessions.
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
| Auth | JWT + refresh-token rotation, bcrypt/argon2 passwords, SMS OTP provider (e.g. Twilio / local SMS gateway), Google OAuth, optional NADRA CNIC verification |
| AI chat | RAG over Pakistani laws (Acts, Rules, judgments) with a vector store, citation extraction, confidence scoring, Urdu + English support, SSE streaming |
| Document analysis | File storage (S3-compatible, encrypted at rest), virus scan, OCR for scans/images, clause/risk/deadline extraction, background job queue, PDF report generation |
| Case briefs | LLM generation into the section/block schema, PDF + DOCX export, share links with expiry/password, invite emails/SMS |
| Vault | Folders, categories, tags, favourites, trash with 30-day retention, storage quotas, signed download URLs, notes, activity log |
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
- Never log document contents or CNIC numbers. Encrypt documents at rest.
- Answers are general legal information, not legal advice. Keep the disclaimer in AI responses.
