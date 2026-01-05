# Deployment Guide

This document describes production deployment automation for the blog application to cPanel shared hosting.

## Deployment Strategy

This project supports **two deployment paths** for different cPanel hosting environments:

### 1. Passenger with UAPI (deploy.sh)

**Use when:** Your cPanel hosting uses Phusion Passenger web server

**Characteristics:**

- cPanel UAPI calls work reliably
- Database and application provisioning fully automated
- End-to-end automation in single command
- Script: `scripts/deploy.sh`

### 2. LiteSpeed with Manual Configuration (litespeed_deploy.sh)

**Use when:** Your cPanel hosting uses LiteSpeed web server

**Characteristics:**

- cPanel UAPI calls **silently fail** (known cPanel/LiteSpeed limitation)
- Database and application must be configured via cPanel web UI manually
- Deployment script handles code upload, dependency installation, and verification
- Script: `scripts/litespeed_deploy.sh`

**Critical Limitation:** On LiteSpeed environments, UAPI database and Passenger application registration calls fail silently without error messages. You must use the cPanel web interface to manually create the database and configure the application.

### Decision Matrix

| Hosting Type     | Web Server | UAPI Works?       | Script to Use         | Manual Steps Required            |
| ---------------- | ---------- | ----------------- | --------------------- | -------------------------------- |
| cPanel Standard  | Passenger  | ✅ Yes            | `deploy.sh`           | None                             |
| cPanel/LiteSpeed | LiteSpeed  | ❌ Fails Silently | `litespeed_deploy.sh` | Database setup, App registration |

## Overview

Both deployment scripts provide comprehensive automation for deploying the blog platform to cPanel hosting. They handle code upload, application installation with uv, and deployment verification. The key difference is how they handle database and application provisioning.

## Features

- **Idempotent Operations**: Safe to run multiple times - only creates resources that don't exist
- **Database Provisioning**: Automatic PostgreSQL database, user, and privilege setup
- **Code Deployment**: Rsync-based upload with checksum verification and deletion of stale files
- **uv Package Management**: Automatic uv installation and dependency management on remote server
- **Schema Migration**: Automatic database schema creation from SQLModel models
- **Application Registration**: Passenger WSGI application configuration with environment variables
- **Health Verification**: Post-deployment validation of critical endpoints
- **Error Handling**: Exponential backoff retry logic for network operations
- **Security**: Input sanitization, secret suppression, SSH key permission validation, audit logging
- **Cross-Platform**: Compatible with Windows Git Bash and Linux environments

## Prerequisites

### Local Environment

1. **Operating System**: Windows with Git Bash, Linux, or macOS
1. **Required Tools**:
   - `bash` 4.0+ (included in Git Bash on Windows)
   - `ssh` client (OpenSSH)
   - `rsync` (for Windows: install via Git Bash or WSL)
1. **Frontend Build**: Run `npm run build` in `frontend/` directory before deploying
1. **SSH Access**: SSH private key with access to cPanel server

### Environment Variables

All environment variables must be set before running the deployment script. These are already configured in your local environment:

| Variable                       | Description               | Example                     |
| ------------------------------ | ------------------------- | --------------------------- |
| `CPANEL_USERNAME`              | cPanel/SSH username       | `myuser`                    |
| `SERVER_IP_ADDRESS`            | Server IP address for SSH | `198.51.100.50`             |
| `SSH_PRIVATE_KEY_PATH`         | Path to SSH private key   | `C:/Users/user/.ssh/id_rsa` |
| `SSH_PORT`                     | SSH port number           | `22`                        |
| `CPANEL_POSTGRES_USER`         | PostgreSQL username       | `myuser_pguser`             |
| `CPANEL_POSTGRES_PASSWORD`     | PostgreSQL password       | (sensitive)                 |
| `GITHUB_PERSONAL_ACCESS_TOKEN` | GitHub API token          | `ghp_...`                   |
| `RESEND_API_KEY`               | Resend email API key      | `re_...`                    |
| `CLERK_PUBLISHABLE_KEY`        | Clerk auth public key     | `pk_test_...`               |
| `CLERK_SECRET_KEY`             | Clerk auth secret key     | `sk_test_...`               |

**Security Note**: Never commit these values to version control. They should only exist in your local environment or secure secret management system.

### Remote Server Requirements

1. **cPanel Hosting**: Shared hosting account with:
   - PostgreSQL database support
   - SSH access enabled
   - Phusion Passenger available
   - Python 3.13+ installed
1. **Domain Configuration**: DNS pointing to server IP
1. **cPanel UAPI Access**: Enabled for database and Passenger operations

## Usage

### Basic Deployment

```bash
cd monorepo/scripts
./deploy.sh
```

The script will:

