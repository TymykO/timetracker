"""
TimesheetService - główny serwis domenowy dla timesheet.

Odpowiada za:
- walidację reguł biznesowych (daty, okno edycji, limity)
- obliczenia (overtime, billable rounding)
- operacje CRUD na TimeEntry (get_day, save_day, month_summary)
- enqueuowanie outbox jobs
"""

from datetime import date, timedelta
from typing import List
from math import ceil

from django.db import transaction
from django.db.models import Sum
from django.utils import timezone

from timetracker_app.models import Employee, TimeEntry, TaskCache, CalendarOverride
from timetracker_app.services import calendar_service
from timetracker_app.api.schemas import (
    DayDTO, MonthDayDTO, MonthSummaryDTO, SaveDayResultDTO,
    TimeEntryDTO, SaveDayItemRequest
)


# === Wyjątki domenowe ===

class FutureDateError(Exception):
    """Próba edycji daty w przyszłości."""
    pass


class NotEditableError(Exception):
    """Data poza oknem edycji (starszy niż poprzedni miesiąc)."""
    pass


class InvalidDurationError(Exception):
    """Duration <= 0 lub nieprawidłowa wartość."""
    pass


class DuplicateTaskInPayloadError(Exception):
    """Duplikat task_id w payload (nie można zapisać tego samego taska 2 razy)."""
    pass


class DayTotalExceededError(Exception):
    """Suma czasu w dniu przekracza 1440 minut (24h)."""
    pass


# === Helpery obliczeniowe ===

def _calculate_billable_half_hours(raw_minutes: int) -> int:
    """
    Oblicza liczbę rozliczalnych półgodzin z surowych minut.
    
    Zasada: ceil(raw_minutes / 30), minimum 1.
    Przykłady:
    - 1-30 min -> 1 półgodzina
    - 31-60 min -> 2 półgodziny
    - 45 min -> 2 półgodziny
    
    Args:
        raw_minutes: Surowe minuty (>0)
        
    Returns:
        Liczba półgodzin (>=1)
    """
    if raw_minutes <= 0:
        return 1  # Fallback, ale normalnie duration > 0 jest wymagane
    
    return max(1, ceil(raw_minutes / 30))


def _calculate_overtime(day_raw_sum: int, day_type: str, employee_norm: int) -> int:
    """
    Oblicza nadgodziny dla dnia.
    
    Zasady:
    - Working day: overtime = max(0, day_raw_sum - employee_norm)
      Przykład: 500 min pracy przy normie 480 -> 20 min overtime
    - Free day: overtime = day_raw_sum (cały czas to nadgodziny)
      Przykład: 300 min w sobotę -> 300 min overtime
    
    Args:
        day_raw_sum: Suma surowych minut w dniu
        day_type: "Working" lub "Free"
        employee_norm: Dzienna norma pracownika w minutach
        
    Returns:
        Nadgodziny w minutach (>=0)
    """
    if day_type == "Working":
        # W dniu roboczym: tylko nadwyżka ponad normę to overtime
        return max(0, day_raw_sum - employee_norm)
    else:  # Free
        # W dniu wolnym: cały czas to overtime
        return day_raw_sum


def _is_editable(work_date: date, today: date) -> bool:
    """
    Sprawdza czy data jest w oknie edycji.
    
    Zasady:
    - NIE: jeśli work_date > today (przyszłość)
    - NIE: jeśli work_date starszy niż poprzedni miesiąc
    - TAK: jeśli obecny miesiąc lub poprzedni miesiąc
    
    Okno edycji: bieżący miesiąc + poprzedni miesiąc.
    Przykład dla 2025-03-15:
    - 2025-03-10 -> editable (bieżący miesiąc)
    - 2025-02-20 -> editable (poprzedni miesiąc)
    - 2025-01-15 -> NOT editable (starszy niż poprzedni)
    - 2025-03-20 -> NOT editable (przyszłość)
    
    Args:
        work_date: Data do sprawdzenia
        today: Dzisiejsza data
        
    Returns:
        True jeśli editable, False w przeciwnym razie
    """
    # Przyszłość = nie editable
    if work_date > today:
        return False
    
    # Wyznacz początek poprzedniego miesiąca
    # Algorytm: idź do pierwszego dnia bieżącego miesiąca, potem cofnij o 1 dzień
    first_of_current_month = today.replace(day=1)
    last_of_previous_month = first_of_current_month - timedelta(days=1)
    first_of_previous_month = last_of_previous_month.replace(day=1)
    
    # Editable jeśli >= pierwszy dzień poprzedniego miesiąca
    return work_date >= first_of_previous_month


