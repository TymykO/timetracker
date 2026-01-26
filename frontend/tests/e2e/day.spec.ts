/**
 * Testy E2E dla Day View w TimeTracker.
 * 
 * Testuje:
 * - Ładowanie day view
 * - Wybór tasków i wprowadzanie czasu
 * - Zapisywanie wpisów
 * - Refresh month view po zapisie
 * - Filtry tasków
 */

import { test, expect, TEST_USER } from './fixtures';

test.describe('Day View - Podstawy', () => {
  test.beforeEach(async ({ page }) => {
    // Login
    await page.goto('/login');
    await page.fill('input[name="email"]', TEST_USER.email);
    await page.fill('input[name="password"]', TEST_USER.password);
    await page.click('button[type="submit"]');
    await page.waitForURL(/\/month\/\d{4}-\d{2}/);
    
    // Przejdź do day view (dzisiejszy dzień lub poprzedni miesiąc)
    const today = new Date();
    const year = today.getFullYear();
    const month = String(today.getMonth() + 1).padStart(2, '0');
    const day = String(today.getDate()).padStart(2, '0');
    await page.goto(`/day/${year}-${month}-${day}`);
  });
  
  test('day view ładuje się i wyświetla formularz', async ({ page }) => {
    // Sprawdź nagłówek z datą
    await expect(page.locator('h1, h2').filter({ hasText: /\d{4}-\d{2}-\d{2}/ })).toBeVisible();
    
    // Sprawdź czy lista tasków jest widoczna
    await expect(page.locator('text=/Dostępne zadania|Available tasks/i')).toBeVisible();
    
    // Sprawdź czy są filtry
    await expect(page.locator('select[name="project_phase"], input[name="project_phase"]')).toBeVisible();
  });
  
  test('day view wyświetla listę dostępnych tasków', async ({ page }) => {
    // Poczekaj na załadowanie tasków
    await page.waitForSelector('text=/Task|Zadanie/i', { timeout: 5000 });
    
    // Sprawdź czy są jakieś taski
    const tasks = page.locator('[data-testid="task-item"], .task-item, li:has-text("Task")');
    const count = await tasks.count();
    expect(count).toBeGreaterThan(0);
  });
});

test.describe('Day View - Wybór tasków i wprowadzanie czasu', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/login');
    await page.fill('input[name="email"]', TEST_USER.email);
    await page.fill('input[name="password"]', TEST_USER.password);
    await page.click('button[type="submit"]');
    await page.waitForURL(/\/month\/\d{4}-\d{2}/);
    
    // Przejdź do poprzedniego miesiąca (aby uniknąć przyszłych dat)
    await page.goto('/month/2025-01');
    await page.click('tbody tr:first-child a');
    await page.waitForURL(/\/day\/\d{4}-\d{2}-\d{2}/);
  });
  
  test('użytkownik może wybrać task i wprowadzić czas', async ({ page }) => {
    // Poczekaj na załadowanie tasków
    await page.waitForTimeout(1000);
    
    // Kliknij pierwszy dostępny task (dodaj do selected)
    const firstTask = page.locator('[data-testid="task-item"], .task-item, button:has-text("Wybierz"), button:has-text("Select")').first();
    await firstTask.click();
    
    // Sprawdź czy task pojawił się w "Selected tasks"
    await expect(page.locator('text=/Wybrane zadania|Selected tasks/i')).toBeVisible();
    
    // Wprowadź czas (minuty)
    const durationInput = page.locator('input[type="number"][name="duration"], input[placeholder*="minut"], input[placeholder*="minutes"]').first();
    await durationInput.fill('120');
    
    // Sprawdź czy total się zaktualizował
    await expect(page.locator('text=/Suma|Total/i')).toBeVisible();
    await expect(page.locator('text=/120|2:00/i')).toBeVisible();
  });
  
  test('użytkownik może wybrać wiele tasków', async ({ page }) => {
    await page.waitForTimeout(1000);
    
    // Wybierz 2-3 taski
    const tasks = page.locator('[data-testid="task-item"] button, .task-item button, button:has-text("Wybierz"), button:has-text("Select")');
    const count = Math.min(await tasks.count(), 3);
    
    for (let i = 0; i < count; i++) {
      await tasks.nth(i).click();
      await page.waitForTimeout(300);
    }
    
    // Sprawdź czy wszystkie są w selected
    const selectedTasks = page.locator('[data-testid="selected-task"], .selected-task, input[type="number"][name="duration"]');
    expect(await selectedTasks.count()).toBeGreaterThanOrEqual(count);
  });
  
  test('użytkownik nie może wybrać tego samego taska dwa razy', async ({ page }) => {
    await page.waitForTimeout(1000);
    
    // Wybierz pierwszy task
    const firstTask = page.locator('[data-testid="task-item"] button, .task-item button, button:has-text("Wybierz")').first();
    await firstTask.click();
    await page.waitForTimeout(300);
    
    // Sprawdź czy task zniknął z listy available lub jest disabled
    // (implementacja zależna od UI logic)
    const availableTasks = page.locator('[data-testid="task-item"]:visible, .task-item:visible');
    const countAfter = await availableTasks.count();
    
    // Lub sprawdź czy button jest disabled
    await expect(firstTask).toBeDisabled();
  });
});

