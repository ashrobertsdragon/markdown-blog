#!/usr/bin/env bash

: <<'DOCSTRING'
Production deployment script for the blog application to cPanel shared hosting
running CloudLinux + LiteSpeed (lswsgi via the CloudLinux Python Selector).

HOW THIS HOST SERVES THE APP:
- The app is run by LiteSpeed's `lswsgi`, configured by the CloudLinux Python
  Selector (the `cloudlinux-selector` CLI). It loads `passenger_wsgi.py` from
  the application root using the selector-managed virtualenv.
- Runtime environment variables (DB_*, CLERK_*, GITHUB_*, RESEND_*, BUILD_DIR,
  FLASK_ENV) are injected into the lswsgi process by the selector, NOT by this
  script and NOT by .htaccess. The app-root .htaccess only carries the routing
  directives that hand requests to lswsgi; it must remain in place.

ONE-TIME MANUAL SETUP (NOT performed by this script):
- The CloudLinux Python application "seeash" must already be registered
  (cloudlinux-selector create ...) with its env vars and the PostgreSQL
  database/user provisioned. This script deploys code and dependencies into
  that existing application.

DEPLOYMENT PROCESS (idempotent, safe to re-run):
- Validates required environment variables and SSH key permissions
- Exports a pinned requirements file from the uv lockfile
- Uploads backend code, scripts, frontend build, entry point and requirements
- Installs dependencies into the selector-managed virtualenv
- Restarts the application (touch tmp/restart.txt)
- Verifies deployment via health endpoints with exponential backoff and prints
  diagnostics (HTTP status, body, remote error log) on failure

USAGE:
  ./litespeed_deploy.sh

REQUIRED ENVIRONMENT VARIABLES:
  DOMAIN               - Domain name serving the application
  PRODUCTION_DOMAIN    - Production domain (used for the confirmation prompt)
  CPANEL_USERNAME      - cPanel/SSH username
  SERVER_IP_ADDRESS    - Server IP for the SSH connection
  SSH_PRIVATE_KEY_PATH - Path to the SSH private key
  SSH_PORT             - SSH port number

EXIT CODES:
  0 - Deployment successful
  1 - Validation failure, deployment error, or user cancellation
DOCSTRING

set -Eeuo pipefail
shopt -s inherit_errexit
IFS=$'\n\t'

readonly SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)"
readonly PROJECT_ROOT="$(cd -- "${SCRIPT_DIR}/.." && pwd -P)"
readonly DOMAIN=$DOMAIN
readonly APP_ROOT_NAME="seeash"

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

export_requirements() {
  logger -t litespeed_deploy.sh -p user.info "Exporting pinned requirements from uv lockfile"
  (
    cd -- "${PROJECT_ROOT}/backend"
    uv export --frozen --no-dev --no-emit-project --no-hashes \
      -o requirements.txt
  ) || return 1

  return 0
}

upload_code() {
  local remote_path
  remote_path="$(get_remote_app_path)"
  local ssh_remote="ssh -i \"$SSH_PRIVATE_KEY_PATH\" -p \"$SSH_PORT\" -o StrictHostKeyChecking=accept-new"

  logger -t litespeed_deploy.sh -p user.info "Creating directory structure on ${SERVER_IP_ADDRESS}"
  run_remote_command "${SERVER_IP_ADDRESS}" \
    "mkdir -p \"${remote_path}/scripts\" \"${remote_path}/build\" \"${remote_path}/backend\" \"${remote_path}/tmp\"" || return 1

  logger -t litespeed_deploy.sh -p user.info "Uploading backend source to ${SERVER_IP_ADDRESS}"
  rsync -avz --perms --checksum --delete \
    --exclude '__pycache__' \
    --exclude '*.pyc' \
    -e "$ssh_remote" \
    "${PROJECT_ROOT}/backend/src/backend/" \
    "${CPANEL_USERNAME}@${SERVER_IP_ADDRESS}:${remote_path}/backend/" || return 1

  logger -t litespeed_deploy.sh -p user.info "Uploading scripts to ${SERVER_IP_ADDRESS}"
  rsync -avz --perms --checksum --delete \
    --exclude '__pycache__' \
    --exclude '*.pyc' \
    -e "$ssh_remote" \
    "${PROJECT_ROOT}/backend/src/scripts/" \
    "${CPANEL_USERNAME}@${SERVER_IP_ADDRESS}:${remote_path}/scripts/" || return 1

  logger -t litespeed_deploy.sh -p user.info "Uploading WSGI entry point to ${SERVER_IP_ADDRESS}"
  rsync -avz --perms --checksum \
    -e "$ssh_remote" \
    "${PROJECT_ROOT}/backend/src/passenger_wsgi.py" \
    "${CPANEL_USERNAME}@${SERVER_IP_ADDRESS}:${remote_path}/passenger_wsgi.py" || return 1

  logger -t litespeed_deploy.sh -p user.info "Uploading requirements to ${SERVER_IP_ADDRESS}"
  rsync -avz --perms --checksum \
    -e "$ssh_remote" \
    "${PROJECT_ROOT}/backend/requirements.txt" \
    "${CPANEL_USERNAME}@${SERVER_IP_ADDRESS}:${remote_path}/requirements.txt" || return 1

  if [[ ! -d "${PROJECT_ROOT}/build" ]]; then
    printf "ERROR: Frontend build directory does not exist\n" >&2
    return 1
  fi

  if [[ -z "$(ls -A "${PROJECT_ROOT}/build" 2>/dev/null || true)" ]]; then
    printf "ERROR: Frontend build directory is empty\n" >&2
    return 1
  fi

  logger -t litespeed_deploy.sh -p user.info "Uploading frontend build to ${SERVER_IP_ADDRESS}"
  rsync -avz --perms --checksum --delete \
    --exclude '.git' \
    --exclude 'node_modules' \
    -e "$ssh_remote" \
    "${PROJECT_ROOT}/build/" \
    "${CPANEL_USERNAME}@${SERVER_IP_ADDRESS}:${remote_path}/build/" || return 1

  return 0
}

