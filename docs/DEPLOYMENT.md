# cPanel Deployment Guide

**Version**: 0.2.0
**Target Environment**: cPanel Shared Hosting with Phusion Passenger
**Deployment Method**: Automated via `monorepo/scripts/deploy.sh`

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
- Application, and dependency installation must be configured via cPanel web UI manually
- Deployment script handles code upload and verification
- Script: `scripts/litespeed_deploy.sh`

**Critical Limitation:** On LiteSpeed environments, UAPI database and Passenger application registration calls fail silently without error messages. You must use the cPanel web interface to manually create the database and configure the application.

### Decision Matrix

| Hosting Type     | Web Server | UAPI Works?       | Script to Use         | Manual Steps Required            |
| ---------------- | ---------- | ----------------- | --------------------- | -------------------------------- |
| cPanel Standard  | Passenger  | ✅ Yes            | `deploy.sh`           | None                             |
| cPanel/LiteSpeed | LiteSpeed  | ❌ Fails Silently | `litespeed_deploy.sh` | Database setup, App registration |

## Overview

Both deployment scripts provide comprehensive automation for deploying the blog platform to cPanel hosting. They handle code upload, application installation with uv, and deployment verification. The key difference is how they handle database and application provisioning.

---

## Table of Contents

1. [Introduction](#introduction)
2. [LiteSpeed Deployment](#litespeed-deployment-manual-configuration-required)
3. [Prerequisites](#prerequisites)
4. [Automated Deployment](#automated-deployment)
5. [Troubleshooting](#troubleshooting)

---

## Introduction

This document provides deployment instructions for the blog platform to a cPanel shared hosting environment. The deployment is fully automated using the `monorepo/scripts/deploy.sh` bash script. This script handles all infrastructure provisioning, code upload, dependency installation, and application registration, ensuring a consistent and repeatable process.

The script leverages SSH for server access and cPanel's UAPI (Universal API) for provisioning resources like PostgreSQL databases and Passenger applications.

### Deployment Philosophy

The deployment is guided by these principles:

- **Idempotency**: The script can be run multiple times safely. It checks if resources (databases, users, apps) exist before attempting to create them.
- **Security**: Secrets are injected via environment variables and never stored in files. SSH keys are validated for correct permissions.
- **Verification**: The deployment is only considered successful if the application passes health checks on the live URL.

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

---

## Prerequisites

### Access Requirements

- **cPanel Account**: An active shared hosting account with SSH access enabled.
- **Domain**: A domain name configured in cPanel and pointing to the server's IP address.
- **SSH Key**: A password-less SSH private key configured for access to your cPanel account.

### Local Environment

- **OS**: A Unix-like environment (Linux, macOS, or WSL on Windows).
- **Tools**: `bash`, `ssh`, `rsync`, and `curl` must be installed.
- **Node.js/npm**: Required to build the frontend artifacts locally before deployment.

### Required Environment Variables

The `deploy.sh` script requires the following environment variables to be set. You can add them to a `.env` file in the project root and load them with `source .env` before running the script.

| Variable | Description | Example Value |
| :--- | :--- | :--- |
| `DOMAIN` | Target domain name | `example.com` |
| `PRODUCTION_DOMAIN` | Production domain for confirmation prompt | `example.com` |
| `CPANEL_USERNAME` | cPanel/SSH username | `myuser` |
| `SERVER_IP_ADDRESS` | Server IP address for SSH | `198.51.100.50` |
| `SSH_PRIVATE_KEY_PATH` | Path to your SSH private key | `~/.ssh/id_rsa` |
| `SSH_PORT` | SSH port number | `22` |
| `CPANEL_POSTGRES_USER` | PostgreSQL username | `myuser_blog` |
| `CPANEL_POSTGRES_PASSWORD` | PostgreSQL password | `(sensitive)` |
| `GITHUB_PERSONAL_ACCESS_TOKEN` | GitHub PAT for draft repo access | `ghp_...` |
| `RESEND_API_KEY` | Resend email service API key | `re_...` |
| `CLERK_PUBLISHABLE_KEY` | Clerk auth publishable key | `pk_test_...` |
| `CLERK_SECRET_KEY` | Clerk auth secret key | `sk_test_...` |
| `PRODUCTION_DOMAIN` | Production domain for confirmation prompt | `example.com` |

**Note**: The script will validate that all these variables are set before starting the deployment.

---

## Automated Deployment

The entire deployment process is handled by a single script.

### Step 1: Build Frontend Artifacts

The deployment script uploads the frontend, but does **not** build it. You must build the production-ready frontend artifacts first. You may use the build script for this.

```bash
# Run the build script
./scripts/build.sh
```

This will create a `monorepo/build` directory containing the static HTML, CSS, and JavaScript files.

### Step 2: Run the Deployment Script

From the `monorepo` directory, execute the `deploy.sh` script.

```bash
# Run the script
./scripts/deploy.sh
```

View logs with: `journalctl -t deploy.sh` (Linux) or `/var/log/messages` (cPanel)

## Deployment Architecture

### Remote Directory Structure

```plaintext
/home/$CPANEL_USERNAME/seeash/
├── passenger_wsgi.py   # WSGI entry point
├── pyproject.toml      # uv project definition
├── uv.lock             # Dependency lockfile
├── requirements.txt    # Fallback dependency list
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

- **Error**: `Required environment variable is not set`
  - **Cause**: One of the variables listed in the "Prerequisites" section is missing.
  - **Solution**: Ensure all required environment variables are exported in your shell.

- **Error**: `SSH key file not found` or `Failed to set or verify proper permissions (600) on SSH key`
  - **Cause**: The path in `SSH_PRIVATE_KEY_PATH` is incorrect, or the script could not set `chmod 600` on the key. This is common when running in WSL with a key stored on the Windows filesystem.
  - **Solution**: Verify the key path. If using WSL, copy the key to the Linux filesystem (e.g., `~/.ssh/`) and update `SSH_PRIVATE_KEY_PATH`.

### Deployment Fails at "provision_database"

- **Cause**: The cPanel user may not have permission to create PostgreSQL databases or users.
- **Solution**: Log in to the cPanel web interface and verify that you can create a database manually. Check your hosting plan's features.

### Deployment Fails at "upload_code"

- **Cause**: `rsync` or `ssh` command failed. This could be due to a network issue or an SSH connection problem.
  - **Solution**: Check your internet connection and ensure you can connect to the server manually with `ssh -i $SSH_PRIVATE_KEY_PATH -p $SSH_PORT $CPANEL_USERNAME@$SERVER_IP_ADDRESS`.

### Deployment Fails at "verify_deployment"

- **Error**: `Health check failed for endpoint...`
  - **Cause**: The application started but is not healthy. This is most likely due to a runtime error.
  - **Solution**: SSH into the server and check the application's error logs. The logs for the Passenger application are typically found in a `logs` or `stderr.log` file within the application directory on the server. Common issues include missing dependencies or incorrect environment variables. The script handles injecting variables, but a typo in a variable name could be the cause.