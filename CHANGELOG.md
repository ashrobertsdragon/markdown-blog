# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Fixed

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
  - Added exports for `DB_HOST`, `DB_NAME`, `DB_USER`, `DB_PASSWORD`, `FLASK_ENV` in run_schema() function
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
