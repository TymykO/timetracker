from django.db import models
from django.conf import settings
from django.contrib.auth.models import User
from django.core.validators import MinValueValidator


class Employee(models.Model):
    """
    Model pracownika - podstawowa encja użytkownika systemu.
    Pracownicy są tworzeni wyłącznie przez admina.
    Employee jest domenową tożsamością, User służy do autentykacji.
    """
    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name="employee",
        verbose_name="Użytkownik Django"
    )
    email = models.EmailField(
        unique=True,
        max_length=255,
        verbose_name="Email"
    )
    is_active = models.BooleanField(
        default=True,
        verbose_name="Aktywny"
    )
    daily_norm_minutes = models.PositiveIntegerField(
        default=480,  # 8 godzin
        verbose_name="Dzienna norma czasu (minuty)"
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name="Data utworzenia"
    )
    updated_at = models.DateTimeField(
        auto_now=True,
        verbose_name="Data aktualizacji"
    )

    class Meta:
        db_table = "employee"
        verbose_name = "Pracownik"
        verbose_name_plural = "Pracownicy"
        ordering = ["email"]

    def __str__(self):
        return self.email


class TaskCache(models.Model):
    """
    Cache zadań z zewnętrznego portalu.
    Przechowuje spłaszczone pola filtrów jako stringi dla wygodnego filtrowania w UI.
    """
    external_id = models.CharField(
        max_length=255,
        unique=True,
        verbose_name="ID zewnętrzne"
    )
    is_active = models.BooleanField(
        default=True,
        db_index=True,  # Częste filtrowanie po aktywności
        verbose_name="Aktywny"
    )
    display_name = models.CharField(
        max_length=255,
        verbose_name="Nazwa wyświetlana"
    )
    search_text = models.TextField(
        verbose_name="Tekst do wyszukiwania"
    )
    
    # Pola filtrów - wszystkie nullable dla elastyczności
    account = models.CharField(
        max_length=255,
        blank=True,
        null=True,
        verbose_name="Konto"
    )
    project = models.CharField(
        max_length=255,
        blank=True,
        null=True,
        verbose_name="Projekt"
    )
    phase = models.CharField(
        max_length=255,
        blank=True,
        null=True,
        verbose_name="Faza"
    )
    project_phase = models.CharField(
        max_length=255,
        blank=True,
        null=True,
        verbose_name="Projekt - Faza"
    )
    department = models.CharField(
        max_length=255,
        blank=True,
        null=True,
        verbose_name="Departament"
    )
    discipline = models.CharField(
        max_length=255,
        blank=True,
        null=True,
        verbose_name="Dyscyplina"
    )
    task_type = models.CharField(
        max_length=255,
        blank=True,
        null=True,
        verbose_name="Typ zadania"
    )
    
    # Pole rezerwowe dla pełnych danych JSON
    fields_json = models.JSONField(
        null=True,
        blank=True,
        verbose_name="Pola JSON (rezerwowe)"
    )
    
    synced_at = models.DateTimeField(
        auto_now=True,
        verbose_name="Ostatnia synchronizacja"
    )
    
    class Meta:
        db_table = "task_cache"
        verbose_name = "Zadanie (cache)"
        verbose_name_plural = "Zadania (cache)"
        ordering = ["display_name"]
        indexes = [
            models.Index(fields=["is_active"], name="idx_task_is_active"),
            models.Index(fields=["external_id"], name="idx_task_external_id"),
        ]

    def __str__(self):
        return self.display_name


