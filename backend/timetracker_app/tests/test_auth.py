"""
Testy autentykacji TimeTracker.

Pokrycie:
- tokens.py: create, validate, consume (expired, used, wrong purpose)
- password_flows.py: invite, set password, reset password
- API endpoints: login, logout, me, invite, set-password, reset
"""

from datetime import timedelta
from django.test import TestCase, Client
from django.contrib.auth.models import User
from django.utils import timezone
from django.core.exceptions import ValidationError

from timetracker_app.models import Employee, AuthToken
from timetracker_app.auth import tokens, password_flows


class TokensTestCase(TestCase):
    """Testy dla modułu tokens.py"""
    
    def setUp(self):
        """Setup: tworzy testowego Employee z User."""
        self.user = User.objects.create_user(
            username="test@example.com",
            email="test@example.com",
            password="oldpassword123"
        )
        self.employee = Employee.objects.create(
            user=self.user,
            email="test@example.com",
            is_active=True,
            daily_norm_minutes=480
        )
    
    def test_create_token(self):
        """Test: create_token generuje token i zapisuje hash."""
        raw_token = tokens.create_token(self.employee, "INVITE", 60)
        
        # Token powinien być string
        self.assertIsInstance(raw_token, str)
        self.assertTrue(len(raw_token) > 0)
        
        # Hash powinien być w bazie
        token_hash = tokens._hash_token(raw_token)
        auth_token = AuthToken.objects.get(token_hash=token_hash)
        
        self.assertEqual(auth_token.purpose, "INVITE")
        self.assertEqual(auth_token.employee, self.employee)
        self.assertIsNone(auth_token.used_at)
    
    def test_validate_token_success(self):
        """Test: validate_token zwraca employee dla poprawnego tokenu."""
        raw_token = tokens.create_token(self.employee, "INVITE", 60)
        
        employee = tokens.validate_token(raw_token, "INVITE")
        
        self.assertEqual(employee, self.employee)
    
    def test_validate_token_expired(self):
        """Test: validate_token rzuca TokenExpired dla wygasłego tokenu."""
        raw_token = tokens.create_token(self.employee, "INVITE", 0)
        
        # Symuluj wygaśnięcie (ustaw expires_at w przeszłości)
        token_hash = tokens._hash_token(raw_token)
        auth_token = AuthToken.objects.get(token_hash=token_hash)
        auth_token.expires_at = timezone.now() - timedelta(minutes=1)
        auth_token.save()
        
        with self.assertRaises(tokens.TokenExpired):
            tokens.validate_token(raw_token, "INVITE")
    
    def test_validate_token_used(self):
        """Test: validate_token rzuca TokenUsed dla użytego tokenu."""
        raw_token = tokens.create_token(self.employee, "INVITE", 60)
        
        # Oznacz token jako użyty
        token_hash = tokens._hash_token(raw_token)
        auth_token = AuthToken.objects.get(token_hash=token_hash)
        auth_token.used_at = timezone.now()
        auth_token.save()
        
        with self.assertRaises(tokens.TokenUsed):
            tokens.validate_token(raw_token, "INVITE")
    
    def test_validate_token_wrong_purpose(self):
        """Test: validate_token rzuca WrongPurpose dla niewłaściwego purpose."""
        raw_token = tokens.create_token(self.employee, "INVITE", 60)
        
        with self.assertRaises(tokens.WrongPurpose):
            tokens.validate_token(raw_token, "RESET")
    
    def test_validate_token_not_found(self):
        """Test: validate_token rzuca TokenNotFound dla nieistniejącego tokenu."""
        with self.assertRaises(tokens.TokenNotFound):
            tokens.validate_token("invalid_token", "INVITE")
    
    def test_consume_token(self):
        """Test: consume_token waliduje i oznacza token jako użyty."""
        raw_token = tokens.create_token(self.employee, "INVITE", 60)
        
        employee = tokens.consume_token(raw_token, "INVITE")
        
        self.assertEqual(employee, self.employee)
        
        # Sprawdź że token jest oznaczony jako użyty
        token_hash = tokens._hash_token(raw_token)
        auth_token = AuthToken.objects.get(token_hash=token_hash)
        self.assertIsNotNone(auth_token.used_at)
        
        # Ponowne użycie powinno rzucić TokenUsed
        with self.assertRaises(tokens.TokenUsed):
            tokens.consume_token(raw_token, "INVITE")


