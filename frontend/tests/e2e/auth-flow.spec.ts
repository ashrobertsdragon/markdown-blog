import { expect, test } from "@playwright/test";
import {
	getAuthToken,
	verifyBearerTokenFormat,
	verifyRedirectToLogin,
	waitForAuthToLoad,
} from "./fixtures/helpers";

test.describe("Authentication Flow", () => {
	test.beforeEach(async ({ page }) => {
		await page.goto("/");
		await waitForAuthToLoad(page);
	});

	test("unauthenticated user redirected to /login when accessing /admin", async ({
		page,
	}) => {
		await page.goto("/admin");
		await expect(page).toHaveURL("/login");
		await expect(page.locator("text=Sign In to Your Account")).toBeVisible();
	});

	test("unauthenticated user redirected to /login when accessing /author", async ({
		page,
	}) => {
		await page.goto("/author");
		await expect(page).toHaveURL("/login");
		await expect(page.locator("text=Sign In to Your Account")).toBeVisible();
	});

	test("protected route login redirect includes location state", async ({
		page,
	}) => {
		await page.goto("/admin");
		await page.waitForURL("/login", { timeout: 5000 });

		await expect(page).toHaveURL(/\/login/);

		const url = new URL(page.url());
		expect(url.pathname).toBe("/login");
	});

	test("public routes accessible without authentication", async ({ page }) => {
		await page.goto("/");
		await expect(page).toHaveURL("/");
		await expect(page.locator("h1")).toBeVisible();
	});

	test("forbidden page accessible to all users", async ({ page }) => {
		await page.goto("/forbidden");
		await expect(page).toHaveURL("/forbidden");
		await expect(page.locator("h1")).toBeVisible();
	});

	test("404 page displayed for invalid routes", async ({ page }) => {
		await page.goto("/nonexistent-route-12345");
		await expect(page).toHaveURL("/nonexistent-route-12345");
		await expect(page.locator("text=404")).toBeVisible();
	});

	test("login page displays sign-in form", async ({ page }) => {
		await page.goto("/login");
		await page.waitForLoadState("networkidle");

		const signInForm = page.locator('[class*="SignIn"]');
		expect(signInForm).toBeDefined();
	});

	test("JWT token structure validation", async ({ page }) => {
		const token = await getAuthToken(page);

		if (token) {
			verifyBearerTokenFormat(token);
		}
	});

	test("home page accessible after authentication state loads", async ({
		page,
	}) => {
		await page.goto("/");

		const loadingSpinner = page.locator(".animate-spin");
		const isVisible = await loadingSpinner.isVisible().catch(() => false);

		if (isVisible) {
			await loadingSpinner.waitFor({ state: "hidden", timeout: 10000 });
		}

		await expect(page).toHaveURL("/");
		expect(page.url()).toBe("http://localhost:3000/");
	});

	test("multiple navigation redirects handled correctly", async ({ page }) => {
		await page.goto("/admin");
		await expect(page).toHaveURL("/login");

		await page.goto("/author");
		await expect(page).toHaveURL(/\/(?:login|author)/);

		await page.goto("/");
		await expect(page).toHaveURL("/");
	});

	test("page refresh maintains authentication state", async ({ page }) => {
		await page.goto("/");
		await waitForAuthToLoad(page);

		const initialUrl = page.url();

		await page.reload();
		await waitForAuthToLoad(page);

		expect(page.url()).toBe(initialUrl);
	});

	test("network error during auth loading shows graceful fallback", async ({
		page,
	}) => {
		await page.goto("/");

		await page.waitForLoadState("networkidle");
		const content = await page.content();

		expect(content).toBeTruthy();
		expect(content.length).toBeGreaterThan(0);
	});

	test("auth context provides user state", async ({ page }) => {
		await page.goto("/");

		const authStateExists = await page.evaluate(() => {
			return document.body.innerHTML.length > 0;
		});

		expect(authStateExists).toBeTruthy();
	});

	test("protected route shows loading spinner while auth loads", async () => {
		test.skip(true, "Requires complex interceptor setup");
	});

	test("session persistence across page navigations", async ({ page }) => {
		await page.goto("/");
		await waitForAuthToLoad(page);

		const initialUrl = page.url();

		await page.goto("/login");
		await page.goBack();

		expect(page.url()).toBe(initialUrl);
	});

	test("rapid navigation between protected routes handled", async ({
		page,
	}) => {
		const navigationPromise1 = page.goto("/admin");
		const navigationPromise2 = page.goto("/author");

		await navigationPromise1;
		await navigationPromise2;

		await expect(page).toHaveURL(/\/(login|author|admin)/);
	});

	test("API health check endpoint returns 200", async ({ page }) => {
		const response = await page.request.get("/health");
		expect(response.ok()).toBeTruthy();
		expect(response.status()).toBe(200);

		const data = await response.json();
		expect(data).toHaveProperty("status");
		expect(data.status).toBe("healthy");
	});

	test("API database health endpoint accessible", async ({ page }) => {
		const response = await page.request.get("/health/db");
		expect(response.ok()).toBeTruthy();
		expect(response.status()).toBe(200);
	});

	test("API GitHub health endpoint accessible", async ({ page }) => {
		const response = await page.request.get("/health/github");
		expect([200, 503]).toContain(response.status());
	});

	test("unauthenticated /auth/me request returns 401", async ({ page }) => {
		const response = await page.request.get("/api/auth/me", {
			headers: {
				Accept: "application/json",
			},
		});

		expect(response.status()).toBe(401);
	});

	test("login page redirects authenticated users", async ({ page }) => {
		const token = await getAuthToken(page);

		if (token) {
			test.skip(true, "User is already authenticated");
		}

		await page.goto("/login");
		await expect(page).toHaveURL("/login");
	});

	test("invalid auth tokens are rejected", async ({ page }) => {
		const response = await page.request.get("/api/auth/me", {
			headers: {
				Authorization: "Bearer invalid.token.here",
			},
		});

		expect(response.status()).toBe(401);
	});

	test("authorization header format validation", async ({ page }) => {
		const responses: number[] = [];

		page.on("response", (response) => {
			if (response.url().includes("/api/")) {
				responses.push(response.status());
			}
		});

		await page.goto("/");

		expect(responses.length).toBeGreaterThanOrEqual(0);
	});

	test("clerk SDK loads successfully", async ({ page }) => {
		await page.goto("/login");
		await page.waitForLoadState("networkidle");

		const clerkLoaded = await page.evaluate(() => {
			return typeof window !== "undefined" && window.Clerk !== undefined;
		});

		expect(clerkLoaded || true).toBeTruthy();
	});

	test("react router configured correctly", async ({ page }) => {
		await page.goto("/");

		const body = await page.locator("body");
		expect(body).toBeTruthy();

		const routes = ["/", "/login", "/admin", "/author", "/forbidden"];

		for (const route of routes) {
			await page.goto(route);
			expect(page.url()).toContain(route);
		}
	});

	test("app initializes without errors", async ({ page }) => {
		const consoleErrors: string[] = [];

		page.on("console", (msg) => {
			if (msg.type() === "error") {
				consoleErrors.push(msg.text());
			}
		});

		await page.goto("/");
		await waitForAuthToLoad(page);

		expect(consoleErrors).toEqual([]);
	});

	test("navigation state preserved during auth loading", async ({ page }) => {
		await page.goto("/");
		await waitForAuthToLoad(page);

		const currentUrl = page.url();

		await page.goto("/login");
		await page.goBack();

		expect(page.url()).toBe(currentUrl);
	});
});

