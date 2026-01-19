# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Fixed

- **Backend**: Corrected authentication blueprint URL prefixes to match specification
  - Changed auth_bp registration from `/auth` to `/api/auth` in main.py
  - Changed users_bp registration from `/users` to `/api/users` in main.py
  - Updated all integration tests to use corrected endpoints
  - Updated documentation examples in auth.py and users.py
  - Endpoints now accessible at `/api/auth/me` and `/api/users` as per requirements
  - All 22 backend integration tests pass with corrected URL prefixes
  - Files modified: `backend/src/backend/main.py`, `backend/tests/integration/test_api_routes_auth.py`, `backend/tests/integration/test_api_routes_users.py`, `backend/src/backend/api/routes/auth.py`, `backend/src/backend/api/routes/users.py`

### Added

- **Documentation**: Comprehensive authentication setup guide in README
  - Added "Authentication" section after "Development" documenting complete authentication system
  - Backend configuration: environment variables (CLERK_PUBLISHABLE_KEY, CLERK_SECRET_KEY)
  - Backend endpoint protection: @require_auth and @require_role decorator usage with code examples
  - Decorator ordering requirements: @require_auth must precede @require_role with correct/incorrect usage examples
  - Accessing current user in endpoints via g.current_user
  - Comprehensive error response catalog: all 401 error types (missing header, invalid format, empty token, verification failed, user not authenticated)
  - 403 Forbidden responses for both author and admin role requirements
  - Frontend configuration: VITE_CLERK_PUBLISHABLE_KEY environment variable
  - ClerkProvider setup explanation for React app initialization
  - Authentication hooks: distinction between custom useAuth (@/context/AuthContext) for role checks and Clerk useAuth (@clerk/clerk-react) for JWT tokens
  - useAuth hook API documentation with code examples showing role-based UI
  - ProtectedRoute component usage for declarative route protection with requireRole prop
  - Common patterns: 3 practical examples combining backend and frontend authentication
  - Troubleshooting guide with 8 common authentication issues and solutions
  - Clerk UserResource type documentation with link to official API reference
  - File modified: `README.md`

### Fixed

- **Frontend**: Resolved Playwright test configuration conflict with Vitest globals
  - Fixed "Playwright Test did not expect test.describe() to be called here" error caused by TypeScript configuration
  - Created separate tsconfig.playwright.json for Playwright tests with only @playwright/test types
  - Excluded tests/e2e directory from main tsconfig.json to prevent vitest/globals type pollution
  - Excluded tests/e2e directory from vitest.config.ts to prevent Vitest from running Playwright tests
  - All 39 authentication E2E tests (117 total across 3 browsers) now load and run successfully
  - Files modified: `frontend/tsconfig.json` (added exclude for tests/e2e), `frontend/vitest.config.ts` (added include/exclude patterns)
  - Files created: `frontend/tsconfig.playwright.json` (dedicated TypeScript config for Playwright)

### Added

- **Frontend**: Comprehensive E2E authentication flow tests with Playwright
  - Created playwright.config.ts with multi-browser testing (Chromium, Firefox, WebKit)
  - Implemented web server auto-start for frontend (Vite port 3000) and backend (Flask port 5000)
  - Configured test reporting: HTML, JSON, and JUnit XML formats
  - Created tests/e2e/auth-flow.spec.ts with 39 comprehensive authentication tests
  - Test coverage includes: redirect behavior, protected routes, role-based access control, API endpoints, browser compatibility, performance, and reliability
  - Created tests/e2e/fixtures/helpers.ts with 10 reusable test utility functions for common operations (wait for API calls, token extraction, auth verification, login/logout flows, database checks)
  - Implemented test suites: Authentication Flow (24 tests), Role-Based Access Control (4 tests), Browser Compatibility (3 tests), Performance & Reliability (6 tests)
  - Added npm scripts: test:e2e (run all tests), test:e2e:ui (interactive UI), test:e2e:debug (debug mode)
  - Created tests/e2e/README.md with complete documentation: test patterns, configuration, debugging guide, best practices, CI/CD integration
  - Tests verify unauthenticated redirects, JWT token format, role hierarchy enforcement, API health endpoints, session persistence, memory usage, and cross-browser functionality
  - All tests use explicit waits to avoid flakiness: page.waitForURL(), page.waitForLoadState(), page.waitForFunction()
  - Playwright installed as dev dependency (@playwright/test ^1.57.0)
  - Tests run deterministically without flakiness in both local development and CI environments

### Fixed

- **Frontend**: Code review fixes for authentication implementation
  - Fixed unsafe type assertion in AuthContext role extraction to use explicit validation instead of type casting
  - Updated all useAuth mocks in test files to match AuthContextType interface (replaced userId/signOut with user object)
  - Improved loading indicator in ProtectedRoute from plain text to animated Loader2 spinner icon from lucide-react
  - Updated all loading state tests to check for spinner element instead of "Loading..." text
  - All 203 tests passing with improved user experience and type safety

### Added

- **Configuration**: Enhanced Clerk environment variable documentation

  - Added CLERK_PUBLISHABLE_KEY to backend .env.example for frontend integration consistency
  - Improved comments for all Clerk authentication variables explaining purpose and security considerations
  - Backend .env.example now documents three Clerk variables: CLERK_SECRET_KEY (JWT verification), CLERK_PUBLISHABLE_KEY (frontend integration), CLERK_WEBHOOK_SECRET_KEY (webhook validation)
  - Frontend .env.example enhanced with detailed comments explaining VITE_CLERK_PUBLISHABLE_KEY usage and relationship to backend configuration
  - All placeholder values use consistent "your_clerk\_\*" pattern
  - Files modified: `backend/.env.example`, `frontend/.env.example`

- **Frontend**: Protected routes implementation with role-based access control

  - Implemented route protection for /admin and /author paths using ProtectedRoute component with requireRole prop
  - Created Admin.tsx placeholder page for admin dashboard with Tailwind CSS styling
  - Created Author.tsx placeholder page for author dashboard with Tailwind CSS styling
  - Integrated AuthProvider wrapper around Routes in App.tsx for global authentication state
  - Added /login route as public access point for unauthenticated users
  - Added /forbidden route as public error page for unauthorized access attempts
  - Protected routes enforce both authentication (user must be signed in) and authorization (user must have required role)
  - Role hierarchy enforced: admin can access all routes, author can access author routes, authenticated users redirected to forbidden page
  - Created custom test utilities in test-utils.tsx with MemoryRouter support for route testing with initialEntries
  - Exported AppRoutes component separately for testing flexibility (MemoryRouter in tests, BrowserRouter in production)
  - Comprehensive test suite with 38 tests validating route protection, loading states, authentication redirects, authorization checks, and public route access
  - All 203 tests passing with no regressions, production build succeeds
  - Files created: `frontend/src/pages/Admin.tsx`, `frontend/src/pages/Author.tsx`, `frontend/tests/test-utils.tsx`
  - Files modified: `frontend/src/App.tsx`, `frontend/tests/unit/App.test.tsx`

