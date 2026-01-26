/**
 * Testy E2E dla walidacji w TimeTracker.
 * 
 * Testuje:
 * - Walidacje duration (>0, <=1440)
 * - Walidacje przyszłych dat
 * - Walidacje duplikatów tasków
 * - Walidacje okna edycji
 */

import { test, expect, TEST_USER } from './fixtures';

test.describe('Validations - Duration', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/login');
    await page.fill('input[name="email"]', TEST_USER.email);
    await page.fill('input[name="password"]', TEST_USER.password);
    await page.click('button[type="submit"]');
    await page.waitForURL(/\/month\/\d{4}-\d{2}/);
    
    // Przejdź do edytowalnego dnia (poprzedni miesiąc)
    await page.goto('/month/2025-01');
    await page.click('tbody tr:first-child a');
    await page.waitForURL(/\/day\/\d{4}-\d{2}-\d{2}/);
  });
  
  test('duration = 0 jest odrzucane', async ({ page }) => {
    await page.waitForTimeout(1000);
    
    // Wybierz task
    const firstTask = page.locator('[data-testid="task-item"] button, button:has-text("Wybierz")').first();
    await firstTask.click();
    
    // Próba wprowadzenia duration = 0
    const durationInput = page.locator('input[type="number"][name="duration"]').first();
    await durationInput.fill('0');
    
    // Kliknij Save
    await page.click('button:has-text("Zapisz"), button:has-text("Save"), button[type="submit"]');
    
    // Sprawdź error message
    await expect(page.locator('text=/Duration must be|Czas musi być|greater than 0/i')).toBeVisible({ timeout: 5000 });
  });
  
  test('duration < 0 jest odrzucane', async ({ page }) => {
    await page.waitForTimeout(1000);
    
    const firstTask = page.locator('[data-testid="task-item"] button, button:has-text("Wybierz")').first();
    await firstTask.click();
    
    const durationInput = page.locator('input[type="number"][name="duration"]').first();
    await durationInput.fill('-10');
    
    await page.click('button:has-text("Zapisz"), button:has-text("Save"), button[type="submit"]');
    
    await expect(page.locator('text=/Duration must be|Czas musi być|positive/i')).toBeVisible({ timeout: 5000 });
  });
  
  test('suma > 1440 minut (24h) jest odrzucana', async ({ page }) => {
    await page.waitForTimeout(1000);
    
    // Wybierz 2 taski
    const tasks = page.locator('[data-testid="task-item"] button, button:has-text("Wybierz")');
    await tasks.nth(0).click();
    await page.waitForTimeout(300);
    await tasks.nth(1).click();
    
    // Wprowadź czasy > 1440 łącznie
    const inputs = page.locator('input[type="number"][name="duration"]');
    await inputs.nth(0).fill('800');
    await inputs.nth(1).fill('700'); // Suma = 1500
    
    // Kliknij Save
    await page.click('button:has-text("Zapisz"), button:has-text("Save"), button[type="submit"]');
    
    // Sprawdź error
    await expect(page.locator('text=/Total exceeds|Suma przekracza|1440|24h/i')).toBeVisible({ timeout: 5000 });
  });
  
  test('suma = 1440 minut jest akceptowana', async ({ page }) => {
    await page.waitForTimeout(1000);
    
    // Wybierz task
    const firstTask = page.locator('[data-testid="task-item"] button, button:has-text("Wybierz")').first();
    await firstTask.click();
    
    // Wprowadź dokładnie 1440
    const durationInput = page.locator('input[type="number"][name="duration"]').first();
    await durationInput.fill('1440');
    
    // Save
    await page.click('button:has-text("Zapisz"), button:has-text("Save"), button[type="submit"]');
    
    // Success (brak error)
    await expect(page.locator('text=/Zapisano|Saved|Success/i')).toBeVisible({ timeout: 10000 });
  });
});

test.describe('Validations - Przyszłe daty', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/login');
    await page.fill('input[name="email"]', TEST_USER.email);
    await page.fill('input[name="password"]', TEST_USER.password);
    await page.click('button[type="submit"]');
    await page.waitForURL(/\/month\/\d{4}-\d{2}/);
  });
  
  test('nie można edytować przyszłego dnia', async ({ page }) => {
    // Przejdź do przyszłego dnia
    const futureDate = new Date();
    futureDate.setDate(futureDate.getDate() + 3);
    const dateStr = futureDate.toISOString().slice(0, 10);
    
    await page.goto(`/day/${dateStr}`);
    
    // Sprawdź czy save button jest disabled
    const saveButton = page.locator('button:has-text("Zapisz"), button:has-text("Save"), button[type="submit"]');
    await expect(saveButton).toBeDisabled();
    
    // Lub sprawdź komunikat
    await expect(page.locator('text=/Cannot edit future|Nie można edytować przyszłości/i')).toBeVisible();
  });
  
  test('nie można przejść do przyszłego miesiąca', async ({ page }) => {
    // Sprawdź czy jesteśmy w bieżącym miesiącu
    const currentMonth = new Date().toISOString().slice(0, 7);
    const currentUrl = page.url();
    
    if (currentUrl.includes(currentMonth)) {
      // Button "Następny" powinien być disabled
      const nextButton = page.locator('button:has-text("Następny"), a:has-text("Następny"), button:has-text("▶")');
      await expect(nextButton).toBeDisabled();
    }
    
    // Próba bezpośredniego wejścia na przyszły miesiąc
    const futureMonth = new Date();
    futureMonth.setMonth(futureMonth.getMonth() + 1);
    const monthStr = futureMonth.toISOString().slice(0, 7);
    
    await page.goto(`/month/${monthStr}`);
    
    // Sprawdź error message lub redirect
    await expect(page.locator('text=/Cannot view future|Nie można wyświetlić przyszłości/i')).toBeVisible({ timeout: 5000 });
  });
});

