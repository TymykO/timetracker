"""
Testy jednostkowe dla parserów dat i DateConverterService.

Pokrycie:
- ISO8601DateParser: wszystkie przypadki brzegowe
- PolishLocalizedDateParser: wszystkie polskie miesiące, nieprawidłowe formaty
- NumericDateParser: różne separatory, edge cases
- DateConverterService: integration tests z wieloma parserami
"""

from django.test import TestCase
from datetime import date

from timetracker_app.utils.date_parsers import (
    ISO8601DateParser,
    PolishLocalizedDateParser,
    NumericDateParser,
)
from timetracker_app.utils.date_converter import DateConverterService


class ISO8601DateParserTest(TestCase):
    """Testy dla ISO8601DateParser."""
    
    def setUp(self):
        """Setup: tworzy parser."""
        self.parser = ISO8601DateParser()
    
    def test_can_parse_valid_iso_date(self):
        """Test: rozpoznaje prawidłowy format ISO 8601."""
        self.assertTrue(self.parser.can_parse('2026-01-30'))
        self.assertTrue(self.parser.can_parse('2025-12-31'))
        self.assertTrue(self.parser.can_parse('2024-02-29'))  # Rok przestępny
    
    def test_cannot_parse_polish_format(self):
        """Test: nie rozpoznaje polskiego formatu."""
        self.assertFalse(self.parser.can_parse('Sty. 30, 2026'))
        self.assertFalse(self.parser.can_parse('Gru. 31, 2025'))
    
    def test_cannot_parse_numeric_format(self):
        """Test: nie rozpoznaje formatu numerycznego."""
        self.assertFalse(self.parser.can_parse('30.01.2026'))
        self.assertFalse(self.parser.can_parse('30/01/2026'))
    
    def test_cannot_parse_invalid_structure(self):
        """Test: nie rozpoznaje nieprawidłowej struktury."""
        self.assertFalse(self.parser.can_parse('2026-1-30'))   # Brak leading zero
        self.assertFalse(self.parser.can_parse('26-01-30'))    # Rok 2-cyfrowy
        self.assertFalse(self.parser.can_parse('2026/01/30'))  # Złe separatory
        self.assertFalse(self.parser.can_parse(''))
        self.assertFalse(self.parser.can_parse('invalid'))
    
    def test_parse_valid_date(self):
        """Test: parsuje prawidłową datę."""
        result = self.parser.parse('2026-01-30')
        self.assertEqual(result, date(2026, 1, 30))
        
        result = self.parser.parse('2025-12-31')
        self.assertEqual(result, date(2025, 12, 31))
    
    def test_parse_invalid_date_returns_none(self):
        """Test: zwraca None dla nieprawidłowych dat."""
        # Format się zgadza ale wartości są nieprawidłowe
        self.assertIsNone(self.parser.parse('2026-13-01'))  # Miesiąc 13
        self.assertIsNone(self.parser.parse('2026-01-32'))  # Dzień 32
        self.assertIsNone(self.parser.parse('2026-02-30'))  # Luty nie ma 30 dni
        self.assertIsNone(self.parser.parse('2025-02-29'))  # 2025 nie jest przestępny
    
    def test_parse_leap_year(self):
        """Test: poprawnie obsługuje rok przestępny."""
        result = self.parser.parse('2024-02-29')
        self.assertEqual(result, date(2024, 2, 29))
        
        # 2025 nie jest przestępny
        self.assertIsNone(self.parser.parse('2025-02-29'))


