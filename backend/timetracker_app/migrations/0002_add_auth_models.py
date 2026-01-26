# Generated manually for auth system implementation

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


def create_users_for_employees(apps, schema_editor):
    """
    Data migration: tworzy User dla każdego istniejącego Employee.
    Username = email, is_active kopiowane z Employee.
    Hasło ustawione jako unusable (wymaga set-password przez invite).
    """
    Employee = apps.get_model('timetracker_app', 'Employee')
    User = apps.get_model('auth', 'User')
    
    for employee in Employee.objects.all():
        # Sprawdź czy user już nie istnieje dla tego email
        user, created = User.objects.get_or_create(
            username=employee.email,
            defaults={
                'email': employee.email,
                'is_active': employee.is_active,
                'is_staff': False,
                'is_superuser': False,
                # Hasło ustawione jako unusable - wymaga invite flow
                'password': '!',  # Django marker for unusable password
            }
        )
        
        # Powiąż employee z user (pole user będzie dodane w kolejnym kroku)
        employee.user = user
        employee.save(update_fields=['user'])


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('timetracker_app', '0001_initial'),
    ]

    operations = [
        # Krok 1: Dodaj model AuthToken
        migrations.CreateModel(
            name='AuthToken',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('token_hash', models.CharField(db_index=True, max_length=64, unique=True, verbose_name='Hash tokenu')),
                ('purpose', models.CharField(choices=[('INVITE', 'Invite'), ('RESET', 'Password Reset')], max_length=20, verbose_name='Cel tokenu')),
                ('expires_at', models.DateTimeField(verbose_name='Wygasa')),
                ('used_at', models.DateTimeField(blank=True, null=True, verbose_name='Użyty')),
                ('created_at', models.DateTimeField(auto_now_add=True, verbose_name='Utworzony')),
            ],
            options={
                'verbose_name': 'Token autentykacji',
                'verbose_name_plural': 'Tokeny autentykacji',
                'db_table': 'auth_token',
                'ordering': ['-created_at'],
                'indexes': [
                    models.Index(fields=['token_hash'], name='idx_auth_token_hash'),
                ],
            },
        ),
        
        # Krok 2: Dodaj pole Employee.user (nullable na początku)
        migrations.AddField(
            model_name='employee',
            name='user',
            field=models.OneToOneField(
                null=True,
                blank=True,
                on_delete=django.db.models.deletion.CASCADE,
                related_name='employee',
                to=settings.AUTH_USER_MODEL,
                verbose_name='Użytkownik Django'
            ),
        ),
        
        # Krok 3: Data migration - utwórz User dla każdego Employee
        migrations.RunPython(
            create_users_for_employees,
            reverse_code=migrations.RunPython.noop,
        ),
        
        # Krok 4: Ustaw Employee.user jako NOT NULL
        migrations.AlterField(
            model_name='employee',
            name='user',
            field=models.OneToOneField(
                on_delete=django.db.models.deletion.CASCADE,
                related_name='employee',
                to=settings.AUTH_USER_MODEL,
                verbose_name='Użytkownik Django'
            ),
        ),
        
        # Krok 5: Usuń pole Employee.password
        migrations.RemoveField(
            model_name='employee',
            name='password',
        ),
        
        # Krok 6: Dodaj FK AuthToken -> Employee
        migrations.AddField(
            model_name='authtoken',
            name='employee',
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.CASCADE,
                related_name='auth_tokens',
                to='timetracker_app.employee',
                verbose_name='Pracownik'
            ),
        ),
        
        # Krok 7: Dodaj dodatkowy index
        migrations.AddIndex(
            model_name='authtoken',
            index=models.Index(fields=['employee', 'purpose'], name='idx_auth_emp_purpose'),
        ),
    ]
