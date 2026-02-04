"""
Parsery dat implementujące Strategy Pattern.

Każdy parser implementuje interfejs DateParser i jest odpowiedzialny
za parsowanie jednego konkretnego formatu daty.

Wykorzystanie:
    parser = PolishLocalizedDateParser()
    if parser.can_parse("Sty. 30, 2026"):
        date_obj = parser.parse("Sty. 30, 2026")  # date(2026, 1, 30)
"""

from abc import ABC, abstractmethod
from datetime import date, datetime
from typing import Optional
import re


class DateParser(ABC):
    """
    Abstrakcyjna klasa bazowa dla parserów dat (Strategy Pattern).
    
    Każdy parser musi implementować dwie metody:
    - can_parse: sprawdza czy parser może sparsować daną wartość
    - parse: parsuje wartość i zwraca obiekt date lub None
    """
    
    @abstractmethod
    def can_parse(self, value: str) -> bool:
        """
        Sprawdź czy parser może sparsować tę wartość.
        
        Args:
            value: String z datą do sprawdzenia
            
        Returns:
            True jeśli parser rozpoznaje ten format, False w przeciwnym razie
        """
        pass
    
    @abstractmethod
    def parse(self, value: str) -> Optional[date]:
        """
        Sparsuj wartość na obiekt date.
        
        Args:
            value: String z datą w formacie obsługiwanym przez parser
            
        Returns:
            Obiekt date lub None jeśli parsowanie się nie powiodło
        """
        pass


class ISO8601DateParser(DateParser):
    """
    Parser dla formatu ISO 8601 (YYYY-MM-DD).
    
    To jest najszybszy parser i powinien być sprawdzany jako pierwszy.
    Obsługuje tylko ścisły format: rok(4 cyfry)-miesiąc(2 cyfry)-dzień(2 cyfry).
    """
    
    def can_parse(self, value: str) -> bool:
        """
        Sprawdza czy wartość jest w formacie YYYY-MM-DD.
        
        Używa prostej heurystyki (długość i pozycje myślników) zamiast regex
        dla maksymalnej wydajności.
        """
        return (
            value and 
            len(value) == 10 and 
            value[4] == '-' and 
            value[7] == '-' and
            value[:4].isdigit() and
            value[5:7].isdigit() and
            value[8:10].isdigit()
        )
    
    def parse(self, value: str) -> Optional[date]:
        """
        Parsuje datę w formacie YYYY-MM-DD.
        
        Returns:
            date object lub None jeśli format jest nieprawidłowy
            (np. 2026-13-40 przejdzie can_parse ale nie parse)
        """
        try:
            return datetime.strptime(value, '%Y-%m-%d').date()
        except ValueError:
            return None


class PolishLocalizedDateParser(DateParser):
    """
    Parser dla polskiego formatu zlokalizowanego (np. "Sty. 30, 2026").
    
    Django z LANGUAGE_CODE='pl-pl' renderuje daty w tym formacie.
    Parser obsługuje tylko skróty miesięcy (nie pełne nazwy).
    
    Format: [Skrót_miesiąca]. [dzień], [rok]
    Przykłady: "Sty. 30, 2026", "Gru. 1, 2025"
    """
    
    # Mapowanie polskich skrótów miesięcy na numery
    MONTH_MAPPING = {
        'Sty': 1,   # Styczeń
        'Lut': 2,   # Luty
        'Mar': 3,   # Marzec
        'Kwi': 4,   # Kwiecień
        'Maj': 5,   # Maj
        'Cze': 6,   # Czerwiec
        'Lip': 7,   # Lipiec
        'Sie': 8,   # Sierpień
        'Wrz': 9,   # Wrzesień
        'Paź': 10,  # Październik
        'Lis': 11,  # Listopad
        'Gru': 12,  # Grudzień
    }
    
    # Pattern: [słowo]. [1-2 cyfry], [4 cyfry]
    PATTERN = re.compile(r'^(\w+)\.\s+(\d{1,2}),\s+(\d{4})$')
    
    def can_parse(self, value: str) -> bool:
        """
        Sprawdza czy wartość pasuje do polskiego formatu zlokalizowanego.
        
        Zwraca True tylko jeśli skrót miesiąca jest rozpoznawalny.
        """
        if not value:
            return False
        
        match = self.PATTERN.match(value)
        if not match:
            return False
        
        month_abbr = match.group(1)
        return month_abbr in self.MONTH_MAPPING
    
    def parse(self, value: str) -> Optional[date]:
        """
        Parsuje polską zlokalizowaną datę.
        
        Returns:
            date object lub None jeśli nie udało się sparsować
            (np. nieprawidłowy dzień/miesiąc: "Sty. 32, 2026")
        """
        match = self.PATTERN.match(value)
        if not match:
            return None
        
        month_abbr, day_str, year_str = match.groups()
        month = self.MONTH_MAPPING.get(month_abbr)
        
        if month is None:
            return None
        
        try:
            return date(int(year_str), month, int(day_str))
        except ValueError:
            # Nieprawidłowa data (np. 32 stycznia)
            return None


class NumericDateParser(DateParser):
    """
    Parser dla numerycznych formatów dat z różnymi separatorami.
    
    Obsługuje formaty:
    - DD.MM.YYYY (polski format)
    - DD/MM/YYYY (międzynarodowy)
    - DD-MM-YYYY (alternatywny)
    
    Format: dzień i rok mogą być 1-4 cyframi, miesiąc 1-2 cyframi.
    """
    
    # Formaty w kolejności popularności (DD.MM.YYYY najczęstszy w Polsce)
    FORMATS = [
        '%d.%m.%Y',
        '%d/%m/%Y',
        '%d-%m-%Y',
    ]
    
    # Pattern sprawdzający czy wartość wygląda jak data numeryczna
    NUMERIC_PATTERN = re.compile(r'^\d{1,2}[./-]\d{1,2}[./-]\d{4}$')
    
    def can_parse(self, value: str) -> bool:
        """
        Sprawdza czy wartość wygląda jak data numeryczna.
        
        Używa prostego regex do szybkiego sprawdzenia struktury.
        """
        if not value:
            return False
        return bool(self.NUMERIC_PATTERN.match(value))
    
    def parse(self, value: str) -> Optional[date]:
        """
        Parsuje datę numeryczną próbując różnych separatorów.
        
        Próbuje każdy format po kolei aż do pierwszego sukcesu.
        
        Returns:
            date object lub None jeśli żaden format nie zadziałał
        """
        for fmt in self.FORMATS:
            try:
                return datetime.strptime(value, fmt).date()
            except ValueError:
                continue
        
        return None