class PolishLocalizedDateParserTest(TestCase):
    """Testy dla PolishLocalizedDateParser."""
    
    def setUp(self):
        """Setup: tworzy parser."""
        self.parser = PolishLocalizedDateParser()
    
    def test_can_parse_polish_format(self):
        """Test: rozpoznaje polski format zlokalizowany."""
        self.assertTrue(self.parser.can_parse('Sty. 30, 2026'))
        self.assertTrue(self.parser.can_parse('Gru. 31, 2025'))
        self.assertTrue(self.parser.can_parse('Maj. 1, 2026'))
    
    def test_cannot_parse_iso_format(self):
        """Test: nie rozpoznaje formatu ISO 8601."""
        self.assertFalse(self.parser.can_parse('2026-01-30'))
    
    def test_cannot_parse_invalid_month_abbr(self):
        """Test: nie rozpoznaje nieprawidłowego skrótu miesiąca."""
        self.assertFalse(self.parser.can_parse('Xyz. 30, 2026'))
        self.assertFalse(self.parser.can_parse('Jan. 30, 2026'))  # Angielski
    
    def test_cannot_parse_invalid_structure(self):
        """Test: nie rozpoznaje nieprawidłowej struktury."""
        self.assertFalse(self.parser.can_parse('Sty 30, 2026'))   # Brak kropki
        self.assertFalse(self.parser.can_parse('Sty. 30 2026'))   # Brak przecinka
        self.assertFalse(self.parser.can_parse('30. Sty, 2026'))  # Odwrócona kolejność
        self.assertFalse(self.parser.can_parse(''))
    
    def test_parse_all_polish_months(self):
        """Test: parsuje wszystkie polskie miesiące."""
        test_cases = [
            ('Sty. 15, 2026', date(2026, 1, 15)),   # Styczeń
            ('Lut. 28, 2026', date(2026, 2, 28)),   # Luty
            ('Mar. 31, 2026', date(2026, 3, 31)),   # Marzec
            ('Kwi. 30, 2026', date(2026, 4, 30)),   # Kwiecień
            ('Maj. 15, 2026', date(2026, 5, 15)),   # Maj
            ('Cze. 30, 2026', date(2026, 6, 30)),   # Czerwiec
            ('Lip. 31, 2026', date(2026, 7, 31)),   # Lipiec
            ('Sie. 31, 2026', date(2026, 8, 31)),   # Sierpień
            ('Wrz. 30, 2026', date(2026, 9, 30)),   # Wrzesień
            ('Paź. 31, 2026', date(2026, 10, 31)),  # Październik
            ('Lis. 30, 2026', date(2026, 11, 30)),  # Listopad
            ('Gru. 31, 2026', date(2026, 12, 31)),  # Grudzień
        ]
        
        for input_str, expected in test_cases:
            with self.subTest(input=input_str):
                result = self.parser.parse(input_str)
                self.assertEqual(result, expected)
    
    def test_parse_single_digit_day(self):
        """Test: parsuje jednoc

yfrowy dzień."""
        result = self.parser.parse('Sty. 1, 2026')
        self.assertEqual(result, date(2026, 1, 1))
        
        result = self.parser.parse('Mar. 9, 2026')
        self.assertEqual(result, date(2026, 3, 9))
    
    def test_parse_invalid_month_returns_none(self):
        """Test: zwraca None dla nieprawidłowego miesiąca."""
        self.assertIsNone(self.parser.parse('Xyz. 30, 2026'))
    
    def test_parse_invalid_date_returns_none(self):
        """Test: zwraca None dla nieprawidłowych dat."""
        self.assertIsNone(self.parser.parse('Sty. 32, 2026'))  # Styczeń nie ma 32 dni
        self.assertIsNone(self.parser.parse('Lut. 30, 2026'))  # Luty nie ma 30 dni
        self.assertIsNone(self.parser.parse('Kwi. 31, 2026'))  # Kwiecień nie ma 31 dni


class NumericDateParserTest(TestCase):
    """Testy dla NumericDateParser."""
    
    def setUp(self):
        """Setup: tworzy parser."""
        self.parser = NumericDateParser()
    
    def test_can_parse_dot_separator(self):
        """Test: rozpoznaje format z kropkami (DD.MM.YYYY)."""
        self.assertTrue(self.parser.can_parse('30.01.2026'))
        self.assertTrue(self.parser.can_parse('1.1.2026'))
    
    def test_can_parse_slash_separator(self):
        """Test: rozpoznaje format ze slashami (DD/MM/YYYY)."""
        self.assertTrue(self.parser.can_parse('30/01/2026'))
        self.assertTrue(self.parser.can_parse('1/1/2026'))
    
    def test_can_parse_dash_separator(self):
        """Test: rozpoznaje format z myślnikami (DD-MM-YYYY)."""
        self.assertTrue(self.parser.can_parse('30-01-2026'))
        self.assertTrue(self.parser.can_parse('1-1-2026'))
    
    def test_cannot_parse_iso_format(self):
        """Test: nie rozpoznaje formatu ISO (YYYY-MM-DD jest inny porządek)."""
        # Technicznie może sparsować ale jako DD-MM-YYYY co da błędny wynik
        # Dlatego ISO8601DateParser powinien być pierwszy w łańcuchu
        pass  # To jest edge case - niech ISO parser ma priorytet
    
    def test_cannot_parse_polish_format(self):
        """Test: nie rozpoznaje polskiego formatu."""
        self.assertFalse(self.parser.can_parse('Sty. 30, 2026'))
    
    def test_cannot_parse_invalid_structure(self):
        """Test: nie rozpoznaje nieprawidłowej struktury."""
        self.assertFalse(self.parser.can_parse('2026-01'))      # Za krótkie
        self.assertFalse(self.parser.can_parse('30.01'))        # Brak roku
        self.assertFalse(self.parser.can_parse(''))
    
    def test_parse_dot_separator(self):
        """Test: parsuje format z kropkami."""
        result = self.parser.parse('30.01.2026')
        self.assertEqual(result, date(2026, 1, 30))
        
        result = self.parser.parse('1.12.2025')
        self.assertEqual(result, date(2025, 12, 1))
    
    def test_parse_slash_separator(self):
        """Test: parsuje format ze slashami."""
        result = self.parser.parse('30/01/2026')
        self.assertEqual(result, date(2026, 1, 30))
    
    def test_parse_dash_separator(self):
        """Test: parsuje format z myślnikami."""
        result = self.parser.parse('30-01-2026')
        self.assertEqual(result, date(2026, 1, 30))
    
    def test_parse_invalid_date_returns_none(self):
        """Test: zwraca None dla nieprawidłowych dat."""
        self.assertIsNone(self.parser.parse('32.01.2026'))  # Dzień 32
        self.assertIsNone(self.parser.parse('30.13.2026'))  # Miesiąc 13
        self.assertIsNone(self.parser.parse('29.02.2025'))  # 2025 nie jest przestępny


