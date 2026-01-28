# TimeTracker — AGENTS (BACKEND / API)

> Scope: `backend/timetracker_app/api/` — API endpoints, DTOs, and request/response contracts.  
> This file complements `../../../AGENTS.md` (root) and `../../AGENTS.md` (backend). Those rules still apply.

---

## 0) API layer responsibilities

This layer owns:
- **HTTP endpoint definitions** (views)
- **Request/response DTOs** (schemas)
- **Input validation** (parse, validate)
- **Auth checks** (login_required, active employee)
- **Mapping service exceptions to HTTP status codes**

This layer must NOT:
- Contain business logic (belongs in services)
- Directly manipulate models (use services)
- Perform calculations (services own domain logic)

---

## 1) API architecture principles

### Thin controllers
- Parse request → validate → call service → return response
- No business logic in views
- Services are the source of truth

### DTOs for clarity
- Request DTOs: Dataclasses for incoming payloads
- Response DTOs: Dataclasses for outgoing JSON
- `to_dict()` method for JSON serialization

### Standard error responses
```json
{
  "error": "Error message in Polish (user-facing)"
}
```

### Standard success responses
```json
{
  "data": { ... }  // or direct object
}
```

---

## 2) Authentication & authorization

### Session-based auth
- **Mechanism**: Django session cookies (HttpOnly, SameSite=Lax)
- **Decorator**: `@login_required` on all protected endpoints
- **CSRF**: Enabled for state-changing requests (POST/PUT/DELETE)

### Employee activation check
All endpoints must verify `employee.is_active`:
```python
try:
    employee = request.user.employee
    if not employee.is_active:
        return JsonResponse({'error': 'Account is inactive'}, status=403)
except AttributeError:
    return JsonResponse({'error': 'Employee not found'}, status=403)
```

### Public endpoints
Only invite/reset token validation endpoints can be accessed without auth:
- `POST /api/auth/invite/validate`
- `POST /api/auth/password-reset/validate`

---

## 3) Endpoint contracts

### Auth endpoints (`views_auth.py`)

#### `POST /api/auth/login`
**Description**: Login with email + password, create session.

**Request:**
```json
{
  "email": "string",
  "password": "string"
}
```

**Response (200):**
```json
{
  "employee": {
    "id": 1,
    "email": "user@example.com",
    "is_active": true,
    "daily_norm_minutes": 480
  }
}
```

**Errors:**
- `400`: Invalid JSON or missing fields
- `401`: Invalid email or password
- `403`: Account inactive

---

#### `POST /api/auth/logout`
**Description**: Logout, destroy session.

**Request:** Empty body

**Response (200):**
```json
{
  "message": "Wylogowano pomyślnie"
}
```

---

#### `GET /api/me`
**Description**: Get current employee profile.

**Response (200):**
```json
{
  "id": 1,
  "email": "user@example.com",
  "is_active": true,
  "daily_norm_minutes": 480
}
```

**Errors:**
- `401`: Not authenticated
- `403`: Employee not found or inactive

---

#### `POST /api/auth/invite/validate`
**Description**: Validate invite token (no auth required).

**Request:**
```json
{
  "token": "string"
}
```

**Response (200):**
```json
{
  "valid": true,
  "employee_email": "user@example.com"
}
```

**Response (200 - invalid):**
```json
{
  "valid": false,
  "employee_email": null
}
```

---

#### `POST /api/auth/set-password`
**Description**: Set password using invite token (first-time setup).

**Request:**
```json
{
  "token": "string",
  "password": "string"
}
```

**Response (200):**
```json
{
  "message": "Hasło ustawione pomyślnie"
}
```

**Errors:**
- `400`: Invalid JSON, missing fields, or password too weak
- `403`: Token invalid, expired, or already used

---

#### `POST /api/auth/password-reset/request`
**Description**: Request password reset (sends email with token).

**Request:**
```json
{
  "email": "string"
}
```

**Response (200):**
```json
{
  "message": "Jeśli konto istnieje, link resetujący został wysłany"
}
```

