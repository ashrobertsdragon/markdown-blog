#!/usr/bin/env bash

: <<'DOCSTRING'
Production deployment script for blog application to cPanel hosting.

SECURITY FEATURES:
- Strict error handling with inherit_errexit and pipefail
- Signal traps to unset secrets on EXIT/INT/TERM
- Input sanitization for environment variables
- SSH key permission validation with TOCTOU mitigation
- Secret suppression in UAPI calls (redirected to /dev/null)
- SSH command construction with proper quoting to prevent injection
- Audit logging to syslog for all security-relevant operations
- Production deployment confirmation prompt

DEPLOYMENT PROCESS:
- Validates environment variables and SSH key permissions
- Provisions PostgreSQL database, user, and privileges (idempotent)
- Uploads code via rsync with checksum verification
- Installs uv on remote server if not present
- Installs application dependencies with uv sync
- Creates database schema using uv run scripts/create_schema.py
- Registers/updates Passenger application with environment variables
- Verifies deployment via health check endpoints with exponential backoff

KNOWN LIMITATIONS:
- Database password appears in process arguments during UAPI calls
  This is a cPanel UAPI limitation - the password is only visible
  briefly during user creation and is automatically cleared by signal traps.
  Risk is minimized through:
    1. Rapid execution (minimal exposure window)
    2. Signal traps clearing secrets immediately on exit
    3. UAPI output suppression to prevent logging

USAGE:
  ./deploy.sh

REQUIRED ENVIRONMENT VARIABLES:
  DOMAIN                       - Domain name
  PRODUCTION_DOMAIN            - Production domain
  CPANEL_USERNAME              - cPanel/SSH username
  SERVER_IP_ADDRESS            - Server IP for SSH connection
  SSH_PRIVATE_KEY_PATH         - Path to SSH private key
  SSH_PORT                     - SSH port number
  DB_USER                      - PostgreSQL username
  DB_PASSWORD                  - PostgreSQL password
  GITHUB_PERSONAL_ACCESS_TOKEN - GitHub API token
  RESEND_API_KEY               - Resend email service API key
  CLERK_PUBLISHABLE_KEY        - Clerk authentication public key
  CLERK_SECRET_KEY             - Clerk authentication secret key

EXIT CODES:
  0 - Deployment successful
  1 - Validation failure, deployment error, or user cancellation
DOCSTRING

set -Eeuo pipefail
shopt -s inherit_errexit
IFS=$'\n\t'

readonly SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)"
readonly PROJECT_ROOT="$(cd -- "${SCRIPT_DIR}/../.." && pwd -P)"
readonly DOMAIN=$DOMAIN
readonly APP_NAME="MarkdownBlog"
readonly BASE_URI="/"

source "${SCRIPT_DIR}/utils/deploy_shared.sh"

setup_test_mocks

trap cleanup_secrets EXIT INT TERM

validate_environment() {
  local required_vars=(
    DOMAIN
    PRODUCTION_DOMAIN
    CPANEL_USERNAME
    SERVER_IP_ADDRESS
    SSH_PRIVATE_KEY_PATH
    SSH_PORT
    DB_USER
    DB_PASSWORD
    GITHUB_PERSONAL_ACCESS_TOKEN
    RESEND_API_KEY
    CLERK_PUBLISHABLE_KEY
    CLERK_SECRET_KEY
  )

  for var in "${required_vars[@]}"; do
    if [[ -z "${!var:-}" ]]; then
      printf "ERROR: Required environment variable %s is not set\n" "$var" >&2
      return 1
    fi
  done

  sanitize_input "${CPANEL_USERNAME}" || return 1
  sanitize_input "${SERVER_IP_ADDRESS}" || return 1

  return 0
}

