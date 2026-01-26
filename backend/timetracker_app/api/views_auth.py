"""
API endpoints dla autentykacji TimeTracker.

Odpowiedzialności:
- Login/logout (session-based auth)
- Profil użytkownika (GET /api/me)
- Invite flow (validate + set password)
- Password reset flow (request + validate + confirm)

Bezpieczeństwo:
- Session cookies (HttpOnly)
- CSRF protection
- Generic error messages (nie ujawniamy szczegółów)
"""

import json
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.core.exceptions import ValidationError
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.views.decorators.csrf import csrf_exempt, ensure_csrf_cookie

from timetracker_app.auth import tokens, password_flows
from timetracker_app.api.schemas import (
    LoginRequest,
    SetPasswordRequest,
    ResetPasswordRequestRequest,
    ResetPasswordConfirmRequest,
    EmployeeProfileDTO,
    LoginResponse,
    MessageResponse,
    TokenValidationResponse,
    parse_json_to_dataclass,
)


# === Helper functions ===

def parse_json_body(request):
    """Parsuje JSON body z requesta."""
    try:
        return json.loads(request.body)
    except (json.JSONDecodeError, ValueError):
        return None


def error_response(message: str, status: int = 400):
    """Zwraca error response."""
    return JsonResponse({"error": message}, status=status)


def success_response(data: dict, status: int = 200):
    """Zwraca success response."""
    return JsonResponse(data, status=status)


# === Endpoints ===

@require_http_methods(["POST"])
@ensure_csrf_cookie
def login_view(request):
    """
    POST /api/auth/login
    
    Loguje użytkownika (email + password) i tworzy sesję.
    
    Request: {"email": str, "password": str}
    Response: {"employee": EmployeeProfileDTO} lub error
    """
    data = parse_json_body(request)
    if not data:
        return error_response("Nieprawidłowe dane JSON.", 400)
    
    try:
        login_req = parse_json_to_dataclass(data, LoginRequest)
    except ValueError as e:
        return error_response(str(e), 400)
    
    # Normalizuj email
    email = login_req.email.lower().strip()
    
    # Authenticate używa username (u nas to email)
    user = authenticate(request, username=email, password=login_req.password)
    
    if user is None:
        return error_response("Nieprawidłowy email lub hasło.", 401)
    
    # Sprawdź czy employee istnieje i jest aktywny
    try:
        employee = user.employee
        if not employee.is_active:
            return error_response("Konto nieaktywne.", 403)
    except Exception:
        return error_response("Nieprawidłowy email lub hasło.", 401)
    
    # Utwórz sesję
    login(request, user)
    
    # Zwróć profil pracownika
    profile = EmployeeProfileDTO(
        id=employee.id,
        email=employee.email,
        is_active=employee.is_active,
        daily_norm_minutes=employee.daily_norm_minutes
    )
    
    response = LoginResponse(employee=profile.to_dict())
    return success_response(response.to_dict(), 200)


@require_http_methods(["POST"])
def logout_view(request):
    """
    POST /api/auth/logout
    
    Wylogowuje użytkownika (niszczy sesję).
    
    Response: 204 No Content
    """
    logout(request)
    return JsonResponse({}, status=204)


@require_http_methods(["GET"])
@login_required
def me_view(request):
    """
    GET /api/me
    
    Zwraca profil zalogowanego użytkownika.
    Wymaga sesji (decorator @login_required).
    
    Response: EmployeeProfileDTO lub 401
    """
    try:
        employee = request.user.employee
        
        profile = EmployeeProfileDTO(
            id=employee.id,
            email=employee.email,
            is_active=employee.is_active,
            daily_norm_minutes=employee.daily_norm_minutes
        )
        
        return success_response(profile.to_dict(), 200)
    except Exception as e:
        return error_response("Nie można pobrać profilu.", 500)