class PasswordFlowsTestCase(TestCase):
    """Testy dla modułu password_flows.py"""
    
    def setUp(self):
        """Setup: tworzy testowego Employee z User."""
        self.user = User.objects.create_user(
            username="test@example.com",
            email="test@example.com",
            is_active=False  # Nowy employee, nieaktywny
        )
        self.user.set_unusable_password()  # Hasło nie ustawione
        self.user.save()
        
        self.employee = Employee.objects.create(
            user=self.user,
            email="test@example.com",
            is_active=True,
            daily_norm_minutes=480
        )
    
    def test_invite_employee(self):
        """Test: invite_employee tworzy INVITE token."""
        result = password_flows.invite_employee(self.employee)
        
        self.assertIn("token", result)
        self.assertIn("link", result)
        self.assertIn(result["token"], result["link"])
        
        # Token powinien być w bazie
        token_hash = tokens._hash_token(result["token"])
        auth_token = AuthToken.objects.get(token_hash=token_hash)
        self.assertEqual(auth_token.purpose, "INVITE")
    
    def test_set_password_from_invite_success(self):
        """Test: set_password_from_invite ustawia hasło i aktywuje user."""
        result = password_flows.invite_employee(self.employee)
        raw_token = result["token"]
        
        employee = password_flows.set_password_from_invite(
            raw_token, 
            "NewSecurePassword123!"
        )
        
        # Sprawdź że hasło jest ustawione
        self.user.refresh_from_db()
        self.assertTrue(self.user.check_password("NewSecurePassword123!"))
        self.assertTrue(self.user.is_active)
        
        # Token powinien być oznaczony jako użyty
        token_hash = tokens._hash_token(raw_token)
        auth_token = AuthToken.objects.get(token_hash=token_hash)
        self.assertIsNotNone(auth_token.used_at)
    
    def test_set_password_from_invite_expired(self):
        """Test: set_password_from_invite odrzuca wygasły token."""
        result = password_flows.invite_employee(self.employee)
        raw_token = result["token"]
        
        # Symuluj wygaśnięcie
        token_hash = tokens._hash_token(raw_token)
        auth_token = AuthToken.objects.get(token_hash=token_hash)
        auth_token.expires_at = timezone.now() - timedelta(minutes=1)
        auth_token.save()
        
        with self.assertRaises(tokens.TokenExpired):
            password_flows.set_password_from_invite(raw_token, "NewPassword123!")
    
    def test_set_password_from_invite_used(self):
        """Test: set_password_from_invite odrzuca użyty token."""
        result = password_flows.invite_employee(self.employee)
        raw_token = result["token"]
        
        # Pierwszy raz - sukces
        password_flows.set_password_from_invite(raw_token, "NewPassword123!")
        
        # Drugi raz - powinien rzucić TokenUsed
        with self.assertRaises(tokens.TokenUsed):
            password_flows.set_password_from_invite(raw_token, "AnotherPassword123!")
    
    def test_set_password_weak_password(self):
        """Test: set_password_from_invite odrzuca słabe hasło."""
        result = password_flows.invite_employee(self.employee)
        raw_token = result["token"]
        
        # Django password validation powinno odrzucić słabe hasło
        with self.assertRaises(ValidationError):
            password_flows.set_password_from_invite(raw_token, "123")
    
    def test_request_password_reset_existing(self):
        """Test: request_password_reset tworzy RESET token dla istniejącego email."""
        # Najpierw ustaw hasło
        self.user.set_password("OldPassword123!")
        self.user.is_active = True
        self.user.save()
        
        result = password_flows.request_password_reset("test@example.com")
        
        self.assertIn("message", result)
        self.assertIn("token", result)
        self.assertIsNotNone(result["token"])
        
        # Token RESET powinien być w bazie
        token_hash = tokens._hash_token(result["token"])
        auth_token = AuthToken.objects.get(token_hash=token_hash)
        self.assertEqual(auth_token.purpose, "RESET")
    
    def test_request_password_reset_nonexisting(self):
        """Test: request_password_reset nie ujawnia że email nie istnieje."""
        result = password_flows.request_password_reset("nonexisting@example.com")
        
        self.assertIn("message", result)
        self.assertIsNone(result["token"])  # Token nie został utworzony
        # Ale wiadomość jest taka sama jak dla istniejącego email
    
    def test_request_password_reset_inactive(self):
        """Test: request_password_reset nie tworzy tokenu dla nieaktywnego employee."""
        self.employee.is_active = False
        self.employee.save()
        
        result = password_flows.request_password_reset("test@example.com")
        
        self.assertIn("message", result)
        self.assertIsNone(result["token"])  # Token nie został utworzony
    
    def test_reset_password_confirm_success(self):
        """Test: reset_password_confirm resetuje hasło."""
        # Setup: user z hasłem
        self.user.set_password("OldPassword123!")
        self.user.is_active = True
        self.user.save()
        
        # Request reset
        result = password_flows.request_password_reset("test@example.com")
        raw_token = result["token"]
        
        # Confirm reset
        employee = password_flows.reset_password_confirm(
            raw_token,
            "NewSecurePassword456!"
        )
        
        # Sprawdź że hasło jest zmienione
        self.user.refresh_from_db()
        self.assertTrue(self.user.check_password("NewSecurePassword456!"))
        self.assertFalse(self.user.check_password("OldPassword123!"))
    
    def test_reset_password_confirm_expired(self):
        """Test: reset_password_confirm odrzuca wygasły token."""
        self.user.set_password("OldPassword123!")
        self.user.is_active = True
        self.user.save()
        
        result = password_flows.request_password_reset("test@example.com")
        raw_token = result["token"]
        
        # Symuluj wygaśnięcie
        token_hash = tokens._hash_token(raw_token)
        auth_token = AuthToken.objects.get(token_hash=token_hash)
        auth_token.expires_at = timezone.now() - timedelta(minutes=1)
        auth_token.save()
        
        with self.assertRaises(tokens.TokenExpired):
            password_flows.reset_password_confirm(raw_token, "NewPassword123!")