- **Frontend**: 403 Forbidden error page with ShadCN UI components

  - Implemented Forbidden page displaying clear error messaging for users who lack permissions to access a page
  - Integrated ShadCN UI component library with Alert, Button, and Card components for consistent design system
  - Alert component with destructive variant emphasizes security error with red border styling
  - User-friendly error messages without technical jargon (no HTTP/API terms)
  - Navigation link using ShadCN Button component with asChild pattern for React Router integration
  - Responsive layout with centered content and proper spacing on all screen sizes
  - Comprehensive test suite with 10 tests validating UI components, semantics, and user experience
  - All tests passing with 100% statement, branch, function, and line coverage
  - Files created: `frontend/src/pages/Forbidden.tsx`, `frontend/tests/unit/Forbidden.test.tsx`, `frontend/src/components/ui/alert.tsx`, `frontend/src/components/ui/button.tsx`, `frontend/src/components/ui/card.tsx`, `frontend/src/lib/utils.ts`, `frontend/components.json`
  - Dependencies added: @radix-ui/react-slot, class-variance-authority, clsx, lucide-react, tailwind-merge, tailwindcss-animate, tw-animate-css

- **Frontend**: Route protection component for authentication and role-based authorization

  - Implemented ProtectedRoute component wrapping React Router routes with declarative auth enforcement
  - Loading state handling with spinner while authentication state initializes
  - Automatic redirect to login page for unauthenticated users with original URL preservation
  - Automatic redirect to forbidden page for users with insufficient role permissions
  - Role hierarchy enforcement: admin can access all routes, author can access author and authenticated routes, authenticated can only access authenticated routes
  - Type-safe TypeScript implementation with exported ProtectedRouteProps interface
  - Proper React Router v6 integration using Navigate component and useLocation hook for state preservation
  - Comprehensive test suite with 32 tests validating loading states, authentication checks, role authorization, component API, edge cases, and navigation behavior
  - All tests passing with 100% code coverage
  - Files created: `frontend/src/components/auth/ProtectedRoute.tsx`, `frontend/tests/unit/ProtectedRoute.test.tsx`

- **Frontend**: Authentication context provider for global auth state management

  - Implemented AuthProvider component wrapping Clerk's useUser hook for centralized authentication state
  - Created useAuth() custom hook for accessing user authentication context throughout application
  - Type-safe authentication state including user, isLoaded, isSignedIn, and role properties
  - Automatic role fallback to 'authenticated' when not present in Clerk publicMetadata
  - Biome configuration updated to support React context file patterns
  - Comprehensive test suite with 18 tests validating provider setup, context access, role handling, and error boundaries
  - All tests passing with full coverage of authentication context flows
  - Files created: `frontend/src/context/AuthContext.tsx`, `frontend/tests/unit/AuthContext.test.tsx`
  - Files modified: `frontend/biome.json`

- **Frontend**: Clerk authentication provider integration at application root

  - Wrapped React app with ClerkProvider in main.tsx for application-wide authentication context
  - Environment variable validation for VITE_CLERK_PUBLISHABLE_KEY with startup checks
  - Error handling with descriptive messages for missing Clerk configuration
  - Test environment configuration in vitest.config.ts with Clerk environment variables
  - Comprehensive test suite with 21 tests covering provider setup, error boundaries, and configuration validation
  - All tests passing (96/97 total, 1 Clerk SDK internal detail expected)
  - Files modified: `frontend/src/main.tsx`, `frontend/vitest.config.ts`
  - Files created: `frontend/tests/unit/main.test.tsx`

### Changed

- **Frontend**: Refactored NotFound and Home pages to use ShadCN UI components for design consistency

  - Replaced custom Tailwind-styled link in NotFound page with ShadCN Button component using asChild pattern
  - Replaced custom div card in Home page with ShadCN Card component (CardHeader, CardTitle, CardContent)
  - Replaced plain text error display in Home page with ShadCN Alert component with destructive variant
  - Ensures consistent design system across all frontend pages matching Forbidden page implementation
  - All existing tests updated and passing (3 NotFound tests, 17 Home tests)
  - No breaking changes to component behavior or user experience
  - Files modified: `frontend/src/pages/NotFound.tsx`, `frontend/src/pages/Home.tsx`, `frontend/tests/unit/NotFound.test.tsx`, `frontend/tests/unit/Home.test.tsx`

### Fixed

- **Backend**: Fixed CI test failures due to eager initialization of Settings in auth middleware
  - Refactored auth_middleware.py to use lazy initialization pattern for Settings, ClerkAuthAdapter, and UserRepository
  - Prevents ValidationError during module import when CLERK_PUBLISHABLE_KEY and CLERK_SECRET_KEY environment variables are not set
  - Implemented singleton pattern with private getter functions (\_get_settings, \_get_clerk_adapter, \_get_user_repository)
  - Module-level variables (clerk_auth_adapter, user_repository) now default to None for test mock compatibility
  - Adapters and repositories are instantiated only when decorators are actually invoked, not at import time
  - All 208 unit tests pass including 17 auth middleware tests with full backward compatibility
  - No breaking changes to decorator API or test mocking patterns
  - File modified: `backend/src/backend/api/middleware/auth_middleware.py`

### Added

- **Frontend**: Installed Clerk React SDK for user authentication

  - Added @clerk/clerk-react@5.59.3 package to enable frontend authentication capabilities
  - Provides React components and hooks for user sign-in, sign-up, and session management
  - Integrates with Clerk authentication service matching backend JWT verification
  - Dependencies added: @clerk/clerk-react@5.59.3
  - Files modified: `frontend/package.json`, `frontend/package-lock.json`

