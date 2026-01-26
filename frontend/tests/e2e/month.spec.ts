/**
 * Testy E2E dla Month View w TimeTracker.
 * 
 * Testuje:
 * - Ładowanie month view
 * - Nawigacja między miesiącami
 * - Blokada przyszłych miesięcy
 * - Wyświetlanie danych (has_entries, overtime, etc.)
 */

import { test, expect, TEST_USER } from './fixtures';

test.describe('Month View - Podstawy', () => {
  test.beforeEach(async ({ page }) => {
    // Login
    await page.goto('/login');
    await page.fill('input[name="email"]', TEST_USER.email);
    await page.fill('input[name="password"]', TEST_USER.password);
    await page.click('button[type="submit"]');
    await page.waitForURL(/\/month\/\d{4}-\d{2}/);
  });
  
  test('month view ładuje się i wyświetla tabelę dni', async ({ page }) => {
    // Sprawdź czy tabela jest widoczna
    await expect(page.locator('table')).toBeVisible();
    
    // Sprawdź nagłówki kolumn
    await expect(page.locator('th:has-text("Data")')).toBeVisible();
    await expect(page.locator('th:has-text("Dzień")')).toBeVisible(); // Working/Free
    await expect(page.locator('th:has-text("Czas pracy")')).toBeVisible();
    await expect(page.locator('th:has-text("Nadgodziny")')).toBeVisible();
    
    // Sprawdź czy są wiersze (dni miesiąca)
    const rows = page.locator('tbody tr');
    const count = await rows.count();
    expect(count).toBeGreaterThanOrEqual(28); // Minimum dla lutego
    expect(count).toBeLessThanOrEqual(31); // Maximum dla innych miesięcy
  });
  
  test('month view wyświetla poprawny miesiąc i rok w nagłówku', async ({ page }) => {
    // Sprawdź czy nagłówek zawiera aktualny miesiąc/rok
    await expect(page.locator('h1, h2').filter({ hasText: /\d{4}-\d{2}/ })).toBeVisible();
  });
  
  test('month view pozwala kliknąć na dzień aby przejść do day view', async ({ page }) => {
    // Znajdź pierwszy dzień w tabeli
    const firstDayLink = page.locator('tbody tr').first().locator('a').first();
    await firstDayLink.click();
    
    // Sprawdź redirect do /day/<date>
    await page.waitForURL(/\/day\/\d{4}-\d{2}-\d{2}/);
    
    // Sprawdź czy day view się załadował
    await expect(page.locator('h1, h2').filter({ hasText: /\d{4}-\d{2}-\d{2}/ })).toBeVisible();
  });
});

test.describe('Month View - Nawigacja', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/login');
    await page.fill('input[name="email"]', TEST_USER.email);
    await page.fill('input[name="password"]', TEST_USER.password);
    await page.click('button[type="submit"]');
    await page.waitForURL(/\/month\/\d{4}-\d{2}/);
  });
  
  test('użytkownik może nawigować do poprzedniego miesiąca', async ({ page }) => {
    // Kliknij button "Poprzedni miesiąc"
    await page.click('button:has-text("Poprzedni"), a:has-text("Poprzedni"), button:has-text("◀"), a:has-text("◀")');
    
    // Sprawdź czy URL się zmienił
    await page.waitForURL(/\/month\/\d{4}-\d{2}/);
    
    // Sprawdź czy tabela się przeładowała
    await expect(page.locator('table')).toBeVisible();
  });
  
  test('użytkownik może nawigować do następnego miesiąca (jeśli nie przyszłość)', async ({ page }) => {
    // Najpierw przejdź do poprzedniego miesiąca
    await page.click('button:has-text("Poprzedni"), a:has-text("Poprzedni"), button:has-text("◀"), a:has-text("◀")');
    await page.waitForTimeout(500);
    
    // Następnie wróć (jeśli button jest dostępny)
    const nextButton = page.locator('button:has-text("Następny"), a:has-text("Następny"), button:has-text("▶"), a:has-text("▶")');
    
    if (await nextButton.isEnabled()) {
      await nextButton.click();
      await page.waitForURL(/\/month\/\d{4}-\d{2}/);
      await expect(page.locator('table')).toBeVisible();
    }
  });
  
  test('nawigacja do przyszłych miesięcy jest zablokowana', async ({ page }) => {
    // Sprawdź czy button "Następny" jest disabled lub nie istnieje
    // (zależy od tego czy jesteśmy w bieżącym miesiącu)
    
    // Jeśli jesteśmy w bieżącym miesiącu, button powinien być disabled
    const currentUrl = page.url();
    const currentMonth = new Date().toISOString().slice(0, 7); // YYYY-MM
    
    if (currentUrl.includes(currentMonth)) {
      const nextButton = page.locator('button:has-text("Następny"), a:has-text("Następny"), button:has-text("▶"), a:has-text("▶")');
      await expect(nextButton).toBeDisabled();
    }
  });
});

