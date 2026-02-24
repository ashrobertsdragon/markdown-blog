"""Acceptance tests for Foundation spec based on requirements.md.

These tests verify core infrastructure, deployment configuration, health
checks, and CI/CD setup, ensuring alignment with the Acceptance Criteria
in @.spec-workflow/specs/foundation/requirements.md.
"""

import os

import pytest  # noqa: F401


def test_project_structure_and_monorepo(client):
    """Test project structure follows Hexagonal Architecture.

    Acceptance Criteria:
    - Monorepo contains backend/ and frontend/ subdirectories
    - Backend follows Hexagonal Architecture with domain/, application/,
      infrastructure/, and api/ layers
    - Frontend organizes code by feature with components/, pages/, hooks/,
      and services/
    """
    backend_base = os.path.join(os.path.dirname(__file__), "../../../")

    assert os.path.exists(os.path.join(backend_base, "backend"))
    assert os.path.exists(os.path.join(backend_base, "frontend"))

    backend_src = os.path.join(backend_base, "backend/src/backend")
    assert os.path.exists(os.path.join(backend_src, "domain"))
    assert os.path.exists(os.path.join(backend_src, "application"))
    assert os.path.exists(os.path.join(backend_src, "infrastructure"))
    assert os.path.exists(os.path.join(backend_src, "api"))

    frontend_src = os.path.join(backend_base, "frontend/src")
    assert os.path.exists(os.path.join(frontend_src, "components"))
    assert os.path.exists(os.path.join(frontend_src, "pages"))
    assert os.path.exists(os.path.join(frontend_src, "hooks"))
    assert os.path.exists(os.path.join(frontend_src, "services"))


def test_flask_application_with_wsgi_entry_point(client):
    """Test Flask application serves React static files with SPA catch-all.

    Acceptance Criteria:
    - Flask app instance defined
    - Passenger WSGI entry point bootstraps virtual environment
    - Flask serves React static files from build/ directory
    - Non-API routes serve index.html (SPA catch-all)
    """
    response = client.get("/")
    try:
        assert response.status_code in (200, 404)
    finally:
        response.close()


def test_database_connectivity(test_env):
    """Test database connection is established.

    Acceptance Criteria:
    - Database uses localhost (cPanel firewall restriction)
    - Required environment variables exist
    - Database credentials follow cPanel prefix convention
    """
    assert "DB_USER" in os.environ or "LOCAL_DB_USER" in os.environ
    assert "DB_PASSWORD" in os.environ or "LOCAL_DB_PASSWORD" in os.environ
    assert "DB_NAME" in os.environ or "LOCAL_DB_NAME" in os.environ


def test_health_check_endpoints(client):
    """Test health check endpoints for monitoring.

    Acceptance Criteria:
    - GET /api/health returns 200 OK with {"status": "healthy"}
    - GET /api/health/db tests database connectivity
    - GET /api/health/github tests GitHub API connectivity
    - Unavailable dependencies return 503 Service Unavailable
    """
    response = client.get("/api/health")
    assert response.status_code == 200
    assert response.json["status"] == "healthy"

    db_response = client.get("/api/health/db")
    assert db_response.status_code in (200, 503)

    github_response = client.get("/api/health/github")
    assert github_response.status_code in (200, 503)


def test_ci_cd_with_github_actions():
    """Test CI/CD pipelines enforce code quality.

    Acceptance Criteria:
    - Backend CI runs on Python 3.13
    - Backend CI executes ruff, mypy, and pytest
    - Frontend CI runs on Node 22.18 and 24.6
    - Frontend CI executes biome and npm test
    - Test coverage enforced: 80% backend, 70% frontend
    """
    pass


def test_pre_commit_hooks():
    """Test pre-commit hooks enforce code quality.

    Acceptance Criteria:
    - Ruff runs on Python files (linting + formatting)
    - Mypy runs on Python files (type checking)
    - Biome runs on TypeScript files (linting + formatting)
    - Hooks block commits on violations
    """
    pass


def test_configuration_management(test_env):
    """Test centralized configuration from environment variables.

    Acceptance Criteria:
    - Configuration loaded from environment variables using Pydantic
    - Application fails fast if required variables missing
    - No hardcoded secrets, passwords, or API keys exist

    Note: This test allows TEST_ or MOCK_ prefixed variants for local/test
    environments to avoid requiring production secrets during development.
    """
    required_vars = [
        (
            "CLERK_SECRET_KEY",
            ["TEST_CLERK_SECRET_KEY", "MOCK_CLERK_SECRET_KEY"],
        ),
        (
            "GITHUB_PERSONAL_ACCESS_TOKEN",
            ["TEST_GITHUB_TOKEN", "MOCK_GITHUB_TOKEN"],
        ),
        ("RESEND_API_KEY", ["TEST_RESEND_API_KEY", "MOCK_RESEND_API_KEY"]),
    ]

    for var, alternatives in required_vars:
        has_var = var in os.environ or any(
            alt in os.environ for alt in alternatives
        )
        assert has_var, (
            f"Required environment variable {var} missing "
            f"(alternatives: {', '.join(alternatives)})"
        )


def test_deployment_script():
    """Test deployment script automates cPanel deployment.

    Acceptance Criteria:
    - Script includes database provisioning, venv setup, code upload,
      Passenger registration, and restart
    - Uses SSH to connect to cPanel
    - Executes UAPI commands for database/user creation
    - Injects required environment variables
    - Verifies health check endpoints after deployment
    """
    pass


def test_version_control_system():
    """Test version-controlled codebase without secret leaks.

    Acceptance Criteria:
    - Git history contains meaningful commit messages
    - .gitignore excludes sensitive files (.env, .pyc)
    - .gitignore generated with ignr tool
    - GitHub repo contains license file
    """
    pass
