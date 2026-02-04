from django.contrib import admin
from django.contrib.auth.models import User
from django.utils.html import format_html
from django.urls import reverse
from django.contrib import messages
from django.db import transaction

from timetracker_app.models import Employee, TaskCache, TimeEntry, CalendarOverride, AuthToken
from timetracker_app.auth import password_flows


@admin.register(Employee)
class EmployeeAdmin(admin.ModelAdmin):
    """Admin dla modelu Employee z akcją generowania invite linku."""
    
    list_display = ["email", "user_username", "is_active", "daily_norm_minutes", "created_at"]
    list_filter = ["is_active", "created_at"]
    search_fields = ["email", "user__username"]
    readonly_fields = ["created_at", "updated_at", "user_link"]
    
    fieldsets = (
        ("Podstawowe informacje", {
            "fields": ("user_link", "email", "is_active")
        }),
        ("Ustawienia czasu pracy", {
            "fields": ("daily_norm_minutes",)
        }),
        ("Metadane", {
            "fields": ("created_at", "updated_at"),
            "classes": ("collapse",)
        }),
    )
    
    actions = ["generate_invite_link"]
    
    def user_username(self, obj):
        """Wyświetla username powiązanego User."""
        return obj.user.username
    user_username.short_description = "User (Django)"
    
    def user_link(self, obj):
        """Link do powiązanego User w Django admin."""
        if obj.user:
            url = reverse("admin:auth_user_change", args=[obj.user.pk])
            return format_html('<a href="{}">{}</a>', url, obj.user.username)
        return "-"
    user_link.short_description = "Użytkownik Django"
    
    def save_model(self, request, obj, form, change):
        """
        Nadpisuje save_model aby automatycznie tworzyć Django User dla nowego Employee.
        
        Dla nowego Employee:
        - tworzy User z username=email (obsługuje kolizje przez dodanie suffiksu)
        - ustawia email, is_active=False, password=unusable
        - przypisuje User do Employee.user
        - zapisuje atomowo
        """
        if not change:  # Nowy Employee
            with transaction.atomic():
                # Utwórz username z email (obsługa kolizji)
                username = obj.email
                suffix = 1
                while User.objects.filter(username=username).exists():
                    username = f"{obj.email}_{suffix}"
                    suffix += 1
                
                # Utwórz User bez hasła, nieaktywny
                user = User.objects.create_user(
                    username=username,
                    email=obj.email,
                    is_active=False
                )
                user.set_unusable_password()
                user.save()
                
                obj.user = user
        
        super().save_model(request, obj, form, change)
    
    def generate_invite_link(self, request, queryset):
        """Akcja: generuje invite link dla wybranych pracowników."""
        for employee in queryset:
            result = password_flows.invite_employee(employee)
            invite_link = result["link"]
            full_url = request.build_absolute_uri(invite_link)
            
            self.message_user(
                request,
                format_html(
                    'Invite link dla {}: <a href="{}" target="_blank">{}</a>',
                    employee.email,
                    full_url,
                    full_url
                ),
                level=messages.SUCCESS
            )
    generate_invite_link.short_description = "Wygeneruj invite link dla wybranych"


@admin.register(AuthToken)
class AuthTokenAdmin(admin.ModelAdmin):
    """Admin dla modelu AuthToken (read-only)."""
    
    list_display = ["employee", "purpose", "created_at", "expires_at", "used_at", "is_valid"]
    list_filter = ["purpose", "used_at", "created_at"]
    search_fields = ["employee__email", "token_hash"]
    readonly_fields = ["token_hash", "purpose", "employee", "expires_at", "used_at", "created_at"]
    
    fieldsets = (
        ("Token", {
            "fields": ("token_hash", "purpose", "employee")
        }),
        ("Status", {
            "fields": ("expires_at", "used_at", "created_at")
        }),
    )
    
    def has_add_permission(self, request):
        """Nie można dodawać tokenów przez admin (tylko przez API)."""
        return False
    
    def has_change_permission(self, request, obj=None):
        """Nie można edytować tokenów (read-only)."""
        return False
    
    def is_valid(self, obj):
        """Wyświetla czy token jest aktualnie ważny."""
        from django.utils import timezone
        if obj.used_at:
            return format_html('<span style="color: red;">Użyty</span>')
        elif obj.expires_at < timezone.now():
            return format_html('<span style="color: orange;">Wygasły</span>')
        else:
            return format_html('<span style="color: green;">Ważny</span>')
    is_valid.short_description = "Status"