1. Validate all required environment variables
1. Configure SSH key with correct permissions
1. Provision PostgreSQL database (idempotent)
1. Upload backend code and frontend build files via rsync
1. Ensure uv is installed on remote server
1. Install application dependencies with `uv sync`
1. Create database schema using `uv run scripts/create_schema.py`
1. Register Passenger application with environment variables
1. Verify deployment via health checks

### Production Deployment Confirmation

When deploying to the production domain (`ashlynantrobus.dev`), the script will prompt for confirmation in interactive terminals:

```text
WARNING: Deploying to PRODUCTION domain: ashlynantrobus.dev
Continue? (yes/no):
```

Type `yes` to proceed or `no` to cancel.

**Note**: This confirmation prompt is automatically bypassed when the script is run in a non-interactive environment (e.g., a CI/CD pipeline), allowing for safe, automated deployments.

## LiteSpeed Deployment (Manual Configuration Required)

### When to Use LiteSpeed Deployment

Use `scripts/litespeed_deploy.sh` when your cPanel hosting environment uses **LiteSpeed web server** instead of Phusion Passenger. LiteSpeed environments experience silent UAPI failures that prevent automated database and application provisioning.

### Key Differences from Passenger Deployment

| Operation                | Passenger (deploy.sh)  | LiteSpeed (litespeed_deploy.sh)       |
| ------------------------ | ---------------------- | ------------------------------------- |
| Database creation        | ✅ Automated via UAPI  | ⚠️ Manual via cPanel web UI           |
| Database user creation   | ✅ Automated via UAPI  | ⚠️ Manual via cPanel web UI           |
| Application registration | ✅ Automated via UAPI  | ⚠️ Manual via cPanel web UI           |
| Code upload              | ✅ Automated via rsync | ✅ Automated via rsync                |
| Dependency installation  | ✅ Automated with uv   | ✅ Automated with uv                  |
| Schema creation          | ✅ Automated           | ✅ Automated (after manual DB setup)  |
| Health verification      | ✅ Automated           | ✅ Automated (after manual app setup) |

### Manual Pre-Deployment Steps (LiteSpeed Only)

Before running `litespeed_deploy.sh`, you must manually configure the following via cPanel web interface:

#### 1. Create PostgreSQL Database

1. Log into cPanel web interface
1. Navigate to **Databases** → **PostgreSQL Databases**
1. Create database: `${CPANEL_USERNAME}_blogdb`
1. Note the database name for environment variables

#### 2. Create PostgreSQL User

1. In **PostgreSQL Databases**, scroll to **PostgreSQL Users**
1. Create user with strong password
1. Note username and password for environment variables

#### 3. Grant User Privileges

1. In **PostgreSQL Databases**, scroll to **Add User To Database**
1. Select the user created in step 2
1. Select the database created in step 1
1. Grant **ALL PRIVILEGES**

#### 4. Register Passenger Application

1. Navigate to **Software** → **Setup Python App** (or **Setup Node.js App** if available)
1. Click **Create Application**
1. Configure:
   - **Python version**: 3.13.5 (must match `pyproject.toml`)
   - **Application root**: `/home/${CPANEL_USERNAME}/seeash`
   - **Application URL**: Your domain (e.g., `ashlynantrobus.dev`)
   - **Application startup file**: `passenger_wsgi.py`
   - **Application Entry point**: `application`
1. Add environment variables (click **Add Variable** for each):
   - `DB_NAME`: Database name from step 1
   - `DB_USER`: Username from step 2
   - `DB_PASSWORD`: Password from step 2
   - `VENV_PATH`: `/home/${CPANEL_USERNAME}/virtualenv/seeash`
   - `GITHUB_PERSONAL_ACCESS_TOKEN`: Your GitHub token
   - `RESEND_API_KEY`: Your Resend API key
   - `CLERK_PUBLISHABLE_KEY`: Your Clerk public key
   - `CLERK_SECRET_KEY`: Your Clerk secret key
1. Save the configuration

### Running LiteSpeed Deployment

After completing the manual setup steps above:

```bash
cd monorepo/scripts
./litespeed_deploy.sh
```

The script will:

1. Validate all required environment variables
1. Configure SSH key permissions
1. Upload backend code and frontend build files via rsync
1. Install uv on remote server (if not present)
1. Install application dependencies with `uv sync`
1. Create database schema using `uv run scripts/create_schema.py`
1. Verify deployment via health checks
1. Report deployment status

### LiteSpeed Deployment Notes

- **UAPI calls are not used** - The script skips all UAPI operations that fail silently on LiteSpeed
- **Manual restart may be required** - After first deployment, restart the Passenger app in cPanel
- **Database schema is automated** - Once the database is created manually, schema creation works normally
- **Environment variables must match** - Ensure cPanel environment variables match your local `.env` variables
- **requirements.txt available** - A `backend/requirements.txt` file is provided for compatibility with environments that don't support uv