class AuthAPITestCase(TestCase):
    """Testy dla API endpoints autentykacji."""
    
    def setUp(self):
        """Setup: tworzy testowego Employee z User i hasłem."""
        self.client = Client()
        
        self.user = User.objects.create_user(
            username="test@example.com",
            email="test@example.com",
            password="TestPassword123!",
            is_active=True
        )
        self.employee = Employee.objects.create(
            user=self.user,
            email="test@example.com",
            is_active=True,
            daily_norm_minutes=480
        )
    
    def test_login_success(self):
        """Test: POST /api/auth/login z poprawnymi danymi."""
        response = self.client.post(
            "/api/auth/login",
            data={"email": "test@example.com", "password": "TestPassword123!"},
            content_type="application/json"
        )
        
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn("employee", data)
        self.assertEqual(data["employee"]["email"], "test@example.com")
    
    def test_login_invalid_credentials(self):
        """Test: POST /api/auth/login z błędnym hasłem."""
        response = self.client.post(
            "/api/auth/login",
            data={"email": "test@example.com", "password": "WrongPassword"},
            content_type="application/json"
        )
        
        self.assertEqual(response.status_code, 401)
        data = response.json()
        self.assertIn("error", data)
    
    def test_login_inactive_employee(self):
        """Test: POST /api/auth/login z nieaktywnym employee."""
        self.employee.is_active = False
        self.employee.save()
        
        response = self.client.post(
            "/api/auth/login",
            data={"email": "test@example.com", "password": "TestPassword123!"},
            content_type="application/json"
        )
        
        self.assertEqual(response.status_code, 403)
        data = response.json()
        self.assertIn("error", data)
    
    def test_logout(self):
        """Test: POST /api/auth/logout."""
        # Najpierw zaloguj
        self.client.login(username="test@example.com", password="TestPassword123!")
        
        # Wyloguj
        response = self.client.post("/api/auth/logout")
        
        self.assertEqual(response.status_code, 204)
    
    def test_me_authenticated(self):
        """Test: GET /api/me zwraca profil dla zalogowanego użytkownika."""
        self.client.login(username="test@example.com", password="TestPassword123!")
        
        response = self.client.get("/api/me")
        
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["email"], "test@example.com")
        self.assertEqual(data["daily_norm_minutes"], 480)
    
    def test_me_unauthenticated(self):
        """Test: GET /api/me zwraca 302 redirect dla niezalogowanego."""
        response = self.client.get("/api/me")
        
        # @login_required redirectuje do /accounts/login/?next=/api/me
        self.assertEqual(response.status_code, 302)
    
    def test_invite_validate_valid(self):
        """Test: GET /api/auth/invite/validate z poprawnym tokenem."""
        result = password_flows.invite_employee(self.employee)
        raw_token = result["token"]
        
        response = self.client.get(f"/api/auth/invite/validate?token={raw_token}")
        
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data["valid"])
        self.assertEqual(data["employee_email"], "test@example.com")
    
    def test_invite_validate_invalid(self):
        """Test: GET /api/auth/invite/validate z nieprawidłowym tokenem."""
        response = self.client.get("/api/auth/invite/validate?token=invalid")
        
        self.assertEqual(response.status_code, 400)
        data = response.json()
        self.assertIn("error", data)
    
    def test_set_password_flow(self):
        """Test: Pełny flow invite -> set password."""
        # Setup: nowy employee bez hasła
        new_user = User.objects.create_user(
            username="new@example.com",
            email="new@example.com",
            is_active=False
        )
        new_user.set_unusable_password()
        new_user.save()
        
        new_employee = Employee.objects.create(
            user=new_user,
            email="new@example.com",
            is_active=True,
            daily_norm_minutes=480
        )
        
        # Invite
        result = password_flows.invite_employee(new_employee)
        raw_token = result["token"]
        
        # Set password
        response = self.client.post(
            "/api/auth/set-password",
            data={"token": raw_token, "password": "NewPassword123!"},
            content_type="application/json"
        )
        
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn("message", data)
        
        # Sprawdź że można się teraz zalogować
        login_response = self.client.post(
            "/api/auth/login",
            data={"email": "new@example.com", "password": "NewPassword123!"},
            content_type="application/json"
        )
        self.assertEqual(login_response.status_code, 200)
    
    def test_reset_password_flow(self):
        """Test: Pełny flow reset password."""
        # Request reset
        response = self.client.post(
            "/api/auth/password-reset/request",
            data={"email": "test@example.com"},
            content_type="application/json"
        )
        
        self.assertEqual(response.status_code, 200)
        
        # Pobierz token z bazy (w MVP bez email)
        auth_token = AuthToken.objects.filter(
            employee=self.employee, 
            purpose="RESET"
        ).latest("created_at")
        
        # Znajdź surowy token - dla testów generujemy go ponownie
        # (w prawdziwym świecie byłby w emailu)
        # Tutaj symulujemy że mamy dostęp do tokenu
        result = password_flows.request_password_reset("test@example.com")
        raw_token = result["token"]
        
        # Validate reset token
        validate_response = self.client.get(
            f"/api/auth/password-reset/validate?token={raw_token}"
        )
        self.assertEqual(validate_response.status_code, 200)
        
        # Confirm reset
        confirm_response = self.client.post(
            "/api/auth/password-reset/confirm",
            data={"token": raw_token, "password": "ResetPassword123!"},
            content_type="application/json"
        )
        
        self.assertEqual(confirm_response.status_code, 200)
        
        # Sprawdź że można się zalogować nowym hasłem
        login_response = self.client.post(
            "/api/auth/login",
            data={"email": "test@example.com", "password": "ResetPassword123!"},
            content_type="application/json"
        )
        self.assertEqual(login_response.status_code, 200)
