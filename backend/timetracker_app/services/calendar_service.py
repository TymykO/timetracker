"""
CalendarService - serwis do określania typu dnia (Working/Free).

Odpowiada za logikę biznesową związaną z kalendarzem:
- domyślne typy dni (weekend = Free, weekday = Working)
- override'y kalendarza (święta, niestandardowe dni)
"""

from datetime import date
from timetracker_app.models import CalendarOverride


def get_day_type(day: date) -> str:
    """
    Zwraca typ dnia: "Working" lub "Free".
    
    Logika:
    1. Sprawdź czy istnieje CalendarOverride dla tej daty
       - jeśli tak, zwróć typ z override (np. święto w poniedziałek -> Free)
    2. Jeśli brak override, użyj domyślnej zasady:
       - Sobota (weekday=5) lub Niedziela (weekday=6) -> "Free"
       - Pozostałe dni (pon-pią) -> "Working"
    
    Args:
        day: Data do sprawdzenia
        
    Returns:
        "Working" lub "Free"
    """
    # Sprawdź czy istnieje override dla tego dnia
    try:
        override = CalendarOverride.objects.get(day=day)
        return override.day_type
    except CalendarOverride.DoesNotExist:
        pass
    
    # Brak override - użyj domyślnej zasady weekendowej
    # weekday(): 0=poniedziałek, 1=wtorek, ..., 5=sobota, 6=niedziela
    weekday = day.weekday()
    
    if weekday in (5, 6):  # Sobota lub niedziela
        return "Free"
    else:  # Poniedziałek-piątek
        return "Working"
