"""
Comprehensive tests dla TimesheetService i CalendarService.

Testuje wszystkie edge cases zgodnie z wymaganiami domenowymi:
- walidacje dat (przyszłość, okno edycji)
- walidacje duration (>0, <=1440)
- logikę save_day (create/update/delete)
- obliczenia (billable rounding, overtime)
- calendar logic (weekend, override)
"""

from datetime import date, timedelta
from decimal import Decimal
from django.test import TestCase
from django.contrib.auth.models import User
from freezegun import freeze_time

from timetracker_app.models import Employee, TaskCache, TimeEntry, CalendarOverride, OutboxJob
from timetracker_app.services import calendar_service
from timetracker_app.services.timesheet_service import (
    get_day, get_month_summary, save_day,
    FutureDateError, NotEditableError, InvalidDurationError,
    DuplicateTaskInPayloadError, DayTotalExceededError,
    _calculate_hours_decimal, _calculate_overtime, _is_editable
)
from timetracker_app.api.schemas import SaveDayItemRequest


class TimesheetServiceTestCase(TestCase):
    """Test case dla TimesheetService."""
    
    def setUp(self):
        """
        Fixture: tworzy Employee, TaskCache i freeze time na 2025-03-15.
        """
        # User + Employee
        self.user = User.objects.create_user(username='test@example.com', password='testpass')
        self.employee = Employee.objects.create(
            user=self.user,
            email='test@example.com',
            is_active=True,
            daily_norm_minutes=480  # 8h
        )
        
        # TaskCache
        self.task1 = TaskCache.objects.create(
            external_id='TASK-001',
            is_active=True,
            display_name='Task 1',
            search_text='task 1',
            project_phase='Project A - Phase 1',
            department='IT',
            discipline='Backend'
        )
        self.task2 = TaskCache.objects.create(
            external_id='TASK-002',
            is_active=True,
            display_name='Task 2',
            search_text='task 2',
            project_phase='Project B - Phase 2',
            department='IT',
            discipline='Frontend'
        )
        self.task3 = TaskCache.objects.create(
            external_id='TASK-003',
            is_active=True,
            display_name='Task 3',
            search_text='task 3',
            project_phase='Project C - Phase 1',
            department='QA',
            discipline='Testing'
        )
    
    # === Tests dla save_day() - walidacje ===
    
    @freeze_time("2025-03-15 12:00:00", tz_offset=1)
    def test_save_day_rejects_future_date(self):
        """Test 1: save_day odrzuca przyszłą datę."""
        future_date = date(2025, 3, 20)  # Za 5 dni
        items = [SaveDayItemRequest(task_id=self.task1.id, duration_minutes_raw=60)]
        
        with self.assertRaises(FutureDateError):
            save_day(self.employee, future_date, items)
    
    @freeze_time("2025-03-15 12:00:00", tz_offset=1)
    def test_save_day_rejects_old_month(self):
        """Test 2: save_day odrzuca miesiąc starszy niż poprzedni."""
        old_date = date(2025, 1, 15)  # Styczeń (2 miesiące wstecz)
        items = [SaveDayItemRequest(task_id=self.task1.id, duration_minutes_raw=60)]
        
        with self.assertRaises(NotEditableError):
            save_day(self.employee, old_date, items)
    
    @freeze_time("2025-03-15 12:00:00", tz_offset=1)
    def test_save_day_accepts_current_month(self):
        """Test 3: save_day akceptuje bieżący miesiąc."""
        current_date = date(2025, 3, 10)
        items = [SaveDayItemRequest(task_id=self.task1.id, duration_minutes_raw=120)]
        
        result = save_day(self.employee, current_date, items)
        
        self.assertTrue(result.success)
        self.assertEqual(TimeEntry.objects.filter(employee=self.employee, work_date=current_date).count(), 1)
    
    @freeze_time("2025-03-15 12:00:00", tz_offset=1)
    def test_save_day_accepts_previous_month(self):
        """Test 4: save_day akceptuje poprzedni miesiąc."""
        prev_month_date = date(2025, 2, 20)
        items = [SaveDayItemRequest(task_id=self.task1.id, duration_minutes_raw=180)]
        
        result = save_day(self.employee, prev_month_date, items)
        
        self.assertTrue(result.success)
        self.assertEqual(TimeEntry.objects.filter(employee=self.employee, work_date=prev_month_date).count(), 1)
    
    @freeze_time("2025-03-15 12:00:00", tz_offset=1)
    def test_save_day_rejects_zero_duration(self):
        """Test 5: save_day odrzuca duration=0."""
        work_date = date(2025, 3, 10)
        items = [SaveDayItemRequest(task_id=self.task1.id, duration_minutes_raw=0)]
        
        with self.assertRaises(InvalidDurationError):
            save_day(self.employee, work_date, items)
    
    @freeze_time("2025-03-15 12:00:00", tz_offset=1)
    def test_save_day_rejects_negative_duration(self):
        """Test 6: save_day odrzuca duration<0."""
        work_date = date(2025, 3, 10)
        items = [SaveDayItemRequest(task_id=self.task1.id, duration_minutes_raw=-10)]
        
        with self.assertRaises(InvalidDurationError):
            save_day(self.employee, work_date, items)
    
    @freeze_time("2025-03-15 12:00:00", tz_offset=1)
    def test_save_day_rejects_duplicate_tasks(self):
        """Test 7: save_day odrzuca duplikaty task_id w payload."""
        work_date = date(2025, 3, 10)
        items = [
            SaveDayItemRequest(task_id=self.task1.id, duration_minutes_raw=60),
            SaveDayItemRequest(task_id=self.task1.id, duration_minutes_raw=90),  # Duplikat
        ]
        
        with self.assertRaises(DuplicateTaskInPayloadError):
            save_day(self.employee, work_date, items)
    
    @freeze_time("2025-03-15")
    def test_save_day_rejects_total_over_1440(self):
        """Test 8: save_day odrzuca sumę >1440 minut."""
        work_date = date(2025, 3, 10)
        items = [
            SaveDayItemRequest(task_id=self.task1.id, duration_minutes_raw=800),
            SaveDayItemRequest(task_id=self.task2.id, duration_minutes_raw=700),  # Suma=1500
        ]
        
        with self.assertRaises(DayTotalExceededError):
            save_day(self.employee, work_date, items)
    
    @freeze_time("2025-03-15 12:00:00", tz_offset=1)
    def test_save_day_accepts_exactly_1440_minutes(self):
        """Test 8b: save_day akceptuje dokładnie 1440 minut (case graniczny)."""
        work_date = date(2025, 3, 10)
        items = [SaveDayItemRequest(task_id=self.task1.id, duration_minutes_raw=1440)]
        
        result = save_day(self.employee, work_date, items)
        
        self.assertTrue(result.success)
        entry = TimeEntry.objects.get(employee=self.employee, work_date=work_date)
        self.assertEqual(entry.duration_minutes_raw, 1440)
    
    @freeze_time("2025-03-15 12:00:00", tz_offset=1)
    def test_db_constraint_duplicate_entry(self):
        """Test 8c: Constraint DB blokuje duplikaty (employee, work_date, task)."""
        from django.db import IntegrityError
        
        work_date = date(2025, 3, 10)
        
        # Utwórz pierwszy entry
        TimeEntry.objects.create(
            employee=self.employee,
            task=self.task1,
            work_date=work_date,
            duration_minutes_raw=120,
            hours_decimal=Decimal('2.0')
        )
        
        # Próba utworzenia duplikatu przez ORM (pominięcie walidacji serwisu)
        with self.assertRaises(IntegrityError):
            TimeEntry.objects.create(
                employee=self.employee,
                task=self.task1,
                work_date=work_date,
                duration_minutes_raw=180,
                hours_decimal=Decimal('3.0')
            )
    
    @freeze_time("2025-03-15 12:00:00", tz_offset=1)
    def test_db_constraint_hours_decimal_min_half(self):
        """Test 8d: Constraint DB wymaga hours_decimal >= 0.5."""
        from django.db import IntegrityError
        from decimal import Decimal
        
        work_date = date(2025, 3, 10)
        
        # Próba utworzenia entry z hours_decimal=0.0 przez ORM
        with self.assertRaises(IntegrityError):
            TimeEntry.objects.create(
                employee=self.employee,
                task=self.task1,
                work_date=work_date,
                duration_minutes_raw=1,  # Technicznie valid duration
                hours_decimal=Decimal('0.0')   # Ale hours_decimal < 0.5 -> constraint fail
            )
    
    # === Tests dla save_day() - CRUD logic ===
    
    @freeze_time("2025-03-15 12:00:00", tz_offset=1)
    def test_save_day_creates_new_entries(self):
        """Test 9: save_day tworzy nowe entries."""
        work_date = date(2025, 3, 10)
        items = [
            SaveDayItemRequest(task_id=self.task1.id, duration_minutes_raw=120),
            SaveDayItemRequest(task_id=self.task2.id, duration_minutes_raw=180),
        ]
        
        result = save_day(self.employee, work_date, items)
        
        self.assertTrue(result.success)
        entries = TimeEntry.objects.filter(employee=self.employee, work_date=work_date)
        self.assertEqual(entries.count(), 2)
        
        entry1 = entries.get(task=self.task1)
        self.assertEqual(entry1.duration_minutes_raw, 120)
        self.assertEqual(entry1.hours_decimal, Decimal('2.0'))  # 120min -> 2.0h
    
    @freeze_time("2025-03-15 12:00:00", tz_offset=1)
    def test_save_day_updates_existing_entries(self):
        """Test 10: save_day aktualizuje istniejące entries."""
        work_date = date(2025, 3, 10)
        
        # Utwórz initial entry
        TimeEntry.objects.create(
            employee=self.employee,
            task=self.task1,
            work_date=work_date,
            duration_minutes_raw=60,
            hours_decimal=Decimal('1.0')
        )
        
        # Update z nową wartością
        items = [SaveDayItemRequest(task_id=self.task1.id, duration_minutes_raw=150)]
        result = save_day(self.employee, work_date, items)
        
        self.assertTrue(result.success)
        entry = TimeEntry.objects.get(employee=self.employee, work_date=work_date, task=self.task1)
        self.assertEqual(entry.duration_minutes_raw, 150)
        self.assertEqual(entry.hours_decimal, Decimal('2.5'))  # 150min -> 2.5h
    
    @freeze_time("2025-03-15 12:00:00", tz_offset=1)
    def test_save_day_deletes_removed_entries(self):
        """Test 11: save_day usuwa entries które zniknęły z payload."""
        work_date = date(2025, 3, 10)
        
        # Utwórz 2 entries
        TimeEntry.objects.create(
            employee=self.employee,
            task=self.task1,
            work_date=work_date,
            duration_minutes_raw=60,
            hours_decimal=Decimal('1.0')
        )
        TimeEntry.objects.create(
            employee=self.employee,
            task=self.task2,
            work_date=work_date,
            duration_minutes_raw=90,
            hours_decimal=Decimal('1.5')
        )
        
        # Payload zawiera tylko task1 (task2 powinien być usunięty)
        items = [SaveDayItemRequest(task_id=self.task1.id, duration_minutes_raw=120)]
        result = save_day(self.employee, work_date, items)
        
        self.assertTrue(result.success)
        entries = TimeEntry.objects.filter(employee=self.employee, work_date=work_date)
        self.assertEqual(entries.count(), 1)
        self.assertEqual(entries.first().task, self.task1)
    
    @freeze_time("2025-03-15 12:00:00", tz_offset=1)
    def test_save_day_mixed_create_update_delete(self):
        """Test 12: save_day - kombinacja create/update/delete."""
        work_date = date(2025, 3, 10)
        
        # Existing: task1, task2
        TimeEntry.objects.create(
            employee=self.employee,
            task=self.task1,
            work_date=work_date,
            duration_minutes_raw=60,
            hours_decimal=Decimal('1.0')
        )
        TimeEntry.objects.create(
            employee=self.employee,
            task=self.task2,
            work_date=work_date,
            duration_minutes_raw=90,
            hours_decimal=Decimal('1.5')
        )
        
        # Payload: task1 (update), task3 (create), task2 missing (delete)
        items = [
            SaveDayItemRequest(task_id=self.task1.id, duration_minutes_raw=150),  # Update
            SaveDayItemRequest(task_id=self.task3.id, duration_minutes_raw=200),  # Create
        ]
        result = save_day(self.employee, work_date, items)
        
        self.assertTrue(result.success)
        entries = TimeEntry.objects.filter(employee=self.employee, work_date=work_date)
        self.assertEqual(entries.count(), 2)
        
        # task1 updated
        entry1 = entries.get(task=self.task1)
        self.assertEqual(entry1.duration_minutes_raw, 150)
        
        # task3 created
        entry3 = entries.get(task=self.task3)
        self.assertEqual(entry3.duration_minutes_raw, 200)
        
        # task2 deleted
        self.assertFalse(entries.filter(task=self.task2).exists())
    
    # === Tests dla hours_decimal calculation ===
    
    def test_hours_decimal_calculation_correct(self):
        """Test 13: hours_decimal zaokrąglone poprawnie do 0.5h."""
        from decimal import Decimal
        
        # 1 min -> 0.5h
        self.assertEqual(_calculate_hours_decimal(1), Decimal('0.5'))
        # 30 min -> 0.5h
        self.assertEqual(_calculate_hours_decimal(30), Decimal('0.5'))
        # 31 min -> 1.0h
        self.assertEqual(_calculate_hours_decimal(31), Decimal('1.0'))
        # 61 min -> 1.5h
        self.assertEqual(_calculate_hours_decimal(61), Decimal('1.5'))
        # 70 min -> 1.5h
        self.assertEqual(_calculate_hours_decimal(70), Decimal('1.5'))
        # 90 min -> 1.5h
        self.assertEqual(_calculate_hours_decimal(90), Decimal('1.5'))
        # 120 min -> 2.0h
        self.assertEqual(_calculate_hours_decimal(120), Decimal('2.0'))
        # 91 min -> 2.0h
        self.assertEqual(_calculate_hours_decimal(91), Decimal('2.0'))
    
    @freeze_time("2025-03-15 12:00:00", tz_offset=1)
    def test_save_day_enqueues_outbox_job(self):
        """Test 14: save_day enqueue'uje OutboxJob z poprawnym dedup_key."""
        work_date = date(2025, 3, 10)
        items = [SaveDayItemRequest(task_id=self.task1.id, duration_minutes_raw=120)]
        
        # Przed save: brak jobów
        self.assertEqual(OutboxJob.objects.count(), 0)
        
        result = save_day(self.employee, work_date, items)
        
        # Po save: job utworzony
        self.assertEqual(OutboxJob.objects.count(), 1)
        job = OutboxJob.objects.first()
        self.assertEqual(job.job_type, "TIMESHEET_DAY_SAVED")
        self.assertEqual(job.dedup_key, f"timesheet:day_saved:{self.employee.id}:2025-03-10")
        self.assertEqual(job.status, "PENDING")
        self.assertEqual(job.payload_json['employee_id'], self.employee.id)
        self.assertEqual(job.payload_json['date'], "2025-03-10")
    
    # === Tests dla month_summary() ===
    
    @freeze_time("2025-03-15 12:00:00", tz_offset=1)
    def test_month_summary_empty_month(self):
        """Test 15: month_summary dla pustego miesiąca."""
        month = date(2025, 3, 1)
        result = get_month_summary(self.employee, month)
        
        self.assertEqual(result.month, "2025-03")
        self.assertEqual(len(result.days), 31)  # Marzec ma 31 dni
        
        # Sprawdź pierwszy dzień
        day1 = result.days[0]
        self.assertEqual(day1['date'], "2025-03-01")
        self.assertEqual(day1['has_entries'], False)
        self.assertEqual(day1['working_time_raw_minutes'], 0)
        # Sobota -> Free -> overtime = 0 (bo raw=0)
        self.assertEqual(day1['day_type'], "Free")
        self.assertEqual(day1['overtime_minutes'], 0)
    
    @freeze_time("2025-03-15 12:00:00", tz_offset=1)
    def test_month_summary_with_entries(self):
        """Test 16: month_summary z entries w kilku dniach."""
        # Utwórz entries
        TimeEntry.objects.create(
            employee=self.employee,
            task=self.task1,
            work_date=date(2025, 3, 5),
            duration_minutes_raw=200,
            hours_decimal=Decimal('3.5')
        )
        TimeEntry.objects.create(
            employee=self.employee,
            task=self.task2,
            work_date=date(2025, 3, 5),
            duration_minutes_raw=300,
            hours_decimal=Decimal('5.0')
        )
        TimeEntry.objects.create(
            employee=self.employee,
            task=self.task1,
            work_date=date(2025, 3, 10),
            duration_minutes_raw=400,
            hours_decimal=Decimal('7.0')
        )
        
        result = get_month_summary(self.employee, date(2025, 3, 1))
        
        # Dzień 5 marca (czwartek)
        day5 = next(d for d in result.days if d['date'] == "2025-03-05")
        self.assertTrue(day5['has_entries'])
        self.assertEqual(day5['working_time_raw_minutes'], 500)  # 200+300
        self.assertEqual(day5['day_type'], "Working")
        self.assertEqual(day5['overtime_minutes'], 20)  # 500-480=20
        
        # Dzień 10 marca (poniedziałek)
        day10 = next(d for d in result.days if d['date'] == "2025-03-10")
        self.assertTrue(day10['has_entries'])
        self.assertEqual(day10['working_time_raw_minutes'], 400)
        self.assertEqual(day10['overtime_minutes'], 0)  # 400<480, brak overtime
    
    @freeze_time("2025-03-15 12:00:00", tz_offset=1)
    def test_month_summary_overtime_working_day(self):
        """Test 17: overtime dla Working day."""
        # Dzień roboczy z 500 min -> overtime = 500-480 = 20
        TimeEntry.objects.create(
            employee=self.employee,
            task=self.task1,
            work_date=date(2025, 3, 5),  # Czwartek
            duration_minutes_raw=500,
            hours_decimal=Decimal('8.5')
        )
        
        result = get_month_summary(self.employee, date(2025, 3, 1))
        day5 = next(d for d in result.days if d['date'] == "2025-03-05")
        
        self.assertEqual(day5['day_type'], "Working")
        self.assertEqual(day5['overtime_minutes'], 20)
    
    @freeze_time("2025-03-15 12:00:00", tz_offset=1)
    def test_month_summary_overtime_free_day(self):
        """Test 18: overtime dla Free day."""
        # Sobota z 300 min -> overtime = 300 (cały czas)
        TimeEntry.objects.create(
            employee=self.employee,
            task=self.task1,
            work_date=date(2025, 3, 1),  # Sobota
            duration_minutes_raw=300,
            hours_decimal=Decimal('5.0')
        )
        
        result = get_month_summary(self.employee, date(2025, 3, 1))
        day1 = next(d for d in result.days if d['date'] == "2025-03-01")
        
        self.assertEqual(day1['day_type'], "Free")
        self.assertEqual(day1['overtime_minutes'], 300)
    
    @freeze_time("2025-03-15 12:00:00", tz_offset=1)
    def test_month_summary_calendar_override(self):
        """Test 19: month_summary z calendar override."""
        # Override: sobota 2025-03-01 jako Working
        CalendarOverride.objects.create(
            day=date(2025, 3, 1),
            day_type="Working",
            note="Dzień pracy zastępczy"
        )
        
        result = get_month_summary(self.employee, date(2025, 3, 1))
        day1 = next(d for d in result.days if d['date'] == "2025-03-01")
        
        # Override nadpisuje weekend rule
        self.assertEqual(day1['day_type'], "Working")
    
    @freeze_time("2025-03-15 12:00:00", tz_offset=1)
    def test_month_summary_future_days_not_editable(self):
        """Test 20: przyszłe dni mają is_future=True, is_editable=False."""
        result = get_month_summary(self.employee, date(2025, 3, 1))
        
        # 2025-03-15 (dziś) - not future, editable
        day15 = next(d for d in result.days if d['date'] == "2025-03-15")
        self.assertFalse(day15['is_future'])
        self.assertTrue(day15['is_editable'])
        
        # 2025-03-20 (przyszłość) - future, not editable
        day20 = next(d for d in result.days if d['date'] == "2025-03-20")
        self.assertTrue(day20['is_future'])
        self.assertFalse(day20['is_editable'])
    
    # === Tests dla get_day() ===
    
    @freeze_time("2025-03-15 12:00:00", tz_offset=1)
    def test_get_day_empty(self):
        """Test 21: get_day dla dnia bez entries."""
        work_date = date(2025, 3, 10)
        result = get_day(self.employee, work_date)
        
        self.assertEqual(result.date, "2025-03-10")
        self.assertEqual(result.day_type, "Working")  # Wtorek
        self.assertFalse(result.is_future)
        self.assertTrue(result.is_editable)
        self.assertEqual(result.total_raw_minutes, 0)
        self.assertEqual(result.total_overtime_minutes, 0)
        self.assertEqual(len(result.entries), 0)
    
    @freeze_time("2025-03-15 12:00:00", tz_offset=1)
    def test_get_day_with_entries(self):
        """Test 22: get_day z entries."""
        work_date = date(2025, 3, 10)
        
        TimeEntry.objects.create(
            employee=self.employee,
            task=self.task1,
            work_date=work_date,
            duration_minutes_raw=200,
            hours_decimal=Decimal('3.5')
        )
        TimeEntry.objects.create(
            employee=self.employee,
            task=self.task2,
            work_date=work_date,
            duration_minutes_raw=300,
            hours_decimal=Decimal('5.0')
        )
        
        result = get_day(self.employee, work_date)
        
        self.assertEqual(result.total_raw_minutes, 500)
        self.assertEqual(result.total_overtime_minutes, 20)  # 500-480
        self.assertEqual(len(result.entries), 2)
        
        # Sprawdź entries
        entry1 = next(e for e in result.entries if e['task_id'] == self.task1.id)
        self.assertEqual(entry1['task_display_name'], "Task 1")
        self.assertEqual(entry1['duration_minutes_raw'], 200)
        self.assertEqual(entry1['hours_decimal'], '3.50')
    
    @freeze_time("2025-03-15 12:00:00", tz_offset=1)
    def test_get_day_future_not_editable(self):
        """Test 23: get_day dla przyszłego dnia."""
        future_date = date(2025, 3, 20)
        result = get_day(self.employee, future_date)
        
        self.assertTrue(result.is_future)
        self.assertFalse(result.is_editable)


