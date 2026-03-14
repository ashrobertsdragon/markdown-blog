#!/usr/bin/env bash

: <<'DOCSTRING'
Production deployment script for blog application to cPanel hosting (LiteSpeed optimized).

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
- Verifies deployment via health check endpoints with exponential backoff

USAGE:
  ./litespeed_deploy.sh

REQUIRED ENVIRONMENT VARIABLES:
  DOMAIN                       - Domain name
  PRODUCTION_DOMAIN            - Production domain (for confirmation)
  CPANEL_USERNAME              - cPanel/SSH username
  SERVER_IP_ADDRESS            - Server IP for SSH connection
  SSH_PRIVATE_KEY_PATH         - Path to SSH private key
  SSH_PORT                     - SSH port number
  VENV_PATH                    - Path to virtual environment
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
    VENV_PATH
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

  logger -t deploy.sh -p user.info "Creating directory structure on ${SERVER_IP_ADDRESS}"
  run_remote_command "${SERVER_IP_ADDRESS}" "mkdir -p \"${remote_path}/scripts\" \"${remote_path}/build\" \"${remote_path}/backend\"" || return 1

  logger -t deploy.sh -p user.info "Uploading backend to ${SERVER_IP_ADDRESS}"
  rsync -avz --perms --checksum \
    --exclude '__pycache__' \
    -e "ssh -i \"$SSH_PRIVATE_KEY_PATH\" -p \"$SSH_PORT\" \
    -o StrictHostKeyChecking=accept-new" \
    "${PROJECT_ROOT}/monorepo/backend/src/backend/" \
    "${CPANEL_USERNAME}@${SERVER_IP_ADDRESS}:${remote_path}/backend/" || return 1

  rsync -avz --perms --checksum \
    --exclude '__pycache__' \
    -e "ssh -i \"$SSH_PRIVATE_KEY_PATH\" -p \"$SSH_PORT\" \
    -o StrictHostKeyChecking=accept-new" \
    "${PROJECT_ROOT}/monorepo/backend/src/scripts/" \
    "${CPANEL_USERNAME}@${SERVER_IP_ADDRESS}:${remote_path}/scripts/" || return 1

  rsync -avz --perms --checksum \
    -e "ssh -i \"$SSH_PRIVATE_KEY_PATH\" -p \"$SSH_PORT\" \
    -o StrictHostKeyChecking=accept-new" \
    "${PROJECT_ROOT}/monorepo/backend/requirements.txt" \
    "${CPANEL_USERNAME}@${SERVER_IP_ADDRESS}:${remote_path}/requirements.txt" || return 1

  if [[ ! -d "${PROJECT_ROOT}/monorepo/build" ]]; then
    printf "WARNING: Frontend build directory does not exist\n" >&2
    return 1
  fi

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