install_dependencies() {
  local remote_path
  remote_path="$(get_remote_app_path)"

  logger -t litespeed_deploy.sh -p user.info "Installing dependencies into the selector virtualenv"
  run_remote_command "${SERVER_IP_ADDRESS}" \
    "cloudlinux-selector install-modules --json --interpreter python --app-root \"${APP_ROOT_NAME}\" --requirements-file \"${remote_path}/requirements.txt\"" || return 1

  return 0
}

restart_app() {
  local remote_path
  remote_path="$(get_remote_app_path)"

  logger -t litespeed_deploy.sh -p user.info "Restarting application"
  run_remote_command "${SERVER_IP_ADDRESS}" \
    "mkdir -p ${remote_path}/tmp && touch ${remote_path}/tmp/restart.txt" || return 1

  return 0
}

verify_deployment() {
  local max_retries=5
  local base_delay=2
  local remote_path
  remote_path="$(get_remote_app_path)"

  local endpoint code body_file
  for endpoint in "/api/health" "/api/health/db" "/api/health/github"; do
    if retry_with_backoff "$max_retries" "$base_delay" \
      curl -sS -f -m 15 "https://${DOMAIN}${endpoint}" >/dev/null 2>&1; then
      printf "  ✓ %s healthy\n" "$endpoint"
      continue
    fi

    body_file="$(mktemp)"
    code="$(curl -sS -o "$body_file" -w '%{http_code}' -m 15 \
      "https://${DOMAIN}${endpoint}" 2>/dev/null || true)"
    printf "ERROR: Health check failed for %s (HTTP %s)\n" "$endpoint" "$code" >&2
    printf "Response body:\n%s\n" "$(head -c 500 "$body_file" 2>/dev/null || true)" >&2
    rm -f "$body_file"
    printf "Remote application error log (last 30 lines):\n" >&2
    run_remote_command "${SERVER_IP_ADDRESS}" \
      "tail -n 30 \"${remote_path}/stderr.log\" 2>/dev/null || true" >&2 || true
    return 1
  done

  return 0
}

main() {
  logger -t litespeed_deploy.sh -p user.notice "Starting deployment to ${DOMAIN}"
  printf "Starting deployment to %s...\n" "$DOMAIN"

  confirm_production_deployment || return 1

  validate_environment || return 1
  printf "✓ Environment variables validated\n"

  setup_ssh_key || return 1
  printf "✓ SSH key configured\n"

  export_requirements || return 1
  printf "✓ Requirements exported\n"

  upload_code || return 1
  printf "✓ Code uploaded\n"

  install_dependencies || return 1
  printf "✓ Dependencies installed\n"

  restart_app || return 1
  printf "✓ Application restarted\n"

  verify_deployment || return 1
  printf "✓ Deployment verified\n"

  logger -t litespeed_deploy.sh -p user.notice "Deployment completed successfully for ${DOMAIN}"
  printf "\nDeployment completed successfully!\n"
  printf "Application URL: https://%s\n" "$DOMAIN"

  return 0
}

if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
  main "$@"
fi
