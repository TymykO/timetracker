"""
Serwis konwersji dat używający Chain of Responsibility pattern.

DateConverterService przyjmuje listę parserów i próbuje ich po kolei
dopóki jeden z nich nie sparsuje wartości pomyślnie.

Wykorzystanie:
    from timetracker_app.utils.date_parsers import (
        ISO8601DateParser,
        PolishLocalizedDateParser,
    )
    
    parsers = [ISO8601DateParser(), PolishLocalizedDateParser()]
    converter = DateConverterService(parsers)
    
    iso_date = converter.convert_to_iso("Sty. 30, 2026")  # "2026-01-30"
"""

from typing import List
import logging

from timetracker_app.utils.date_parsers import DateParser

logger = logging.getLogger(__name__)


class DateConverterService:
    """
    Serwis odpowiedzialny za konwersję dat z różnych formatów na ISO 8601.
    
    Używa Chain of Responsibility pattern - próbuje parsery po kolei
    w kolejności przekazanej w konstruktorze, aż do pierwszego sukcesu.
    
    Attributes:
        parsers: Lista parserów dat w kolejności priorytetu
    """
    
    def __init__(self, parsers: List[DateParser]):
        """
        Inicjalizuje serwis z listą parserów.
        
        Args:
            parsers: Lista parserów dat (w kolejności priorytetu).
                     Zalecana kolejność:
                     1. ISO8601DateParser (najszybszy)
                     2. PolishLocalizedDateParser (specyficzny dla lokalizacji)
                     3. NumericDateParser (fallback)
        """
        if not parsers:
            raise ValueError("DateConverterService wymaga przynajmniej jednego parsera")
        
        self.parsers = parsers
    
    def convert_to_iso(self, value: str) -> str:
        """
        Konwertuj wartość na format ISO 8601 (YYYY-MM-DD).
        
        Próbuje każdy parser po kolei używając can_parse() i parse().
        Pierwszy parser który pomyślnie sparsuje wartość wygrywa.
        
        Args:
            value: String z datą w dowolnym obsługiwanym formacie
            
        Returns:
            Data w formacie YYYY-MM-DD
            
        Raises:
            ValueError: Jeśli wartość jest pusta lub żaden parser nie rozpoznał formatu
        """
        if not value:
            raise ValueError("Pusta wartość daty")
        
        for parser in self.parsers:
            if parser.can_parse(value):
                parsed = parser.parse(value)
                if parsed:
                    result = parsed.strftime('%Y-%m-%d')
                    logger.debug(
                        f"Sparsowano '{value}' używając {parser.__class__.__name__} -> {result}"
                    )
                    return result
                else:
                    # Parser rozpoznał format ale parsowanie się nie powiodło
                    # (np. nieprawidłowa data: "Sty. 32, 2026")
                    logger.warning(
                        f"{parser.__class__.__name__} rozpoznał format '{value}' "
                        f"ale parsowanie się nie powiodło (nieprawidłowa data)"
                    )
        
        # Żaden parser nie rozpoznał formatu lub parsowanie się nie powiodło
        logger.error(f"Nie udało się sparsować daty: '{value}'")
        raise ValueError(f"Nie można sparsować daty: {value}")
    
    def convert_many(self, values: List[str]) -> List[str]:
        """
        Konwertuj listę wartości na format ISO 8601.
        
        Wartości które nie mogą być sparsowane są logowane jako błędy
        i POMIJANE (nie są dodawane do wyniku).
        
        To jest fail-fast approach - jeśli nie możemy być pewni że data
        jest poprawna, lepiej ją pominąć niż przepuścić złe dane.
        
        Args:
            values: Lista stringów z datami
            
        Returns:
            Lista dat w formacie YYYY-MM-DD (tylko pomyślnie sparsowane)
            
        Note:
            Jeśli chcesz aby nieparsowalne daty rzucały wyjątek,
            użyj convert_to_iso() w pętli zamiast tej metody.
        """
        results = []
        
        for value in values:
            try:
                converted = self.convert_to_iso(value)
                results.append(converted)
            except ValueError as e:
                # Loguj błąd ale kontynuuj - pozwól na pomyślne sparsowanie
                # reszty dat nawet jeśli jedna jest błędna
                logger.error(
                    f"Pomijam nieparsowaną datę '{value}': {e}",
                    exc_info=False  # Nie loguj stack trace dla oczekiwanych błędów
                )
                # NIE dodajemy value do results - fail-fast approach
        
        return results
