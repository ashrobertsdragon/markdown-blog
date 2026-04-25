import { defineConfig, devices } from '@playwright/test'

export default defineConfig({
  globalSetup: './tests/acceptance/global-setup.ts',
  testDir: './tests',
  testMatch: ['**/e2e/*.ts', '**/acceptance/*.ts'],
  fullyParallel: false,
  forbidOnly: !!process.env.CI,
  retries: process.env.CI ? 2 : 0,
  workers: 1,
  reporter: process.env.CI
    ? [['list']]
    : [
        ['json', { outputFile: 'test-results/results.json' }],
        ['junit', { outputFile: 'test-results/junit.xml' }],
        ['list'],
      ],
  use: {
    baseURL: 'http://localhost:5556',
    trace: 'on-first-retry',
    screenshot: 'only-on-failure',
    video: 'retain-on-failure',
  },
  webServer: [
    {
      command: 'npx tsx tests/fixtures/jwks-server.ts',
      url: 'http://127.0.0.1:5557/.well-known/jwks.json',
      reuseExistingServer: true,
      timeout: 120000,
    },
    {
      command: 'uv run --directory ../backend dev_flask',
      env: {
        FLASK_ENV: 'TESTING',
        CLERK_JWKS_URL: 'http://127.0.0.1:5557/.well-known/jwks.json',
        DRAFTS_PATH: '/tmp/test-drafts',
        GITHUB_PERSONAL_ACCESS_TOKEN: 'test',
        GITHUB_OWNER: 'test-owner',
        GITHUB_REPO: 'test-repo',
        CLERK_PUBLISHABLE_KEY: 'pk_test_123',
        CLERK_SECRET_KEY: 'sk_test_123',
        SECRET_KEY: 'test-secret-key-for-e2e',
        LOCAL_DB_NAME: 'test',
        LOCAL_DB_USER: 'test',
        LOCAL_DB_PASSWORD: 'test',
      },
      url: 'http://localhost:5555/api/health',
      reuseExistingServer: true,
      timeout: 120000,
    },
    {
      command: 'npm run dev -- --mode test',
      url: 'http://localhost:5556',
      reuseExistingServer: !process.env.CI,
      timeout: 120000,
    },
  ],
  projects: process.env.CI
    ? [
        {
          name: 'chromium',
          use: {
            ...devices['Desktop Chrome'],
            permissions: ['clipboard-read', 'clipboard-write'],
          },
        },
        {
          name: 'firefox',
          use: { ...devices['Desktop Firefox'] },
        },
        {
          name: 'webkit',
          use: { ...devices['Desktop Safari'] },
        },
      ]
    : [
        {
          name: 'chromium',
          use: {
            ...devices['Desktop Chrome'],
            permissions: ['clipboard-read', 'clipboard-write'],
          },
        },
      ],
})
