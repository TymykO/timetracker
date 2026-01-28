# TimeTracker — Frontend (React + TypeScript)

This directory contains the **React SPA** for TimeTracker.  
It implements the MVP UI:
- **Month view** (monthly summary, overtime, navigation)
- **Day view** (task filtering, selected tasks, durations, save)
- **Auth pages** (login, set-password, forgot-password, reset-password)

Backend remains the **source of truth** for all calculations and constraints.  
Agent rules live in:
- `../AGENTS.md` (root)
- `./AGENTS.md` (frontend)
- Day page specifics: `src/pages/Day/AGENTS.md`
- Month page specifics: `src/pages/Month/AGENTS.md`

---

## 🧰 Tech stack

- **Framework**: Vite + React 18 + TypeScript
- **UI Library**: Material-UI (MUI) 5
- **Routing**: React Router 6
- **Data fetching**: TanStack Query (React Query)
- **HTTP**: Fetch API with cookie sessions
- **Testing**: Playwright (E2E)
- **Styling**: MUI `sx` prop + theme system

---

## 📁 Directory structure

```text
frontend/
├── package.json
├── vite.config.ts
├── index.html
├── playwright.config.ts
└── src/
    ├── main.tsx               # app bootstrap
    ├── App.tsx                # root component
    ├── app/
    │   ├── api_client.ts      # fetch wrapper (credentials included)
    │   ├── router.tsx         # route definitions
    │   ├── auth_guard.tsx     # session check + redirects
    │   ├── query.ts           # TanStack Query config
    │   └── theme.ts           # MUI theme configuration
    ├── pages/
    │   ├── Month/             # Month view
    │   │   ├── MonthPage.tsx
    │   │   └── AGENTS.md
    │   ├── Day/               # Day view (core MVP)
    │   │   ├── DayPage.tsx
    │   │   └── AGENTS.md
    │   ├── Login/             # Login page
    │   │   └── LoginPage.tsx
    │   ├── SetPassword/       # Invite token flow
    │   │   └── SetPasswordPage.tsx
    │   ├── ForgotPassword/    # Password reset request
    │   │   └── ForgotPasswordPage.tsx
    │   └── ResetPassword/     # Password reset confirm
    │       └── ResetPasswordPage.tsx
    ├── components/            # Shared UI components
    │   ├── README.md          # Component library guide
    │   ├── AppShell.tsx       # Layout wrapper
    │   ├── Page.tsx           # Page wrapper
    │   ├── LoadingState.tsx   # Loading spinner
    │   ├── ErrorState.tsx     # Error display
    │   ├── MonthTable.tsx     # Month calendar table
    │   ├── MonthSummaryPanel.tsx  # Month totals
    │   ├── FiltersBar.tsx     # Task filters
    │   ├── TaskPicker.tsx     # Available tasks list
    │   └── SelectedTasksTable.tsx  # Selected tasks table
    ├── types/
    │   └── dto.ts             # API DTO types
    └── utils/
        └── timeUtils.ts       # Date/time helpers
```

---

## 🔐 Authentication behavior

Frontend uses **session cookies** (HttpOnly) provided by backend:

* All API calls include `credentials: "include"`
* On `401 Unauthorized` → redirect to `/login`
* Protected pages wrapped with `AuthGuard`

### Auth flows

#### Login
- Route: `/login`
- User enters email + password
- On success: redirect to `/month` (current month)
- Failed login: show error message

#### Set Password (Invite flow)
- Route: `/set-password?token=...`
- Admin creates employee → generates invite link
- User clicks link, sets password
- On success: redirect to `/login`
- Token validation: done by backend

