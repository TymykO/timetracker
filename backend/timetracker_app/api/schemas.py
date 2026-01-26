"""
Schematy DTO dla API TimeTracker.

Używamy dataclasses dla prostoty (bez dodatkowych zależności).
Schematy dzielą się na Request (wejście) i Response (wyjście).
"""

from dataclasses import dataclass, asdict
from typing import Optional


# === Request Schemas (wejście z API) ===

@dataclass
class LoginRequest:
    """Request dla logowania (POST /api/auth/login)."""
    email: str
    password: str


@dataclass
class SetPasswordRequest:
    """Request dla ustawienia hasła z invite tokenu."""
    token: str
    password: str


@dataclass
class ResetPasswordRequestRequest:
    """Request dla żądania resetu hasła."""
    email: str


@dataclass
class ResetPasswordConfirmRequest:
    """Request dla potwierdzenia resetu hasła."""
    token: str
    password: str


# === Response Schemas (wyjście z API) ===

@dataclass
class EmployeeProfileDTO:
    """Profil pracownika (zwracany w /api/me i login)."""
    id: int
    email: str
    is_active: bool
    daily_norm_minutes: int
    
    def to_dict(self):
        """Konwersja do dict dla JSON response."""
        return asdict(self)


@dataclass
class LoginResponse:
    """Response dla logowania."""
    employee: dict  # EmployeeProfileDTO.to_dict()
    
    def to_dict(self):
        return asdict(self)


@dataclass
class MessageResponse:
    """Generyczna odpowiedź z wiadomością."""
    message: str
    
    def to_dict(self):
        return asdict(self)


@dataclass
class TokenValidationResponse:
    """Response dla walidacji tokenu."""
    valid: bool
    employee_email: Optional[str] = None
    
    def to_dict(self):
        return asdict(self)


# === Helpery do parsowania ===

def parse_json_to_dataclass(data: dict, dataclass_type):
    """
    Parsuje dict (z request.POST lub json.loads) do dataclass.
    
    Args:
        data: Dict z danymi
        dataclass_type: Klasa dataclass docelowa
        
    Returns:
        Instancja dataclass
        
    Raises:
        ValueError: Jeśli brakuje wymaganych pól
    """
    try:
        return dataclass_type(**data)
    except TypeError as e:
        raise ValueError(f"Nieprawidłowe dane wejściowe: {e}")
