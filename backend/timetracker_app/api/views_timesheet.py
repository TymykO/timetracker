"""
Widoki API dla timesheet.
"""

from datetime import datetime, timedelta
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.contrib.auth.decorators import login_required
from django.utils import timezone
import json

from timetracker_app.services.timesheet_service import (
    get_month_summary, get_day, save_day,
    FutureDateError, NotEditableError, InvalidDurationError,
    DuplicateTaskInPayloadError, DayTotalExceededError
)
from timetracker_app.api.schemas import SaveDayItemRequest


# Helper dla 401/403 checks
def _get_active_employee(request):
    """
    Zwraca employee lub JsonResponse z błędem.
    
    Returns:
        tuple: (employee, None) jeśli OK, lub (None, error_response) jeśli błąd
    """
    try:
        employee = request.user.employee
    except AttributeError:
        return None, JsonResponse({'error': 'Employee not found'}, status=403)
    
    if not employee.is_active:
        return None, JsonResponse({'error': 'Account is inactive'}, status=403)
    
    return employee, None


@require_http_methods(["GET"])
@login_required
def month_summary_view(request):
    """
    GET /api/timesheet/month?month=YYYY-MM
    
    Zwraca podsumowanie miesiąca dla month view.
    
    Query params:
    - month: string YYYY-MM (np. "2025-03")
    
    Response:
    {
        "month": "YYYY-MM",
        "days": [
            {
                "date": "YYYY-MM-DD",
                "day_type": "Working"|"Free",
                "working_time_raw_minutes": int,
                "overtime_minutes": int,
                "has_entries": bool,
                "is_future": bool,
                "is_editable": bool
            },
            ...
        ]
    }
    
    Status codes:
    - 200: Success
    - 400: Invalid month format lub future month
    - 403: Employee nieaktywny
    """
    employee, error_response = _get_active_employee(request)
    if error_response:
        return error_response
    
    # Parsuj month
    month_str = request.GET.get('month')
    if not month_str:
        return JsonResponse({'error': 'Missing month parameter'}, status=400)
    
    try:
        month_date = datetime.strptime(month_str, '%Y-%m').date()
    except ValueError:
        return JsonResponse({'error': 'Invalid month format (expected YYYY-MM)'}, status=400)
    
    # Nie pozwalaj na przyszłe miesiące
    today = timezone.now().date()
    first_of_next_month = (today.replace(day=1) + timedelta(days=32)).replace(day=1)
    if month_date >= first_of_next_month:
        return JsonResponse({'error': 'Cannot access future months'}, status=400)
    
    # Wywołaj service
    result = get_month_summary(employee, month_date)
    return JsonResponse(result.to_dict())


@require_http_methods(["GET"])
@login_required
def day_view(request):
    """
    GET /api/timesheet/day?date=YYYY-MM-DD
    
    Zwraca szczegóły dnia dla day view.
    
    Query params:
    - date: string YYYY-MM-DD
    
    Response:
    {
        "date": "YYYY-MM-DD",
        "day_type": "Working"|"Free",
        "is_future": bool,
        "is_editable": bool,
        "total_raw_minutes": int,
        "total_overtime_minutes": int,
        "entries": [
            {
                "task_id": int,
                "task_display_name": str,
                "duration_minutes_raw": int,
                "billable_half_hours": int
            },
            ...
        ]
    }
    
    Status codes:
    - 200: Success
    - 400: Invalid date format
    - 403: Employee nieaktywny
    """
    employee, error_response = _get_active_employee(request)
    if error_response:
        return error_response
    
    # Parsuj date
    date_str = request.GET.get('date')
    if not date_str:
        return JsonResponse({'error': 'Missing date parameter'}, status=400)
    
    try:
        work_date = datetime.strptime(date_str, '%Y-%m-%d').date()
    except ValueError:
        return JsonResponse({'error': 'Invalid date format (expected YYYY-MM-DD)'}, status=400)
    
    # Wywołaj service
    result = get_day(employee, work_date)
    return JsonResponse(result.to_dict())


@require_http_methods(["POST"])
@login_required
def save_day_view(request):
    """
    POST /api/timesheet/day/save
    
    Zapisuje entries dla dnia (full-state).
    
    Request body:
    {
        "date": "YYYY-MM-DD",
        "items": [
            {"task_id": int, "duration_minutes_raw": int},
            ...
        ]
    }
    
    Response:
    {
        "success": bool,
        "day": {DayDTO},
        "errors": [str] | null
    }
    
    Status codes:
    - 200: Success
    - 400: Validation errors (future date, not editable, duration errors, etc.)
    - 403: Employee nieaktywny
    - 500: Unexpected error
    """
    employee, error_response = _get_active_employee(request)
    if error_response:
        return error_response
    
    # Parsuj JSON
    try:
        data = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({'error': 'Invalid JSON'}, status=400)
    
    # Parsuj date
    date_str = data.get('date')
    if not date_str:
        return JsonResponse({'error': 'Missing date field'}, status=400)
    
    try:
        work_date = datetime.strptime(date_str, '%Y-%m-%d').date()
    except ValueError:
        return JsonResponse({'error': 'Invalid date format'}, status=400)
    
    # Parsuj items
    items_raw = data.get('items', [])
    try:
        items = [
            SaveDayItemRequest(
                task_id=item['task_id'],
                duration_minutes_raw=item['duration_minutes_raw']
            )
            for item in items_raw
        ]
    except (KeyError, TypeError) as e:
        return JsonResponse({'error': f'Invalid items format: {e}'}, status=400)
    
    # Wywołaj service (obsługa wyjątków domenowych)
    try:
        result = save_day(employee, work_date, items)
        return JsonResponse(result.to_dict())
    except FutureDateError as e:
        return JsonResponse({'error': str(e)}, status=400)
    except NotEditableError as e:
        return JsonResponse({'error': str(e)}, status=400)
    except InvalidDurationError as e:
        return JsonResponse({'error': str(e)}, status=400)
    except DuplicateTaskInPayloadError as e:
        return JsonResponse({'error': str(e)}, status=400)
    except DayTotalExceededError as e:
        return JsonResponse({'error': str(e)}, status=400)
    except Exception as e:
        # Unexpected errors
        return JsonResponse({'error': f'Internal error: {str(e)}'}, status=500)
