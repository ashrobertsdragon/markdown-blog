import { defineConfig, devices } from '@playwright/test'

export default defineConfig({
  testDir: './tests',
  testMatch: ['**/e2e/*.ts', '**/acceptance/*.ts'],
  fullyParallel: true,
  forbidOnly: !!process.env.CI,
  retries: process.env.CI ? 2 : 0,
  workers: 1,
  reporter: [
    ['html'],
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
      reuseExistingServer: !process.env.CI,
      timeout: 120000,
    },
    {
      command:
        'cd ../backend && FLASK_ENV=TESTING CLERK_JWKS_URL=http://127.0.0.1:5557/.well-known/jwks.json DRAFTS_PATH=/tmp/test-drafts GITHUB_PERSONAL_ACCESS_TOKEN=test GITHUB_OWNER=test-owner GITHUB_REPO=test-repo uv run dev_flask',
      url: 'http://localhost:5555/api/health',
      reuseExistingServer: !process.env.CI,
      timeout: 120000,
    },
    {
      command: 'npm run dev',
      url: 'http://localhost:5556',
      reuseExistingServer: !process.env.CI,
      timeout: 120000,
    },
  ],
  projects: process.env.CI
    ? [
        {
          name: 'chromium',
          use: { ...devices['Desktop Chrome'] },
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
          use: { ...devices['Desktop Chrome'] },
        },
      ],
})