class TimeEntry(models.Model):
    """
    Wpis czasu pracy - pojedynczy rekord czasu dla pracownika/daty/zadania.
    Centralny model domeny timesheet.
    """
    employee = models.ForeignKey(
        Employee,
        on_delete=models.CASCADE,
        related_name="time_entries",
        verbose_name="Pracownik"
    )
    task = models.ForeignKey(
        TaskCache,
        on_delete=models.PROTECT,  # PROTECT - nie usuwaj zadania jeśli są wpisy
        related_name="time_entries",
        verbose_name="Zadanie"
    )
    work_date = models.DateField(
        verbose_name="Data pracy"
    )
    duration_minutes_raw = models.PositiveIntegerField(
        validators=[MinValueValidator(1)],
        verbose_name="Czas trwania (minuty)"
    )
    billable_half_hours = models.PositiveIntegerField(
        validators=[MinValueValidator(1)],
        verbose_name="Rozliczalne półgodziny"
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name="Data utworzenia"
    )
    updated_at = models.DateTimeField(
        auto_now=True,
        verbose_name="Data aktualizacji"
    )

    class Meta:
        db_table = "time_entry"
        verbose_name = "Wpis czasu"
        verbose_name_plural = "Wpisy czasu"
        ordering = ["-work_date", "employee"]
        
        # Ograniczenia bazodanowe
        constraints = [
            # Unikalność: jeden wpis na pracownika/datę/zadanie
            models.UniqueConstraint(
                fields=["employee", "work_date", "task"],
                name="unique_entry_per_employee_date_task"
            ),
            # Walidacja: czas > 0
            models.CheckConstraint(
                condition=models.Q(duration_minutes_raw__gt=0),
                name="check_duration_positive"
            ),
            # Walidacja: rozliczalne półgodziny >= 1
            models.CheckConstraint(
                condition=models.Q(billable_half_hours__gte=1),
                name="check_billable_min_one"
            ),
        ]
        
        # Indeksy dla częstych zapytań
        indexes = [
            # Composite index dla zapytań dzień/miesiąc na pracownika
            models.Index(
                fields=["employee", "work_date"],
                name="idx_entry_emp_date"
            ),
            # Index dla zapytań globalnych po dacie
            models.Index(
                fields=["work_date"],
                name="idx_entry_date"
            ),
        ]

    def __str__(self):
        return f"{self.employee.email} - {self.work_date} - {self.task.display_name}"


class CalendarOverride(models.Model):
    """
    Override typu dnia - nadpisanie domyślnego typu dnia (weekend/święta/custom).
    Używane do oznaczania świąt państwowych lub niestandardowych dni roboczych.
    """
    
    DAY_TYPE_CHOICES = [
        ("Working", "Dzień roboczy"),
        ("Free", "Dzień wolny"),
    ]
    
    day = models.DateField(
        primary_key=True,
        unique=True,
        verbose_name="Data"
    )
    day_type = models.CharField(
        max_length=20,
        choices=DAY_TYPE_CHOICES,
        verbose_name="Typ dnia"
    )
    note = models.TextField(
        blank=True,
        null=True,
        verbose_name="Notatka"
    )

    class Meta:
        db_table = "calendar_override"
        verbose_name = "Override kalendarza"
        verbose_name_plural = "Override'y kalendarza"
        ordering = ["-day"]

    def __str__(self):
        return f"{self.day} - {self.get_day_type_display()}"


class AuthToken(models.Model):
    """
    Token autentykacji dla invite i password reset.
    Tokeny są jednorazowe (used_at) i wygasają (expires_at).
    Przechowywany jest tylko hash tokenu (SHA-256), nie surowy token.
    """
    
    PURPOSE_CHOICES = [
        ("INVITE", "Invite"),
        ("RESET", "Password Reset"),
    ]
    
    token_hash = models.CharField(
        max_length=64,  # SHA-256 hex = 64 znaki
        unique=True,
        db_index=True,
        verbose_name="Hash tokenu"
    )
    purpose = models.CharField(
        max_length=20,
        choices=PURPOSE_CHOICES,
        verbose_name="Cel tokenu"
    )
    employee = models.ForeignKey(
        Employee,
        on_delete=models.CASCADE,
        related_name="auth_tokens",
        verbose_name="Pracownik"
    )
    expires_at = models.DateTimeField(
        verbose_name="Wygasa"
    )
    used_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name="Użyty"
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name="Utworzony"
    )

    class Meta:
        db_table = "auth_token"
        verbose_name = "Token autentykacji"
        verbose_name_plural = "Tokeny autentykacji"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["token_hash"], name="idx_auth_token_hash"),
            models.Index(fields=["employee", "purpose"], name="idx_auth_emp_purpose"),
        ]

    def __str__(self):
        return f"{self.get_purpose_display()} - {self.employee.email} - {self.created_at}"