class CalendarServiceTestCase(TestCase):
    """Test case dla CalendarService."""
    
    def test_get_day_type_weekend(self):
        """Test 24: get_day_type dla soboty/niedzieli."""
        # Sobota 2025-03-01
        saturday = date(2025, 3, 1)
        self.assertEqual(calendar_service.get_day_type(saturday), "Free")
        
        # Niedziela 2025-03-02
        sunday = date(2025, 3, 2)
        self.assertEqual(calendar_service.get_day_type(sunday), "Free")
    
    def test_get_day_type_weekday(self):
        """Test 25: get_day_type dla dni roboczych."""
        # Poniedziałek 2025-03-03
        monday = date(2025, 3, 3)
        self.assertEqual(calendar_service.get_day_type(monday), "Working")
        
        # Środa 2025-03-05
        wednesday = date(2025, 3, 5)
        self.assertEqual(calendar_service.get_day_type(wednesday), "Working")
        
        # Piątek 2025-03-07
        friday = date(2025, 3, 7)
        self.assertEqual(calendar_service.get_day_type(friday), "Working")
    
    def test_get_day_type_override(self):
        """Test 26: get_day_type z override."""
        # Override: sobota jako Working
        saturday = date(2025, 3, 1)
        CalendarOverride.objects.create(
            day=saturday,
            day_type="Working",
            note="Test override"
        )
        
        self.assertEqual(calendar_service.get_day_type(saturday), "Working")
        
        # Override: poniedziałek jako Free (święto)
        monday = date(2025, 3, 3)
        CalendarOverride.objects.create(
            day=monday,
            day_type="Free",
            note="Święto"
        )
        
        self.assertEqual(calendar_service.get_day_type(monday), "Free")