# === Główne funkcje serwisu ===

def get_day(employee: Employee, work_date: date) -> DayDTO:
    """
    Zwraca szczegóły dnia dla day view.
    
    Pseudokod:
    1. Pobierz day_type z CalendarService
    2. Wyznacz is_future (work_date > today)
    3. Wyznacz is_editable (_is_editable)
    4. Query TimeEntry dla (employee, work_date) z select_related(task)
    5. Oblicz total_raw = sum(duration_minutes_raw)
    6. Oblicz overtime = _calculate_overtime(total_raw, day_type, employee.daily_norm_minutes)
    7. Zbuduj listę entries: [{task_id, duration_minutes_raw, billable_half_hours, task_display_name}]
    8. Zwróć DayDTO
    
    Args:
        employee: Pracownik
        work_date: Data dnia
        
    Returns:
        DayDTO z danymi dnia
    """
    today = timezone.now().date()
    
    # 1. Pobierz typ dnia
    day_type = calendar_service.get_day_type(work_date)
    
    # 2-3. Flagi
    is_future = work_date > today
    is_editable = _is_editable(work_date, today)
    
    # 4. Query entries z task info
    entries_qs = TimeEntry.objects.filter(
        employee=employee,
        work_date=work_date
    ).select_related('task')
    
    # 5. Oblicz totals
    total_raw_minutes = sum(e.duration_minutes_raw for e in entries_qs)
    
    # 6. Overtime
    total_overtime_minutes = _calculate_overtime(
        total_raw_minutes,
        day_type,
        employee.daily_norm_minutes
    )
    
    # 7. Zbuduj listę entries
    entries = [
        TimeEntryDTO(
            task_id=entry.task.id,
            task_display_name=entry.task.display_name,
            duration_minutes_raw=entry.duration_minutes_raw,
            billable_half_hours=entry.billable_half_hours
        ).to_dict()
        for entry in entries_qs
    ]
    
    # 8. Zwróć DTO
    return DayDTO(
        date=work_date.isoformat(),
        day_type=day_type,
        is_future=is_future,
        is_editable=is_editable,
        total_raw_minutes=total_raw_minutes,
        total_overtime_minutes=total_overtime_minutes,
        entries=entries
    )