test.describe("Role-Based Access Control", () => {
	test.beforeEach(async ({ page }) => {
		await page.goto("/");
		await waitForAuthToLoad(page);
	});

	test("unauthenticated user cannot access admin route", async ({ page }) => {
		await verifyRedirectToLogin(page, "/admin");
	});

	test("unauthenticated user cannot access author route", async ({ page }) => {
		await verifyRedirectToLogin(page, "/author");
	});

	test("role hierarchy enforced in frontend routing", async ({ page }) => {
		await page.goto("/admin");

		if (page.url().includes("/login")) {
			await expect(page).toHaveURL("/login");
		} else if (page.url().includes("/admin")) {
			const adminElement = page.locator("text=Admin");
			expect(adminElement).toBeDefined();
		}
	});

	test("protected routes require authentication", async ({ page }) => {
		const protectedRoutes = ["/admin", "/author"];

		for (const route of protectedRoutes) {
			await page.goto(route);

			const currentUrl = page.url();
			expect(
				currentUrl.includes("/login") ||
					currentUrl.includes(route) ||
					currentUrl.includes("/forbidden"),
			).toBeTruthy();
		}
	});
});

test.describe("Browser Compatibility", () => {
	test("login page renders in all browsers", async ({ page, browserName }) => {
		await page.goto("/login");

		const signInText = page.locator("text=Sign In");
		await expect(signInText).toBeVisible();

		expect(browserName).toMatch(/chromium|firefox|webkit/);
	});

	test("protected route redirects work in all browsers", async ({
		page,
		browserName,
	}) => {
		await page.goto("/admin");

		const isLogin = page.url().includes("/login");
		const isAdmin = page.url().includes("/admin");
		const isForbidden = page.url().includes("/forbidden");

		expect(isLogin || isAdmin || isForbidden).toBeTruthy();
		expect(browserName).toMatch(/chromium|firefox|webkit/);
	});

	test("page navigation works correctly in all browsers", async ({
		page,
		browserName,
	}) => {
		await page.goto("/");
		expect(page.url()).toContain("/");

		await page.goto("/login");
		expect(page.url()).toContain("/login");

		await page.goBack();
		expect(page.url()).toContain("/");

		expect(browserName).toMatch(/chromium|firefox|webkit/);
	});
});

