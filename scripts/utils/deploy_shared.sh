#!/usr/bin/env bash

# Common deployment utilities for blog application

cleanup_secrets() {
  unset DB_PASSWORD
  unset GITHUB_PERSONAL_ACCESS_TOKEN
  unset RESEND_API_KEY
  unset CLERK_PUBLISHABLE_KEY
  unset CLERK_SECRET_KEY
}

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

  if command -v uapi &>/dev/null; then
    local uapi_output
    local exit_status
    uapi_output=$(uapi --output=jsonpretty "$module" "$function" "$@" 2>/dev/null)
    exit_status=$?

    if [[ $exit_status -ne 0 ]]; then
      logger -t "deploy_utils.bash[uapi_call]" -p user.warning "uapi ${module}::${function} failed with exit status ${exit_status}"
      printf '%s\n' '{"data":[]}'
      return "${exit_status}"
    fi

    printf '%s\n' "${uapi_output}"
  else
    local ssh_cmd="uapi --output=jsonpretty \"$module\" \"$function\""
    for arg in "$@"; do
      ssh_cmd+=" \"$arg\""
    done

    local uapi_output
    uapi_output=$(run_remote_command "${SERVER_IP_ADDRESS}" "${ssh_cmd}" 2>/dev/null) || return 1
    printf '%s\n' "${uapi_output}"
  fi
}

uapi_list_contains() {
  local json_output="$1"
  local search_term="$2"

  echo "$json_output" | grep -qw "$search_term"
}

get_remote_app_path() {
  echo "/home/${CPANEL_USERNAME}/seeash"
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

setup_ssh_key() {
  if [[ ! -f "$SSH_PRIVATE_KEY_PATH" ]]; then
    logger -t "deploy_utils.bash[setup_ssh_key]" -p user.error "SSH key file not found at ${SSH_PRIVATE_KEY_PATH}"
    printf "ERROR: SSH key file not found at %s\n" "$SSH_PRIVATE_KEY_PATH" >&2
    return 1
  fi

  chmod 600 -- "$SSH_PRIVATE_KEY_PATH" || return 1

  local actual_perms
  actual_perms=$(stat -c %a "$SSH_PRIVATE_KEY_PATH" 2>/dev/null || stat -f %Lp "$SSH_PRIVATE_KEY_PATH" 2>/dev/null)

  if [[ -z "$actual_perms" ]] || [[ "$actual_perms" != "600" ]]; then
    logger -t "deploy_utils.bash[setup_ssh_key]" -p user.error "Failed to set or verify proper permissions (600) on SSH key"
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
    logger -t deploy_utils.bash -p user.info "Creating database: ${database_name}"
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
    logger -t deploy_utils.bash -p user.info "Creating PostgreSQL user: ${username}"
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
    logger -t deploy_utils.bash -p user.info "Granting privileges to ${username} on ${database_name}"
    uapi_call Postgresql grant_all_privileges \
      user="$username" \
      database="$database_name" >/dev/null 2>&1 || return 1
  fi

  return 0
}

provision_database() {
  local database_name
  database_name="$(get_database_name)"

  logger -t deploy_utils.bash -p user.info "Provisioning database: ${database_name}"

  ensure_database_exists "$database_name" || return 1
  ensure_user_exists "$DB_USER" "$DB_PASSWORD" || return 1
  ensure_privileges_granted "$DB_USER" "$database_name" || return 1

  return 0
}

verify_deployment() {
  local max_retries=5
  local base_delay=2

  for endpoint in "/api/health" "/api/health/db" "/api/health/github"; do
    if ! retry_with_backoff "$max_retries" "$base_delay" curl -sS -f -m 10 "https://${DOMAIN}${endpoint}" >/dev/null 2>&1; then
      printf "ERROR: Health check failed for endpoint %s after %d retries\n" "$endpoint" "$max_retries" >&2
      return 1
    fi
  done

  return 0
}

confirm_production_deployment() {
  local prod_domain="${1:-$PRODUCTION_DOMAIN}"
  if [[ "${DOMAIN}" == "${prod_domain}" ]] && [[ -t 0 ]] && [[ -z "${BATS_TEST_TMPDIR:-}" ]]; then
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

setup_test_mocks() {
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
}