def get_month_summary(employee: Employee, month: date) -> MonthSummaryDTO:
    """
    Zwraca podsumowanie miesiąca dla month view.
    
    Pseudokod:
    1. month_start = first day of month
    2. month_end = last day of month
    3. today = timezone.now().date()
    4. QUERY: aggregate time entries per date
    5. QUERY: calendar overrides dla miesiąca
    6. Dla każdego dnia w [month_start..month_end]:
       a. day_type = overrides.get(day) or CalendarService.get_day_type(day)
       b. raw_sum = entries_dict.get(day, 0)
       c. has_entries = (day in entries_dict)
       d. is_future = (day > today)
       e. is_editable = _is_editable(day, today)
       f. overtime = _calculate_overtime(raw_sum, day_type, employee.daily_norm_minutes)
       g. Dodaj MonthDayDTO do listy
    7. Zwróć MonthSummaryDTO
    
    Wydajność: tylko 2 query (aggregate + overrides), bez N+1.
    
    Args:
        employee: Pracownik
        month: Data reprezentująca miesiąc (np. 2025-03-01 lub dowolny dzień marca)
        
    Returns:
        MonthSummaryDTO z listą dni
    """
    today = timezone.now().date()
    
    # 1-2. Wyznacz zakres miesiąca
    month_start = month.replace(day=1)
    
    # Oblicz ostatni dzień miesiąca: idź do pierwszego dnia następnego miesiąca, cofnij o 1 dzień
    if month_start.month == 12:
        next_month = month_start.replace(year=month_start.year + 1, month=1)
    else:
        next_month = month_start.replace(month=month_start.month + 1)
    month_end = next_month - timedelta(days=1)
    
    # 4. QUERY: aggregate entries per date
    entries_agg = TimeEntry.objects.filter(
        employee=employee,
        work_date__gte=month_start,
        work_date__lte=month_end
    ).values('work_date').annotate(
        raw_sum=Sum('duration_minutes_raw')
    )
    
    # Zbuduj dict {date: raw_sum}
    entries_dict = {item['work_date']: item['raw_sum'] for item in entries_agg}
    
    # 5. QUERY: calendar overrides dla miesiąca
    overrides_qs = CalendarOverride.objects.filter(
        day__gte=month_start,
        day__lte=month_end
    )
    overrides_dict = {override.day: override.day_type for override in overrides_qs}
    
    # 6. Iteracja po dniach miesiąca
    days = []
    current_day = month_start
    
    while current_day <= month_end:
        # a. day_type
        if current_day in overrides_dict:
            day_type = overrides_dict[current_day]
        else:
            day_type = calendar_service.get_day_type(current_day)
        
        # b-c. entries
        raw_sum = entries_dict.get(current_day, 0)
        has_entries = current_day in entries_dict
        
        # d-e. flagi
        is_future = current_day > today
        is_editable = _is_editable(current_day, today)
        
        # f. overtime
        overtime = _calculate_overtime(raw_sum, day_type, employee.daily_norm_minutes)
        
        # g. Dodaj do listy
        day_dto = MonthDayDTO(
            date=current_day.isoformat(),
            day_type=day_type,
            working_time_raw_minutes=raw_sum,
            overtime_minutes=overtime,
            has_entries=has_entries,
            is_future=is_future,
            is_editable=is_editable
        )
        days.append(day_dto.to_dict())
        
        current_day += timedelta(days=1)
    
    # 7. Zwróć DTO
    return MonthSummaryDTO(
        month=month_start.strftime('%Y-%m'),
        days=days
    )