### Troubleshooting LiteSpeed Deployments

**Health checks fail after deployment:**

- Verify application is registered correctly in cPanel
- Check that all 8 environment variables are set in cPanel
- Manually restart the application in cPanel → Setup Python App
- Check Passenger logs: `~/seeash/passenger.log`

**Database connection errors:**

- Verify database was created with correct name
- Verify user has ALL PRIVILEGES on the database
- Test connection manually: `psql -h localhost -U $DB_USER -d $DB_NAME`

**uv installation fails:**

- Check remote server internet connectivity
- Verify curl is available: `ssh ... "which curl"`
- Try manual installation: `ssh ... "curl -LsSf https://astral.sh/uv/install.sh | sh"`

### Cross-Platform SSH Key Handling

On **Windows Git Bash**, the script automatically uses the SSH key at `$SSH_PRIVATE_KEY_PATH`.

On **Linux/macOS**, the script will automatically run `linuxify_ssh_key.sh` (if available in project root) to copy the SSH key to a Linux-compatible location before use.

## Idempotency

The deployment script is fully idempotent - safe to run multiple times without side effects:

- **Database Creation**: Only creates database if it doesn't exist
- **User Creation**: Only creates PostgreSQL user if it doesn't exist
- **Privilege Grants**: Only grants privileges if not already granted
- **Application Registration**: Creates new app or updates existing app configuration
- **File Upload**: Rsync uses checksums to only transfer changed files
- **uv Installation**: Only installs uv if not already present

This means you can safely re-run the deployment after failures without manual cleanup.

## Output and Logging

The script provides progress feedback during deployment:

```text
Starting deployment to ashlynantrobus.dev...
✓ Environment variables validated
✓ SSH key configured
✓ Database provisioned
✓ Code uploaded
✓ uv installation verified
✓ Application installed
✓ Database schema created
✓ Passenger application registered
✓ Deployment verified

Deployment completed successfully!
Application URL: https://ashlynantrobus.dev
```

All security-relevant operations are logged to syslog with the tag `deploy.sh`.

## Error Handling

### Retry Logic

Network operations (health checks) use exponential backoff retry:

- Maximum retries: 5
- Base delay: 2 seconds
- Delay increases: 2s, 4s, 8s, 16s, 32s

### Common Errors

| Error                                      | Cause               | Solution                                  |
| ------------------------------------------ | ------------------- | ----------------------------------------- |
| `Required environment variable is not set` | Missing env var     | Set all required variables                |
| `Backend source directory is empty`        | Missing code        | Ensure `monorepo/backend/` exists         |
| `Frontend build directory is empty`        | Build not run       | Run `npm run build` in frontend/          |
| `SSH connection failed`                    | Invalid key/network | Verify SSH key and server access          |
| `Health check failed`                      | App not responding  | Check Passenger logs on server            |
| `Failed to set restrictive permissions`    | SSH key permissions | Ensure key file is owned by current user  |
| `Failed to install uv`                     | Network/curl error  | Check remote server internet connectivity |

### Exit Codes

- `0`: Deployment successful
- `1`: Validation failure, deployment error, or user cancellation

## Testing

The deployment script has comprehensive BATS test coverage.

### Running Tests

```bash
cd monorepo/scripts/tests

# Run all tests
bats .

# Run specific test file
bats deploy.bats

# Run tests with specific filter
bats deploy.bats --filter "database"

# Run with verbose output
bats deploy.bats --tap
```

### Test Coverage

- **Environment Validation** (6 tests): Missing variables, invalid input, production confirmation.
- **SSH Key Handling** (3 tests): Permissions and error handling.
- **Database Provisioning** (6 tests): DB/user creation, privileges, idempotency.
- **Code Upload** (5 tests): Rsync success/failure, frontend/backend assets.
- **uv and Application Installation** (4 tests): Remote `uv` and dependency installation.
- **Schema Execution** (3 tests): Remote schema script execution.
- **Passenger Registration** (5 tests): App configuration and environment variables.
- **Health Check Verification** (5 tests): Endpoint checks with retry logic.

All tests use mocks - no actual network calls or database operations.

## Security Considerations

### Secret Handling

- Secrets are stored in environment variables (never in code)
- UAPI calls redirect output to `/dev/null` to prevent logging passwords
- Signal traps (`EXIT`, `INT`, `TERM`) automatically unset secrets on script termination
- SSH key permissions validated (must be `600`)
- Audit logging for all security-relevant operations

### Known Limitations

**Database password in process arguments**: During PostgreSQL user creation, the password briefly appears in process arguments due to cPanel UAPI design. This is mitigated by:

1. Rapid execution (minimal exposure window)
1. Automatic secret cleanup via signal traps
1. UAPI output suppression

