import { defineConfig, devices } from '@playwright/test'
import dotenv from 'dotenv'

dotenv.config()

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
      command: 'uv run --directory ../backend dev_flask',
      env: {
        FLASK_ENV: 'TESTING',
        DRAFTS_PATH: '/tmp/test-drafts',
        GITHUB_PERSONAL_ACCESS_TOKEN: 'test',
        GITHUB_OWNER: 'test-owner',
        GITHUB_REPO: 'test-repo',
        CLERK_PUBLISHABLE_KEY: process.env.CLERK_PUBLISHABLE_KEY ?? '',
        CLERK_SECRET_KEY: process.env.CLERK_SECRET_KEY ?? '',
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
      env: {
        VITE_CLERK_PUBLISHABLE_KEY: process.env.CLERK_PUBLISHABLE_KEY ?? '',
      },
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