def save_day(employee: Employee, work_date: date, items: List[SaveDayItemRequest]) -> SaveDayResultDTO:
    """
    Zapisuje entries dla dnia (full-state: create/update/delete).
    
    Pseudokod:
    
    # WALIDACJE PRE-TRANSACTION
    1. Jeśli work_date > today → raise FutureDateError
    2. Jeśli !_is_editable(work_date, today) → raise NotEditableError
    3. Dla każdego item:
       - Jeśli duration_minutes_raw <= 0 → raise InvalidDurationError
    4. Sprawdź duplikaty task_id w items → raise DuplicateTaskInPayloadError
    5. total_minutes = sum(item.duration_minutes_raw for item in items)
       - Jeśli total_minutes > 1440 → raise DayTotalExceededError
    
    # TRANSAKCJA
    with transaction.atomic():
        6. SELECT existing entries FOR UPDATE
        7. Zbuduj mapę existing_by_task = {entry.task_id: entry}
        8. Zbuduj mapę payload_task_ids = set(item.task_id for item in items)
        
        9. Dla każdego item w items:
           a. billable = _calculate_billable_half_hours(item.duration_minutes_raw)
           b. Jeśli task_id w existing_by_task:
              - UPDATE: entry.duration_minutes_raw = raw, entry.billable_half_hours = billable
           c. Jeśli task_id NIE w existing_by_task:
              - CREATE: TimeEntry(employee, task_id, work_date, raw, billable)
        
        10. Dla każdego existing_entry gdzie task_id NOT IN payload_task_ids:
            - DELETE: existing_entry.delete()
        
        11. ENQUEUE outbox job
    
    # POST-TRANSACTION
    12. Wywołaj get_day(employee, work_date)
    13. Zwróć SaveResultDTO(success=True, day=day_dto)
    
    Args:
        employee: Pracownik
        work_date: Data dnia
        items: Lista wpisów do zapisania (full state)
        
    Returns:
        SaveDayResultDTO z wynikiem
        
    Raises:
        FutureDateError: Data w przyszłości
        NotEditableError: Data poza oknem edycji
        InvalidDurationError: Duration <= 0
        DuplicateTaskInPayloadError: Duplikat task_id w payload
        DayTotalExceededError: Suma > 1440 min
    """
    from timetracker_app.outbox.dispatcher import enqueue
    
    today = timezone.now().date()
    
    # === WALIDACJE PRE-TRANSACTION ===
    
    # 1. Przyszłość
    if work_date > today:
        raise FutureDateError(f"Nie można edytować przyszłej daty: {work_date}")
    
    # 2. Okno edycji
    if not _is_editable(work_date, today):
        raise NotEditableError(
            f"Data {work_date} poza oknem edycji (dozwolony: bieżący i poprzedni miesiąc)"
        )
    
    # 3. Walidacja duration
    for item in items:
        if item.duration_minutes_raw <= 0:
            raise InvalidDurationError(
                f"Duration musi być > 0, otrzymano: {item.duration_minutes_raw}"
            )
    
    # 4. Duplikaty task_id w payload
    task_ids = [item.task_id for item in items]
    if len(task_ids) != len(set(task_ids)):
        raise DuplicateTaskInPayloadError("Duplikat task_id w payload")
    
    # 5. Suma > 1440 min (24h)
    total_minutes = sum(item.duration_minutes_raw for item in items)
    if total_minutes > 1440:
        raise DayTotalExceededError(
            f"Suma czasu w dniu przekracza 1440 minut: {total_minutes}"
        )
    
    # === TRANSAKCJA ===
    
    with transaction.atomic():
        # 6. SELECT FOR UPDATE
        existing_entries = list(
            TimeEntry.objects.select_for_update().filter(
                employee=employee,
                work_date=work_date
            ).select_related('task')
        )
        
        # 7. Mapa existing
        existing_by_task = {entry.task_id: entry for entry in existing_entries}
        
        # 8. Zbiór task_ids z payload
        payload_task_ids = {item.task_id for item in items}
        
        # 9. CREATE/UPDATE z payload
        for item in items:
            billable = _calculate_billable_half_hours(item.duration_minutes_raw)
            
            if item.task_id in existing_by_task:
                # UPDATE
                entry = existing_by_task[item.task_id]
                entry.duration_minutes_raw = item.duration_minutes_raw
                entry.billable_half_hours = billable
                entry.save(update_fields=['duration_minutes_raw', 'billable_half_hours', 'updated_at'])
            else:
                # CREATE
                task = TaskCache.objects.get(id=item.task_id)
                TimeEntry.objects.create(
                    employee=employee,
                    task=task,
                    work_date=work_date,
                    duration_minutes_raw=item.duration_minutes_raw,
                    billable_half_hours=billable
                )
        
        # 10. DELETE entries nie ma w payload
        for entry in existing_entries:
            if entry.task_id not in payload_task_ids:
                entry.delete()
        
        # 11. ENQUEUE outbox job
        enqueue(
            job_type="TIMESHEET_DAY_SAVED",
            dedup_key=f"timesheet:day_saved:{employee.id}:{work_date.isoformat()}",
            payload={
                "employee_id": employee.id,
                "date": work_date.isoformat(),
            }
        )
    
    # === POST-TRANSACTION ===
    
    # 12. Pobierz świeży stan
    day_dto = get_day(employee, work_date)
    
    # 13. Zwróć wynik
    return SaveDayResultDTO(
        success=True,
        day=day_dto.to_dict()
    )