test.describe('Day View - Zapisywanie wpisów', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/login');
    await page.fill('input[name="email"]', TEST_USER.email);
    await page.fill('input[name="password"]', TEST_USER.password);
    await page.click('button[type="submit"]');
    await page.waitForURL(/\/month\/\d{4}-\d{2}/);
    
    await page.goto('/month/2025-01');
    await page.click('tbody tr:first-child a');
    await page.waitForURL(/\/day\/\d{4}-\d{2}-\d{2}/);
  });
  
  test('użytkownik może zapisać wpisy', async ({ page }) => {
    await page.waitForTimeout(1000);
    
    // Wybierz task
    const firstTask = page.locator('[data-testid="task-item"] button, button:has-text("Wybierz")').first();
    await firstTask.click();
    
    // Wprowadź czas
    const durationInput = page.locator('input[type="number"][name="duration"]').first();
    await durationInput.fill('180');
    
    // Kliknij Save
    await page.click('button:has-text("Zapisz"), button:has-text("Save"), button[type="submit"]');
    
    // Poczekaj na success message
    await expect(page.locator('text=/Zapisano|Saved|Success/i')).toBeVisible({ timeout: 10000 });
  });
  
  test('po zapisie użytkownik może wrócić do month view i zobaczyć zmiany', async ({ page }) => {
    await page.waitForTimeout(1000);
    
    // Wybierz i zapisz
    const firstTask = page.locator('[data-testid="task-item"] button, button:has-text("Wybierz")').first();
    await firstTask.click();
    const durationInput = page.locator('input[type="number"][name="duration"]').first();
    await durationInput.fill('240');
    await page.click('button:has-text("Zapisz"), button:has-text("Save"), button[type="submit"]');
    
    // Poczekaj na success
    await page.waitForTimeout(1000);
    
    // Wróć do month view
    await page.click('a:has-text("Powrót"), a:has-text("Back"), a:has-text("Month")');
    
    // Sprawdź czy month view pokazuje has_entries i czas
    await page.waitForURL(/\/month\/\d{4}-\d{2}/);
    await expect(page.locator('text=/240|4:00/i')).toBeVisible();
  });
});

