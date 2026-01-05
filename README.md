# Flask + React Blog Platform

A modern blog platform combining Domain-Driven Design principles with a dual-storage architecture. Draft posts exist as version-controlled markdown files synced to GitHub, while published content is cached in PostgreSQL for high performance.

## Table of Contents

- [Overview](#overview)
- [Quick Start](#quick-start)
- [Development](#development)
- [Testing](#testing)
- [Deployment](#deployment)
- [Troubleshooting](#troubleshooting)

## Overview

### Key Features

- **Dual Storage**: Markdown drafts on the filesystem with GitHub sync; published HTML in PostgreSQL.
- **Domain-Driven Design**: Organized into 5 bounded contexts (Content, Version Control, Discussion, Notification, Identity).
- **Hexagonal Architecture**: A clean separation between domain logic and infrastructure.
- **Real-time Version Control**: Every save commits to the GitHub API for a complete revision history.
- **Test-Driven Development**: High test coverage with a comprehensive test pyramid.
- **Modern Stack**: Flask, React, TypeScript, Tailwind CSS, and Clerk for authentication.

### Tech Stack

| Layer | Technology | Purpose |
| :--- | :--- | :--- |
| **Frontend** | React 18 + Vite | UI framework and build tool |
| **Styling** | Tailwind CSS | Utility-first styling |
| **Backend** | Flask 3.0+ | REST API server |
| **Language** | Python 3.13 | Backend runtime |
| **Database** | PostgreSQL | Persistent storage for published posts |
| **Storage** | Filesystem + GitHub | Draft markdown version control |
| **Auth** | Clerk | Authentication and user management |
| **Email** | Resend | Transactional emails |
| **Package Manager** | uv | Fast Python dependency resolver |
| **Linting** | Ruff + Biome | Code quality enforcement |
| **Testing** | pytest + Vitest + Playwright | Test automation |

## Quick Start

### Prerequisites

- **Python 3.13+**
- **Node.js 22.18+ or 24.6+**
- **PostgreSQL 10.23+**
- **uv** (Python package manager): `curl -LsSf https://astral.sh/uv/install.sh | sh`
- **Git**

### Local Development Setup

1. **Clone the Repository**

    ```bash
    git clone https://github.com/ashrobertsdragon/markdown-blog
    cd markdown-blog
    ```

2. **Configure Environment**
    - Copy `backend/.env.example` to `backend/.env`.
    - Copy `frontend/.env.example` to `frontend/.env`.
    - Fill in the required values in both `.env` files, such as database credentials and API keys.

3. **Setup Backend**

    ```bash
    cd backend
    uv sync
    ```

4. **Setup Frontend**

    ```bash
    cd ../frontend
    npm install
    ```

5. **Setup Database**
    Ensure your PostgreSQL server is running, then create the development database.

    ```bash
    createdb blog_dev
    ```

    The backend is configured to use this database via the `DATABASE_URL` in `backend/.env`.

6. **Run the Application**
    Open two terminals:

    ```bash
    # Terminal 1: Start the Backend with entrypoint script (from backend/)
    uv run dev_flask

    # Terminal 2: Start the Frontend (from frontend/)
    npm run dev
    ```

    - The backend API will be available at `http://localhost:5000`.
    - The frontend will be available at `http://localhost:5173`.

## Development

### Project Structure

```plaintext
monorepo/
├── backend/                      # Flask API (Python 3.13)
│   ├── src/
│   │   ├── passenger_wsgi.py    # Production WSGI entry
│   │   ├── scripts/             # Cron jobs (notifications, sync, cleanup)
│   │   └── backend/
│   │       ├── main.py          # Flask app factory
│   │       ├── config.py        # Environment configuration
│   │       ├── domain/          # Business logic (aggregates, value objects, events)
│   │       ├── application/     # Use cases (commands, queries, handlers)
│   │       ├── infrastructure/  # External adapters (DB, GitHub, email, auth)
│   │       └── api/             # HTTP layer (routes, middleware)
│   ├── tests/                   # Test suite (unit, integration, e2e)
│   ├── pyproject.toml           # uv project definition
│   └── uv.lock                  # Dependency lockfile
├── frontend/                     # React SPA (Node.js 22+)
│   ├── src/
│   │   ├── components/          # Reusable UI (post, comment, admin, common)
│   │   ├── pages/               # Route pages (Home, PostPage, AdminPage)
│   │   ├── hooks/               # Custom hooks (useAuth, usePostMutation)
│   │   ├── services/            # API clients (postService, commentService)
│   │   ├── context/             # React context (AuthContext)
│   │   ├── App.jsx              # Root component
│   │   └── main.jsx             # Vite entry point
│   ├── tests/                   # Vitest unit + Playwright e2e
│   ├── package.json             # npm dependencies
│   ├── vite.config.js           # Vite configuration
│   ├── biome.json               # Linter/formatter config
│   └── tailwind.config.js       # Tailwind CSS config
├── shared/
│   └── openapi.yaml             # API contract specification
├── .github/workflows/           # CI/CD (backend-ci.yml, frontend-ci.yml)
├── .pre-commit-config.yaml      # Pre-commit hooks
└── README.md                    # This file
```

### Environment Variables

#### Backend (.env)

```bash
# Database (for development)
LOCAL_DB_HOST=localhost
LOCAL_DB_NAME=blog_dev
LOCAL_DB_USER=your_user
LOCAL_DB_PASSWORD=your_password

# GitHub API (for draft sync)
GITHUB_TOKEN=your_github_personal_access_token
GITHUB_REPO_OWNER=yourusername
GITHUB_REPO_NAME=blog-drafts

# Resend (email notifications)
RESEND_API_KEY=re_your_resend_api_key
NOTIFICATION_FROM_EMAIL=notifications@yourdomain.com

# Clerk (authentication)
CLERK_SECRET_KEY=sk_test_your_clerk_secret_key

# Flask
FLASK_ENV=development
FLASK_DEBUG=1
SECRET_KEY=your_secret_key_for_sessions
```

#### Frontend (.env)

```bash
# API Configuration
VITE_API_BASE_URL=http://localhost:5000

# Clerk (authentication)
VITE_CLERK_PUBLISHABLE_KEY=pk_test_your_clerk_publishable_key
```

### Common Commands

#### Backend (Python + uv)

```bash
cd backend

# Install/update dependencies
uv sync

# Run Flask development server with entrypoint
uv run dev_flask

# Code quality
uvx ruff check --fix .           # Lint and auto-fix
uvx ruff format .                # Format code
uv run mypy src/                 # Type checking with mypy
uvx ty check                     # Type checking with ty (faster alternative)

**CRITICAL**: Always use `uv run` to execute Python commands to ensure the correct virtual environment is used.

#### Frontend (React + Vite)

```bash
./scripts/build.sh
```

## Testing

### Backend Testing

```bash
cd backend

# Run all tests
uv run pytest

# Run tests by type
uv run pytest tests/unit
uv run pytest tests/integration

# Generate a coverage report
uv run pytest --cov=src/backend
```

### Frontend Testing

```bash
cd frontend

# Run unit tests
npm test

# Run end-to-end tests
npm run test:e2e
```

### Pre-commit Hooks

The project uses pre-commit hooks to enforce code quality before commits. Hooks automatically run on `git commit` and will block commits if checks fail.

**Installed hooks:**

- **Python**: Ruff linting/formatting, mypy type checking
- **JavaScript/TypeScript**: Biome linting/formatting
- **General**: Trailing whitespace removal, YAML validation, merge conflict detection

**Setup:**

```bash
# Install pre-commit (one-time setup)
uv tool install pre-commit
uvx pre-commit install

# Manual run (tests all files)
uvx pre-commit run --all-files
```

#### Common hook failures

| Error                 | Fix                                    |
| --------------------- | -------------------------------------- |
| `Ruff format failed`  | Run `uvx ruff format .` in backend/    |
| `Biome check failed`  | Run `biome check --write` in frontend/ |
| `mypy type errors`    | Fix type annotations in flagged files  |
| `Trailing whitespace` | Auto-fixed by hook, re-stage files     |

## Deployment

Deployment to the cPanel hosting environment is automated with a bash script.

### Automated Deployment to cPanel

The `scripts/deploy.sh` script handles all aspects of the deployment, including:

- Provisioning the database and user.
- Uploading backend and frontend code.
- Installing dependencies on the server.
- Registering the application with the Passenger WSGI server.
- Verifying the deployment with health checks.

**For full instructions, refer to the official deployment guide:**
➡️ **[cPanel Deployment Guide](docs/DEPLOYMENT.md)**

---

## Troubleshooting

| Problem | Cause | Solution |
| :--- | :--- | :--- |
| `ModuleNotFoundError` | Not using `uv run` | Always prefix Python commands with `uv run` (e.g., `uv run pytest`). |
| PostgreSQL connection refused | Database not running | Start your local PostgreSQL service. |
| API calls fail with 404 | Backend not running | Start the Flask server: `cd backend && uv run dev_flask`. |
| `CORS error` in browser | CORS misconfiguration | Ensure `CORS(app)` is configured in `backend/src/backend/main.py`. |

## CI/CD

### GitHub Actions Workflows

Two workflows run automatically on push and pull requests to `main`:

#### Backend CI (`backend-ci.yml`)

- **Python version:** 3.13
- **Steps:**
  1. Install uv and sync dependencies
  1. Run Ruff linting and formatting checks
  1. Run mypy type checking
  1. Run pytest with coverage (must be 80%+)
  1. Upload coverage report to Codecov
  1. Build backend artifacts

#### Frontend CI (`frontend-ci.yml`)

- **Node versions:** 22.18, 24.6 (matrix)
- **Steps:**
  1. Install npm dependencies
  1. Run Biome linting and formatting checks
  1. Run Vitest tests with coverage (must be 70%+)
  1. Run Playwright e2e tests
  1. Upload test artifacts and coverage
  1. Build production bundle

**Branch protection:**

Both CI workflows must pass before merging to `main`.

### Pre-deployment Checklist

Before deploying to production:

- [ ] All CI checks pass (green checkmarks on GitHub)
- [ ] Coverage targets met (80% backend, 70% frontend)
- [ ] Manual smoke test on staging environment
- [ ] Database migrations tested
- [ ] Environment variables configured on production
- [ ] Backup current production database
- [ ] Monitor logs for 1 hour post-deployment

## Contributing

### Development Workflow

1. **Create feature branch**

   ```bash
   git checkout -b feature/your-feature-name
   ```

2. **Write failing tests (TDD)**

   ```bash
   # Backend
   cd backend && uv run pytest tests/unit/test_new_feature.py

   # Frontend
   cd frontend && npm test -- tests/NewComponent.test.jsx
   ```

3. **Implement feature**

   - Follow existing patterns in codebase
   - Keep domain logic in `domain/` layer
   - Infrastructure concerns in `infrastructure/`

4. **Ensure tests pass**

   ```bash
   uv run pytest          # Backend
   npm test               # Frontend
   ```

5. **Run quality checks**

```bash
uvx ruff check --fix . # Backend lint
biome check --write # Frontend lint/format
uv run mypy src/ # Type checking
```

6. **Commit with conventional commits format**

```bash
git add .
git commit -m "feat: add post revision comparison API"
```

7.**Push and create PR**

```bash
git push origin feature/your-feature-name
#Create PR on GitHub
```

### Commit Message Convention

Follow [Conventional Commits](https://www.conventionalcommits.org/):

```text
<type>(<scope>): <description>

[optional body]

[optional footer]
```

**Types:**

- `feat`: New feature
- `fix`: Bug fix
- `docs`: Documentation only
- `style`: Code style changes (formatting, no logic change)
- `refactor`: Code restructuring (no behavior change)
- `test`: Add or modify tests
- `chore`: Build process or auxiliary tool changes

**Examples:**

```text
feat(comments): add reply functionality with @mentions
fix(auth): resolve Clerk session timeout issue
docs(readme): update deployment instructions
test(posts): add integration tests for publish workflow
```

### Code Review Guidelines

PRs must meet these criteria before merging:

- [ ] All CI checks pass (backend-ci and frontend-ci)
- [ ] Coverage targets met (no decrease in coverage)
- [ ] Pre-commit hooks pass
- [ ] At least one approving review
- [ ] No merge conflicts with `main`
- [ ] Conventional commit message format
- [ ] Tests added for new functionality
- [ ] Documentation updated if API changes

## Resources & Links

### Documentation

- [Deployment Guide](docs/deployment.md) - Production deployment instructions
- [API Reference](docs/api.md) - REST API endpoints documentation

### External Resources

- [Flask Documentation](https://flask.palletsprojects.com/)
- [React Documentation](https://react.dev/)
- [uv Documentation](https://docs.astral.sh/uv/)
- [Clerk Authentication](https://clerk.com/docs)
- [Resend Email API](https://resend.com/docs)
- [Tailwind CSS](https://tailwindcss.com/docs)
- [Domain-Driven Design](https://martinfowler.com/bliki/DomainDrivenDesign.html)
- [Hexagonal Architecture](https://alistair.cockburn.us/hexagonal-architecture/)

### Development Tools

- [Ruff](https://docs.astral.sh/ruff/) - Python linter and formatter
- [Biome](https://biomejs.dev/) - JavaScript/TypeScript linter and formatter
- [pytest](https://docs.pytest.org/) - Python testing framework
- [Vitest](https://vitest.dev/) - Vite-native test framework
- [Playwright](https://playwright.dev/) - End-to-end testing

### Support

- **Issues:** [GitHub Issues](https://github.com/ashrobertsdragon/markdown-blog/issues)
- **Email:** See [pyproject.toml](backend/pyproject.toml)

---

**License:** MIT

**Last Updated:** 2025-12-22
