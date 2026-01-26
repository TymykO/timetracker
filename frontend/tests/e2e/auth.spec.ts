/**
 * Testy E2E dla flow autoryzacji w TimeTracker.
 * 
 * Testuje:
 * - Login/logout
 * - Invite flow (set password)
 * - Password reset
 * - Session management
 */

import { test, expect, TEST_USER, TEST_ADMIN, API_BASE_URL } from './fixtures';

test.describe('Auth Flow - Login/Logout', () => {
  test('użytkownik może zalogować się email+password', async ({ page }) => {
    // Przejdź do strony logowania
    await page.goto('/login');
    
    // Sprawdź czy formularz jest widoczny
    await expect(page.locator('input[name="email"]')).toBeVisible();
    await expect(page.locator('input[name="password"]')).toBeVisible();
    
    // Wypełnij formularz
    await page.fill('input[name="email"]', TEST_USER.email);
    await page.fill('input[name="password"]', TEST_USER.password);
    
    // Submituj
    await page.click('button[type="submit"]');
    
    // Poczekaj na redirect do month view
    await page.waitForURL(/\/month\/\d{4}-\d{2}/);
    
    // Sprawdź czy jesteśmy zalogowani (user info powinien być widoczny)
    await expect(page.locator('text=' + TEST_USER.email)).toBeVisible();
  });
  
  test('błędne hasło pokazuje error', async ({ page }) => {
    await page.goto('/login');
    
    await page.fill('input[name="email"]', TEST_USER.email);
    await page.fill('input[name="password"]', 'wrong_password');
    await page.click('button[type="submit"]');
    
    // Sprawdź czy error message jest widoczny
    await expect(page.locator('text=/Nieprawidłowe dane|Invalid credentials/i')).toBeVisible();
  });
  
  test('użytkownik może się wylogować', async ({ page }) => {
    // Login
    await page.goto('/login');
    await page.fill('input[name="email"]', TEST_USER.email);
    await page.fill('input[name="password"]', TEST_USER.password);
    await page.click('button[type="submit"]');
    await page.waitForURL(/\/month\/\d{4}-\d{2}/);
    
    // Logout (kliknij button/link)
    await page.click('text=/Wyloguj|Logout/i');
    
    // Sprawdź redirect do /login
    await page.waitForURL('/login');
    
    // Sprawdź że nie możemy wejść na chronione strony
    await page.goto('/month/2025-01');
    await page.waitForURL('/login'); // Powinien redirectować
  });
});

test.describe('Auth Flow - Invite (Set Password)', () => {
  test.skip('employee może ustawić hasło z invite token', async ({ page }) => {
    // TODO: Wymaga utworzenia employee i wygenerowania tokenu przez Django Admin
    // Teraz skip, zaimplementować po manualnym teście
    
    const INVITE_TOKEN = 'test_invite_token_placeholder';
    
    await page.goto(`/set-password?token=${INVITE_TOKEN}`);
    
    // Sprawdź czy token jest validowany
    await expect(page.locator('text=/Email:|E-mail:/i')).toBeVisible();
    
    // Wypełnij formularz
    await page.fill('input[name="password"]', 'newpassword123');
    await page.fill('input[name="password_confirm"]', 'newpassword123');
    await page.click('button[type="submit"]');
    
    // Sprawdź success message
    await expect(page.locator('text=/Hasło ustawione|Password set/i')).toBeVisible();
    
    // Przekierowanie do login
    await page.waitForURL('/login');
  });
  
  test.skip('nieprawidłowy invite token pokazuje error', async ({ page }) => {
    await page.goto('/set-password?token=invalid_token_12345');
    
    // Error message
    await expect(page.locator('text=/Token nieprawidłowy|Invalid token/i')).toBeVisible();
  });
});

test.describe('Auth Flow - Password Reset', () => {
  test.skip('użytkownik może zresetować hasło', async ({ page }) => {
    // TODO: Wymaga implementacji flow i testowania
    
    // Krok 1: Request reset
    await page.goto('/forgot-password');
    await page.fill('input[name="email"]', TEST_USER.email);
    await page.click('button[type="submit"]');
    
    // Success message (zawsze 200 aby nie ujawniać czy email istnieje)
    await expect(page.locator('text=/Link wysłany|Link sent/i')).toBeVisible();
    
    // Krok 2: W realnym scenariuszu trzeba by wyciągnąć token z emaila
    // Tutaj skip, bo wymaga integracji z email system
  });
});

test.describe('Auth Flow - Session Management', () => {
  test('chronione strony redirectują do /login gdy nie zalogowany', async ({ page }) => {
    // Próba dostępu do month view bez logowania
    await page.goto('/month/2025-01');
    
    // Redirect do login
    await page.waitForURL('/login');
  });
  
  test('chronione strony redirectują do /login gdy nie zalogowany (day view)', async ({ page }) => {
    // Próba dostępu do day view
    await page.goto('/day/2025-01-15');
    
    // Redirect do login
    await page.waitForURL('/login');
  });
});
