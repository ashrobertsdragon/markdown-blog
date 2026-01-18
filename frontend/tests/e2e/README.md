# E2E Authentication Flow Tests

Comprehensive end-to-end tests for the blog platform authentication flow using Playwright.

## Overview

These tests verify the complete authentication system including:

- Clerk OAuth integration
- Protected route redirects
- Role-based access control (authenticated, author, admin)
- JWT token handling
- API authentication headers
- Cross-browser compatibility

## Test Files

### `auth-flow.spec.ts`

Main test suite containing three test suites:

1. **Authentication Flow** (24 tests)

   - Unauthenticated redirects to protected routes
   - Login page rendering and form display
   - JWT token validation
   - Home page accessibility
   - Session persistence
   - Navigation behavior

1. **Role-Based Access Control** (4 tests)

   - Admin route protection
   - Author route protection
   - Role hierarchy enforcement

1. **Browser Compatibility** (3 tests)

   - Chrome, Firefox, Safari compatibility
   - Cross-browser navigation
   - Multi-browser login flows

1. **Performance and Reliability** (6 tests)

   - Initial page load timing
   - Redirect performance
   - Memory usage under stress
   - Multiple concurrent requests

### `fixtures/helpers.ts`

Utility functions for common test operations:

- `waitForApiCall(page, pattern, timeout)` - Wait for specific API responses
- `getAuthToken(page)` - Extract JWT token from cookies/storage
- `verifyAuthHeaderInRequest(page, apiPath)` - Verify Bearer token in request headers
- `login(page, email, password)` - Perform login flow
- `checkUserCreatedInDatabase(page, clerkUserId)` - Verify user record in database
- `verifyRedirectToLogin(page, protectedPath)` - Assert redirect to /login
- `logout(page)` - Sign out from application
- `waitForAuthToLoad(page)` - Wait for auth state to initialize
- `verifyBearerTokenFormat(token)` - Validate JWT token format
- `interceptApiRequests(page)` - Track all API requests and auth headers

## Configuration

### `playwright.config.ts`

Playwright configuration with:

- **Base URL**: <http://localhost:3000>
- **Test Directory**: ./tests/e2e
- **Browsers**: Chromium, Firefox, WebKit
- **Web Servers**: Frontend (Vite) and Backend (Flask) auto-start
- **Reporting**: HTML, JSON, JUnit XML formats
- **Artifacts**: Screenshots on failure, video retention, trace logs

## Running Tests

### Development

```bash
npm run test:e2e
```

Run all E2E tests in headless mode.

```bash
npm run test:e2e:ui
```

Run tests with interactive UI (Playwright Inspector).

```bash
npm run test:e2e:debug
```

Run tests in debug mode with step-by-step execution.

### CI/CD

```bash
CI=true npm run test:e2e
```

Run tests with CI settings (retries enabled, single worker, existing servers not reused).

## Test Coverage

### Authentication Flow (24 tests)

#### Redirect Tests

- [x] Unauthenticated user redirected to /login from /admin
- [x] Unauthenticated user redirected to /login from /author
- [x] Protected route preserves location state on redirect
- [x] Public routes accessible without authentication
- [x] Forbidden page accessible to all users
- [x] 404 page displayed for invalid routes

#### Login Tests

- [x] Login page displays sign-in form
- [x] JWT token structure validation
- [x] Home page accessible after auth loads
- [x] Multiple redirects handled correctly
- [x] Page refresh maintains auth state
- [x] Network errors handled gracefully
- [x] Auth context provides user state

#### Session Tests

- [x] Session persistence across navigations
- [x] Rapid navigation handled correctly
- [x] API health endpoints return 200
- [x] Database health endpoint accessible
- [x] GitHub health endpoint accessible
- [x] Unauthenticated /auth/me returns 401
- [x] Invalid tokens rejected
- [x] Authorization header format validation
- [x] Clerk SDK loads successfully
- [x] React Router configured correctly
- [x] App initializes without errors
- [x] Navigation state preserved during auth

### Role-Based Access Control (4 tests)

- [x] Unauthenticated cannot access /admin
- [x] Unauthenticated cannot access /author
- [x] Role hierarchy enforced in routing
- [x] Protected routes require authentication

### Browser Compatibility (3 tests)

- [x] Login renders in all browsers
- [x] Protected route redirects work in all browsers
- [x] Navigation works in all browsers

### Performance & Reliability (6 tests)

