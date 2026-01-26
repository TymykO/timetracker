"""
Moduł przepływów autentykacji (invite, set password, reset password).

Odpowiedzialności:
- Invite flow: generowanie invite tokenu dla nowego pracownika
- Set password: ustawienie hasła z invite tokenu (jednorazowe)
- Reset password: request + confirm z jednorazowym tokenem

Bezpieczeństwo:
- Używa Django password validation
- Używa Django password hashing (User.set_password)
- Request reset nie ujawnia czy email istnieje
- Wszystkie tokeny są jednorazowe i wygasają
"""

from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from django.db import transaction
from timetracker_app.models import Employee
from timetracker_app.auth.tokens import create_token, consume_token


# Stałe TTL dla tokenów (w minutach)
INVITE_TTL_MINUTES = 24 * 60  # 24 godziny
RESET_TTL_MINUTES = 60  # 1 godzina


def invite_employee(employee: Employee) -> dict:
    """
    Generuje invite token dla pracownika.
    
    W MVP: admin kopiuje link ręcznie (bez wysyłania email).
    
    Args:
        employee: Obiekt Employee
        
    Returns:
        Dict z tokenem i linkiem: {"token": str, "link": str}
    """
    raw_token = create_token(employee, "INVITE", INVITE_TTL_MINUTES)
    
    # Buduj link (frontend route)
    link = f"/set-password?token={raw_token}"
    
    return {
        "token": raw_token,
        "link": link
    }


def set_password_from_invite(raw_token: str, new_password: str) -> Employee:
    """
    Ustawia hasło dla pracownika używając invite tokenu.
    
    Konsumuje token (jednorazowe użycie), waliduje hasło,
    ustawia hasło i aktywuje użytkownika.
    
    Args:
        raw_token: Surowy invite token
        new_password: Nowe hasło do ustawienia
        
    Returns:
        Obiekt Employee
        
    Raises:
        TokenError: Jeśli token jest nieprawidłowy/wygasły/użyty
        ValidationError: Jeśli hasło nie spełnia wymagań
    """
    with transaction.atomic():
        # Konsumuj invite token (walidacja + oznaczenie jako użyty)
        employee = consume_token(raw_token, "INVITE")
        
        # Waliduj hasło zgodnie z Django password validators
        user = employee.user
        validate_password(new_password, user=user)
        
        # Ustaw hasło (automatycznie hashowane)
        user.set_password(new_password)
        
        # Aktywuj użytkownika (jeśli nie był aktywny)
        if not user.is_active:
            user.is_active = True
        
        user.save(update_fields=['password', 'is_active'])
        
        # Synchronizuj is_active z Employee
        if not employee.is_active:
            employee.is_active = True
            employee.save(update_fields=['is_active'])
    
    return employee


def request_password_reset(email: str) -> dict:
    """
    Przetwarza request resetu hasła.
    
    Jeśli employee istnieje i jest aktywny: tworzy RESET token.
    ZAWSZE zwraca sukces (nie ujawnia czy email istnieje).
    
    Args:
        email: Email pracownika
        
    Returns:
        Dict z message i opcjonalnie tokenem (tylko dla testów/MVP):
        {"message": str, "token": str or None}
    """
    # Normalizuj email (lowercase)
    email = email.lower().strip()
    
    token = None
    
    try:
        # Szukaj Employee po email (case-insensitive)
        employee = Employee.objects.select_related('user').get(email__iexact=email)
        
        # Sprawdź czy employee jest aktywny
        if employee.is_active and employee.user.is_active:
            # Utwórz RESET token
            raw_token = create_token(employee, "RESET", RESET_TTL_MINUTES)
            token = raw_token  # Zwróć token dla testów/MVP
    except Employee.DoesNotExist:
        # Nie ujawniaj że email nie istnieje
        pass
    
    # Zawsze zwracaj generyczną wiadomość
    return {
        "message": "Jeśli podany adres email istnieje, wysłano link do resetowania hasła.",
        "token": token  # None jeśli employee nie istnieje lub nieaktywny
    }


def reset_password_confirm(raw_token: str, new_password: str) -> Employee:
    """
    Potwierdza reset hasła i ustawia nowe hasło.
    
    Konsumuje token (jednorazowe użycie), waliduje hasło,
    i ustawia nowe hasło.
    
    Args:
        raw_token: Surowy reset token
        new_password: Nowe hasło do ustawienia
        
    Returns:
        Obiekt Employee
        
    Raises:
        TokenError: Jeśli token jest nieprawidłowy/wygasły/użyty
        ValidationError: Jeśli hasło nie spełnia wymagań
    """
    with transaction.atomic():
        # Konsumuj reset token (walidacja + oznaczenie jako użyty)
        employee = consume_token(raw_token, "RESET")
        
        # Waliduj hasło zgodnie z Django password validators
        user = employee.user
        validate_password(new_password, user=user)
        
        # Ustaw hasło (automatycznie hashowane)
        user.set_password(new_password)
        user.save(update_fields=['password'])
    
    return employee
