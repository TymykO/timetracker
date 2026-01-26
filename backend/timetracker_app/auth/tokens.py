"""
Moduł zarządzania tokenami autentykacji (INVITE, RESET).

Odpowiedzialności:
- Generowanie bezpiecznych tokenów (secrets)
- Hashowanie tokenów (SHA-256) przed zapisem do DB
- Walidacja tokenów (purpose, expiry, used_at)
- Konsumpcja tokenów (oznaczenie jako użyty)

Bezpieczeństwo:
- Tokeny nigdy nie są przechowywane w surowej formie
- Tokeny są jednorazowe (used_at)
- Tokeny wygasają (expires_at)
"""

import hashlib
import secrets
from datetime import timedelta
from django.utils import timezone
from timetracker_app.models import AuthToken, Employee


# Wyjątki tokenów
class TokenError(Exception):
    """Bazowy wyjątek dla błędów tokenów."""
    pass


class TokenNotFound(TokenError):
    """Token nie istnieje w bazie danych."""
    pass


class TokenExpired(TokenError):
    """Token wygasł."""
    pass


class TokenUsed(TokenError):
    """Token został już użyty."""
    pass


class WrongPurpose(TokenError):
    """Token ma inny purpose niż oczekiwany."""
    pass


def _hash_token(raw_token: str) -> str:
    """
    Hashuje surowy token za pomocą SHA-256.
    
    Args:
        raw_token: Surowy token do zhashowania
        
    Returns:
        Hex string SHA-256 hash (64 znaki)
    """
    return hashlib.sha256(raw_token.encode('utf-8')).hexdigest()


def create_token(employee: Employee, purpose: str, ttl_minutes: int) -> str:
    """
    Tworzy nowy token autentykacji dla pracownika.
    
    Args:
        employee: Obiekt Employee
        purpose: Cel tokenu ("INVITE" lub "RESET")
        ttl_minutes: Czas życia tokenu w minutach
        
    Returns:
        Surowy token (tylko raz zwracany, nie jest zapisywany)
        
    Raises:
        ValueError: Jeśli purpose jest nieprawidłowy
    """
    if purpose not in ["INVITE", "RESET"]:
        raise ValueError(f"Invalid purpose: {purpose}. Must be INVITE or RESET.")
    
    # Generuj bezpieczny losowy token
    raw_token = secrets.token_urlsafe(32)
    
    # Hashuj token przed zapisem
    token_hash = _hash_token(raw_token)
    
    # Oblicz czas wygaśnięcia
    expires_at = timezone.now() + timedelta(minutes=ttl_minutes)
    
    # Zapisz do bazy danych
    AuthToken.objects.create(
        token_hash=token_hash,
        purpose=purpose,
        employee=employee,
        expires_at=expires_at,
        used_at=None
    )
    
    # Zwróć surowy token (tylko raz!)
    return raw_token


def validate_token(raw_token: str, purpose: str) -> Employee:
    """
    Waliduje token bez oznaczania go jako użyty.
    
    Args:
        raw_token: Surowy token do walidacji
        purpose: Oczekiwany cel tokenu ("INVITE" lub "RESET")
        
    Returns:
        Obiekt Employee powiązany z tokenem
        
    Raises:
        TokenNotFound: Token nie istnieje w bazie
        TokenExpired: Token wygasł
        TokenUsed: Token został już użyty
        WrongPurpose: Token ma inny purpose
    """
    # Hashuj token aby wyszukać w bazie
    token_hash = _hash_token(raw_token)
    
    try:
        token = AuthToken.objects.select_related('employee').get(token_hash=token_hash)
    except AuthToken.DoesNotExist:
        raise TokenNotFound("Token nie istnieje lub jest nieprawidłowy.")
    
    # Sprawdź purpose
    if token.purpose != purpose:
        raise WrongPurpose(
            f"Token ma purpose '{token.purpose}', oczekiwano '{purpose}'."
        )
    
    # Sprawdź czy token nie został już użyty
    if token.used_at is not None:
        raise TokenUsed("Token został już użyty.")
    
    # Sprawdź czy token nie wygasł
    if timezone.now() > token.expires_at:
        raise TokenExpired("Token wygasł.")
    
    return token.employee


def consume_token(raw_token: str, purpose: str) -> Employee:
    """
    Waliduje token i oznacza go jako użyty (jednorazowe użycie).
    
    Ta funkcja jest atomowa - walidacja i oznaczenie następują w transakcji.
    
    Args:
        raw_token: Surowy token do skonsumowania
        purpose: Oczekiwany cel tokenu ("INVITE" lub "RESET")
        
    Returns:
        Obiekt Employee powiązany z tokenem
        
    Raises:
        TokenNotFound: Token nie istnieje w bazie
        TokenExpired: Token wygasł
        TokenUsed: Token został już użyty
        WrongPurpose: Token ma inny purpose
    """
    from django.db import transaction
    
    with transaction.atomic():
        # Waliduj token
        employee = validate_token(raw_token, purpose)
        
        # Oznacz token jako użyty
        token_hash = _hash_token(raw_token)
        AuthToken.objects.filter(token_hash=token_hash).update(
            used_at=timezone.now()
        )
    
    return employee