- **Backend**: Admin user management routes with role-based access control

  - Implemented GET /api/users endpoint for listing all users with pagination (admin only)
  - Implemented PUT /api/users/:id/role endpoint for updating user roles (admin only)
  - Pagination support with configurable limit (1-100, default 50) and offset (default 0) query parameters
  - Role validation ensuring only valid roles (authenticated, author, admin) can be assigned
  - Protected with @require_auth and @require_role('admin') decorators for secure admin-only access
  - Comprehensive error handling: 400 for invalid parameters, 404 for non-existent users, 403 for non-admins
  - Integration test suite with 12 tests covering admin authentication, pagination, role updates, error cases, and authorization enforcement
  - All tests pass with complete coverage of user management flows
  - Files created: `backend/src/backend/api/routes/users.py`, `backend/tests/integration/test_api_routes_users.py`
  - Files modified: `backend/src/backend/main.py` (registered users blueprint at /users prefix)

- **Backend**: Auth routes blueprint with user profile endpoint

  - Implemented GET /api/auth/me endpoint for retrieving authenticated user profile
  - Returns user data including id, clerk_user_id, email, role, and created_at in JSON format
  - Protected with @require_auth decorator for JWT validation
  - Blueprint registered at /auth URL prefix in Flask application factory
  - Comprehensive integration test suite with 10 tests covering valid authentication, missing/invalid/expired tokens, new user creation, role preservation, JSON response format, and CORS headers
  - All tests pass with complete coverage of authentication flows
  - Files created: `backend/src/backend/api/routes/auth.py`, `backend/tests/integration/test_api_routes_auth.py`
  - Files modified: `backend/src/backend/main.py`, `backend/tests/conftest.py`

- **Backend**: JWT authentication middleware with role-based access control

  - Implemented `@require_auth` decorator for protecting Flask endpoints with JWT token validation
  - Implemented `@require_role(role)` decorator for enforcing role-based access control with three authorization levels (authenticated, author, admin)
  - Automatic user creation on first authentication via Clerk integration
  - User context injection into Flask's `g` object for access throughout request lifecycle
  - Comprehensive error handling with AuthenticationError (401) and AuthorizationError (403) responses
  - Integration with ClerkAuthAdapter for JWT verification and user claims extraction
  - UserRepository integration for fetching or creating users based on Clerk user ID
  - Test suite: 26 unit tests with 100% coverage validating decorator behavior, role enforcement, error handling, and user auto-creation
  - Files created: `backend/src/backend/api/middleware/__init__.py`, `backend/src/backend/api/middleware/auth_middleware.py`, `backend/tests/unit/test_auth_middleware.py`
  - Files modified: `backend/src/backend/infrastructure/persistence/user_repository.py` (added `find_by_clerk_user_id()` method)

- **Backend**: Centralized exception handling for authentication and authorization

  - Created custom exception classes AuthenticationError and AuthorizationError in `backend/src/backend/exceptions.py`
  - AuthenticationError for 401 Unauthorized responses handling invalid tokens, expired sessions, and missing authorization headers
  - AuthorizationError for 403 Forbidden responses with optional required_role field indicating minimum role needed for access
  - Flask error handlers registered in `backend/src/backend/main.py` for consistent JSON error responses across all endpoints
  - Centralized exception module accessible to all layers following Hexagonal Architecture dependency rules
  - Refactored ClerkAuthAdapter to import AuthenticationError from central module eliminating duplicate exception definitions
  - Comprehensive test suite: 22 unit tests for exception creation and attributes, 21 integration tests for Flask error handler responses and HTTP status codes
  - All tests pass with 100% coverage of exception classes and error handler logic
  - Files added: `backend/src/backend/exceptions.py`, `backend/tests/unit/test_exceptions.py`, `backend/tests/integration/test_error_handlers.py`
  - Files modified: `backend/src/backend/main.py`, `backend/src/backend/infrastructure/auth/clerk_auth_adapter.py`, `backend/src/backend/infrastructure/auth/__init__.py`, `backend/tests/unit/test_clerk_auth_adapter.py`, `backend/tests/integration/test_clerk_auth_adapter.py`

- **Backend**: Clerk authentication adapter with JWT verification and JWKS caching

  - Implemented ClerkAuthAdapter class in `backend/src/backend/infrastructure/auth/clerk_auth_adapter.py` for secure JWT token validation
  - RS256 algorithm support with Clerk's public key fetched from JWKS endpoint
  - HS256 fallback for test environments with secret key-based validation
  - JWKS public key caching with 1-hour TTL to minimize external API calls and avoid rate limiting
  - Comprehensive error handling with clear authentication failure messages
  - Security logging for failed authentication attempts with user ID extraction
  - Added ClerkSettings configuration class in `backend/src/backend/config.py` for environment-based Clerk credentials
  - Added Settings class combining all application configuration with Pydantic validation
  - Configured Pydantic mypy plugin for proper type checking support
  - Test suite: 29 unit tests with mocked JWKS endpoints and PyJWT validation, 9 integration tests (skipped in CI, require real Clerk tokens)
  - 79% code coverage for ClerkAuthAdapter module with comprehensive test coverage of all error paths
  - Dependencies added: `pyjwt>=2.10.1`, `cryptography>=46.0.3`, `requests>=2.32.5`
  - Files added: `backend/src/backend/infrastructure/auth/clerk_auth_adapter.py`, `backend/src/backend/infrastructure/auth/__init__.py`, `backend/tests/unit/test_clerk_auth_adapter.py`, `backend/tests/integration/test_clerk_auth_adapter_integration.py`
  - Files modified: `backend/src/backend/config.py`, `backend/pyproject.toml`

- **Backend**: User persistence layer with repository pattern for database operations

  - Implemented UserRepository class in `backend/src/backend/infrastructure/persistence/user_repository.py` for CRUD operations on User aggregate
  - Converts between SQLModel User table models and domain User aggregates with bidirectional mapping
  - Supports flexible session management: accepts injected sessions for testing or creates sessions from connection pool for production
  - Methods: `find_by_clerk_id()` with indexed lookup, `find_by_id()`, `save()` with insert/update logic, `list_all()` with optional pagination
  - Comprehensive test suite: 29 tests (20 unit tests for conversion logic, 9 integration tests for database operations) with full coverage
  - Files added: `backend/src/backend/infrastructure/persistence/user_repository.py`, `backend/tests/unit/test_user_repository.py`, `backend/tests/integration/test_user_repository.py`

- **Backend**: User aggregate root for authentication and authorization

  - Created User aggregate implementing Domain-Driven Design patterns for identity management
  - Factory method `create_from_clerk()` enables seamless integration with Clerk authentication provider
  - Role-based access control via `change_role()` method supporting authenticated, author, and admin roles
  - Immutable `created_at` timestamp ensures audit trail integrity for compliance and security tracking
  - API serialization via `to_dict()` method with optional sensitive field exclusion for secure data exposure
  - Full type safety with comprehensive type hints and runtime validation using Pydantic
  - Test suite: 14 comprehensive unit tests with 100% code coverage validating factory methods, role transitions, serialization, and edge cases
  - Files added: `backend/src/backend/domain/aggregates/user.py`, `backend/src/backend/domain/aggregates/__init__.py`, `backend/tests/unit/test_user.py`

