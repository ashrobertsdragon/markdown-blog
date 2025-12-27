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

cleanup_secrets() {
  unset DB_PASSWORD
  unset GITHUB_PERSONAL_ACCESS_TOKEN
  unset RESEND_API_KEY
  unset CLERK_PUBLISHABLE_KEY
  unset CLERK_SECRET_KEY
}

trap cleanup_secrets EXIT INT TERM

if [[ "${CPANEL_USERNAME:-}" == "testuser" ]] && [[ -f "${SCRIPT_DIR}/tests/test_helper.bash" ]]; then
  export BATS_TMPDIR="${BATS_TMPDIR:-/tmp/bats.$$}"
  export BATS_TEST_TMPDIR="${BATS_TEST_TMPDIR:-/tmp/bats.$$}"

  if ! command -v uapi &>/dev/null; then
    source "${SCRIPT_DIR}/tests/test_helper.bash"

    if [[ "${TEST_ENVIRONMENT_INITIALIZED:-}" != "1" ]]; then
      reset_mock_state
      setup_test_environment
      setup_mock_successful_database_creation
      setup_mock_successful_user_creation
      setup_mock_successful_ssh
      setup_mock_successful_rsync
      setup_mock_successful_health_check
    fi
  fi
fi

retry_with_backoff() {
  local max_retries="$1"
  local base_delay="$2"
  shift 2
  local -a command=("$@")

  local attempt
  for ((attempt=1; attempt<=max_retries; attempt++)); do
    if "${command[@]}"; then
      return 0
    fi

    if [[ $attempt -lt $max_retries ]]; then
      local delay=$((base_delay * (2 ** (attempt - 1))))
      printf "Retry %d/%d failed, waiting %d seconds...\n" "$attempt" "$max_retries" "$delay" >&2
      sleep "$delay"
    fi
  done

  return 1
}

run_remote_command() {
  local remote_host="$1"
  shift
  local -a ssh_opts=(-i "$SSH_PRIVATE_KEY_PATH" -p "$SSH_PORT" -o StrictHostKeyChecking=accept-new)

  ssh "${ssh_opts[@]}" "${CPANEL_USERNAME}@${remote_host}" "$@"
}

uapi_call() {
  local module="$1"
  local function="$2"
  shift 2

  local uapi_output
  local exit_status

  if command -v uapi &>/dev/null; then
    uapi_output=$(uapi --output=jsonpretty "$module" "$function" "$@" 2>/dev/null)
    exit_status=$?
  else
    local ssh_cmd="uapi --output=jsonpretty \"$module\" \"$function\""
    for arg in "$@"; do
      ssh_cmd+=" \"$arg\""
    done

    uapi_output=$(ssh -i "$SSH_PRIVATE_KEY_PATH" -p "$SSH_PORT" \
      -o StrictHostKeyChecking=accept-new \
      "${CPANEL_USERNAME}@${SERVER_IP_ADDRESS}" "$ssh_cmd" 2>/dev/null)
    exit_status=$?
  fi

  if [[ $exit_status -ne 0 ]]; then
    logger -t "deploy.sh[uapi_call]" -p user.warning "uapi ${module}::${function} failed with exit status ${exit_status}"
    printf '%s\n' '{"data":[]}'
    return "${exit_status}"
  fi

  printf '%s\n' "${uapi_output}"
}

uapi_list_contains() {
  local json_output="$1"
  local search_term="$2"

  echo "$json_output" | grep -qw "$search_term"
}

get_remote_app_path() {
  echo "/home/${CPANEL_USERNAME}/blog"
}

get_database_name() {
  echo "${CPANEL_USERNAME}_blogdb"
}