**Note**: Always returns success (don't leak email existence).

---

#### `POST /api/auth/password-reset/validate`
**Description**: Validate reset token (no auth required).

**Request:**
```json
{
  "token": "string"
}
```

**Response (200):**
```json
{
  "valid": true,
  "employee_email": "user@example.com"
}
```

---

#### `POST /api/auth/password-reset/confirm`
**Description**: Confirm password reset with token.

**Request:**
```json
{
  "token": "string",
  "password": "string"
}
```

**Response (200):**
```json
{
  "message": "Hasło zresetowane pomyślnie"
}
```

**Errors:**
- `400`: Invalid JSON or weak password
- `403`: Token invalid, expired, or already used

---

### Timesheet endpoints (`views_timesheet.py`)

#### `GET /api/timesheet/month?month=YYYY-MM`
**Description**: Get month summary for month view.

**Query params:**
- `month`: String in format `YYYY-MM` (e.g., "2025-03")

**Response (200):**
```json
{
  "month": "2025-03",
  "days": [
    {
      "date": "2025-03-01",
      "day_type": "Working",
      "working_time_raw_minutes": 480,
      "overtime_minutes": 0,
      "has_entries": true,
      "is_future": false,
      "is_editable": true
    },
    ...
  ]
}
```

**Errors:**
- `400`: Missing month, invalid format, or future month
- `401`: Not authenticated
- `403`: Employee inactive

**Notes:**
- Cannot access future months (returns 400)
- Returns all days in the month (1st to last day)
- `is_editable`: true only for current and previous month

---

#### `GET /api/timesheet/day?date=YYYY-MM-DD`
**Description**: Get day details for day view.

**Query params:**
- `date`: String in format `YYYY-MM-DD` (e.g., "2025-03-15")

**Response (200):**
```json
{
  "date": "2025-03-15",
  "day_type": "Working",
  "is_future": false,
  "is_editable": true,
  "total_raw_minutes": 480,
  "total_overtime_minutes": 0,
  "entries": [
    {
      "task_id": 123,
      "task_display_name": "Project A / Phase 1 / Development",
      "duration_minutes_raw": 240,
      "hours_decimal": "4.0"
    },
    {
      "task_id": 456,
      "task_display_name": "Project B / Phase 2 / Testing",
      "duration_minutes_raw": 240,
      "hours_decimal": "4.0"
    }
  ]
}
```

**Errors:**
- `400`: Missing date or invalid format
- `401`: Not authenticated
- `403`: Employee inactive

**Notes:**
- Returns empty `entries` array if no entries for the day
- `hours_decimal`: Billable hours as string (Decimal precision)

---

#### `POST /api/timesheet/day/save`
**Description**: Save time entries for a day (full-state: create/update/delete).

**Request:**
```json
{
  "date": "2025-03-15",
  "items": [
    {
      "task_id": 123,
      "duration_minutes_raw": 240
    },
    {
      "task_id": 456,
      "duration_minutes_raw": 240
    }
  ]
}
```

**Response (200):**
```json
{
  "success": true,
  "day": {
    "date": "2025-03-15",
    "day_type": "Working",
    "is_future": false,
    "is_editable": true,
    "total_raw_minutes": 480,
    "total_overtime_minutes": 0,
    "entries": [...]
  }
}
```

**Errors:**
- `400`: Invalid JSON, missing fields, or domain validation error
  - Future date
  - Date outside editable window
  - Duration <= 0
  - Duplicate task_id in payload
  - Day total > 1440 minutes
- `401`: Not authenticated
- `403`: Employee inactive

**Notes:**
- Payload is full-state: tasks not in payload are deleted
- This is how "removing a task" works (omit from payload)
- Entries for tasks in payload are created or updated
- Transaction guarantees atomicity

**Domain validation errors (400):**
```json
{
  "error": "Nie można edytować przyszłej daty: 2025-12-25"
}
```

---

### Tasks endpoints (`views_tasks.py`)

#### `GET /api/tasks/active`
**Description**: Get list of active tasks with filter values.

**Response (200):**
```json
{
  "tasks": [
    {
      "id": 123,
      "display_name": "Project A / Phase 1 / Development",
      "search_text": "project a phase 1 development",
      "project_phase": "Project A / Phase 1",
      "department": "Engineering",
      "discipline": "Development",
      "account": "ACC-001",
      "project": "Project A",
      "phase": "Phase 1",
      "task_type": "Development"
    },
    ...
  ],
  "filter_values": {
    "project_phases": ["Project A / Phase 1", "Project B / Phase 2", ...],
    "departments": ["Engineering", "QA", ...],
    "disciplines": ["Development", "Testing", ...]
  }
}
```

**Errors:**
- `401`: Not authenticated
- `403`: Employee inactive

**Notes:**
- Only returns active tasks (`is_active=True`)
- `filter_values`: Distinct values for dropdowns (sorted)
- `search_text`: Lowercase for case-insensitive filtering
- Frontend performs client-side filtering (no server-side filter params in MVP)

---

## 4) DTO schemas (`schemas.py`)

### Request DTOs

| DTO | Fields | Used in |
|-----|--------|---------|
| `LoginRequest` | email, password | POST /api/auth/login |
| `SetPasswordRequest` | token, password | POST /api/auth/set-password |
| `ResetPasswordRequestRequest` | email | POST /api/auth/password-reset/request |
| `ResetPasswordConfirmRequest` | token, password | POST /api/auth/password-reset/confirm |
| `SaveDayItemRequest` | task_id, duration_minutes_raw | POST /api/timesheet/day/save (items) |
| `SaveDayRequest` | date, items[] | POST /api/timesheet/day/save |

### Response DTOs

| DTO | Fields | Used in |
|-----|--------|---------|
| `EmployeeProfileDTO` | id, email, is_active, daily_norm_minutes | /api/me, login response |
| `LoginResponse` | employee | POST /api/auth/login |
| `MessageResponse` | message | Logout, set-password, etc. |
| `TokenValidationResponse` | valid, employee_email? | Invite/reset validation |
| `TimeEntryDTO` | task_id, task_display_name, duration_minutes_raw, hours_decimal | Day entries |
| `DayDTO` | date, day_type, is_future, is_editable, totals, entries[] | GET/POST day |
| `MonthDayDTO` | date, day_type, working_time, overtime, flags | Month day item |
| `MonthSummaryDTO` | month, days[] | GET month |
| `SaveDayResultDTO` | success, day | POST day/save |
| `TaskDTO` | id, display_name, search_text, filter fields | Task item |
| `FilterValuesDTO` | project_phases[], departments[], disciplines[] | Filter dropdowns |
| `TaskListResponseDTO` | tasks[], filter_values | GET /api/tasks/active |

---

## 5) Error handling strategy

### Service exceptions → HTTP status mapping

| Service Exception | HTTP Status | Message |
|-------------------|-------------|---------|
| `FutureDateError` | 400 | "Nie można edytować przyszłej daty: {date}" |
| `NotEditableError` | 400 | "Data {date} poza oknem edycji" |
| `InvalidDurationError` | 400 | "Duration musi być > 0" |
| `DuplicateTaskInPayloadError` | 400 | "Duplikat task_id w payload" |
| `DayTotalExceededError` | 400 | "Suma czasu w dniu przekracza 1440 minut" |
| Auth errors | 401 | "Nieprawidłowy email lub hasło" |
| Inactive employee | 403 | "Konto nieaktywne" |
| Token errors | 403 | "Token nieprawidłowy lub wygasł" |

### Generic errors for security
- Don't leak user existence: Always return success for password reset requests
- Don't reveal which field failed: Use generic "Invalid email or password"
- Don't expose stack traces: Catch all exceptions and return 500 with generic message

---

## 6) CORS & CSRF configuration

### CORS (handled in Django settings)
- **CORS_ALLOWED_ORIGINS**: Whitelist of allowed frontend origins
  - Dev: `http://localhost:5173` (Vite)
  - Prod: `https://yourdomain.com`
- **CORS_ALLOW_CREDENTIALS**: `True` (enable cookie-based auth)

### CSRF
- **Enabled**: CSRF middleware active for POST/PUT/DELETE/PATCH
- **Cookie**: `csrftoken` cookie (HttpOnly=False, SameSite=Lax)
- **Header**: Frontend must send `X-CSRFToken` header
- **Trusted origins**: `CSRF_TRUSTED_ORIGINS` whitelist

### Session cookies
- **HttpOnly**: `True` (prevent XSS)
- **SameSite**: `Lax` (prevent CSRF)
- **Secure**: `True` in production (HTTPS only)
- **Max age**: 14 days

---

## 7) Request validation patterns

### JSON parsing
```python
try:
    data = json.loads(request.body)
except (json.JSONDecodeError, ValueError):
    return JsonResponse({'error': 'Invalid JSON'}, status=400)
```

### DTO validation
```python
try:
    dto = parse_json_to_dataclass(data, SaveDayRequest)
except ValueError as e:
    return JsonResponse({'error': str(e)}, status=400)
```

### Query param validation
```python
date_str = request.GET.get('date')
if not date_str:
    return JsonResponse({'error': 'Missing date parameter'}, status=400)

try:
    work_date = datetime.strptime(date_str, '%Y-%m-%d').date()
except ValueError:
    return JsonResponse({'error': 'Invalid date format (expected YYYY-MM-DD)'}, status=400)
```

---

## 8) Response formatting patterns

### Success with data
```python
result = service.get_data(...)
return JsonResponse(result.to_dict())
```

### Success with message
```python
return JsonResponse({'message': 'Operation successful'}, status=200)
```

### Error response
```python
return JsonResponse({'error': 'Error message'}, status=400)
```

### Service exception handling
```python
try:
    result = service.save_day(...)
    return JsonResponse(result.to_dict())
except FutureDateError as e:
    return JsonResponse({'error': str(e)}, status=400)
except NotEditableError as e:
    return JsonResponse({'error': str(e)}, status=400)
```

---

## 9) Testing strategy

### API tests should cover:
- **Auth flow**: Login, logout, session persistence
- **Invite flow**: Token validation, set password, one-time use
- **Reset flow**: Request, validate, confirm, one-time use
- **Timesheet**: Month summary, day details, save day (all validations)
- **Tasks**: Active tasks list, filter values
- **Authorization**: 401 for unauthenticated, 403 for inactive

### Test patterns:
```python
# Setup
client = Client()
employee = Employee.objects.create(...)

# Auth
client.force_login(employee.user)

# Request
response = client.post('/api/timesheet/day/save', 
                      data=json.dumps({...}),
                      content_type='application/json')

# Assert
assert response.status_code == 200
data = response.json()
assert data['success'] == True
```

---

## 10) URL routing (`urls.py`)

### Structure
```python
urlpatterns = [
    # Auth
    path('auth/login', views_auth.login_view),
    path('auth/logout', views_auth.logout_view),
    path('auth/invite/validate', views_auth.validate_invite_view),
    path('auth/set-password', views_auth.set_password_view),
    path('auth/password-reset/request', views_auth.request_password_reset_view),
    path('auth/password-reset/validate', views_auth.validate_reset_token_view),
    path('auth/password-reset/confirm', views_auth.confirm_password_reset_view),
    path('me', views_auth.me_view),
    
    # Timesheet
    path('timesheet/month', views_timesheet.month_summary_view),
    path('timesheet/day', views_timesheet.day_view),
    path('timesheet/day/save', views_timesheet.save_day_view),
    
    # Tasks
    path('tasks/active', views_tasks.active_tasks_view),
]
```

### Mounted at `/api/` in main urls.py

---

## 11) Do / Don't

### DO
- Keep views thin (call services)
- Use DTOs for clarity
- Validate all inputs
- Check employee.is_active
- Map service exceptions to HTTP status
- Use transactions in services (not views)
- Return JSON everywhere

### DON'T
- Don't put business logic in views
- Don't query models directly (use services)
- Don't expose stack traces
- Don't leak user existence
- Don't skip auth checks
- Don't forget CSRF token for state-changing requests
- Don't hardcode URLs (use Django URL routing)

---

## 12) Future improvements (not MVP)

- OpenAPI/Swagger documentation generation
- Request rate limiting (per-user, per-IP)
- API versioning (e.g., `/api/v1/`)
- Pagination for large task lists
- Server-side filtering/search for tasks
- Bulk operations (e.g., copy week to week)
- Audit logging (who changed what when)

---

## 13) Compliance with root AGENTS.md

This API layer follows root AGENTS.md principles:
- **Backend as source of truth** (Section 2)
- **Thin controllers, logic in services** (Section 2)
- **Session-based auth** (Section 7)
- **Polish user-facing messages** (Section 10)
- **Domain rules enforced** (Section 1)
