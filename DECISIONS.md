# Architecture Decision Records

This document tracks significant architectural and technical decisions made during the development of this project.

## Environment Variable Naming for Production Database Configuration

**Date**: 2025-12-27
**Status**: Implemented
**Context**: Deployment to cPanel with Passenger WSGI

### Problem

ProductionDBSettings was configured with `env_prefix="CPANEL_"`, expecting environment variables named `CPANEL_DB_HOST`, `CPANEL_DB_NAME`, `CPANEL_DB_USER`, `CPANEL_DB_PASSWORD`. However, Passenger WSGI provides standard environment variable names: `DB_HOST`, `DB_NAME`, `DB_USER`, `DB_PASSWORD`.

This mismatch prevented Flask from connecting to the database on startup, causing deployment failure with ValidationError indicating missing required fields.

### Decision

Changed ProductionDBSettings in `backend/src/backend/config.py` to use `env_prefix=""` instead of `env_prefix="CPANEL_"`, allowing it to read standard environment variable names that Passenger provides.

### Rationale

- **Alignment with Passenger**: Passenger WSGI uses standard naming conventions for environment variables registered via UAPI
- **Industry Standard**: Other hosting platforms (Heroku, Railway, Render) also use standard `DB_*` naming without custom prefixes
- **Simplicity**: Removes unnecessary prefix that doesn't add value and creates configuration complexity
- **No Local Impact**: Local development uses DevDBSettings with `LOCAL_` prefix, which remains unchanged
- **Consistency**: Environment variables set in deploy.sh run_schema() and Passenger registration now all use the same naming scheme

### Alternatives Considered

**Option A: Add environment variable conversion layer in passenger_wsgi.py**

- Would map unprefixed Passenger vars to prefixed ProductionDBSettings vars
- Rejected because it adds unnecessary complexity and doesn't align with standard conventions

**Option B: Remove CPANEL\_ prefix (CHOSEN)**

- Simplest solution that aligns with industry standards
- No code complexity added
- Matches what Passenger naturally provides

**Option C: Pass prefixed variables to Passenger**

- Would register variables as `CPANEL_DB_HOST` etc. in deploy.sh
- Rejected because it violates Passenger deployment patterns and cPanel conventions

### Consequences

**Positive**:

- Production environment variables set by Passenger now work correctly without modification
- Deploy script's register_passenger() function uses standard names (DB_HOST, DB_NAME, etc.)
- Schema creation script receives standard env var names during deployment
- Reduced cognitive overhead for developers familiar with standard hosting conventions

**Neutral**:

- Local development unaffected (continues using LOCAL\_\* prefix via DevDBSettings)
- Test suite unaffected (uses LOCAL\_\* prefix via TestDBSettings)

**Negative**:

- None identified

### Implementation

**Files Modified**:

- `backend/src/backend/config.py` (line 105): Changed `env_prefix="CPANEL_"` to `env_prefix=""`
- `backend/tests/unit/conftest.py`: Updated production_env fixture to use standard names
- `backend/tests/unit/test_config.py`: Updated test assertions to use standard names
- `scripts/deploy.sh` (lines 361-365): Added standard env var exports to run_schema()

**Tests Added**:

- `backend/tests/unit/test_config_production_env_prefix.py`: 4 comprehensive tests verifying standard env var behavior
- `scripts/tests/deploy_config_fix.bats`: 5 BATS tests verifying deployment script fixes

### References

- [Passenger Environment Variables](https://www.phusionpassenger.com/library/deploy/apache/deploy/#deploying_an_app_to_a_sub_uri_or_subdirectory)
- [cPanel UAPI PassengerApps Documentation](https://api.docs.cpanel.net/openapi/cpanel/operation/register_application/)
- DEPLOYMENT_ISSUES.md: Original problem analysis
