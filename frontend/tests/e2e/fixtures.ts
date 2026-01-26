/**
 * Fixtures dla testów E2E projektu TimeTracker.
 * 
 * Fixtures to helpery które:
 * - Tworzą test data przed testami
 * - Cleanup po testach
 * - Zapewniają izolację między testami
 */

import { test as base, expect } from '@playwright/test';

/**
 * Backend API base URL
 */
export const API_BASE_URL = process.env.VITE_API_URL || 'http://localhost:8000';

/**
 * Test user credentials (utworzone przez Django seeder)
 */
export const TEST_USER = {
  email: 'testuser@example.com',
  password: 'testpass123',
};

/**
 * Test admin credentials
 */
export const TEST_ADMIN = {
  username: 'admin',
  password: 'admin',
};

/**
 * Extended test fixture z helpers
 */
type TestFixtures = {
  authenticatedPage: any;
};

/**
 * Custom test z fixtures
 */
export const test = base.extend<TestFixtures>({
  /**
   * Authenticated page fixture - automatycznie loguje użytkownika
   */
  authenticatedPage: async ({ page }, use) => {
    // Setup: zaloguj użytkownika
    await page.goto('/login');
    await page.fill('input[name="email"]', TEST_USER.email);
    await page.fill('input[name="password"]', TEST_USER.password);
    await page.click('button[type="submit"]');
    
    // Poczekaj na redirect do month view
    await page.waitForURL(/\/month\/\d{4}-\d{2}/);
    
    // Use fixture
    await use(page);
    
    // Teardown: wyloguj (opcjonalnie)
    // await page.goto('/api/auth/logout');
  },
});

/**
 * Helper: utworzenie employee przez Django Admin
 * (dla testów auth flow)
 */
export async function createEmployeeViaAdmin(
  page: any,
  email: string
): Promise<string> {
  // Login do Django Admin
  await page.goto(`${API_BASE_URL}/admin/`);
  await page.fill('input[name="username"]', TEST_ADMIN.username);
  await page.fill('input[name="password"]', TEST_ADMIN.password);
  await page.click('input[type="submit"]');
  
  // Przejdź do tworzenia Employee
  await page.goto(`${API_BASE_URL}/admin/timetracker_app/employee/add/`);
  
  // Wypełnij formularz
  await page.fill('input[name="email"]', email);
  await page.check('input[name="is_active"]');
  await page.fill('input[name="daily_norm_minutes"]', '480');
  
  // Zapisz
  await page.click('input[name="_save"]');
  
  // Wróć do listy i znajdź employee
  await page.goto(`${API_BASE_URL}/admin/timetracker_app/employee/`);
  
  // Kliknij na employee aby przejść do widoku szczegółów
  await page.click(`text=${email}`);
  
  // Wykonaj akcję "Generate invite link"
  // (Implementacja zależy od konfiguracji Django Admin action)
  // TODO: Zaimplementować po sprawdzeniu jak działa akcja w admin
  
  return 'TODO_TOKEN'; // Placeholder
}

/**
 * Helper: cleanup test data
 */
export async function cleanupTestData(page: any) {
  // TODO: Implementować cleanup przez API lub management command
  // Na razie pusta implementacja
}

/**
 * Re-export expect
 */
export { expect };