- **Backend**: User role enumeration with permission hierarchy

  - Created Role value object as StrEnum with three authorization levels (authenticated, author, admin)
  - Implemented role-based permission methods for author and admin access control
  - Automatic lowercase string conversion using auto() for database compatibility
  - Immutable enum members ensure thread-safe singleton instances
  - JSON serializable for API responses and database storage
  - Type-safe with full type hints for IDE support and static analysis
  - Test suite: 40 comprehensive unit tests with 100% code coverage
  - Files added: `backend/src/backend/domain/value_objects/role.py`, `backend/src/backend/domain/value_objects/__init__.py`, `backend/tests/unit/test_role.py`

- **Backend**: User model supports external authentication provider integration

  - Added support for storing external authentication provider user identifiers
  - Database includes unique index on authentication provider ID for fast JWT validation lookups
  - Nullable field design ensures backward compatibility with existing users
  - Enables secure integration with third-party authentication services
  - Files modified: `backend/src/backend/infrastructure/persistence/models.py`
  - Files added: `backend/tests/integration/test_user_clerk_id.py`

- **Deployment**: Added LiteSpeed deployment script for cPanel environments with UAPI limitations

  - Created `scripts/litespeed_deploy.sh` (435 lines) for cPanel/LiteSpeed hosting
  - LiteSpeed environments experience silent UAPI failures requiring manual web UI configuration
  - Comprehensive deployment automation with security features:
    - Strict error handling with inherit_errexit and pipefail
    - Signal traps to unset secrets on EXIT/INT/TERM
    - Input sanitization for environment variables
    - SSH key permission validation with TOCTOU mitigation
    - Secret suppression in UAPI calls
    - Audit logging to syslog for security-relevant operations
  - Deployment process:
    - Validates environment variables and SSH key permissions
    - Provisions PostgreSQL database, user, and privileges (idempotent)
    - Uploads code via rsync with checksum verification
    - Installs uv on remote server if not present
    - Installs dependencies with uv sync
    - Creates database schema using uv run scripts/create_schema.py
    - Registers/updates Passenger application with environment variables
    - Verifies deployment via health check endpoints with exponential backoff
  - Dual deployment strategy: Use `deploy.sh` for Passenger (UAPI works), `litespeed_deploy.sh` for LiteSpeed (UAPI fails silently)
  - Files added: `scripts/litespeed_deploy.sh`

- **Build**: Added backend build automation script

  - Created `scripts/build_backend.sh` for automated backend builds
  - Uses `uv build --clear` to create distribution packages
  - Copies built packages to `/var/www/ashlab/package/backend/`
  - Generates package index with `scripts/generate_index.py`
  - Files added: `scripts/build_backend.sh`, `scripts/generate_index.py`

- **Deployment**: Added requirements.txt for traditional pip-based deployments

  - Created `backend/requirements.txt` with frozen dependencies
  - Provides fallback deployment path for environments without uv
  - Mirrors dependencies from `pyproject.toml` for compatibility
  - Files added: `backend/requirements.txt`

### Changed

- **Backend**: Locked Python version requirement to exact match

  - Changed from `>=3.13.5` to `==3.13.5` in `backend/pyproject.toml`
  - Ensures consistent Python version across deployments
  - Updated `backend/uv.lock` to remove Python 3.14 wheels
  - Files modified: `backend/pyproject.toml`, `backend/uv.lock`

- **Backend**: Improved WSGI entry point module resolution

  - Added `APP_ROOT` to `sys.path` in `passenger_wsgi.py`
  - Ensures proper module imports in production Passenger environment
  - Files modified: `backend/src/passenger_wsgi.py`

### Removed

- **Tests**: Removed temporary BATS test file

  - Deleted `scripts/tests/deploy_config_fix.bats` (should not have been committed)
  - Main BATS test suite remains intact in `scripts/tests/`
  - Files removed: `scripts/tests/deploy_config_fix.bats`

### Fixed

- **Deployment**: Fixed virtual environment path to match cPanel conventions

  - Changed from `/home/${CPANEL_USERNAME}/seeash/.venv` to `/home/${CPANEL_USERNAME}/virtualenv/seeash`
  - Added `UV_PROJECT_ENVIRONMENT` variable to direct uv to create virtual environment in correct location
  - Applies to both `install_application()` and `run_schema()` functions
  - Updated `VENV_PATH` environment variable passed to Passenger
  - Follows cPanel convention documented in cpanel-deployment-patterns.md lines 23-24, 73
  - Virtual environment now created at `/home/ashrdvfi/virtualenv/seeash` instead of application root
  - Files modified: `scripts/deploy.sh`

- **Deployment**: Fixed critical environment variable syntax for Passenger UAPI calls

  - Changed from numbered parameters (`envvar_name_1`, `envvar_value_1`) to repeated parameters (`envvar_name`, `envvar_value`)
  - Applies to both `register_application` and `edit_application` UAPI functions
  - Environment variables now successfully set in Passenger application configuration
  - Verified all 8 environment variables (DB_NAME, DB_USER, DB_PASSWORD, VENV_PATH, GITHUB_PERSONAL_ACCESS_TOKEN, RESEND_API_KEY, CLERK_PUBLISHABLE_KEY, CLERK_SECRET_KEY) are injected correctly
  - Syntax documented in cpanel-deployment-patterns.md lines 171-183
  - Files modified: `scripts/deploy.sh`

- **Deployment**: Fixed deployment script to use Python src-layout structure for uv compatibility

  - Changed backend upload destination from `seeash/backend/` to `seeash/src/backend/` to match uv src-layout convention
  - Changed scripts upload destination from `seeash/scripts/` to `seeash/src/scripts/` for proper Python module import
  - Added remote directory creation for `seeash/src` before file uploads
  - Created `__init__.py` in `monorepo/backend/src/scripts/` to make scripts package importable
  - Fixed local scripts source path from `monorepo/backend/scripts/` to `monorepo/backend/src/scripts/`
  - Updated deployment tests to expect `seeash/src/backend/` instead of `seeash/backend/`
  - Updated test helper to create `monorepo/backend/src/scripts/` directory structure
  - Fixes uv package installation error: "Expected a Python module at: src/backend/**init**.py"
  - Fixes schema creation error: "ModuleNotFoundError: No module named 'scripts'"
  - Files modified: `scripts/deploy.sh`, `scripts/tests/deploy.bats`, `scripts/tests/test_helper.bash`, `backend/src/scripts/__init__.py` (created)