test.describe('Validations - Okno edycji', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/login');
    await page.fill('input[name="email"]', TEST_USER.email);
    await page.fill('input[name="password"]', TEST_USER.password);
    await page.click('button[type="submit"]');
    await page.waitForURL(/\/month\/\d{4}-\d{2}/);
  });
  
  test('nie można edytować dnia sprzed 2 miesięcy', async ({ page }) => {
    // Przejdź do dnia 2 miesiące wstecz
    const oldDate = new Date();
    oldDate.setMonth(oldDate.getMonth() - 2);
    const dateStr = oldDate.toISOString().slice(0, 10);
    
    await page.goto(`/day/${dateStr}`);
    
    // Save button disabled
    const saveButton = page.locator('button:has-text("Zapisz"), button:has-text("Save"), button[type="submit"]');
    await expect(saveButton).toBeDisabled();
    
    // Komunikat
    await expect(page.locator('text=/Cannot edit|Nie można edytować|outside edit window/i')).toBeVisible();
  });
  
  test('można edytować dzień z poprzedniego miesiąca', async ({ page }) => {
    // Przejdź do dnia poprzedniego miesiąca
    const prevMonth = new Date();
    prevMonth.setMonth(prevMonth.getMonth() - 1);
    prevMonth.setDate(15); // Środek miesiąca
    const dateStr = prevMonth.toISOString().slice(0, 10);
    
    await page.goto(`/day/${dateStr}`);
    
    // Save button enabled
    const saveButton = page.locator('button:has-text("Zapisz"), button:has-text("Save"), button[type="submit"]');
    await expect(saveButton).toBeEnabled();
  });
  
  test('można edytować dzień z bieżącego miesiąca', async ({ page }) => {
    // Przejdź do dnia z bieżącego miesiąca (nie przyszłość)
    const today = new Date();
    today.setDate(today.getDate() - 1); // Wczoraj
    const dateStr = today.toISOString().slice(0, 10);
    
    await page.goto(`/day/${dateStr}`);
    
    // Save button enabled
    const saveButton = page.locator('button:has-text("Zapisz"), button:has-text("Save"), button[type="submit"]');
    await expect(saveButton).toBeEnabled();
  });
});

test.describe('Validations - Duplikaty tasków', () => {
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
  
  test('nie można dodać tego samego taska dwa razy', async ({ page }) => {
    await page.waitForTimeout(1000);
    
    // Wybierz pierwszy task
    const firstTask = page.locator('[data-testid="task-item"] button, button:has-text("Wybierz")').first();
    const taskText = await firstTask.textContent();
    await firstTask.click();
    await page.waitForTimeout(300);
    
    // Sprawdź czy task zniknął z listy available
    const availableTasks = page.locator(`[data-testid="task-item"]:visible:has-text("${taskText}"), .task-item:visible:has-text("${taskText}")`);
    expect(await availableTasks.count()).toBe(0);
    
    // Lub sprawdź czy button jest disabled
    await expect(firstTask).toBeDisabled();
  });
  
  test('wybrany task pojawia się tylko w "Selected tasks"', async ({ page }) => {
    await page.waitForTimeout(1000);
    
    // Wybierz task
    const firstTask = page.locator('[data-testid="task-item"] button, button:has-text("Wybierz")').first();
    await firstTask.click();
    
    // Sprawdź czy jest w selected
    await expect(page.locator('text=/Wybrane zadania|Selected tasks/i')).toBeVisible();
    
    // Sprawdź czy nie ma duplikatu w available
    const selectedCount = page.locator('[data-testid="selected-task"], .selected-task, input[type="number"][name="duration"]');
    expect(await selectedCount.count()).toBe(1);
  });
});

test.describe('Validations - Frontend validation', () => {
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
  
  test('total suma jest wyświetlany na bieżąco', async ({ page }) => {
    await page.waitForTimeout(1000);
    
    // Wybierz task
    const firstTask = page.locator('[data-testid="task-item"] button, button:has-text("Wybierz")').first();
    await firstTask.click();
    
    // Wprowadź czas
    const durationInput = page.locator('input[type="number"][name="duration"]').first();
    await durationInput.fill('120');
    
    // Sprawdź czy total się zaktualizował
    await expect(page.locator('text=/Total|Suma/i')).toBeVisible();
    await expect(page.locator('text=/120|2:00/i')).toBeVisible();
  });
  
  test('warning gdy zbliżamy się do limitu 1440', async ({ page }) => {
    await page.waitForTimeout(1000);
    
    const firstTask = page.locator('[data-testid="task-item"] button, button:has-text("Wybierz")').first();
    await firstTask.click();
    
    const durationInput = page.locator('input[type="number"][name="duration"]').first();
    await durationInput.fill('1400');
    
    // Sprawdź czy jest warning lub info o pozostałym czasie
    await expect(page.locator('text=/40.*remaining|pozostało.*40/i')).toBeVisible();
  });
});
