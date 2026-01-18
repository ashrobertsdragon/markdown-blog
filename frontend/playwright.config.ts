import { defineConfig, devices } from "@playwright/test";

export default defineConfig({
	testDir: "./tests/e2e",
	fullyParallel: false,
	forbidOnly: !!process.env.CI,
	retries: process.env.CI ? 2 : 0,
	workers: process.env.CI ? 1 : 1,
	reporter: [
		["html"],
		["json", { outputFile: "test-results/results.json" }],
		["junit", { outputFile: "test-results/junit.xml" }],
		["list"],
	],
	use: {
		baseURL: "http://localhost:3000",
		trace: "on-first-retry",
		screenshot: "only-on-failure",
		video: "retain-on-failure",
	},
	webServer: [
		{
			command: "npm run dev",
			url: "http://localhost:3000",
			reuseExistingServer: !process.env.CI,
			timeout: 120000,
		},
		{
			command: "cd ../backend && uv run -m backend.main",
			url: "http://localhost:5000/health",
			reuseExistingServer: !process.env.CI,
			timeout: 120000,
		},
	],
	projects: [
		{
			name: "chromium",
			use: { ...devices["Desktop Chrome"] },
		},
		{
			name: "firefox",
			use: { ...devices["Desktop Firefox"] },
		},
		{
			name: "webkit",
			use: { ...devices["Desktop Safari"] },
		},
	],
});