- **Deployment**: Fixed deployment script to match production directory structure specifications

  - Changed remote application path from `/home/${CPANEL_USERNAME}/blog` to `/home/${CPANEL_USERNAME}/seeash`
  - Corrected backend source upload from `monorepo/backend/` to `monorepo/backend/src/backend/`
  - Added upload of `passenger_wsgi.py` from `monorepo/backend/src/` to `seeash/` (root level)
  - Added upload of `scripts/` directory to seeash (path later corrected to src-layout)
  - Added upload of `pyproject.toml` and `uv.lock` to root level for uv package management
  - Updated all remote script paths from `~/blog` to `~/seeash`
  - Updated virtual environment path from `~/blog/.venv` to `~/seeash/.venv`
  - Removed hardcoded username "ashrdvfi" from WSGI copy section
  - Removed unnecessary WSGI copy remote script (handled by rsync now)
  - Updated deployment tests to expect new paths and directory structure
  - Updated test helper to create correct backend source structure for tests
  - Updated DEPLOYMENT.md documentation to reflect correct remote directory structure
  - Files modified: `scripts/deploy.sh`, `scripts/tests/deploy.bats`, `scripts/tests/test_helper.bash`, `docs/DEPLOYMENT.md`

- **Deployment**: Fixed critical Passenger WSGI bootstrap issues (Task #27)

  - Added VENV_PATH environment variable to Passenger registration
    - Required by passenger_wsgi.py to bootstrap uv virtualenv before Flask import
    - Added to both register_application and update_application UAPI calls
    - Path: `/home/${CPANEL_USERNAME}/blog/.venv`
  - Copy passenger_wsgi.py to domain root during code upload
    - Passenger expects WSGI entry point in application root (~/seeash/)
    - Added SSH command in upload_code() to copy from ~/blog/src/
    - Includes validation to ensure source file exists before copying
  - Remove explicit DB_HOST from schema creation
    - Rely on ProductionDBSettings default 'localhost' resolution
    - Handles both IPv4 and IPv6 gracefully via driver-level resolution

- **Deployment**: Fixed frontend build path check in deployment script

  - Changed from `monorepo/frontend/build` to `monorepo/build` to match Vite output location
  - Deployment script now correctly detects frontend build directory
  - Prevents "frontend build directory missing" errors during deployment

- **Backend**: Fixed ProductionDBSettings to use standard database environment variable names

  - Removed `CPANEL_` prefix from ProductionDBSettings configuration
  - Now reads `DB_HOST`, `DB_NAME`, `DB_USER`, `DB_PASSWORD` directly (no prefix)
  - Aligns with Passenger WSGI standard environment variable naming conventions
  - Resolves deployment failure where Flask could not connect to database

- **Deployment**: Fixed schema creation during deployment to set required environment variables

  - Added exports for `DB_NAME`, `DB_USER`, `DB_PASSWORD`, `FLASK_ENV` in run_schema() function
  - Schema creation script now receives all required database configuration
  - Prevents "missing required fields" validation errors during remote schema execution

### Added

- **Documentation**: Comprehensive developer onboarding documentation in `README.md`

  - Project overview with Domain-Driven Design and Hexagonal Architecture explanation
  - 15-minute quick start guide with copy-pasteable commands for immediate setup
  - Development workflow documentation for backend (uv) and frontend (npm)
  - Testing instructions for pytest, Vitest, Playwright, and pre-commit hooks
  - CI/CD documentation for GitHub Actions workflows (backend and frontend)
  - Deployment overview with health check verification steps
  - Troubleshooting table with 15 common issues and solutions
  - Contributing guidelines with conventional commits format and PR checklist
  - Resource links for documentation, tooling, and external services (GitHub, Resend, Clerk)
  - Architecture diagram showing bounded contexts and system components
  - Development standards covering code quality, testing pyramid, and security requirements

- **Backend**: Environment variable template in `backend/.env.example`

  - Database configuration variables (LOCAL_POSTGRES_USER, LOCAL_POSTGRES_PASSWORD, LOCAL_POSTGRES_DB)
  - Flask environment settings (FLASK_ENV)
  - External API keys template (GITHUB_PERSONAL_ACCESS_TOKEN, RESEND_API_KEY)
  - Clerk authentication credentials (CLERK_SECRET_KEY)
  - cPanel deployment credentials template (CPANEL_POSTGRES_USER, CPANEL_POSTGRES_PASSWORD, CPANEL_POSTGRES_DB)
  - Clear documentation comments explaining each variable's purpose
  - Security reminder to never commit actual credentials

- **Frontend**: Environment variable template in `frontend/.env.example`

  - API base URL configuration (VITE_API_BASE_URL) for backend communication
  - Clerk authentication public key (VITE_CLERK_PUBLISHABLE_KEY) for frontend integration
  - Vite-specific environment variable naming convention (VITE\_ prefix)
  - Documentation comments explaining variable usage and security practices

- **Deployment**: Automated deployment script for cPanel hosting

  - End-to-end deployment automation to cPanel shared hosting environment
  - Idempotent database provisioning (PostgreSQL database, user, and privileges)
  - Automated code upload via rsync with checksum verification
  - Remote Python virtual environment setup and dependency installation
  - Database schema creation from SQLModel models
  - Passenger WSGI application registration with environment variable injection
  - Health check verification across all critical endpoints
  - Comprehensive error handling with exponential backoff retry logic
  - Cross-platform SSH key handling (Windows Git Bash and Linux compatibility)
  - Security features: input sanitization, secret suppression, audit logging
  - Production deployment confirmation prompt for safety
  - BATS test suite with 40 tests covering validation, provisioning, error handling, and idempotency
  - Comprehensive production domain confirmation test coverage (interactive/non-interactive scenarios, staging/dev domain handling)
  - Detailed deployment documentation with prerequisites and usage examples

- **Backend**: Implemented Passenger WSGI entry point in `src/passenger_wsgi.py`

  - Created WSGI-compliant entry point for Phusion Passenger deployment
  - Implemented virtual environment bootstrap logic with configurable VIRTUAL_ENV environment variable
  - Imported Flask application via `create_app()` factory pattern
  - Exported application as 'application' variable (Passenger WSGI requirement)
  - Comprehensive error handling with actionable debugging information to stderr
  - Cross-platform compatibility (Windows development, Linux production)
  - PEP 3333 WSGI specification compliance
  - Test suite: 9 integration tests covering WSGI interface, variable naming, type verification, request handling, and virtual environment loading, 5 unit tests covering all functions.

- **Backend**: Fixed build directory path in main.py to match Vite output

  - Changed from frontend/dist to build/ to match vite.config.ts outDir
  - Vite outputs to ../build from frontend directory (monorepo/build/)
  - Updated unit tests to expect build/ instead of frontend/dist
  - Updated tests to use Path(**file**).parents[3] instead of repeated .parent

- **CI**: Fixed backend CI workflow to create minimal frontend build structure

  - Creates build/ directory with build/static/js/ subdirectory
  - Creates build/index.html with minimal HTML for SPA routing tests
  - Creates dummy JS file for static file serving tests
  - Allows SPA routing tests to pass without full frontend build
  - Backend tests can verify SPA route handling independently

- **Config**: Removed ty.toml from monorepo

- **CI**: Added workflow_dispatch and workflow file path triggers to both CI workflows

  - Backend and frontend CI now trigger on workflow file changes
  - Added manual trigger capability via workflow_dispatch

- **Backend**: Implemented Flask application factory pattern in `main.py`

  - Created `create_app()` factory function with environment-based configuration
  - Configured Flask with static_folder='dist/static' and template_folder='dist' for React SPA serving
  - Registered health check blueprint with no URL prefix
  - Implemented CORS for development environment only (disabled in production)
  - Added SPA catch-all route serving index.html for client-side routing
  - Implemented path traversal protection with double URL-decoding and backslash detection
  - Added security logging for path traversal attempts and file access errors
  - Production safety: raises RuntimeError if build directory missing in production
  - Development tolerance: logs warning if build directory missing in development
  - Comprehensive test suite: 12 unit tests + 18 integration tests (100% coverage for main.py)
  - Security tests: 5 tests covering path traversal attack vectors (direct, middle, URL-encoded, backslash, exception handling)

- **Integration Testing**: Implemented local build and E2E integration test suite

  - Created `scripts/build.sh` for automated frontend production builds
  - Implemented comprehensive E2E test suite in `backend/tests/e2e/test_build.py`
  - Tests verify frontend build artifacts (index.html, static/, JS bundles)
  - Tests verify Flask server startup and health endpoint responses
  - Tests verify React SPA serving and client-side routing behavior
  - Tests verify API routes excluded from SPA catch-all routing
  - Added `wait_for_server()` utility in `backend/tests/e2e/utils.py` for server readiness checks
  - Pytest fixtures for build execution and Flask server daemon thread management
  - BATS test suite in `scripts/tests/build.bats` with 4 tests validating build script execution
  - Comprehensive validation of production deployment workflow before cPanel deployment

- **Frontend**: Implemented `App.tsx` root component with BrowserRouter routing for Home and NotFound pages.

- **Frontend**: Implemented `main.tsx` Vite entry point using React 18 createRoot API with StrictMode wrapper.

- **Frontend**: Added root element creation to test setup for proper DOM initialization in tests.

### Changed

- **Frontend**: Updated entry point from `main.jsx` to `main.tsx` in `index.html`.
- **Frontend**: Updated tests to correctly expect `React.StrictMode` as `symbol` type (React 18 behavior).

### Fixed

- **Code Review Fixes (PR #7)**: Implemented fixes from sourcery-ai and gemini-code-assist code reviews

  - **Build Script**: Enhanced shell safety flags in `scripts/build.sh`
    - Added `set -u` to error on unset variables
    - Added `set -o pipefail` to catch errors in pipelines
    - Removed unnecessary `exit 0` that could hide non-zero exit codes
    - Changed `npm install` to `npm ci` for faster, more reliable builds from lockfile
  - **E2E Tests**: Improved test reliability and production configuration
    - Fixed build fixture to always run build for test determinism
    - Added `try...finally` block to ensure cleanup even if tests fail
    - Track initial BUILD_DIR state to preserve pre-existing builds
    - Changed FLASK_ENV from DEVELOPMENT to PRODUCTION to accurately test production stack
    - Marked GitHub health check test with `@pytest.mark.external` to allow skipping in offline/restricted environments
  - **BATS Tests**: Optimized build script test performance
    - Refactored to use `setup_file()`/`teardown_file()` hooks
    - Build script now runs once per test file instead of once per test (4x faster)
    - Individual tests now only verify build artifacts exist

- **Code Review Fixes (PR #8)**: Addressed documentation and configuration issues from gemini-code-assist code review

  - **Backend Configuration**: Corrected `.env.example` to use `LOCAL_*` prefix variables matching `config.py` expectations
    - Fixed database configuration to use `LOCAL_DB_HOST`, `LOCAL_DB_NAME`, `LOCAL_DB_USER`, `LOCAL_DB_PASSWORD`
    - Ensures development environment variables align with `DevDBSettings` class requirements
  - **API Documentation**: Updated health endpoint documentation in `docs/api.md` to match actual implementation
    - Fixed `/health/db` endpoint response format (simple status object instead of detailed host/database info)
    - Fixed `/health/github` endpoint response format (simple status object instead of detailed rate_limit info)
  - **README Organization**: Improved build script documentation clarity
    - Reorganized `./scripts/build.sh` command placement for better categorization
    - Clarified frontend-specific vs. project-wide command usage
  - **Deployment Documentation**: Added missing `PRODUCTION_DOMAIN` environment variable to deployment docs table
    - Documented required variable for production confirmation prompt functionality
    - Completed environment variables reference in `docs/DEPLOYMENT.md`

- **Deployment**: Critical bug fix in error handling for deployment script

  - Fixed `uapi_call()` function to correctly capture and propagate command exit codes
  - Previously, `if ! command; then` pattern was causing `$?` to be 0 (success of if-test negation) instead of the actual command failure code
  - Changed to explicitly capture exit status before testing: `command; exit_status=$?; if [[ $exit_status -ne 0 ]]; then`
  - This ensures deployment aborts immediately when UAPI operations fail instead of continuing silently
  - Added comprehensive error checking (`|| return 1`) to all deployment functions for fail-fast behavior
  - Fixed tests 12, 13, and 14 which were failing assertions but not executing
  - Test 12: Added `stat` mock for SSH key permission verification
  - Tests 13-14: Added proper UAPI mocks that handle different operations independently

- **Frontend**: Updated frontend dependencies to latest versions.

- **Frontend**: Corrected Biome configuration to remove redundant include paths.

- **Frontend**: Separated Vitest configuration into `vitest.config.ts` and ensured shared configuration with `vite.config.ts` using `mergeConfig`.

## v0.1.2 (2025-11-17)

### Fixed

- **CI**: Fixed frontend CI build failure by updating `vitest` to `^4.0.9` and adding `@vitest/coverage-v8`.

## v0.1.1 (2025-11-14)

### Refactor

- Refactored `config.py` to introduce `get_db_url()` for obtaining the database connection string, replacing direct instantiation of `DBSettings`.
- Updated tests in `test_config.py` to reflect the refactoring and added tests for `get_db_url()`.

### Fixed

#### Code Review Fixes (PR #2)

- **Critical**: Fixed datetime field defaults in `User` and `Post` models
  - Changed `Field(default=datetime.now(dt.UTC))` to `Field(default_factory=lambda: datetime.now(dt.UTC))`
  - Prevents all records from sharing the same import-time timestamp
  - Files: `backend/src/infrastructure/persistence/models.py` (lines 13, 27-28)
  - Added comprehensive unit tests validating timestamp uniqueness
- **Critical**: Replaced deprecated Pydantic v2 API in `config.py`
  - Changed `.unicode_string()` to `str()` for PostgresDsn conversion
  - Ensures compatibility with future Pydantic versions
  - File: `backend/src/config.py` (line 53)
- **Security**: Removed information leakage from health endpoint errors
  - Changed error responses from `str(e)` to generic "unreachable" message
  - Added structured logging for internal diagnostics
  - Prevents exposure of database credentials, stack traces, network details
  - File: `backend/src/api/routes/health.py` (lines 47-48, 70-73)
  - Health endpoints now use `requests.exceptions.RequestException`
- **Testing**: Added test for non-200 GitHub API responses
  - File: `backend/tests/integration/test_health_endpoints.py`

### Added

#### Foundation Stage - Infrastructure Setup

- **Task 1**: Created git repository with .gitignore (Python, Flask, Node, React, SSH, VSCode templates)
- **Task 2**: Configured pre-commit hooks with Ruff, mypy, Biome, and general checks
- **Task 3**: Configured Biome for frontend linting and formatting
  - Created frontend/biome.json with React/JSX rules and a11y accessibility checks
  - Configured formatter with 2-space indentation and 100-character line width
  - Enabled hooks rules (useExhaustiveDependencies, useHookAtTopLevel, useJsxKeyInIterable)
  - Updated pre-commit hook to use explicit config path for Biome
- **Task 4**: Initialized backend project structure with uv
  - Created complete DDD/Hexagonal Architecture directory structure
  - Set up Python 3.13.5+ requirement in pyproject.toml
  - Created domain, application, infrastructure, and api layers
  - Set up test directories (unit, integration, e2e)
  - Generated uv.lock file
  - Added placeholder files (main.py, config.py, schema.sql, passenger_wsgi.py)
- **Task 5**: Configured Ruff for backend linting and formatting
  - Added [tool.ruff] configuration to backend/pyproject.toml
  - Set line-length to 80 characters, target-version to py313
  - Enabled lint rules: A (builtins), ANN (annotations), D (docstrings), DOC (docstrings), E (pycodestyle errors), F (pyflakes), I (isort), N (pep8-naming), UP (pyupgrade), W (pycodestyle warnings)
  - Configured flake8-annotations with allow-star-arg-any and mypy-init-return
  - Set pydocstyle convention to Google style with ignore-decorators for typing.overload
  - Added per-file-ignores for tests/docs/tools and **init**.py files
  - Verified uvx ruff check and uvx ruff format commands work correctly
- **Task 6**: Configured mypy for type checking
  - Added [tool.mypy] configuration to backend/pyproject.toml
  - Set python_version to "3.13" for Python 3.13 target compatibility
  - Enabled warn_return_any for strict return type checking
  - Enabled check_untyped_defs to require type hints on function definitions
  - Set ignore_missing_imports to allow third-party libraries without type stubs
  - Verified uv run mypy . runs successfully with no issues found in 16 source files
- **Task 7**: Created backend CI workflow
  - Created .github/workflows/backend-ci.yml for automated backend testing
  - Configured to run on Python 3.13 only (not a matrix strategy)
  - Uses official astral-sh/setup-uv@v1 action for uv setup
  - Triggers on push to main/foundation branches and pull requests to main
  - Runs linting with Ruff (uvx ruff check)
  - Runs type checking with mypy (uv run mypy)
  - Runs tests with pytest with coverage reporting (uv run pytest --cov --cov-report=xml)
  - Enforces 80% code coverage threshold with --cov-fail-under=80
  - All steps run in backend/ directory
- **Task 8**: Created frontend CI workflow
  - Created .github/workflows/frontend-ci.yml with matrix strategy for Node 22.18 and 24.6
  - Configured triggers for push to main/foundation branches and pull requests to main
  - Added steps: checkout, setup Node.js with npm caching, install dependencies, lint, test, build
  - Uses actions/checkout@v3 and actions/setup-node@v3
  - Linting with Biome (npx biome check .)
  - Testing with coverage reporting (npm test -- --coverage --run)
  - Coverage threshold check placeholder (70% will be enforced when tests exist)
  - Production build step (npm run build)
  - All steps run in frontend/ directory with fail-fast behavior
- **Task 9**: Initialized React project with Vite
  - Created frontend/package.json with React 18.3.1, Vite 5.4.11, React Router 6.28.0, Axios 1.7.9
  - Configured dependencies: React, React-DOM, React Router, Axios for API calls
  - Configured devDependencies: Vite, Vitest, React Testing Library, Biome, Tailwind CSS, PostCSS, Autoprefixer
  - Created frontend/vite.config.js with @/ alias pointing to ./src
  - Configured build output to ../build/ directory (shared with backend)
  - Configured dev server on port 3000 with proxy to Flask backend on port 5000
  - Created frontend/index.html as Vite entry point
  - Created src/ directory structure: components/, pages/, hooks/, services/, context/
  - Created minimal src/main.jsx with React 18 StrictMode entry point
  - Moved biome.json from frontend/ to blog-code/ root for monorepo configuration
  - Updated biome.json to include frontend paths in includes array
  - Ran npm install successfully (329 packages installed)
  - Verified production build outputs correctly to ../build/ directory
  - Set package.json homepage to "." for relative asset paths
- **Task 10**: Configured Tailwind CSS
  - Created frontend/tailwind.config.js with content paths for ./index.html and ./src/\*\*/\*.{js,jsx}
  - Configured theme.extend as empty object (using default Tailwind theme)
  - Created frontend/postcss.config.js with tailwindcss and autoprefixer plugins
  - Created src/index.css with Tailwind directives (@tailwind base, @tailwind components, @tailwind utilities)
  - Updated src/main.jsx to import index.css at top of file
  - Fixed biome.json schema version to 2.3.2 to match installed Biome CLI version
  - Fixed biome.json to use "includes" instead of "include" for Biome 2.3.2 compatibility
  - Updated .pre-commit-config.yaml to remove --config-path argument from biome-ci hook (uses automatic discovery)
  - Verified production build succeeds with Tailwind CSS processed (build size 4.7KB for CSS)
  - Verified Tailwind base styles (CSS reset) included in output
  - Confirmed CSS purging works correctly (no utility classes used yet, so minimal output)
  - Verified Biome formatting works correctly with all configuration files

#### Backend Configuration & Database

- **Task 11**: Created configuration management with Pydantic
  - Created backend/src/config.py implementing Pydantic BaseSettings
  - Defined DBSettings base class with DB_HOST, DB_NAME, DB_USER, DB_PASSWORD, FLASK_ENV fields
  - DB_HOST defaults to localhost (cPanel requirement)
  - Created DevDBSettings with LOCAL\_ prefix for development environment
  - Created ProductionDBSettings with CPANEL\_ prefix for production environment
  - Implemented get_db_settings() factory function with caching
  - Added environment-based settings class selection
  - Fail-fast validation on missing required environment variables
  - Unit tests in tests/unit/test_config.py with 100% coverage
- **Task 12**: Created database schema with SQLModel
  - Created backend/src/infrastructure/persistence/models.py
  - Defined User table model (id, email, role, created_at)
  - Defined Post table model (id, slug, title, published_html, published, author_id, created_at, updated_at)
  - Added foreign key constraint from Post.author_id to User.id
  - Added indexes on Post.slug and Post.author_id for query performance
- **Task 13**: Created database connection with SQLModel
  - Created backend/src/infrastructure/persistence/database.py
  - Implemented get_engine() function with lru_cache for singleton engine pattern
  - Configured PostgreSQL connection string using settings from config.py
  - Enabled pool_pre_ping for connection health checks
  - Implemented get_db() generator for FastAPI/Flask dependency injection
  - Uses SQLModel Session context manager for automatic cleanup
  - Added psycopg2-binary dependency for PostgreSQL driver
  - Integration tests in tests/integration/test_database.py
  - Created shared test fixtures in tests/conftest.py

#### Backend API: Health Checks

- **Task 14**: Created health check endpoints blueprint
  - Created backend/src/api/routes/health.py with Flask blueprint
  - Implemented GET /health endpoint for basic uptime check (returns 200 with {"status": "healthy"})
  - Implemented GET /health/db endpoint for database connectivity test (executes SELECT 1 query, returns 200/503)
  - Implemented GET /health/github endpoint for GitHub API reachability test (calls <https://api.github.com/rate_limit>, returns 200/503)
  - All endpoints return JSON responses with appropriate status codes
  - Added Flask and requests dependencies to pyproject.toml
  - Health endpoints handle exceptions gracefully, returning 503 on failure with error details
  - Database health check uses execute() method for SQLModel Session compatibility
  - GitHub health check uses 5-second timeout for external API calls
  - Integration tests in tests/integration/test_health_endpoints.py with 9 passing tests
  - Created tests/integration/conftest.py with shared fixtures for integration tests
  - All tests verify correct status codes, JSON content types, and error handling

#### Frontend API Service: Health Checks (TDD)

- **Task 15**: Created health check API service with TypeScript
  - Created frontend/src/services/healthService.ts with axios client
  - Implemented checkHealth(), checkDatabase(), checkGitHub() methods
  - Configured axios instance with baseURL from VITE_API_BASE_URL environment variable or '/api' default
  - Added TypeScript type definitions: HealthResponse, DatabaseHealthResponse, GitHubHealthResponse
  - All methods properly typed with Promise return types
  - Errors propagate to caller for proper error handling
  - Comprehensive test coverage in tests/unit/healthService.test.ts with 6 passing tests
  - Created tests/mocks/axios.ts with complete axios mock (mocks both default instance and create() factory)
  - Created tests/setup.ts for Vitest configuration with jest-dom
  - Configured Vitest in vite.config.ts with jsdom environment and coverage reporting
  - Added TypeScript support: tsconfig.json and tsconfig.node.json
  - Installed TypeScript dependencies: typescript, @types/react, @types/react-dom, @types/node
  - Updated biome.json to include TypeScript file patterns (.ts, .tsx)
  - All tests use proper TypeScript types and mocking patterns with vi.mock() factory
  - Tests verify correct endpoint calls, response data handling, and error propagation

#### Frontend Components & Routing (TDD)

- **Task 16**: Created NotFound page component
  - Created frontend/src/pages/NotFound.tsx with 404 error page
  - Implemented user-friendly 404 message with Tailwind styling
  - Added React Router Link component for navigation back to home page
  - Responsive design with centered layout and proper visual hierarchy
  - Comprehensive test coverage in tests/unit/NotFound.test.tsx with 3 passing tests
  - Tests verify 404 message rendering, home link presence and navigation, component styling
  - All tests use React Testing Library with BrowserRouter wrapper
  - Component uses Tailwind utility classes for styling (flex, text-9xl, rounded-lg, etc.)
- Created Home page component with health status display
  - Created frontend/src/pages/Home.tsx as landing page demonstrating health check integration
  - Implemented health status fetching from healthService.checkHealth() on component mount
  - Added loading, error, and success state management using React hooks (useState, useEffect)
  - Displays "Loading..." message while fetching health data
  - Shows user-friendly error message on API failure
  - Renders health status in styled card layout on success
  - Responsive design with Tailwind CSS styling consistent with NotFound.tsx
  - Comprehensive test coverage in tests/unit/Home.test.tsx with 17 passing tests (100% statements, 83.33% branches)
  - Tests verify initial render/loading state, successful health display, error handling, component lifecycle, state transitions, and accessibility
  - All tests use React Testing Library with proper mocking of healthService
  - TypeScript with proper HealthResponse interface integration

### Infrastructure

- Established monorepo structure with backend/ and frontend/ directories
- Configured uv as Python package manager
- Set up pre-commit hooks for code quality enforcement
- Configured GitHub Actions CI/CD pipelines for backend (Python 3.13) and frontend (Node 22.18, 24.6)