class IsEditableHelperTestCase(TestCase):
    """Testy dla helpera _is_editable (dodatkowe edge cases)."""
    
    @freeze_time("2025-03-15 12:00:00", tz_offset=1)
    def test_is_editable_current_month(self):
        """is_editable: bieżący miesiąc."""
        today = date(2025, 3, 15)
        work_date = date(2025, 3, 1)
        self.assertTrue(_is_editable(work_date, today))
    
    @freeze_time("2025-03-15 12:00:00", tz_offset=1)
    def test_is_editable_previous_month(self):
        """is_editable: poprzedni miesiąc."""
        today = date(2025, 3, 15)
        work_date = date(2025, 2, 20)
        self.assertTrue(_is_editable(work_date, today))
    
    @freeze_time("2025-03-15 12:00:00", tz_offset=1)
    def test_is_editable_two_months_ago(self):
        """is_editable: 2 miesiące wstecz -> NOT editable."""
        today = date(2025, 3, 15)
        work_date = date(2025, 1, 15)
        self.assertFalse(_is_editable(work_date, today))
    
    @freeze_time("2025-03-15 12:00:00", tz_offset=1)
    def test_is_editable_future(self):
        """is_editable: przyszłość -> NOT editable."""
        today = date(2025, 3, 15)
        work_date = date(2025, 3, 20)
        self.assertFalse(_is_editable(work_date, today))


