"""
Testy dla API tasków.
"""

from django.test import TestCase, Client
from django.contrib.auth.models import User

from timetracker_app.models import Employee, TaskCache


class TasksAPITestCase(TestCase):
    """Testy integracyjne dla API tasków."""
    
    def setUp(self):
        """Setup dla testów - tworzy użytkownika, pracownika i testowe taski."""
        self.client = Client()
        self.user = User.objects.create_user(username='test@example.com', password='pass')
        self.employee = Employee.objects.create(
            user=self.user,
            email='test@example.com',
            is_active=True,
            daily_norm_minutes=480
        )
        
        # Create test tasks
        TaskCache.objects.create(
            external_id='T1',
            is_active=True,
            display_name='Task 1',
            search_text='task 1',
            project_phase='Proj A - Phase 1',
            department='IT',
            discipline='Backend'
        )
        TaskCache.objects.create(
            external_id='T2',
            is_active=True,
            display_name='Task 2',
            search_text='task 2',
            project_phase='Proj B - Phase 2',
            department='QA',
            discipline='Testing'
        )
        TaskCache.objects.create(
            external_id='T3',
            is_active=False,  # Inactive - nie powinien być zwrócony
            display_name='Task 3',
            search_text='task 3',
            project_phase='Proj C - Phase 1',
            department='IT',
            discipline='Frontend'
        )
    
    def test_active_tasks_401_when_not_logged_in(self):
        """Test: 401/302 gdy użytkownik nie jest zalogowany."""
        response = self.client.get('/api/tasks/active')
        # Django @login_required redirects to login page (302) by default
        # W produkcji można to zmienić na 401 przez middleware
        self.assertIn(response.status_code, [302, 401])
    
    def test_active_tasks_403_when_inactive(self):
        """Test: 403 gdy employee jest nieaktywny."""
        self.employee.is_active = False
        self.employee.save()
        self.client.login(username='test@example.com', password='pass')
        
        response = self.client.get('/api/tasks/active')
        self.assertEqual(response.status_code, 403)
        self.assertIn('error', response.json())
    
    def test_active_tasks_returns_only_active(self):
        """Test: endpoint zwraca tylko aktywne taski."""
        self.client.login(username='test@example.com', password='pass')
        
        response = self.client.get('/api/tasks/active')
        self.assertEqual(response.status_code, 200)
        
        data = response.json()
        self.assertIn('tasks', data)
        self.assertEqual(len(data['tasks']), 2)  # Tylko aktywne (T1, T2)
        
        # Sprawdź strukturę task
        task1 = data['tasks'][0]
        self.assertIn('id', task1)
        self.assertIn('display_name', task1)
        self.assertIn('search_text', task1)
        self.assertIn('project_phase', task1)
        self.assertIn('department', task1)
        self.assertIn('discipline', task1)
    
    def test_active_tasks_returns_filter_values(self):
        """Test: endpoint zwraca wartości dla dropdownów filtrów."""
        self.client.login(username='test@example.com', password='pass')
        
        response = self.client.get('/api/tasks/active')
        self.assertEqual(response.status_code, 200)
        
        data = response.json()
        self.assertIn('filter_values', data)
        
        filter_values = data['filter_values']
        self.assertIn('project_phases', filter_values)
        self.assertIn('departments', filter_values)
        self.assertIn('disciplines', filter_values)
        
        # Sprawdź że wartości są correct
        self.assertIn('IT', filter_values['departments'])
        self.assertIn('QA', filter_values['departments'])
        self.assertIn('Backend', filter_values['disciplines'])
        self.assertIn('Testing', filter_values['disciplines'])
        
        # Frontend task (T3) jest inactive, więc nie powinien być w filtrach
        self.assertNotIn('Frontend', filter_values['disciplines'])