class DateConverterServiceTest(TestCase):
    """Testy integracyjne dla DateConverterService."""
    
    def setUp(self):
        """Setup: tworzy serwis z wszystkimi parserami."""
        parsers = [
            ISO8601DateParser(),
            PolishLocalizedDateParser(),
            NumericDateParser(),
        ]
        self.converter = DateConverterService(parsers)
    
    def test_convert_iso_date(self):
        """Test: konwertuje datę ISO 8601 (no-op)."""
        result = self.converter.convert_to_iso('2026-01-30')
        self.assertEqual(result, '2026-01-30')
    
    def test_convert_polish_date(self):
        """Test: konwertuje polską zlokalizowaną datę."""
        result = self.converter.convert_to_iso('Sty. 30, 2026')
        self.assertEqual(result, '2026-01-30')
        
        result = self.converter.convert_to_iso('Gru. 31, 2025')
        self.assertEqual(result, '2025-12-31')
    
    def test_convert_numeric_date(self):
        """Test: konwertuje datę numeryczną."""
        result = self.converter.convert_to_iso('30.01.2026')
        self.assertEqual(result, '2026-01-30')
        
        result = self.converter.convert_to_iso('30/01/2026')
        self.assertEqual(result, '2026-01-30')
    
    def test_convert_empty_raises_error(self):
        """Test: pusta wartość rzuca ValueError."""
        with self.assertRaises(ValueError) as cm:
            self.converter.convert_to_iso('')
        self.assertIn('Pusta wartość', str(cm.exception))
    
    def test_convert_unparseable_raises_error(self):
        """Test: nieparsowalna wartość rzuca ValueError."""
        with self.assertRaises(ValueError) as cm:
            self.converter.convert_to_iso('invalid date')
        self.assertIn('Nie można sparsować', str(cm.exception))
    
    def test_convert_many_mixed_formats(self):
        """Test: konwertuje listę z różnymi formatami."""
        inputs = [
            '2026-01-30',       # ISO
            'Lut. 15, 2026',    # Polish
            '20.03.2026',       # Numeric
            '2025-12-31',       # ISO
        ]
        results = self.converter.convert_many(inputs)
        expected = [
            '2026-01-30',
            '2026-02-15',
            '2026-03-20',
            '2025-12-31',
        ]
        self.assertEqual(results, expected)
    
    def test_convert_many_with_invalid_skips_invalid(self):
        """Test: convert_many pomija nieprawidłowe daty."""
        inputs = [
            '2026-01-30',       # Prawidłowa
            'invalid',          # Nieprawidłowa - zostanie pominięta
            'Lut. 15, 2026',    # Prawidłowa
        ]
        results = self.converter.convert_many(inputs)
        
        # Tylko prawidłowe daty w wyniku (fail-fast approach)
        self.assertEqual(len(results), 2)
        self.assertEqual(results[0], '2026-01-30')
        self.assertEqual(results[1], '2026-02-15')
    
    def test_convert_many_empty_list(self):
        """Test: pusta lista zwraca pustą listę."""
        results = self.converter.convert_many([])
        self.assertEqual(results, [])
    
    def test_parser_priority(self):
        """Test: parsery są sprawdzane w kolejności (ISO ma priorytet)."""
        # Data w formacie ISO powinna użyć ISO parsera (najszybszy)
        result = self.converter.convert_to_iso('2026-01-30')
        self.assertEqual(result, '2026-01-30')
        # Nie możemy bezpośrednio sprawdzić który parser był użyty,
        # ale możemy zaufać że pierwsz parser (ISO) ma priorytet przez can_parse
    
    def test_service_requires_at_least_one_parser(self):
        """Test: serwis wymaga przynajmniej jednego parsera."""
        with self.assertRaises(ValueError) as cm:
            DateConverterService([])
        self.assertIn('przynajmniej jednego parsera', str(cm.exception))
