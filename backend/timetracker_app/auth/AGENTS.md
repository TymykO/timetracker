
# TimeTracker — AGENTS (BACKEND / AUTH)

> Scope: `backend/timetracker_app/auth/`  
> This module implements **Option B**: email + password login, with **admin-only user creation**.
>
> Core idea: employees are provisioned by admin, then users set their password via a one-time token link.

---

## 0) Responsibilities

This module owns:
- generating and validating one-time tokens (invite + reset)
- password set/reset flows (token → set new password)
- helpers for login/session behavior used by API views

This module must NOT:
- contain timesheet business logic
- contain task filtering logic
- perform outbox job execution (can enqueue email job later, but MVP can skip emailing)

---

## 1) Non-negotiable product rules

- Employees are **created only by admin** (no public registration).
- Login is **email + password** (no magic-link login).
- Invite and reset links are **one-time**:
  - after successful use: token is marked used (cannot be reused)
- Tokens are **time-limited**:
  - invite expires (e.g. 24h)
  - reset expires (e.g. 1h)
- Never store raw tokens in DB (store hash).
- Email is the stable identifier (unique).

---

## 2) Model expectations (minimal)

This module relies on models (likely in `models.py`):
- `Employee` (SSoT for employees)
- `AuthToken`:
  - `token_hash` (indexed)
  - `purpose` ENUM: `INVITE`, `RESET`
  - `employee` FK
  - `expires_at` datetime
  - `used_at` nullable datetime
  - `created_at`

Optional (later):
- `last_login_at`, `failed_login_attempts`, etc. (not MVP)

---

## 3) Token format and security

### Raw token generation
- Use a strong random generator (`secrets.token_urlsafe(32)`).
- Store only a hash, e.g. SHA-256:
  - `token_hash = sha256(raw_token + pepper?)`
- Pepper can be optional; if used, keep in environment variable.

### Validation rules
A token is valid if:
- hash exists in DB
- `purpose` matches the flow
- `expires_at > now`
- `used_at is NULL`

Return structured errors for:
- not found
- expired
- used
- wrong purpose

---

## 4) Password handling

- Use Django’s built-in password hashing.
- Do not invent custom password hashing.
- If you use Django’s `User` model:
  - keep `User` as auth identity
  - link `Employee` to `User` (OneToOne)
- If you avoid Django User:
  - you must still use Django’s password hasher utilities
  - but **prefer Django User** for correctness and admin tooling

**MVP recommendation**:
- Create a `User` for each `Employee` (username=email, is_active follows employee).
- Employee is still the domain identity; User is authentication.

---

## 5) Required auth service functions (MVP)

Implement these in `password_flows.py` and `tokens.py` (or an `auth_service.py` if you prefer).

### Tokens

#### `create_token(employee, purpose, ttl_minutes) -> raw_token`
- creates AuthToken row with hashed token, expiry, used_at NULL
- returns raw token (only at creation time)

#### `validate_token(raw_token, purpose) -> Employee`
- returns employee if valid
- raises domain errors if invalid/expired/used

#### `consume_token(raw_token, purpose) -> Employee`
- validates
- marks used_at in the same transaction
- returns employee

### Invite flow

#### `invite_employee(employee) -> invite_link`
- creates INVITE token
- builds link `/set-password?token=...`
- sending email can be stubbed in MVP (return link to admin)

#### `set_password_from_invite(raw_token, new_password) -> result`
- consume INVITE token
- set password for associated user
- ensure employee/user active
- return success

### Password reset flow

#### `request_password_reset(email) -> reset_link`
- if employee exists and is active:
  - create RESET token
  - build link `/reset-password?token=...`
- do not leak whether email exists (return generic OK)

#### `reset_password_confirm(raw_token, new_password) -> result`
- consume RESET token
- set password
- return success

---

## 6) API layer integration expectations

API views (in `timetracker_app/api/views_auth.py`) should:
- accept JSON bodies
- call auth functions
- return clear DTO responses

Expected endpoints semantics (names may differ):
- `POST /api/auth/login` (email+password) → establishes session cookie
- `POST /api/auth/logout` → clears session
- `GET /api/me` → returns employee profile + flags
- `GET /api/auth/invite/validate?token=` → validates invite token (no consume)
- `POST /api/auth/set-password` → consumes invite token and sets password
- `POST /api/auth/password-reset/request` → triggers reset
- `GET /api/auth/password-reset/validate?token=` → validates reset token
- `POST /api/auth/password-reset/confirm` → consumes reset token and sets password

Backend must return 401 on invalid session, 403 on inactive employee.

---

## 7) Rate limiting / abuse prevention (MVP-light)

We won’t implement full rate limiting in MVP, but:
- password reset request should always return a generic response
- login should return generic “invalid credentials” without revealing which part failed

---

## 8) Tests that must exist

`test_auth.py` must cover:
- invite token: valid → set password works
- invite token: expired → rejected
- invite token: used → rejected
- reset token: valid → reset password works
- reset token: expired/used → rejected
- request reset does not leak existence
- inactive employee cannot login / cannot set/reset password

Tests should:
- freeze time for expiry checks (helper or injection)
- assert `used_at` is set on consume

---

## 9) Do / Don’t

### DO
- store hashed tokens only
- consume tokens atomically (transaction)
- use Django password hashing
- keep errors typed and mappable to HTTP

### DON’T
- don’t store raw tokens
- don’t build timesheet logic here
- don’t add third-party auth libs for MVP
- don’t implement magic-link login (not this project)
