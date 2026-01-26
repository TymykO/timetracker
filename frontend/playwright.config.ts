import { defineConfig, devices } from '@playwright/test';

/**
 * Playwright configuration dla testów E2E projektu TimeTracker.
 * 
 * Konfiguruje:
 * - Base URL dla frontend i backend
 * - Timeouty
 * - Browsers (Chromium dla CI, wszystkie dla local)
 * - Fixtures dla setup/teardown
 */
export default defineConfig({
  testDir: './tests/e2e',
  
  // Timeout dla każdego testu
  timeout: 30 * 1000,
  
  // Timeout dla expect()
  expect: {
    timeout: 5000
  },
  
  // Uruchamiaj testy sekwencyjnie w każdym pliku
  fullyParallel: false,
  
  // Nie retry w dev (szybsze debugowanie)
  retries: process.env.CI ? 2 : 0,
  
  // Workers: 1 w CI, kilka lokalnie
  workers: process.env.CI ? 1 : undefined,
  
  // Reporter: lista dla dev, html dla CI
  reporter: process.env.CI ? 'html' : 'list',
  
  // Global setup/teardown
  use: {
    // Base URL dla aplikacji
    baseURL: process.env.VITE_APP_URL || 'http://localhost:5173',
    
    // Trace tylko on first retry
    trace: 'on-first-retry',
    
    // Screenshot tylko on failure
    screenshot: 'only-on-failure',
    
    // Video tylko on failure
    video: 'retain-on-failure',
    
    // API context
    extraHTTPHeaders: {
      // Accept JSON
      'Accept': 'application/json',
    },
  },

  // Projekty - różne przeglądarki
  projects: [
    {
      name: 'chromium',
      use: { 
        ...devices['Desktop Chrome'],
        // Credentials (cookies) dla API calls
        storageState: undefined,
      },
    },

    // Opcjonalnie: Firefox i WebKit (odkomentować dla pełnego testowania)
    // {
    //   name: 'firefox',
    //   use: { ...devices['Desktop Firefox'] },
    // },
    // {
    //   name: 'webkit',
    //   use: { ...devices['Desktop Safari'] },
    // },

    // Mobile viewports (opcjonalnie)
    // {
    //   name: 'Mobile Chrome',
    //   use: { ...devices['Pixel 5'] },
    // },
  ],

  // Dev server - jeśli nie jest już uruchomiony
  webServer: {
    command: 'npm run dev',
    url: 'http://localhost:5173',
    reuseExistingServer: !process.env.CI,
    timeout: 120 * 1000,
    stdout: 'ignore',
    stderr: 'pipe',
  },
});