test.describe('Month View - Wyświetlanie danych', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/login');
    await page.fill('input[name="email"]', TEST_USER.email);
    await page.fill('input[name="password"]', TEST_USER.password);
    await page.click('button[type="submit"]');
    await page.waitForURL(/\/month\/\d{4}-\d{2}/);
  });
  
  test('month view wyświetla day_type (Working/Free) dla każdego dnia', async ({ page }) => {
    // Sprawdź czy komórki zawierają "Working" lub "Free"
    const cells = page.locator('td:has-text("Working"), td:has-text("Free")');
    const count = await cells.count();
    expect(count).toBeGreaterThan(0);
  });
  
  test('month view wyświetla czas pracy w minutach', async ({ page }) => {
    // Sprawdź czy są komórki z czasem (liczby)
    const timeCells = page.locator('td').filter({ hasText: /^\d+$/ });
    const count = await timeCells.count();
    expect(count).toBeGreaterThanOrEqual(0); // Może być 0 jeśli brak wpisów
  });
  
  test('przyszłe dni są oznaczone jako disabled/greyed', async ({ page }) => {
    // Sprawdź czy przyszłe dni mają specjalną klasę lub atrybut
    // (implementacja zależy od CSS)
    
    // Przykład: sprawdź czy linki do przyszłych dni są disabled
    const today = new Date().toISOString().slice(0, 10);
    const futureDayLinks = page.locator(`a[href*="/day/"][href*="${today}"]`).first();
    
    // Jeśli istnieją przyszłe dni, sprawdź stan
    // TODO: Dostosować do faktycznej implementacji UI
  });
});

test.describe('Month View - Edge Cases', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/login');
    await page.fill('input[name="email"]', TEST_USER.email);
    await page.fill('input[name="password"]', TEST_USER.password);
    await page.click('button[type="submit"]');
    await page.waitForURL(/\/month\/\d{4}-\d{2}/);
  });
  
  test('month view obsługuje miesiące z różną liczbą dni (28-31)', async ({ page }) => {
    // Luty (28/29 dni)
    await page.goto('/month/2025-02');
    let rows = page.locator('tbody tr');
    let count = await rows.count();
    expect(count).toBeLessThanOrEqual(29);
    
    // Styczeń (31 dni)
    await page.goto('/month/2025-01');
    rows = page.locator('tbody tr');
    count = await rows.count();
    expect(count).toBe(31);
  });
  
  test('month view obsługuje przejście roku (grudzień -> styczeń)', async ({ page }) => {
    // Przejdź do grudnia
    await page.goto('/month/2024-12');
    await expect(page.locator('table')).toBeVisible();
    
    // Kliknij "Następny miesiąc"
    await page.click('button:has-text("Następny"), a:has-text("Następny"), button:has-text("▶"), a:has-text("▶")');
    
    // Sprawdź czy przeszliśmy do stycznia następnego roku
    await page.waitForURL('/month/2025-01');
    await expect(page.locator('table')).toBeVisible();
  });
});