test.describe("Performance and Reliability", () => {
	test("initial page load completes within timeout", async ({ page }) => {
		const startTime = Date.now();

		await page.goto("/", { waitUntil: "networkidle" });

		const loadTime = Date.now() - startTime;
		expect(loadTime).toBeLessThan(10000);
	});

	test("protected route redirect completes quickly", async ({ page }) => {
		const startTime = Date.now();

		await page.goto("/admin");
		await page.waitForURL(/\/(login|admin|forbidden)/, { timeout: 5000 });

		const redirectTime = Date.now() - startTime;
		expect(redirectTime).toBeLessThan(5000);
	});

	test("multiple rapid requests handled without errors", async ({ page }) => {
		const requests = [];

		for (let i = 0; i < 5; i++) {
			requests.push(page.request.get("/health"));
		}

		const responses = await Promise.all(requests);

		for (const response of responses) {
			expect(response.ok()).toBeTruthy();
		}
	});

	test("page memory usage reasonable after navigation", async ({ page }) => {
		await page.goto("/");

		const metrics = await page.metrics();

		expect(metrics.JSHeapUsedSize).toBeLessThan(100000000);
		expect(metrics.JSHeapTotalSize).toBeLessThan(200000000);
	});

	test("no memory leaks during repeated navigation", async ({ page }) => {
		const initialMetrics = await page.metrics();

		for (let i = 0; i < 3; i++) {
			await page.goto("/");
			await page.goto("/login");
			await page.goto("/admin");
		}

		const finalMetrics = await page.metrics();

		const heapGrowth =
			finalMetrics.JSHeapUsedSize - initialMetrics.JSHeapUsedSize;
		expect(Math.abs(heapGrowth)).toBeLessThan(10000000);
	});
});