@require_http_methods(["GET"])
def invite_validate_view(request):
    """
    GET /api/auth/invite/validate?token=...
    
    Waliduje invite token (bez konsumpcji).
    
    Query params: token
    Response: {"valid": bool, "employee_email": str} lub error
    """
    raw_token = request.GET.get('token', '').strip()
    
    if not raw_token:
        return error_response("Brak tokenu.", 400)
    
    try:
        employee = tokens.validate_token(raw_token, "INVITE")
        response = TokenValidationResponse(
            valid=True,
            employee_email=employee.email
        )
        return success_response(response.to_dict(), 200)
    except tokens.TokenError as e:
        return error_response(str(e), 400)


@require_http_methods(["POST"])
def set_password_view(request):
    """
    POST /api/auth/set-password
    
    Ustawia hasło używając invite tokenu (konsumuje token).
    
    Request: {"token": str, "password": str}
    Response: {"message": str} lub error
    """
    data = parse_json_body(request)
    if not data:
        return error_response("Nieprawidłowe dane JSON.", 400)
    
    try:
        req = parse_json_to_dataclass(data, SetPasswordRequest)
    except ValueError as e:
        return error_response(str(e), 400)
    
    try:
        employee = password_flows.set_password_from_invite(
            req.token,
            req.password
        )
        
        response = MessageResponse(
            message=f"Hasło ustawione dla {employee.email}. Możesz się teraz zalogować."
        )
        return success_response(response.to_dict(), 200)
    except tokens.TokenError as e:
        return error_response(str(e), 400)
    except ValidationError as e:
        # Django password validation errors
        errors = "; ".join(e.messages) if hasattr(e, 'messages') else str(e)
        return error_response(f"Hasło nie spełnia wymagań: {errors}", 400)


@require_http_methods(["POST"])
def password_reset_request_view(request):
    """
    POST /api/auth/password-reset/request
    
    Przetwarza żądanie resetu hasła.
    ZAWSZE zwraca sukces (nie ujawnia czy email istnieje).
    
    Request: {"email": str}
    Response: {"message": str} (zawsze 200)
    """
    data = parse_json_body(request)
    if not data:
        return error_response("Nieprawidłowe dane JSON.", 400)
    
    try:
        req = parse_json_to_dataclass(data, ResetPasswordRequestRequest)
    except ValueError as e:
        return error_response(str(e), 400)
    
    result = password_flows.request_password_reset(req.email)
    
    # Zwróć generyczną wiadomość (nie ujawniaj czy email istnieje)
    response = MessageResponse(message=result["message"])
    return success_response(response.to_dict(), 200)


@require_http_methods(["GET"])
def password_reset_validate_view(request):
    """
    GET /api/auth/password-reset/validate?token=...
    
    Waliduje reset token (bez konsumpcji).
    
    Query params: token
    Response: {"valid": bool, "employee_email": str} lub error
    """
    raw_token = request.GET.get('token', '').strip()
    
    if not raw_token:
        return error_response("Brak tokenu.", 400)
    
    try:
        employee = tokens.validate_token(raw_token, "RESET")
        response = TokenValidationResponse(
            valid=True,
            employee_email=employee.email
        )
        return success_response(response.to_dict(), 200)
    except tokens.TokenError as e:
        return error_response(str(e), 400)


@require_http_methods(["POST"])
def password_reset_confirm_view(request):
    """
    POST /api/auth/password-reset/confirm
    
    Resetuje hasło używając reset tokenu (konsumuje token).
    
    Request: {"token": str, "password": str}
    Response: {"message": str} lub error
    """
    data = parse_json_body(request)
    if not data:
        return error_response("Nieprawidłowe dane JSON.", 400)
    
    try:
        req = parse_json_to_dataclass(data, ResetPasswordConfirmRequest)
    except ValueError as e:
        return error_response(str(e), 400)
    
    try:
        employee = password_flows.reset_password_confirm(
            req.token,
            req.password
        )
        
        response = MessageResponse(
            message=f"Hasło zresetowane dla {employee.email}. Możesz się teraz zalogować."
        )
        return success_response(response.to_dict(), 200)
    except tokens.TokenError as e:
        return error_response(str(e), 400)
    except ValidationError as e:
        # Django password validation errors
        errors = "; ".join(e.messages) if hasattr(e, 'messages') else str(e)
        return error_response(f"Hasło nie spełnia wymagań: {errors}", 400)
