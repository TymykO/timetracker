"""
Widoki API dla tasków.
"""

from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.contrib.auth.decorators import login_required

from timetracker_app.models import TaskCache
from timetracker_app.api.schemas import TaskDTO, FilterValuesDTO, TaskListResponseDTO


@require_http_methods(["GET"])
@login_required
def active_tasks_view(request):
    """
    GET /api/tasks/active
    
    Zwraca listę aktywnych tasków z wartościami filtrów.
    
    Response:
    {
        "tasks": [{id, display_name, search_text, ...}, ...],
        "filter_values": {
            "project_phases": [...],
            "departments": [...],
            "disciplines": [...]
        }
    }
    
    Status codes:
    - 200: Success
    - 403: Employee not found lub inactive
    """
    # Auth check
    try:
        employee = request.user.employee
    except AttributeError:
        return JsonResponse({'error': 'Employee not found'}, status=403)
    
    if not employee.is_active:
        return JsonResponse({'error': 'Account is inactive'}, status=403)
    
    # Query active tasks
    tasks_qs = TaskCache.objects.filter(is_active=True).order_by('display_name')
    
    # Build TaskDTOs
    tasks = [
        TaskDTO(
            id=task.id,
            display_name=task.display_name,
            search_text=task.search_text,
            project_phase=task.project_phase,
            department=task.department,
            discipline=task.discipline,
            account=task.account,
            project=task.project,
            phase=task.phase,
            task_type=task.task_type
        ).to_dict()
        for task in tasks_qs
    ]
    
    # Extract distinct filter values (dla dropdownów w UI)
    project_phases = sorted(set(t.project_phase for t in tasks_qs if t.project_phase))
    departments = sorted(set(t.department for t in tasks_qs if t.department))
    disciplines = sorted(set(t.discipline for t in tasks_qs if t.discipline))
    
    filter_values = FilterValuesDTO(
        project_phases=project_phases,
        departments=departments,
        disciplines=disciplines
    )
    
    response = TaskListResponseDTO(
        tasks=tasks,
        filter_values=filter_values.to_dict()
    )
    
    return JsonResponse(response.to_dict())
