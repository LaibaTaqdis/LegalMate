# LegalMate - Frontend

React + Vite implementation of the **UI Designs By Isha** screens (18 screens / 20 design images), plus a Settings page.

All data flows through an API layer. By default it runs on built-in **mock data** (no backend needed: login and signup accept any input). Point it at a real backend with one environment switch, and every page loads and saves through the API with no page changes.

## Run

```bash
npm install
npm run dev
```

Open http://localhost:5173

## Connecting the backend

1. Copy `.env.example` to `.env.local`.
2. Set `VITE_USE_MOCKS=false` and `VITE_API_BASE_URL=https://your-api/api/v1`.
3. Implement the endpoints in **[BACKEND_API.md](BACKEND_API.md)**: 89 endpoints with request/response contracts, auth, errors, uploads, SSE chat streaming and offline sync.

For local development without CORS, set `VITE_API_BASE_URL=/api/v1` and `VITE_PROXY_TARGET=http://localhost:8000`.

## Screens and routes

| # | Screen | Route |
|---|---|---|
| 1 | Splash / Landing | `/` |
| 2 | Onboarding (3 slides, ← → keys work) | `/onboarding` |
| 3 | Login | `/login` |
| 4 | Signup (+ verification & complete steps) | `/signup` |
| 5 | Citizen Dashboard | `/dashboard` |
| 6 | Chat (empty state) | `/chat` |
| 7 | Chat with Citations | `/chat/tenant-rights` |
| 8 | Confidence Indicator | `/chat/tenant-rights?panel=confidence` (or click the “% Confidence” chip) |
| 9 | Document Upload | `/documents/upload` |
| 10 | Document Analysis Result | `/documents/analysis/tenancy` |
| 11 | Legal Vault | `/vault` |
| 12 | Document View | `/vault/document/tenancy` |
| 13 | AI Case Brief | `/case-briefs/new` |
| 14 | Case Brief Share | `/case-briefs/ahmad-khan-vs-state?share=1` (or click Share) |
| 15 | Legal Calculator | `/calculator` |
| 16 | Legal Aid | `/legal-aid` |
| 17 | Offline Mode | `/offline` |
| 18 | WhatsApp Bot | `/whatsapp` |
| - | Settings | `/settings` |

User flow: Landing → Get Started → Onboarding → Create Account → Signup ↔ Login → Dashboard.

## Structure

```
public/assets/img/        illustrations cropped from the design images
src/App.jsx               routes (the signed-in area is wrapped in <RequireAuth>)
src/api/
  config.js               VITE_API_BASE_URL / VITE_USE_MOCKS switches
  client.js               fetch wrapper: auth header, token refresh, errors, uploads with progress, SSE, downloads
  tokenStore.js           access/refresh token storage ("Remember me" aware)
  endpoints.js            every backend route in one place
  services/               one service per area (auth, dashboard, chat, documents, vault, caseBrief,
                          calculator, legalAid, offline, whatsapp, settings, notifications);
                          each function returns mock data or calls the API
  mocks/                  mock data in the exact API response shapes
src/context/AuthContext   current user, login/logout, session restore, route guard
src/hooks/                useQuery / useMutation (loading, error, reload, polling), useDebounced, useOnline
src/components/States.jsx skeletons, error (with retry) and empty states
src/utils/format.js       date/size/currency formatting (API sends raw values)
src/components/           AppLayout (sidebar + top bar), shared UI, custom icons, toast context
src/pages/                one file per screen
src/styles/               base tokens + one stylesheet per area
```

### How a page talks to the backend

```jsx
const vault = useQuery(signal => vaultService.listDocuments({ category, sort }, signal), [category, sort])
// vault.data / vault.loading / vault.error / vault.reload() / vault.setData() for optimistic updates

await vaultService.setFavourite(id, true)   // mutations call the service directly
```

To change an endpoint, edit `src/api/endpoints.js` and the matching service. Pages never call `fetch` directly.

The previous `src`, `docs` and README were moved to `_backup_old_src/`. Delete that folder once you no longer need it.