upload_code() {
  local remote_path
  remote_path="$(get_remote_app_path)"

  local backend_src="${PROJECT_ROOT}/monorepo/backend/src/backend/"
  if [[ ! -d "$backend_src" ]] || [[ -z "$(ls -A "$backend_src" 2>/dev/null || true)" ]]; then
    printf "ERROR: Backend source directory is empty or missing\n" >&2
    return 1
  fi

  logger -t deploy.sh -p user.info "Creating remote directory structure at ${SERVER_IP_ADDRESS}"
  ssh -i "$SSH_PRIVATE_KEY_PATH" -p "$SSH_PORT" -o StrictHostKeyChecking=accept-new \
    "${CPANEL_USERNAME}@${SERVER_IP_ADDRESS}" \
    "mkdir -p ${remote_path}/src" || return 1

  logger -t deploy.sh -p user.info "Uploading backend source code to ${SERVER_IP_ADDRESS}"
  rsync -avz --perms --checksum --delete \
    --exclude '.git' \
    --exclude '__pycache__' \
    --exclude '*.pyc' \
    --exclude '.pytest_cache' \
    --exclude '.mypy_cache' \
    --exclude '.ruff_cache' \
    -e "ssh -i \"$SSH_PRIVATE_KEY_PATH\" -p \"$SSH_PORT\" \
    -o StrictHostKeyChecking=accept-new" "$backend_src" \
    "${CPANEL_USERNAME}@${SERVER_IP_ADDRESS}:${remote_path}/src/backend/" || return 1

  logger -t deploy.sh -p user.info "Uploading passenger_wsgi.py to ${SERVER_IP_ADDRESS}"
  rsync -avz --perms --checksum \
    -e "ssh -i \"$SSH_PRIVATE_KEY_PATH\" -p \"$SSH_PORT\" \
    -o StrictHostKeyChecking=accept-new" \
    "${PROJECT_ROOT}/monorepo/backend/src/passenger_wsgi.py" \
    "${CPANEL_USERNAME}@${SERVER_IP_ADDRESS}:${remote_path}/" || return 1

  logger -t deploy.sh -p user.info "Uploading scripts directory to ${SERVER_IP_ADDRESS}"
  rsync -avz --perms --checksum --delete \
    --exclude '__pycache__' \
    --exclude '*.pyc' \
    -e "ssh -i \"$SSH_PRIVATE_KEY_PATH\" -p \"$SSH_PORT\" \
    -o StrictHostKeyChecking=accept-new" \
    "${PROJECT_ROOT}/monorepo/backend/src/scripts/" \
    "${CPANEL_USERNAME}@${SERVER_IP_ADDRESS}:${remote_path}/src/scripts/" || return 1

  logger -t deploy.sh -p user.info "Uploading pyproject.toml and uv.lock to ${SERVER_IP_ADDRESS}"
  rsync -avz --perms --checksum \
    -e "ssh -i \"$SSH_PRIVATE_KEY_PATH\" -p \"$SSH_PORT\" \
    -o StrictHostKeyChecking=accept-new" \
    "${PROJECT_ROOT}/monorepo/backend/pyproject.toml" \
    "${PROJECT_ROOT}/monorepo/backend/uv.lock" \
    "${CPANEL_USERNAME}@${SERVER_IP_ADDRESS}:${remote_path}/" || return 1

  if [[ -d "${PROJECT_ROOT}/monorepo/build" ]]; then
    local frontend_src="${PROJECT_ROOT}/monorepo/build/"
    if [[ -z "$(ls -A "$frontend_src" 2>/dev/null || true)" ]]; then
      printf "WARNING: Frontend build directory is empty\n" >&2
    else
      logger -t deploy.sh -p user.info "Uploading frontend build to ${SERVER_IP_ADDRESS}"
      rsync -avz --perms --checksum --delete \
        --exclude '.git' \
        --exclude 'node_modules' \
        --exclude '.next' \
        --exclude 'dist' \
        -e "ssh -i \"$SSH_PRIVATE_KEY_PATH\" -p \"$SSH_PORT\" -o StrictHostKeyChecking=accept-new" \
        "$frontend_src" \
        "${CPANEL_USERNAME}@${SERVER_IP_ADDRESS}:${remote_path}/build/" || return 1
    fi
  fi

  return 0
}

ensure_uv_installed() {
  logger -t deploy.sh -p user.info "Checking for uv installation on ${SERVER_IP_ADDRESS}"
  run_remote_command "${SERVER_IP_ADDRESS}" bash <<'REMOTE_SCRIPT' || return 1
set -Eeuo pipefail

if command -v uv &>/dev/null; then
  echo "✓ uv is already installed"
  uv --version
else
  echo "Installing uv..."
  curl -LsSf https://astral.sh/uv/install.sh | sh
  export PATH="$HOME/.cargo/bin:$PATH"

  if ! command -v uv &>/dev/null; then
    echo "ERROR: Failed to install uv" >&2
    exit 1
  fi

  echo "✓ uv installed successfully"
  uv --version
fi
REMOTE_SCRIPT

  return 0
}

install_application() {
  logger -t deploy.sh -p user.info "Installing application with uv on ${SERVER_IP_ADDRESS}"
  run_remote_command "${SERVER_IP_ADDRESS}" bash <<'REMOTE_SCRIPT' || return 1
set -Eeuo pipefail

export PATH="$HOME/.cargo/bin:$PATH"
export UV_PROJECT_ENVIRONMENT="$HOME/virtualenv/seeash"
cd ~/seeash

echo "Installing application dependencies with uv..."
uv sync --frozen

echo "✓ Application dependencies installed"
REMOTE_SCRIPT

  return 0
}

