from django.urls import path
from timetracker_app.api import views_auth, views_tasks, views_timesheet

# API endpoints
urlpatterns = [
    # Auth endpoints
    path("auth/login", views_auth.login_view, name="login"),
    path("auth/logout", views_auth.logout_view, name="logout"),
    path("me", views_auth.me_view, name="me"),
    path("auth/invite/validate", views_auth.invite_validate_view, name="invite_validate"),
    path("auth/set-password", views_auth.set_password_view, name="set_password"),
    path("auth/password-reset/request", views_auth.password_reset_request_view, name="password_reset_request"),
    path("auth/password-reset/validate", views_auth.password_reset_validate_view, name="password_reset_validate"),
    path("auth/password-reset/confirm", views_auth.password_reset_confirm_view, name="password_reset_confirm"),
    
    # Tasks endpoints
    path("tasks/active", views_tasks.active_tasks_view, name="tasks_active"),
    
    # Timesheet endpoints
    path("timesheet/month", views_timesheet.month_summary_view, name="timesheet_month"),
    path("timesheet/day", views_timesheet.day_view, name="timesheet_day"),
    path("timesheet/day/save", views_timesheet.save_day_view, name="timesheet_day_save"),
]
