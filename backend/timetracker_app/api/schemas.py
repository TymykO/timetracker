"""
Schematy DTO dla API TimeTracker.

Używamy dataclasses dla prostoty (bez dodatkowych zależności).
Schematy dzielą się na Request (wejście) i Response (wyjście).
"""

from dataclasses import dataclass, asdict, field
from typing import Optional, List
from datetime import date


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


@dataclass
class SaveDayItemRequest:
    """Pojedynczy wpis czasu w request save_day."""
    task_id: int
    duration_minutes_raw: int


@dataclass
class SaveDayRequest:
    """Request dla zapisania dnia (POST /api/timesheet/day/save)."""
    date: str  # Format ISO: YYYY-MM-DD
    items: List[SaveDayItemRequest]


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


# === Timesheet DTOs ===

@dataclass
class TimeEntryDTO:
    """Wpis czasu w day view."""
    task_id: int
    task_display_name: str
    duration_minutes_raw: int
    billable_half_hours: int
    
    def to_dict(self):
        return asdict(self)


@dataclass
class DayDTO:
    """Dane dla day view - szczegóły jednego dnia."""
    date: str  # ISO format
    day_type: str  # "Working" lub "Free"
    is_future: bool
    is_editable: bool
    total_raw_minutes: int
    total_overtime_minutes: int
    entries: List[dict]  # Lista TimeEntryDTO.to_dict()
    
    def to_dict(self):
        return asdict(self)


@dataclass
class MonthDayDTO:
    """Pojedynczy dzień w month summary view."""
    date: str  # ISO format
    day_type: str  # "Working" lub "Free"
    working_time_raw_minutes: int
    overtime_minutes: int
    has_entries: bool
    is_future: bool
    is_editable: bool
    
    def to_dict(self):
        return asdict(self)


@dataclass
class MonthSummaryDTO:
    """Podsumowanie miesiąca dla month view."""
    month: str  # Format: YYYY-MM
    days: List[dict]  # Lista MonthDayDTO.to_dict()
    
    def to_dict(self):
        return asdict(self)


@dataclass
class SaveDayResultDTO:
    """Wynik operacji save_day."""
    success: bool
    day: Optional[dict] = None  # DayDTO.to_dict()
    errors: Optional[List[str]] = None
    
    def to_dict(self):
        return asdict(self)


# === Task DTOs ===

@dataclass
class TaskDTO:
    """Pojedynczy task w response dla API."""
    id: int
    display_name: str
    search_text: str
    project_phase: Optional[str]
    department: Optional[str]
    discipline: Optional[str]
    account: Optional[str]
    project: Optional[str]
    phase: Optional[str]
    task_type: Optional[str]
    
    def to_dict(self):
        return asdict(self)


@dataclass
class FilterValuesDTO:
    """Distinct values dla dropdownów filtrów."""
    project_phases: List[str]
    departments: List[str]
    disciplines: List[str]
    
    def to_dict(self):
        return asdict(self)


@dataclass
class TaskListResponseDTO:
    """Response dla GET /api/tasks/active."""
    tasks: List[dict]  # Lista TaskDTO.to_dict()
    filter_values: dict  # FilterValuesDTO.to_dict()
    
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