@admin.register(TaskCache)
class TaskCacheAdmin(admin.ModelAdmin):
    """Admin dla modelu TaskCache."""
    
    list_display = ["display_name", "external_id", "is_active", "project", "department", "synced_at"]
    list_filter = ["is_active", "department", "discipline", "task_type"]
    search_fields = ["display_name", "external_id", "search_text"]
    readonly_fields = ["synced_at"]
    
    fieldsets = (
        ("Podstawowe informacje", {
            "fields": ("external_id", "display_name", "is_active")
        }),
        ("Pola filtrów", {
            "fields": ("account", "project", "phase", "project_phase", "department", "discipline", "task_type")
        }),
        ("Wyszukiwanie", {
            "fields": ("search_text",)
        }),
        ("Dane rezerwowe", {
            "fields": ("fields_json", "synced_at"),
            "classes": ("collapse",)
        }),
    )


@admin.register(TimeEntry)
class TimeEntryAdmin(admin.ModelAdmin):
    """Admin dla modelu TimeEntry."""
    
    list_display = ["employee", "work_date", "task", "duration_minutes_raw", "hours_decimal", "created_at"]
    list_filter = ["work_date", "employee", "created_at"]
    search_fields = ["employee__email", "task__display_name"]
    readonly_fields = ["created_at", "updated_at"]
    date_hierarchy = "work_date"
    
    fieldsets = (
        ("Wpis", {
            "fields": ("employee", "task", "work_date")
        }),
        ("Czas", {
            "fields": ("duration_minutes_raw", "hours_decimal")
        }),
        ("Metadane", {
            "fields": ("created_at", "updated_at"),
            "classes": ("collapse",)
        }),
    )


@admin.register(CalendarOverride)
class CalendarOverrideAdmin(admin.ModelAdmin):
    """
    Admin dla modelu CalendarOverride.
    
    Obsługuje zlokalizowane wartości PK (DateField) przy bulk actions.
    """
    
    list_display = ["day", "day_type", "note"]
    list_filter = ["day_type"]
    search_fields = ["note"]
    date_hierarchy = "day"
    
    def __init__(self, *args, **kwargs):
        """
        Inicjalizuje admin z DateConverterService.
        
        DateConverterService jest używany do konwersji zlokalizowanych dat
        z formularzy admin na format ISO 8601.
        """
        super().__init__(*args, **kwargs)
        self.date_converter = self._create_date_converter()
    
    def _create_date_converter(self):
        """
        Factory method dla DateConverterService.
        
        Konfiguruje parsery w kolejności priorytetu:
        1. ISO8601DateParser - najszybszy, dla dat już w ISO format
        2. PolishLocalizedDateParser - dla "Sty. 30, 2026" z Django lokalizacji
        3. NumericDateParser - fallback dla DD.MM.YYYY, DD/MM/YYYY, DD-MM-YYYY
        
        Returns:
            DateConverterService skonfigurowany z parserami
            
        Note:
            Metoda jest wydzielona dla łatwego override w testach lub subclassach.
        """
        from timetracker_app.utils.date_parsers import (
            ISO8601DateParser,
            PolishLocalizedDateParser,
            NumericDateParser,
        )
        from timetracker_app.utils.date_converter import DateConverterService
        
        parsers = [
            ISO8601DateParser(),
            PolishLocalizedDateParser(),
            NumericDateParser(),
        ]
        return DateConverterService(parsers)
    
    def response_action(self, request, queryset):
        """
        Nadpisz response_action aby obsłużyć zlokalizowane wartości PK.
        
        Problem: pole day jest primary_key (DateField) z włączoną lokalizacją (pl-pl).
        Django renderuje checkboxy w changelist z formatem "Sty. 30, 2026".
        request.POST zawiera te zlokalizowane wartości, które powodują ValidationError
        przy próbie użycia ich w queryset.filter(pk__in=selected).
        
        Rozwiązanie: używamy DateConverterService do konwersji dat na format ISO 8601
        przed wywołaniem oryginalnej response_action.
        """
        if '_selected_action' in request.POST:
            selected = request.POST.getlist('_selected_action')
            
            # Użyj DateConverterService do konwersji wszystkich dat na ISO 8601
            converted = self.date_converter.convert_many(selected)
            
            # Zamień request.POST na mutable copy i zaktualizuj wartości
            request.POST = request.POST.copy()
            request.POST.setlist('_selected_action', converted)
        
        return super().response_action(request, queryset)
    
    fieldsets = (
        ("Data i typ", {
            "fields": ("day", "day_type")
        }),
        ("Notatka", {
            "fields": ("note",)
        }),
    )