#### Forgot Password
- Route: `/forgot-password`
- User enters email
- Backend sends reset link (if account exists)
- Always shows success (don't leak account existence)

#### Reset Password
- Route: `/reset-password?token=...`
- User clicks reset link from email
- Enters new password
- On success: redirect to `/login`
- Token validation: done by backend

No public registration exists in MVP.

---

## 🌐 API integration

### Base rules

* Use single API client: `src/app/api_client.ts`
* Always send cookies: `fetch(url, { credentials: "include", ... })`
* Handle errors consistently:
  * 401 → redirect to login
  * 403 → show "no access"
  * 4xx validation → show message from backend
  * 5xx/network → show generic retry message

### Core endpoints

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/api/me` | GET | Get current user profile |
| `/api/auth/login` | POST | Login with email/password |
| `/api/auth/logout` | POST | Logout and clear session |
| `/api/auth/invite/validate` | POST | Validate invite token |
| `/api/auth/set-password` | POST | Set password with token |
| `/api/auth/password-reset/request` | POST | Request password reset |
| `/api/auth/password-reset/validate` | POST | Validate reset token |
| `/api/auth/password-reset/confirm` | POST | Confirm password reset |
| `/api/timesheet/month` | GET | Get month summary |
| `/api/timesheet/day` | GET | Get day details |
| `/api/timesheet/day/save` | POST | Save day entries |
| `/api/tasks/active` | GET | Get active tasks list |

For detailed API contracts, see [`backend/timetracker_app/api/AGENTS.md`](../backend/timetracker_app/api/AGENTS.md).

---

## 🖥️ Pages overview

### Month view (`/month/:yyyy-mm`)

**Purpose**: Monthly timesheet overview

**Features:**
- Calendar table of all days in month
- Day columns: date, day type, working time, overtime, status
- Navigation: previous/next month buttons
- Cannot navigate to future months
- Future days grayed out and not clickable
- Click day → open Day view for that date

**Components:**
- `MonthTable` — calendar grid
- `MonthSummaryPanel` — month totals and navigation

**Data loading:**
- Query key: `['month', yearMonth]`
- Refetch after saving day (cache invalidation)

For detailed rules, see [`src/pages/Month/AGENTS.md`](src/pages/Month/AGENTS.md).

---

### Day view (`/day/:yyyy-mm-dd`)

**Purpose**: Daily time entry

**Features:**
- Task filtering: project_phase, department, discipline + free-text search
- Available tasks list (excludes already selected)
- Selected tasks table with duration inputs
- Day totals: working time + overtime
- Save button (full-state payload)
- Validation: no duplicates, duration > 0, day total ≤ 24h

**Components:**
- `FiltersBar` — filter dropdowns and search
- `TaskPicker` — available tasks with add buttons
- `SelectedTasksTable` — selected tasks with inputs

**Editability:**
- Only current month + previous month
- No future dates
- Inputs disabled if not editable

**Data loading:**
- Query keys: `['day', date]` + `['tasks']`
- Save invalidates day + month queries

For detailed rules, see [`src/pages/Day/AGENTS.md`](src/pages/Day/AGENTS.md).

---

### Auth pages

#### Login (`/login`)
- Email + password form
- Session cookie created on success
- Redirect to `/month` after login

#### Set Password (`/set-password?token=...`)
- Token validation (backend)
- Password input (with confirmation)
- One-time token usage

#### Forgot Password (`/forgot-password`)
- Email input
- Generic success message (don't leak existence)
- Backend sends reset email

#### Reset Password (`/reset-password?token=...`)
- Token validation (backend)
- New password input (with confirmation)
- One-time token usage

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

Vite will display the local URL (default: http://localhost:5173).

> Backend must be running and configured for cookies/CORS in dev.

### Build for production

```bash
npm run build
```

### Preview production build

```bash
npm run preview
```

### Lint

```bash
npm run lint
```

---

## 🧪 Testing

### E2E tests (Playwright)

Location: `frontend/tests/e2e/`

**Test files:**
- `auth.spec.ts` — Login, logout, set-password, reset flows
- `day.spec.ts` — Day view (filters, add tasks, save)
- `month.spec.ts` — Month view (navigation, day click)
- `validations.spec.ts` — Domain rules (future dates, 24h limit)

**Run tests:**

```bash
# Run all E2E tests
npm run test:e2e

# Run in UI mode (interactive)
npm run test:e2e:ui

# Run specific test file
npx playwright test tests/e2e/auth.spec.ts
```

**Test data:**
- Use `seed_testdata` management command for consistent test data
- Test user: `test@example.com` / `testpass123`

---

## ⚙️ Configuration

### Environment variables

Create `.env` file (copy from `.env.example`):

```bash
VITE_API_BASE_URL=http://localhost:8000/api
```

### Vite config

See `vite.config.ts` for:
- Dev server port (5173)
- Proxy configuration (if needed)
- Build optimizations

### MUI theme

See `src/app/theme.ts` for:
- Color palette
- Typography
- Spacing
- Breakpoints

---

## 📚 Component library

For detailed component documentation, see [`src/components/README.md`](src/components/README.md).

**Shared components:**
- `AppShell` — App layout with AppBar
- `Page` — Page wrapper with title
- `LoadingState` — Loading spinner
- `ErrorState` — Error display with retry

**Domain components:**
- `MonthTable` — Month calendar grid
- `MonthSummaryPanel` — Month totals and navigation
- `FiltersBar` — Task filters
- `TaskPicker` — Available tasks list
- `SelectedTasksTable` — Selected tasks table

---

## 🎨 Styling guidelines

### Material-UI (MUI)

- Use MUI components for consistency
- Follow MUI accessibility patterns
- Use theme system (no custom CSS)
- Leverage responsive utilities

### `sx` prop

```tsx
<Box sx={{ 
  mb: 3,                           // margin-bottom: theme.spacing(3)
  py: { xs: 2, md: 4 },           // responsive padding
  display: 'flex',
  justifyContent: 'space-between'
}}>
  ...
</Box>
```

### Theme values

```tsx
// Good: use theme
sx={{ color: 'primary.main', spacing: 2 }}

// Bad: hardcode
sx={{ color: '#1976d2', margin: '16px' }}
```

---

## 🔍 Best practices

### Data fetching
- Use TanStack Query for all API calls
- Define clear query keys (`['me']`, `['month', yearMonth]`, etc.)
- Invalidate caches after mutations
- Handle loading and error states

### State management
- **Server state**: TanStack Query
- **Local state**: React hooks (`useState`, `useReducer`)
- **Form state**: Controlled components
- **Derived state**: `useMemo`

### Component design
- Keep components focused (single responsibility)
- Pass callbacks as props (not Context for MVP)
- Use TypeScript interfaces for props
- Memoize expensive computations

### Performance
- Use `useMemo` for filtering large lists
- Use `useCallback` for stable callbacks
- Don't over-optimize (profile first)

### Accessibility
- Use semantic HTML
- Add ARIA labels to icon buttons
- Support keyboard navigation
- Ensure color contrast

---

## 🔧 Troubleshooting

### Backend connection issues

**Problem**: API calls fail with CORS errors  
**Solution**: Check `CORS_ALLOWED_ORIGINS` in backend `.env`

**Problem**: Session cookies not sent  
**Solution**: Ensure `credentials: "include"` in all fetch calls

### Build errors

**Problem**: TypeScript errors  
**Solution**: Run `npm run build` to see all errors, fix one by one

**Problem**: Missing dependencies  
**Solution**: Delete `node_modules` and `package-lock.json`, run `npm install`

### Dev server issues

**Problem**: Changes not reflected  
**Solution**: Restart Vite dev server (`Ctrl+C`, then `npm run dev`)

**Problem**: Port 5173 already in use  
**Solution**: Stop other Vite instances or change port in `vite.config.ts`

---

## 📖 Related documentation

- **Frontend AGENTS.md**: Architecture and patterns
- **Day page AGENTS.md**: Day view rules and behavior
- **Month page AGENTS.md**: Month view rules and behavior
- **Components README**: Component library guide
- **API documentation**: `backend/timetracker_app/api/AGENTS.md`
- **Root AGENTS.md**: Project-wide rules and conventions

---

## 📄 Vite + React template info

This project was bootstrapped with Vite + React + TypeScript template.

### Available plugins

- [@vitejs/plugin-react](https://github.com/vitejs/vite-plugin-react/blob/main/packages/plugin-react) — uses Babel for Fast Refresh
- [@vitejs/plugin-react-swc](https://github.com/vitejs/vite-plugin-react/blob/main/packages/plugin-react-swc) — uses SWC for Fast Refresh

### Expanding ESLint configuration

For production applications, update the configuration to enable type-aware lint rules:

```js
export default defineConfig([
  globalIgnores(['dist']),
  {
    files: ['**/*.{ts,tsx}'],
    extends: [
      tseslint.configs.recommendedTypeChecked,
      // or tseslint.configs.strictTypeChecked for stricter rules
    ],
    languageOptions: {
      parserOptions: {
        project: ['./tsconfig.node.json', './tsconfig.app.json'],
        tsconfigRootDir: import.meta.dirname,
      },
    },
  },
])
```

---

## Summary

TimeTracker frontend is a focused SPA built with modern React patterns and Material-UI. It provides intuitive Month and Day views for time entry, with robust auth flows and comprehensive E2E testing. The codebase follows strict conventions to maintain simplicity and consistency.