run_schema() {
  local database_name
  database_name="$(get_database_name)"

  logger -t deploy.sh -p user.info "Creating database schema on ${SERVER_IP_ADDRESS}"
  run_remote_command "${SERVER_IP_ADDRESS}" bash -s "${database_name}" "${DB_USER}" "${DB_PASSWORD}" <<'REMOTE_SCRIPT' || return 1
set -Eeuo pipefail

export PATH="$HOME/.cargo/bin:$PATH"
export UV_PROJECT_ENVIRONMENT="$HOME/virtualenv/seeash"
cd ~/seeash

export DB_NAME="$1"
export DB_USER="$2"
export DB_PASSWORD="$3"
export FLASK_ENV="PRODUCTION"

echo "Creating database schema..."
uv run create-schema
REMOTE_SCRIPT

  return 0
}

register_passenger() {
  local remote_path
  remote_path="$(get_remote_app_path)"
  local database_name
  database_name="$(get_database_name)"
  local venv_path="/home/${CPANEL_USERNAME}/virtualenv/seeash"

  logger -t deploy.sh -p user.info "Registering Passenger application: ${APP_NAME}"

  local app_list
  app_list=$(uapi_call PassengerApps list_applications) || return 1

  local app_exists=0
  if uapi_list_contains "$app_list" "$APP_NAME"; then
    app_exists=1
  fi

  if [[ "$app_exists" -eq 0 ]]; then
    logger -t deploy.sh -p user.notice "Creating new Passenger application with environment variables"
    uapi_call PassengerApps register_application \
      name="$APP_NAME" \
      path="$remote_path" \
      domain="$DOMAIN" \
      base_uri="$BASE_URI" \
      deployment_mode="production" \
      envvar_name="DB_NAME" envvar_value="$database_name" \
      envvar_name="DB_USER" envvar_value="$DB_USER" \
      envvar_name="DB_PASSWORD" envvar_value="$DB_PASSWORD" \
      envvar_name="GITHUB_PERSONAL_ACCESS_TOKEN" envvar_value="$GITHUB_PERSONAL_ACCESS_TOKEN" \
      envvar_name="RESEND_API_KEY" envvar_value="$RESEND_API_KEY" \
      envvar_name="CLERK_PUBLISHABLE_KEY" envvar_value="$CLERK_PUBLISHABLE_KEY" \
      envvar_name="CLERK_SECRET_KEY" envvar_value="$CLERK_SECRET_KEY" \
      envvar_name="VENV_PATH" envvar_value="$venv_path" >/dev/null 2>&1 || return 1
  else
    logger -t deploy.sh -p user.notice "Updating existing Passenger application path and environment variables"
    uapi_call PassengerApps edit_application \
      name="$APP_NAME" \
      path="$remote_path" \
      envvar_name="DB_NAME" envvar_value="$database_name" \
      envvar_name="DB_USER" envvar_value="$DB_USER" \
      envvar_name="DB_PASSWORD" envvar_value="$DB_PASSWORD" \
      envvar_name="GITHUB_PERSONAL_ACCESS_TOKEN" envvar_value="$GITHUB_PERSONAL_ACCESS_TOKEN" \
      envvar_name="RESEND_API_KEY" envvar_value="$RESEND_API_KEY" \
      envvar_name="CLERK_PUBLISHABLE_KEY" envvar_value="$CLERK_PUBLISHABLE_KEY" \
      envvar_name="CLERK_SECRET_KEY" envvar_value="$CLERK_SECRET_KEY" \
      envvar_name="VENV_PATH" envvar_value="$venv_path" >/dev/null 2>&1 || return 1
  fi

  return 0
}

main() {
  logger -t deploy.sh -p user.notice "Starting deployment to ${DOMAIN}"
  printf "Starting deployment to %s...\n" "$DOMAIN"

  confirm_production_deployment || return 1

  validate_environment || return 1
  printf "✓ Environment variables validated\n"

  setup_ssh_key || return 1
  printf "✓ SSH key configured\n"

  provision_database || return 1
  printf "✓ Database provisioned\n"

  upload_code || return 1
  printf "✓ Code uploaded\n"

  ensure_uv_installed || return 1
  printf "✓ uv installation verified\n"

  install_application || return 1
  printf "✓ Application installed\n"

  run_schema || return 1
  printf "✓ Database schema created\n"

  register_passenger || return 1
  printf "✓ Passenger application registered\n"

  verify_deployment || return 1
  printf "✓ Deployment verified\n"

  logger -t deploy.sh -p user.notice "Deployment completed successfully for ${DOMAIN}"
  printf "\nDeployment completed successfully!\n"
  printf "Application URL: https://%s\n" "$DOMAIN"

  return 0
}

if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
  main "$@"
fi
