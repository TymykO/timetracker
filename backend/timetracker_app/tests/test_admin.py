"""
Testy dla Django Admin.

Pokrycie:
- EmployeeAdmin.save_model: automatyczne tworzenie User dla nowego Employee
- Obsługa kolizji username
"""

from django.test import TestCase
from django.contrib.admin.sites import AdminSite
from django.contrib.auth.models import User

from timetracker_app.admin import EmployeeAdmin
from timetracker_app.models import Employee


class MockRequest:
    """Mock request dla testów admin."""
    pass


class EmployeeAdminTestCase(TestCase):
    """Testy dla EmployeeAdmin."""
    
    def setUp(self):
        """Setup: tworzy AdminSite i EmployeeAdmin."""
        self.site = AdminSite()
        self.admin = EmployeeAdmin(Employee, self.site)
    
    def test_save_model_creates_user(self):
        """Test: save_model automatycznie tworzy User dla nowego Employee."""
        employee = Employee(
            email="newemployee@example.com",
            is_active=True,
            daily_norm_minutes=480
        )
        
        request = MockRequest()
        
        # Zapisz przez admin (change=False oznacza nowy obiekt)
        self.admin.save_model(request, employee, None, change=False)
        
        # Sprawdź że Employee został zapisany
        self.assertIsNotNone(employee.pk)
        employee.refresh_from_db()
        
        # Sprawdź że User został utworzony
        self.assertIsNotNone(employee.user)
        self.assertEqual(employee.user.username, "newemployee@example.com")
        self.assertEqual(employee.user.email, "newemployee@example.com")
        self.assertFalse(employee.user.is_active)
        self.assertFalse(employee.user.has_usable_password())
    
    def test_save_model_handles_username_collision(self):
        """Test: save_model obsługuje kolizję username dodając suffix."""
        # Utwórz istniejącego User z tym samym email jako username
        User.objects.create_user(
            username="test@example.com",
            email="other@example.com"
        )
        
        employee = Employee(
            email="test@example.com",
            is_active=True,
            daily_norm_minutes=480
        )
        
        request = MockRequest()
        
        # Zapisz - powinno dodać suffix
        self.admin.save_model(request, employee, None, change=False)
        
        # Sprawdź że Employee został zapisany
        self.assertIsNotNone(employee.pk)
        employee.refresh_from_db()
        
        # Username powinien być test@example.com_1 (lub kolejny wolny suffix)
        self.assertIsNotNone(employee.user)
        self.assertNotEqual(employee.user.username, "test@example.com")
        self.assertTrue(employee.user.username.startswith("test@example.com"))
        self.assertEqual(employee.user.email, "test@example.com")
        self.assertFalse(employee.user.is_active)
        self.assertFalse(employee.user.has_usable_password())
    
    def test_save_model_handles_multiple_collisions(self):
        """Test: save_model obsługuje wiele kolizji username."""
        # Utwórz kilku użytkowników z kolizyjnymi username
        User.objects.create_user(
            username="collision@example.com",
            email="first@example.com"
        )
        User.objects.create_user(
            username="collision@example.com_1",
            email="second@example.com"
        )
        User.objects.create_user(
            username="collision@example.com_2",
            email="third@example.com"
        )
        
        employee = Employee(
            email="collision@example.com",
            is_active=True,
            daily_norm_minutes=480
        )
        
        request = MockRequest()
        
        # Zapisz - powinno znaleźć wolny suffix (_3)
        self.admin.save_model(request, employee, None, change=False)
        
        # Sprawdź że Employee został zapisany z poprawnym username
        self.assertIsNotNone(employee.pk)
        employee.refresh_from_db()
        
        self.assertEqual(employee.user.username, "collision@example.com_3")
        self.assertEqual(employee.user.email, "collision@example.com")
        self.assertFalse(employee.user.is_active)
    
    def test_save_model_does_not_modify_existing_employee(self):
        """Test: save_model nie modyfikuje istniejącego Employee (change=True)."""
        # Utwórz Employee z User
        user = User.objects.create_user(
            username="existing@example.com",
            email="existing@example.com",
            is_active=True
        )
        employee = Employee.objects.create(
            user=user,
            email="existing@example.com",
            is_active=True,
            daily_norm_minutes=480
        )
        
        original_user_id = employee.user.id
        
        # Edytuj Employee (zmień daily_norm_minutes)
        employee.daily_norm_minutes = 520
        
        request = MockRequest()
        
        # Zapisz przez admin (change=True oznacza edycję)
        self.admin.save_model(request, employee, None, change=True)
        
        employee.refresh_from_db()
        
        # Sprawdź że User nie został zmieniony
        self.assertEqual(employee.user.id, original_user_id)
        self.assertEqual(employee.daily_norm_minutes, 520)
    
    def test_created_user_can_be_activated_by_invite_flow(self):
        """Test: User utworzony przez admin może być aktywowany przez invite flow."""
        from timetracker_app.auth import password_flows
        
        # Utwórz Employee przez admin
        employee = Employee(
            email="invite@example.com",
            is_active=True,
            daily_norm_minutes=480
        )
        
        request = MockRequest()
        self.admin.save_model(request, employee, None, change=False)
        
        employee.refresh_from_db()
        
        # Sprawdź stan początkowy
        self.assertFalse(employee.user.is_active)
        self.assertFalse(employee.user.has_usable_password())
        
        # Symuluj invite flow
        result = password_flows.invite_employee(employee)
        raw_token = result["token"]
        
        # Set password przez invite
        password_flows.set_password_from_invite(raw_token, "SecurePassword123!")
        
        employee.user.refresh_from_db()
        
        # Sprawdź że User został aktywowany i ma hasło
        self.assertTrue(employee.user.is_active)
        self.assertTrue(employee.user.has_usable_password())
        self.assertTrue(employee.user.check_password("SecurePassword123!"))


