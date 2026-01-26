"""
Management command do tworzenia danych testowych.
"""

from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from timetracker_app.models import Employee, TaskCache, TimeEntry
from datetime import date, timedelta


class Command(BaseCommand):
    help = 'Tworzy dane testowe dla aplikacji'

    def handle(self, *args, **options):
        self.stdout.write('Tworzenie danych testowych...')

        # Utwórz użytkownika User
        user, created = User.objects.get_or_create(
            username='test@example.com',
            defaults={'email': 'test@example.com'}
        )
        if created:
            user.set_password('testpass123')
            user.save()
            self.stdout.write(self.style.SUCCESS(f'Utworzono User: {user.username}'))
        else:
            self.stdout.write(f'User już istnieje: {user.username}')

        # Utwórz Employee
        employee, created = Employee.objects.get_or_create(
            user=user,
            defaults={
                'email': 'test@example.com',
                'is_active': True,
                'daily_norm_minutes': 480
            }
        )
        if created:
            self.stdout.write(self.style.SUCCESS(f'Utworzono Employee: {employee.email}'))
        else:
            self.stdout.write(f'Employee już istnieje: {employee.email}')

        # Utwórz kilka TaskCache (aktywne zadania)
        tasks = []
        for i in range(1, 6):
            task, created = TaskCache.objects.get_or_create(
                external_id=f'TASK-{i}',
                defaults={
                    'display_name': f'Zadanie {i}',
                    'search_text': f'zadanie {i}',
                    'project_phase': 'Phase 1' if i % 2 == 0 else 'Phase 2',
                    'department': 'IT' if i % 2 == 0 else 'Development',
                    'discipline': 'Backend',
                    'is_active': True
                }
            )
            tasks.append(task)
            if created:
                self.stdout.write(self.style.SUCCESS(f'Utworzono TaskCache: {task.display_name}'))

        # Utwórz wpisy czasu dla ostatnich 3 dni
        today = date.today()
        for days_ago in range(3):
            work_date = today - timedelta(days=days_ago)
            
            # 2 wpisy dla każdego dnia
            for task_idx in range(2):
                TimeEntry.objects.get_or_create(
                    employee=employee,
                    work_date=work_date,
                    task=tasks[task_idx],
                    defaults={
                        'duration_minutes_raw': 200 + (task_idx * 60),
                        'billable_half_hours': (200 + (task_idx * 60)) // 30 + 1
                    }
                )

        self.stdout.write(self.style.SUCCESS('\n=== Dane testowe utworzone ==='))
        self.stdout.write(self.style.SUCCESS('Email: test@example.com'))
        self.stdout.write(self.style.SUCCESS('Hasło: testpass123'))