### Input Validation

The script validates environment variables to prevent injection attacks:

- Blocks characters: `;`, `&`, `|`, `` ` ``, `$`, `(`, `)`
- Validates SSH key file permissions
- Strict SSH command construction to prevent injection

### Audit Logging

All security-relevant operations are logged to syslog:

```bash
logger -t deploy.sh -p user.info "Creating database: cpaneluser_blogdb"
logger -t deploy.sh -p user.notice "Deployment completed successfully"
logger -t "deploy.sh[uapi_call]" -p user.warning "uapi Postgresql::list_databases failed"
logger -t "deploy.sh[setup_ssh_key]" -p user.error "Failed to verify SSH key permissions"
```

View logs with: `journalctl -t deploy.sh` (Linux) or `/var/log/messages` (cPanel)

## Deployment Architecture

### Remote Directory Structure

```plaintext
/home/$CPANEL_USERNAME/seeash/
├── passenger_wsgi.py   # WSGI entry point
├── pyproject.toml      # uv project definition
├── uv.lock             # Dependency lockfile
├── scripts/
│   └── create_schema.py    # Database schema creation script
├── backend/                # Application code
│   ├── main.py
│   ├── config.py
│   ├── domain/
│   ├── application/
│   ├── infrastructure/
│   └── api/
├── build/                  # Frontend static files (optional)
│   ├── index.html
│   ├── static/
│   └── assets/
└── .venv/                  # uv-managed virtual environment
    ├── bin/
    ├── lib/
    └── pyvenv.cfg
```

### Database Naming Convention

- Database: `${CPANEL_USERNAME}_blogdb`
- User: Value of `$CPANEL_POSTGRES_USER` environment variable
- Connection: `localhost` (cPanel default)

### Passenger Configuration

The script registers a Passenger application with:

- **Name**: `BlogAppProd`
- **Domain**: `ashlynantrobus.dev`
- **Base URI**: `/` (root)
- **Deployment Mode**: `production`
- **Environment Variables**: All secrets injected at application level

## Rollback

To roll back a deployment:

1. **Database**: PostgreSQL is idempotent - old schema remains intact
1. **Code**: Deploy previous git commit or manually revert files
1. **Passenger**: Use cPanel interface to restart application

**Note**: The script does not currently support automated rollback. Manual intervention required.

## Troubleshooting

### Debugging Failed Deployments

1. **Check SSH connectivity**:

   ```bash
   ssh -i "$SSH_PRIVATE_KEY_PATH" -p "$SSH_PORT" "$CPANEL_USERNAME@$SERVER_IP_ADDRESS"
   ```

1. **Verify remote directory structure**:

   ```bash
   ssh ... "ls -la ~/seeash"
   ```

1. **Check Passenger logs** (via cPanel or SSH):

   ```bash
   tail -f ~/seeash/passenger.log
   ```

1. **Test health endpoints manually**:

   ```bash
   curl https://ashlynantrobus.dev/health
   curl https://ashlynantrobus.dev/health/db
   curl https://ashlynantrobus.dev/health/github
   ```

1. **Verify database connectivity** (via SSH):

   ```bash
   psql -h localhost -U "$CPANEL_POSTGRES_USER" -d "${CPANEL_USERNAME}_blogdb"
   ```

1. **Check uv installation**:

   ```bash
   ssh ... "~/.cargo/bin/uv --version"
   ```

### Common Issues

**Frontend build missing**: Ensure you run `npm run build` before deploying.

**SSH key permissions error**: The key must be owned by the current user and have `600` permissions. On Windows, this may require administrator privileges.

**Health check timeout**: Passenger may take 30-60 seconds to start the application on first deployment. The script automatically retries with backoff.

**Database connection refused**: Verify PostgreSQL is running in cPanel and credentials are correct.

**uv not found**: The script installs uv automatically. If installation fails, check remote server internet connectivity and curl availability.

## Future Enhancements

Potential improvements for future versions:

- Automated rollback capability
- Blue-green deployment support
- Database migration management
- Backup creation before deployment
- Slack/email deployment notifications
- Deployment metrics and timing
- Parallel file upload optimization
- Environment-specific configuration (staging/production)

## Related Documentation

- cPanel deployment strategies: `../cpanel-deployment-patterns.md`
- Backend configuration: `backend/README.md`
- WSGI entry point: `backend/src/passenger_wsgi.py`
- Test documentation: `scripts/tests/README.md`
- Project structure: `../.spec-workflow/steering/structure.md`

## Support

For deployment issues:

1. Review error messages in script output
1. Check syslog for audit trail
1. Verify all prerequisites are met
1. Run BATS tests to validate local environment
1. Consult cPanel documentation for UAPI/Passenger issues

## License

This deployment script is part of the blog platform project and follows the same license.