class CalendarOverrideAdminTestCase(TestCase):
    """
    Testy integracyjne dla CalendarOverrideAdmin.response_action.
    
    Sprawdza czy konwersja zlokalizowanych dat działa poprawnie w kontekście
    Django admin bulk actions.
    """
    
    def setUp(self):
        """Setup: tworzy AdminSite, CalendarOverrideAdmin i test data."""
        from timetracker_app.admin import CalendarOverrideAdmin
        from timetracker_app.models import CalendarOverride
        from datetime import date
        from django.test import RequestFactory
        
        self.site = AdminSite()
        self.admin = CalendarOverrideAdmin(CalendarOverride, self.site)
        self.factory = RequestFactory()
        
        # Utwórz testowe override'y
        CalendarOverride.objects.create(
            day=date(2026, 1, 30),
            day_type="Free",
            note="Święto"
        )
        CalendarOverride.objects.create(
            day=date(2026, 2, 15),
            day_type="Working",
            note="Dodatkowy dzień roboczy"
        )
    
    def test_response_action_converts_polish_localized_dates(self):
        """Test: response_action konwertuje polskie zlokalizowane daty."""
        # Użyj RequestFactory aby utworzyć prawidłowy request
        request = self.factory.post('/admin/timetracker_app/calendaroverride/', {
            '_selected_action': ['Sty. 30, 2026'],  # Polski format
            'action': 'delete_selected',
        })
        
        # Dodaj user do request (wymagane przez Django admin)
        from django.contrib.auth.models import User
        request.user = User.objects.create_superuser('admin', 'admin@test.com', 'pass')
        
        queryset = self.admin.get_queryset(request)
        
        # Wywołaj response_action - powinno przekonwertować datę
        result = self.admin.response_action(request, queryset)
        
        # Sprawdź że request.POST zawiera teraz datę w formacie ISO
        converted_dates = request.POST.getlist('_selected_action')
        self.assertEqual(converted_dates, ['2026-01-30'])
    
    def test_response_action_converts_iso_dates_unchanged(self):
        """Test: response_action pozostawia daty ISO bez zmian."""
        from django.contrib.auth.models import User
        
        request = self.factory.post('/admin/timetracker_app/calendaroverride/', {
            '_selected_action': ['2026-01-30'],  # ISO format
            'action': 'delete_selected',
        })
        request.user = User.objects.create_superuser('admin2', 'admin2@test.com', 'pass')
        
        queryset = self.admin.get_queryset(request)
        
        # Wywołaj response_action
        result = self.admin.response_action(request, queryset)
        
        # Daty ISO powinny pozostać bez zmian
        converted_dates = request.POST.getlist('_selected_action')
        self.assertEqual(converted_dates, ['2026-01-30'])
    
    def test_response_action_converts_numeric_dates(self):
        """Test: response_action konwertuje daty numeryczne."""
        from django.contrib.auth.models import User
        
        request = self.factory.post('/admin/timetracker_app/calendaroverride/', {
            '_selected_action': ['30.01.2026'],  # Numeric format
            'action': 'delete_selected',
        })
        request.user = User.objects.create_superuser('admin3', 'admin3@test.com', 'pass')
        
        queryset = self.admin.get_queryset(request)
        
        # Wywołaj response_action
        result = self.admin.response_action(request, queryset)
        
        # Sprawdź konwersję
        converted_dates = request.POST.getlist('_selected_action')
        self.assertEqual(converted_dates, ['2026-01-30'])
    
    def test_response_action_converts_mixed_formats(self):
        """Test: response_action obsługuje mieszane formaty."""
        from django.contrib.auth.models import User
        
        request = self.factory.post('/admin/timetracker_app/calendaroverride/', {
            '_selected_action': ['2026-01-30', 'Lut. 15, 2026'],
            'action': 'delete_selected',
        })
        request.user = User.objects.create_superuser('admin4', 'admin4@test.com', 'pass')
        
        queryset = self.admin.get_queryset(request)
        
        # Wywołaj response_action
        result = self.admin.response_action(request, queryset)
        
        # Sprawdź konwersję
        converted_dates = request.POST.getlist('_selected_action')
        self.assertEqual(converted_dates, ['2026-01-30', '2026-02-15'])
    
    def test_response_action_skips_invalid_dates(self):
        """Test: response_action pomija nieprawidłowe daty (fail-fast)."""
        from django.contrib.auth.models import User
        
        request = self.factory.post('/admin/timetracker_app/calendaroverride/', {
            '_selected_action': ['2026-01-30', 'invalid date', 'Lut. 15, 2026'],
            'action': 'delete_selected',
        })
        request.user = User.objects.create_superuser('admin5', 'admin5@test.com', 'pass')
        
        queryset = self.admin.get_queryset(request)
        
        # Wywołaj response_action
        result = self.admin.response_action(request, queryset)
        
        # Tylko prawidłowe daty powinny być w wyniku (fail-fast approach)
        converted_dates = request.POST.getlist('_selected_action')
        self.assertEqual(len(converted_dates), 2)
        self.assertEqual(converted_dates, ['2026-01-30', '2026-02-15'])
    
    def test_response_action_without_selected_action(self):
        """Test: response_action działa gdy brak _selected_action."""
        from django.contrib.auth.models import User
        from django.contrib.messages.storage.fallback import FallbackStorage
        
        request = self.factory.post('/admin/timetracker_app/calendaroverride/', {
            'action': 'some_action',
            # Brak '_selected_action'
        })
        request.user = User.objects.create_superuser('admin6', 'admin6@test.com', 'pass')
        
        # Dodaj messages storage (wymagane przez Django admin)
        setattr(request, 'session', {})
        setattr(request, '_messages', FallbackStorage(request))
        
        queryset = self.admin.get_queryset(request)
        
        # Wywołaj response_action - nie powinno rzucić wyjątku
        # Result może być None jeśli akcja nie została znaleziona (to jest OK)
        try:
            result = self.admin.response_action(request, queryset)
            # Jeśli nie rzuciło wyjątku, test przeszedł
        except Exception as e:
            self.fail(f"response_action rzuciło nieoczekiwany wyjątek: {e}")
