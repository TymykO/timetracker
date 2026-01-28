# Generated migration for TimeEntry refactoring: billable_half_hours -> hours_decimal

from django.db import migrations, models
from decimal import Decimal
from math import ceil
import django.core.validators


def backfill_hours_decimal(apps, schema_editor):
    """
    Wypełnij hours_decimal z istniejących duration_minutes_raw.
    
    Formuła: ceil((minutes / 60) * 2) / 2
    """
    TimeEntry = apps.get_model('timetracker_app', 'TimeEntry')
    
    for entry in TimeEntry.objects.all():
        raw_minutes = entry.duration_minutes_raw
        if raw_minutes <= 0:
            half_hours_count = 1  # Minimum
        else:
            half_hours_count = ceil((raw_minutes / 60) * 2)
        entry.hours_decimal = Decimal(half_hours_count) / Decimal('2')
        entry.save(update_fields=['hours_decimal'])


class Migration(migrations.Migration):

    dependencies = [
        ('timetracker_app', '0004_update_task_verbose_names'),
    ]

    operations = [
        # 1. Dodaj hours_decimal (nullable na początku, aby umożliwić backfill)
        migrations.AddField(
            model_name='timeentry',
            name='hours_decimal',
            field=models.DecimalField(
                decimal_places=2,
                max_digits=5,
                null=True,
                verbose_name='Godziny rozliczalne'
            ),
        ),
        
        # 2. Backfill danych z duration_minutes_raw do hours_decimal
        migrations.RunPython(backfill_hours_decimal, migrations.RunPython.noop),
        
        # 3. Usuń constraint dla billable_half_hours
        migrations.RemoveConstraint(
            model_name='timeentry',
            name='check_billable_min_one',
        ),
        
        # 4. Usuń pole billable_half_hours
        migrations.RemoveField(
            model_name='timeentry',
            name='billable_half_hours',
        ),
        
        # 5. Ustaw hours_decimal jako NOT NULL (po backfill wszystkie rekordy mają wartość)
        migrations.AlterField(
            model_name='timeentry',
            name='hours_decimal',
            field=models.DecimalField(
                decimal_places=2,
                max_digits=5,
                validators=[django.core.validators.MinValueValidator(Decimal('0.5'))],
                verbose_name='Godziny rozliczalne'
            ),
        ),
        
        # 6. Dodaj constraint dla hours_decimal >= 0.5
        migrations.AddConstraint(
            model_name='timeentry',
            constraint=models.CheckConstraint(
                condition=models.Q(hours_decimal__gte=Decimal('0.5')),
                name='check_hours_decimal_min_half'
            ),
        ),
    ]