class OvertimeCalculationTestCase(TestCase):
    """Testy dla helpera _calculate_overtime (dodatkowe edge cases)."""
    
    def test_overtime_working_day_under_norm(self):
        """overtime Working: poniżej normy -> 0."""
        self.assertEqual(_calculate_overtime(400, "Working", 480), 0)
    
    def test_overtime_working_day_exact_norm(self):
        """overtime Working: dokładnie norma -> 0."""
        self.assertEqual(_calculate_overtime(480, "Working", 480), 0)
    
    def test_overtime_working_day_over_norm(self):
        """overtime Working: ponad normę -> nadwyżka."""
        self.assertEqual(_calculate_overtime(500, "Working", 480), 20)
    
    def test_overtime_free_day_zero(self):
        """overtime Free: 0 minut -> 0."""
        self.assertEqual(_calculate_overtime(0, "Free", 480), 0)
    
    def test_overtime_free_day_nonzero(self):
        """overtime Free: >0 minut -> cały czas to overtime."""
        self.assertEqual(_calculate_overtime(300, "Free", 480), 300)
        self.assertEqual(_calculate_overtime(600, "Free", 480), 600)


class TimesheetAPITestCase(TestCase):
    """Testy integracyjne dla API timesheet."""
    
    def setUp(self):
        """Setup dla testów API."""
        from django.test import Client
        import json
        
        self.client = Client()
        self.user = User.objects.create_user(username='test@example.com', password='pass')
        self.employee = Employee.objects.create(
            user=self.user,
            email='test@example.com',
            is_active=True,
            daily_norm_minutes=480
        )
        self.task = TaskCache.objects.create(
            external_id='T1',
            is_active=True,
            display_name='Task 1',
            search_text='task 1',
            project_phase='Proj A - Phase 1',
            department='IT',
            discipline='Backend'
        )
    
    @freeze_time("2025-03-15 12:00:00", tz_offset=1)
    def test_month_summary_401_when_not_logged_in(self):
        """Test: 401/302 gdy nie zalogowany."""
        response = self.client.get('/api/timesheet/month?month=2025-03')
        self.assertIn(response.status_code, [302, 401])
    
    @freeze_time("2025-03-15 12:00:00", tz_offset=1)
    def test_month_summary_403_when_inactive(self):
        """Test: 403 gdy employee nieaktywny."""
        self.employee.is_active = False
        self.employee.save()
        self.client.login(username='test@example.com', password='pass')
        
        response = self.client.get('/api/timesheet/month?month=2025-03')
        self.assertEqual(response.status_code, 403)
    
    @freeze_time("2025-03-15 12:00:00", tz_offset=1)
    def test_month_summary_400_invalid_format(self):
        """Test: 400 przy nieprawidłowym formacie month."""
        self.client.login(username='test@example.com', password='pass')
        
        response = self.client.get('/api/timesheet/month?month=invalid')
        self.assertEqual(response.status_code, 400)
    
    @freeze_time("2025-03-15 12:00:00", tz_offset=1)
    def test_month_summary_400_future_month(self):
        """Test: 400 przy próbie dostępu do przyszłego miesiąca."""
        self.client.login(username='test@example.com', password='pass')
        
        response = self.client.get('/api/timesheet/month?month=2025-04')
        self.assertEqual(response.status_code, 400)
    
    @freeze_time("2025-03-15 12:00:00", tz_offset=1)
    def test_month_summary_success(self):
        """Test: sukces dla bieżącego miesiąca."""
        self.client.login(username='test@example.com', password='pass')
        
        response = self.client.get('/api/timesheet/month?month=2025-03')
        self.assertEqual(response.status_code, 200)
        
        data = response.json()
        self.assertEqual(data['month'], '2025-03')
        self.assertEqual(len(data['days']), 31)
        
        # Sprawdź strukturę dnia
        day = data['days'][0]
        self.assertIn('date', day)
        self.assertIn('day_type', day)
        self.assertIn('working_time_raw_minutes', day)
        self.assertIn('overtime_minutes', day)
        self.assertIn('has_entries', day)
        self.assertIn('is_future', day)
        self.assertIn('is_editable', day)
    
    @freeze_time("2025-03-15 12:00:00", tz_offset=1)
    def test_day_view_success(self):
        """Test: GET /api/timesheet/day zwraca szczegóły dnia."""
        self.client.login(username='test@example.com', password='pass')
        
        response = self.client.get('/api/timesheet/day?date=2025-03-10')
        self.assertEqual(response.status_code, 200)
        
        data = response.json()
        self.assertEqual(data['date'], '2025-03-10')
        self.assertIn('day_type', data)
        self.assertIn('total_raw_minutes', data)
        self.assertIn('entries', data)
    
    @freeze_time("2025-03-15 12:00:00", tz_offset=1)
    def test_save_day_success(self):
        """Test: POST /api/timesheet/day/save zapisuje entries."""
        self.client.login(username='test@example.com', password='pass')
        
        import json
        payload = {
            'date': '2025-03-10',
            'items': [
                {'task_id': self.task.id, 'duration_minutes_raw': 120}
            ]
        }
        
        response = self.client.post(
            '/api/timesheet/day/save',
            data=json.dumps(payload),
            content_type='application/json'
        )
        self.assertEqual(response.status_code, 200)
        
        data = response.json()
        self.assertTrue(data['success'])
        self.assertEqual(data['day']['total_raw_minutes'], 120)
        
        # Sprawdź że entry został utworzony w DB
        self.assertEqual(
            TimeEntry.objects.filter(
                employee=self.employee,
                work_date=date(2025, 3, 10)
            ).count(),
            1
        )
    
    @freeze_time("2025-03-15 12:00:00", tz_offset=1)
    def test_save_day_400_future_date(self):
        """Test: 400 przy próbie zapisu przyszłej daty."""
        self.client.login(username='test@example.com', password='pass')
        
        import json
        payload = {
            'date': '2025-03-20',
            'items': [{'task_id': self.task.id, 'duration_minutes_raw': 120}]
        }
        
        response = self.client.post(
            '/api/timesheet/day/save',
            data=json.dumps(payload),
            content_type='application/json'
        )
        self.assertEqual(response.status_code, 400)
        self.assertIn('error', response.json())
    
    @freeze_time("2025-03-15 12:00:00", tz_offset=1)
    def test_save_day_400_zero_duration(self):
        """Test: 400 przy próbie zapisu duration=0."""
        self.client.login(username='test@example.com', password='pass')
        
        import json
        payload = {
            'date': '2025-03-10',
            'items': [{'task_id': self.task.id, 'duration_minutes_raw': 0}]
        }
        
        response = self.client.post(
            '/api/timesheet/day/save',
            data=json.dumps(payload),
            content_type='application/json'
        )
        self.assertEqual(response.status_code, 400)
        self.assertIn('error', response.json())
    
    @freeze_time("2025-03-15 12:00:00", tz_offset=1)
    def test_save_day_400_total_exceeds_1440(self):
        """Test: 400 gdy suma przekracza 1440 minut."""
        self.client.login(username='test@example.com', password='pass')
        
        task2 = TaskCache.objects.create(
            external_id='T2',
            is_active=True,
            display_name='Task 2',
            search_text='task 2',
            project_phase='Proj B - Phase 1',
            department='IT',
            discipline='Backend'
        )
        
        import json
        payload = {
            'date': '2025-03-10',
            'items': [
                {'task_id': self.task.id, 'duration_minutes_raw': 800},
                {'task_id': task2.id, 'duration_minutes_raw': 700}  # Suma: 1500
            ]
        }
        
        response = self.client.post(
            '/api/timesheet/day/save',
            data=json.dumps(payload),
            content_type='application/json'
        )
        self.assertEqual(response.status_code, 400)
        self.assertIn('error', response.json())