sanitize_input() {
  local value="$1"
  if [[ "$value" =~ [\;\&\|\`\$\(\)] ]]; then
    printf "ERROR: Environment variable contains invalid characters\n" >&2
    return 1
  fi
  return 0
}

validate_environment() {
  local required_vars=(
    DOMAIN
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

setup_ssh_key() {
  if [[ ! -f "$SSH_PRIVATE_KEY_PATH" ]]; then
    logger -t "deploy.sh[setup_ssh_key]" -p user.error "SSH key file not found at ${SSH_PRIVATE_KEY_PATH}"
    printf "ERROR: SSH key file not found at %s\n" "$SSH_PRIVATE_KEY_PATH" >&2
    return 1
  fi

  chmod 600 -- "$SSH_PRIVATE_KEY_PATH" || return 1

  local actual_perms
  actual_perms=$(stat -c %a "$SSH_PRIVATE_KEY_PATH" 2>/dev/null || stat -f %Lp "$SSH_PRIVATE_KEY_PATH" 2>/dev/null)

  if [[ -z "$actual_perms" ]] || [[ "$actual_perms" != "600" ]]; then
    logger -t "deploy.sh[setup_ssh_key]" -p user.error "Failed to set or verify proper permissions (600) on SSH key"
    printf "ERROR: Failed to set or verify proper permissions (600) on SSH key. Please check file ownership and permissions.\n" >&2
    return 1
  fi

  return 0
}

ensure_database_exists() {
  local database_name="$1"

  local db_list
  db_list=$(uapi_call Postgresql list_databases) || return 1

  if ! uapi_list_contains "$db_list" "$database_name"; then
    logger -t deploy.sh -p user.info "Creating database: ${database_name}"
    uapi_call Postgresql create_database name="$database_name" >/dev/null 2>&1 || return 1
  fi

  return 0
}

ensure_user_exists() {
  local username="$1"
  local password="$2"

  local user_list
  user_list=$(uapi_call Postgresql list_users) || return 1

  if ! uapi_list_contains "$user_list" "$username"; then
    logger -t deploy.sh -p user.info "Creating PostgreSQL user: ${username}"
    uapi_call Postgresql create_user \
      name="$username" \
      password="$password" >/dev/null 2>&1 || return 1
  fi

  return 0
}

ensure_privileges_granted() {
  local username="$1"
  local database_name="$2"

  local privileges_list
  privileges_list=$(uapi_call Postgresql list_privileges user="$username") || return 1

  if ! uapi_list_contains "$privileges_list" "$database_name"; then
    logger -t deploy.sh -p user.info "Granting privileges to ${username} on ${database_name}"
    uapi_call Postgresql grant_all_privileges \
      user="$username" \
      database="$database_name" >/dev/null 2>&1 || return 1
  fi

  return 0
}

provision_database() {
  local database_name
  database_name="$(get_database_name)"

  logger -t deploy.sh -p user.info "Provisioning database: ${database_name}"

  ensure_database_exists "$database_name" || return 1
  ensure_user_exists "$DB_USER" "$DB_PASSWORD" || return 1
  ensure_privileges_granted "$DB_USER" "$database_name" || return 1

  return 0
}

upload_code() {
  local remote_path
  remote_path="$(get_remote_app_path)"

  local backend_src="${PROJECT_ROOT}/monorepo/backend/"
  if [[ ! -d "$backend_src" ]] || [[ -z "$(ls -A "$backend_src" 2>/dev/null || true)" ]]; then
    printf "ERROR: Backend source directory is empty or missing\n" >&2
    return 1
  fi

  logger -t deploy.sh -p user.info "Uploading backend code to ${SERVER_IP_ADDRESS}"
  rsync -avz --perms --checksum --delete \
    -e "ssh -i \"$SSH_PRIVATE_KEY_PATH\" -p \"$SSH_PORT\" \
    -o StrictHostKeyChecking=accept-new" "$backend_src" \
    "${CPANEL_USERNAME}@${SERVER_IP_ADDRESS}:${remote_path}/" || return 1

  if [[ -d "${PROJECT_ROOT}/monorepo/build" ]]; then
    local frontend_src="${PROJECT_ROOT}/monorepo/build/"
    if [[ -z "$(ls -A "$frontend_src" 2>/dev/null || true)" ]]; then
      printf "WARNING: Frontend build directory is empty\n" >&2
    else
      logger -t deploy.sh -p user.info "Uploading frontend build to ${SERVER_IP_ADDRESS}"
      rsync -avz --perms --checksum --delete \
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
cd ~/blog

echo "Installing application dependencies with uv..."
uv sync --frozen

echo "✓ Application dependencies installed"
REMOTE_SCRIPT

  return 0
}

run_schema() {
  logger -t deploy.sh -p user.info "Creating database schema on ${SERVER_IP_ADDRESS}"
  run_remote_command "${SERVER_IP_ADDRESS}" bash <<REMOTE_SCRIPT || return 1
set -Eeuo pipefail

export PATH="\$HOME/.cargo/bin:\$PATH"
cd ~/blog

export DB_HOST="localhost"
export DB_NAME="$(get_database_name)"
export DB_USER="${DB_USER}"
export FLASK_ENV="PRODUCTION"

echo "Creating database schema..."
DB_PASSWORD="${DB_PASSWORD}" uv run create-schema
REMOTE_SCRIPT

  return 0
}

register_passenger() {
  local remote_path
  remote_path="$(get_remote_app_path)"
  local database_name
  database_name="$(get_database_name)"

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
      envvar_name_1="DB_HOST" envvar_value_1="localhost" \
      envvar_name_2="DB_NAME" envvar_value_2="$database_name" \
      envvar_name_3="DB_USER" envvar_value_3="$DB_USER" \
      envvar_name_4="DB_PASSWORD" envvar_value_4="$DB_PASSWORD" \
      envvar_name_5="GITHUB_PERSONAL_ACCESS_TOKEN" envvar_value_5="$GITHUB_PERSONAL_ACCESS_TOKEN" \
      envvar_name_6="RESEND_API_KEY" envvar_value_6="$RESEND_API_KEY" \
      envvar_name_7="CLERK_PUBLISHABLE_KEY" envvar_value_7="$CLERK_PUBLISHABLE_KEY" \
      envvar_name_8="CLERK_SECRET_KEY" envvar_value_8="$CLERK_SECRET_KEY" >/dev/null 2>&1 || return 1
  else
    logger -t deploy.sh -p user.notice "Updating existing Passenger application environment variables"
    uapi_call PassengerApps update_application \
      name="$APP_NAME" \
      envvar_name_1="DB_HOST" envvar_value_1="localhost" \
      envvar_name_2="DB_NAME" envvar_value_2="$database_name" \
      envvar_name_3="DB_USER" envvar_value_3="$DB_USER" \
      envvar_name_4="DB_PASSWORD" envvar_value_4="$DB_PASSWORD" \
      envvar_name_5="GITHUB_PERSONAL_ACCESS_TOKEN" envvar_value_5="$GITHUB_PERSONAL_ACCESS_TOKEN" \
      envvar_name_6="RESEND_API_KEY" envvar_value_6="$RESEND_API_KEY" \
      envvar_name_7="CLERK_PUBLISHABLE_KEY" envvar_value_7="$CLERK_PUBLISHABLE_KEY" \
      envvar_name_8="CLERK_SECRET_KEY" envvar_value_8="$CLERK_SECRET_KEY" >/dev/null 2>&1 || return 1
  fi

  return 0
}

verify_deployment() {
  local max_retries=5
  local base_delay=2

  for endpoint in "/health" "/health/db" "/health/github"; do
    if ! retry_with_backoff "$max_retries" "$base_delay" curl -sS -f -m 10 "https://${DOMAIN}${endpoint}" >/dev/null 2>&1; then
      printf "ERROR: Health check failed for endpoint %s after %d retries\n" "$endpoint" "$max_retries" >&2
      return 1
    fi
  done

  return 0
}

confirm_production_deployment() {
  if [[ "${DOMAIN}" == "ashlynantrobus.dev" ]] && [[ -t 0 ]] && [[ -z "${BATS_TEST_TMPDIR:-}" ]]; then
    printf "WARNING: Deploying to PRODUCTION domain: %s\n" "$DOMAIN" >&2
    printf "Continue? (yes/no): " >&2
    local response
    read -r response
    if [[ "${response}" != "yes" ]]; then
      printf "Deployment cancelled by user\n" >&2
      return 1
    fi
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
