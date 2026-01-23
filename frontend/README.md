# React + TypeScript + Vite

This template provides a minimal setup to get React working in Vite with HMR and some ESLint rules.

Currently, two official plugins are available:

- [@vitejs/plugin-react](https://github.com/vitejs/vite-plugin-react/blob/main/packages/plugin-react) uses [Babel](https://babeljs.io/) (or [oxc](https://oxc.rs) when used in [rolldown-vite](https://vite.dev/guide/rolldown)) for Fast Refresh
- [@vitejs/plugin-react-swc](https://github.com/vitejs/vite-plugin-react/blob/main/packages/plugin-react-swc) uses [SWC](https://swc.rs/) for Fast Refresh

## React Compiler

The React Compiler is not enabled on this template because of its impact on dev & build performances. To add it, see [this documentation](https://react.dev/learn/react-compiler/installation).

## Expanding the ESLint configuration

If you are developing a production application, we recommend updating the configuration to enable type-aware lint rules:

```js
export default defineConfig([
  globalIgnores(['dist']),
  {
    files: ['**/*.{ts,tsx}'],
    extends: [
      // Other configs...

      // Remove tseslint.configs.recommended and replace with this
      tseslint.configs.recommendedTypeChecked,
      // Alternatively, use this for stricter rules
      tseslint.configs.strictTypeChecked,
      // Optionally, add this for stylistic rules
      tseslint.configs.stylisticTypeChecked,

      // Other configs...
    ],
    languageOptions: {
      parserOptions: {
        project: ['./tsconfig.node.json', './tsconfig.app.json'],
        tsconfigRootDir: import.meta.dirname,
      },
      // other options...
    },
  },
])
```

You can also install [eslint-plugin-react-x](https://github.com/Rel1cx/eslint-react/tree/main/packages/plugins/eslint-plugin-react-x) and [eslint-plugin-react-dom](https://github.com/Rel1cx/eslint-react/tree/main/packages/plugins/eslint-plugin-react-dom) for React-specific lint rules:

```js
// eslint.config.js
import reactX from 'eslint-plugin-react-x'
import reactDom from 'eslint-plugin-react-dom'

export default defineConfig([
  globalIgnores(['dist']),
  {
    files: ['**/*.{ts,tsx}'],
    extends: [
      // Other configs...
      // Enable lint rules for React
      reactX.configs['recommended-typescript'],
      // Enable lint rules for React DOM
      reactDom.configs.recommended,
    ],
    languageOptions: {
      parserOptions: {
        project: ['./tsconfig.node.json', './tsconfig.app.json'],
        tsconfigRootDir: import.meta.dirname,
      },
      // other options...
    },
  },
])
```

###

````md
# TimeTracker — Frontend (React + TypeScript)

This directory contains the **React SPA** for TimeTracker.  
It implements the MVP UI:
- **Month view** (monthly summary, overtime, navigation)
- **Day view** (task filtering, selected tasks, durations, save)

Backend remains the **source of truth** for all calculations and constraints.  
Agent rules live in:
- `../AGENTS.md` (root)
- `./AGENTS.md` (frontend)
- Day page specifics: `src/pages/Day/AGENTS.md`

---

## 🧰 Tech stack

- Vite
- React + TypeScript
- SPA routing
- Fetch-based API client (cookies / sessions)
- Minimal dependencies (KISS)

---

## 📁 Directory map

```text
frontend/
├── package.json
├── vite.config.ts
├── index.html
└── src/
    ├── main.tsx               # app bootstrap
    ├── App.tsx                # root component
    ├── app/
    │   ├── api_client.ts      # fetch wrapper (credentials included)
    │   ├── router.tsx         # route definitions
    │   └── auth_guard.tsx     # session check + redirects
    ├── pages/
    │   ├── Month/             # Month view (to be created/extended)
    │   ├── Day/               # Day view (core MVP)
    │   ├── Login/             # login page
    │   ├── SetPassword/       # invite token flow
    │   └── ResetPassword/     # reset flow
    ├── components/            # shared UI parts
    └── types/
        └── dto.ts             # API DTO types
````

> Note: folder names may evolve during implementation; keep responsibilities stable.

---

## 🔐 Authentication behavior (frontend)

Frontend uses **session cookies** (HttpOnly) provided by backend:

* All API calls must include `credentials: "include"`.
* On `401 Unauthorized`, frontend must redirect to `/login`.
* Pages that require auth are wrapped with `AuthGuard`.

Supported flows:

* Login (email + password)
* Set password (invite token)
* Password reset (request + confirm)

No public registration exists in MVP.

---

## 🌐 API integration

### Base rules

* Use a single API client module (`src/app/api_client.ts`).
* Always send cookies:

  * `fetch(url, { credentials: "include", ... })`
* Handle errors consistently:

  * 401 → redirect to login
  * 403 → show “no access”
  * 4xx validation → show message from backend
  * 5xx/network → show generic retry message

### Core endpoints (conceptual)

* `GET /api/me`
* `POST /api/auth/login`
* `POST /api/auth/logout`
* `GET /api/timesheet/month?month=YYYY-MM`
* `GET /api/timesheet/day?date=YYYY-MM-DD`
* `POST /api/timesheet/day/save`
* `GET /api/tasks/active`

Exact schemas are defined by backend DTOs and frontend `types/dto.ts`.

---

## 🖥️ UX summary (MVP)

### Month view

* Month table of days
* Cannot navigate to future months
* Future days disabled
* Day rows show:

  * `day_type` (Working/Free)
  * `working_time_raw` (hh:mm)
  * `overtime` (hh:mm)
  * `has_entries` indicator
* Click day → open Day view for that date

### Day view (core)

* Shows day totals + day type
* Shows filtered list of tasks (active tasks only)
* Filters: `project_phase`, `department`, `discipline` + search
* Selected tasks list:

  * no duplicates within a user/day
  * tasks already selected are not shown in filtered list
* Durations:

  * required, must be > 0
  * day total must be <= 24h
* Editing:

  * only current month + previous month
  * no future dates
* Save sends **full day state** payload to backend

Day page details are strictly specified in `src/pages/Day/AGENTS.md`.

---

## 🚀 Running frontend (dev)

### Install dependencies

```bash
cd frontend
npm install
```

### Start dev server

```bash
npm run dev
```

Vite will display the local URL (default: [http://localhost:5173](http://localhost:5173)).

> Backend must be running and configured for cookies/CORS in dev.

### Build

```bash
npm run build
```

### Lint (if enabled)

```bash
npm run lint
```

---

## 🧪 Frontend testing (MVP)

In MVP we focus on:

* stable UX flows
* API integration correctness
* core constraints (prevent obvious invalid saves)

If automated tests are added later:

* prefer simple component tests for Day/Month
* avoid heavy E2E until flows stabilize

---

## ⚙️ Configuration notes

* API base URL can be configured via env (Vite):

  * e.g. `VITE_API_BASE_URL=http://localhost:8000`
* In dev, proxy can be configured in `vite.config.ts` if needed
* Cookies require:

  * correct CORS settings on backend
  * matching domain/ports rules (dev setup dependent)

```
::contentReference[oaicite:0]{index=0}
```