- [x] Initial page load completes within timeout
- [x] Protected route redirect is quick
- [x] Multiple rapid requests handled
- [x] Memory usage reasonable
- [x] No memory leaks during navigation
- [x] Load time under 10 seconds

## Key Testing Patterns

### Waiting for Authentication

```typescript
await waitForAuthToLoad(page);
```

Waits for loading spinner to disappear, indicating auth state has loaded.

### Verifying Redirects

```typescript
await verifyRedirectToLogin(page, "/admin");
expect(page).toHaveURL("/login");
```

Tests that protected routes redirect unauthenticated users to login.

### API Request Validation

```typescript
const response = await page.request.get("/api/auth/me");
expect(response.status()).toBe(401);
```

Verifies API endpoints return appropriate status codes.

### Bearer Token Verification

```typescript
const token = await getAuthToken(page);
verifyBearerTokenFormat(token);
```

Validates JWT token format and structure.

## Environment Variables

Tests automatically use:

- `VITE_CLERK_PUBLISHABLE_KEY` - Clerk public key from .env
- `VITE_API_BASE_URL` - API base URL (defaults to /api)

For E2E testing, ensure:

1. Frontend running on <http://localhost:3000>
1. Backend running on <http://localhost:5000>
1. Clerk test credentials configured

## Debugging Tests

### View Test Report

After running tests, open the HTML report:

```bash
npx playwright show-report
```

### Debug Specific Test

```bash
npx playwright test --debug --grep "unauthenticated user redirected"
```

### Inspect Network Requests

Tests automatically capture network requests. Check:

- Network tab in report
- HTTP status codes
- Request/response bodies
- Headers including Authorization

### Screenshot and Video Artifacts

Tests capture:

- Screenshots on failure
- Video recordings on failure
- Trace logs for debugging

Located in `playwright-report/` directory.

## Common Issues

### Tests Timing Out

**Issue**: Tests fail with timeout error
**Solution**: Increase timeout in playwright.config.ts or specific test:

```typescript
test("long running test", async ({ page }) => {
  // ...
}, { timeout: 60000 });
```

### Web Server Not Starting

**Issue**: "ECONNREFUSED" connecting to localhost
**Solution**: Ensure servers can start independently:

```bash
npm run dev               # Frontend
cd ../backend && uv run -m backend.main  # Backend
```

### Playwright Browsers Not Found

**Issue**: "Chromium is not installed"
**Solution**: Install browsers:

```bash
npx playwright install
```

### Cookie/Session Persistence Issues

**Issue**: Auth token not persisting between tests
**Solution**: Use `test.beforeEach` to ensure clean state:

```typescript
test.beforeEach(async ({ page }) => {
  await page.goto("/");
  await waitForAuthToLoad(page);
});
```

## Best Practices

1. **Use Explicit Waits**: Don't rely on fixed delays

   ```typescript
   await page.waitForURL("/admin", { timeout: 5000 });
   ```

1. **Test User Interactions**: Test what users actually do

   ```typescript
   await page.fill("input[type='email']", "user@example.com");
   await page.click("button:has-text('Sign In')");
   ```

1. **Verify State Changes**: Check DOM after interactions

   ```typescript
   await expect(page.locator("text=Sign In to Your Account")).toBeVisible();
   ```

1. **Isolate Tests**: Each test should be independent

   ```typescript
   test.beforeEach(async ({ page }) => {
     await page.goto("/");
   });
   ```

1. **Use Helpers**: Leverage utility functions

   ```typescript
   await verifyRedirectToLogin(page, "/admin");
   ```

## CI/CD Integration

Tests run automatically in GitHub Actions:

1. Frontend CI workflow installs dependencies
1. Starts frontend and backend servers
1. Runs full E2E test suite
1. Uploads test reports as artifacts
1. Blocks merge on test failure

## Future Enhancements

- [ ] Add login flow tests with real Clerk test account
- [ ] Add logout flow tests
- [ ] Add password reset flow tests
- [ ] Add role update verification tests
- [ ] Add API authentication header tests
- [ ] Add concurrent session tests
- [ ] Add device compatibility tests
- [ ] Add accessibility testing (axe)

## References

- [Playwright Documentation](https://playwright.dev)
- [Clerk Authentication](https://clerk.com/docs)
- [React Router](https://reactrouter.com)
- [Playwright Best Practices](https://playwright.dev/docs/best-practices)