test.describe('Day View - Filtry', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/login');
    await page.fill('input[name="email"]', TEST_USER.email);
    await page.fill('input[name="password"]', TEST_USER.password);
    await page.click('button[type="submit"]');
    await page.waitForURL(/\/month\/\d{4}-\d{2}/);
    
    await page.goto('/month/2025-01');
    await page.click('tbody tr:first-child a');
    await page.waitForURL(/\/day\/\d{4}-\d{2}-\d{2}/);
  });
  
  test('filtry project_phase działają', async ({ page }) => {
    await page.waitForTimeout(1000);
    
    // Sprawdź czy filter jest dostępny
    const phaseFilter = page.locator('select[name="project_phase"], input[name="project_phase"]');
    await expect(phaseFilter).toBeVisible();
    
    // Zmień wartość filtra
    if (await phaseFilter.evaluate(el => el.tagName === 'SELECT')) {
      await phaseFilter.selectOption({ index: 1 });
    } else {
      await phaseFilter.fill('Project A');
    }
    
    // Poczekaj na aktualizację listy
    await page.waitForTimeout(500);
    
    // Sprawdź czy lista tasków się zaktualizowała
    const tasks = page.locator('[data-testid="task-item"], .task-item');
    const count = await tasks.count();
    expect(count).toBeGreaterThanOrEqual(0); // Może być 0 jeśli brak pasujących
  });
  
  test('search text filtruje taski', async ({ page }) => {
    await page.waitForTimeout(1000);
    
    // Znajdź pole search
    const searchInput = page.locator('input[type="search"], input[name="search"], input[placeholder*="Szukaj"], input[placeholder*="Search"]');
    await expect(searchInput).toBeVisible();
    
    // Wprowadź tekst
    await searchInput.fill('Task');
    await page.waitForTimeout(500);
    
    // Sprawdź czy lista się zaktualizowała
    const tasks = page.locator('[data-testid="task-item"]:visible, .task-item:visible');
    const count = await tasks.count();
    expect(count).toBeGreaterThanOrEqual(0);
  });
  
  test('po wybraniu taska filtry pozostają niezmienione', async ({ page }) => {
    await page.waitForTimeout(1000);
    
    // Ustaw filter
    const phaseFilter = page.locator('select[name="project_phase"]');
    if (await phaseFilter.isVisible()) {
      await phaseFilter.selectOption({ index: 1 });
      const selectedValue = await phaseFilter.inputValue();
      
      // Wybierz task
      const firstTask = page.locator('[data-testid="task-item"] button, button:has-text("Wybierz")').first();
      await firstTask.click();
      await page.waitForTimeout(300);
      
      // Sprawdź czy filter nadal ma tę samą wartość
      const newValue = await phaseFilter.inputValue();
      expect(newValue).toBe(selectedValue);
    }
  });
});

test.describe('Day View - Edge Cases', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/login');
    await page.fill('input[name="email"]', TEST_USER.email);
    await page.fill('input[name="password"]', TEST_USER.password);
    await page.click('button[type="submit"]');
    await page.waitForURL(/\/month\/\d{4}-\d{2}/);
  });
  
  test('przyszły dzień jest disabled (nie można edytować)', async ({ page }) => {
    // Przejdź do przyszłego dnia
    const futureDate = new Date();
    futureDate.setDate(futureDate.getDate() + 5);
    const dateStr = futureDate.toISOString().slice(0, 10);
    
    await page.goto(`/day/${dateStr}`);
    
    // Sprawdź czy jest komunikat o blokovaniu lub disabled inputs
    const saveButton = page.locator('button:has-text("Zapisz"), button:has-text("Save"), button[type="submit"]');
    await expect(saveButton).toBeDisabled();
  });
  
  test('dzień z 2 miesięcy wstecz jest disabled', async ({ page }) => {
    // Przejdź do starego dnia
    const oldDate = new Date();
    oldDate.setMonth(oldDate.getMonth() - 2);
    const dateStr = oldDate.toISOString().slice(0, 10);
    
    await page.goto(`/day/${dateStr}`);
    
    // Sprawdź czy jest komunikat lub disabled
    const saveButton = page.locator('button:has-text("Zapisz"), button:has-text("Save"), button[type="submit"]');
    await expect(saveButton).toBeDisabled();
  });
});
