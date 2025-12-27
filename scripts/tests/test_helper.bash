#!/usr/bin/env bash

set -eo pipefail

export BATS_TEST_TMPDIR="${BATS_TEST_TMPDIR:-${BATS_TMPDIR}}"

declare -gxA MOCK_CALL_LOG
declare -gxA MOCK_CALL_COUNT
declare -gxA MOCK_EXIT_CODES
declare -gxA MOCK_OUTPUTS

reset_mock_state() {
  unset MOCK_CALL_LOG MOCK_CALL_COUNT MOCK_EXIT_CODES MOCK_OUTPUTS MOCK_CHMOD_FAIL_ON_600
  declare -gA MOCK_CALL_LOG
  declare -gA MOCK_CALL_COUNT
  declare -gA MOCK_EXIT_CODES
  declare -gA MOCK_OUTPUTS
}

log_mock_call() {
  local cmd="$1"
  shift
  local args="$*"

  MOCK_CALL_COUNT["$cmd"]=$((${MOCK_CALL_COUNT["$cmd"]:-0} + 1))
  local call_key="${cmd}_${MOCK_CALL_COUNT["$cmd"]}"
  MOCK_CALL_LOG["$call_key"]="$args"
}

was_command_called() {
  local cmd="$1"
  [[ ${MOCK_CALL_COUNT["$cmd"]:-0} -gt 0 ]]
}

get_command_call_count() {
  local cmd="$1"
  echo "${MOCK_CALL_COUNT["$cmd"]:-0}"
}

get_command_args() {
  local cmd="$1"
  local call_num="${2:-1}"
  local call_key="${cmd}_${call_num}"
  echo "${MOCK_CALL_LOG["$call_key"]:-}"
}

assert_command_called() {
  local cmd="$1"
  local expected_count="${2:-1}"
  local actual_count="${MOCK_CALL_COUNT["$cmd"]:-0}"

  if [[ "$actual_count" -lt "$expected_count" ]]; then
    echo "Expected $cmd to be called at least $expected_count times, got $actual_count" >&2
    return 1
  fi
}

assert_command_not_called() {
  local cmd="$1"
  local actual_count="${MOCK_CALL_COUNT["$cmd"]:-0}"

  if [[ "$actual_count" -gt 0 ]]; then
    echo "Expected $cmd to not be called, but it was called $actual_count times" >&2
    return 1
  fi
}

assert_command_called_with() {
  local cmd="$1"
  shift
  local expected_pattern="$*"

  if ! was_command_called "$cmd"; then
    echo "Expected $cmd to be called with pattern '$expected_pattern', but it was never called" >&2
    return 1
  fi

  local count="${MOCK_CALL_COUNT["$cmd"]}"
  for ((i=1; i<=count; i++)); do
    local args
    args="$(get_command_args "$cmd" "$i")"
    if [[ "$args" == *"$expected_pattern"* ]]; then
      return 0
    fi
  done

  echo "Expected $cmd to be called with pattern '$expected_pattern', but no matching call found" >&2
  return 1
}

set_mock_exit_code() {
  local cmd="$1"
  local exit_code="$2"
  MOCK_EXIT_CODES["$cmd"]="$exit_code"
}

get_mock_exit_code() {
  local cmd="$1"
  echo "${MOCK_EXIT_CODES["$cmd"]:-0}"
}

set_mock_output() {
  local cmd="$1"
  local output="$2"
  MOCK_OUTPUTS["$cmd"]="$output"
}

get_mock_output() {
  local cmd="$1"
  echo "${MOCK_OUTPUTS["$cmd"]:-}"
}

ssh() {
  log_mock_call "ssh" "$@"

  local output
  output="$(get_mock_output "ssh")"
  if [[ -n "$output" ]]; then
    echo "$output"
  fi

  local exit_code
  exit_code="$(get_mock_exit_code "ssh")"
  return "$exit_code"
}

uapi() {
  log_mock_call "uapi" "$@"

  local output
  output="$(get_mock_output "uapi")"
  if [[ -n "$output" ]]; then
    echo "$output"
  fi

  local exit_code
  exit_code="$(get_mock_exit_code "uapi")"
  return "$exit_code"
}

rsync() {
  log_mock_call "rsync" "$@"

  local output
  output="$(get_mock_output "rsync")"
  if [[ -n "$output" ]]; then
    echo "$output"
  fi

  local exit_code
  exit_code="$(get_mock_exit_code "rsync")"
  return "$exit_code"
}

curl() {
  log_mock_call "curl" "$@"

  local output
  output="$(get_mock_output "curl")"
  if [[ -n "$output" ]]; then
    echo "$output"
  fi

  local exit_code
  exit_code="$(get_mock_exit_code "curl")"
  return "$exit_code"
}

jq() {
  log_mock_call "jq" "$@"

  local output
  output="$(get_mock_output "jq")"
  if [[ -n "$output" ]]; then
    echo "$output"
  fi

  local exit_code
  exit_code="$(get_mock_exit_code "jq")"
  return "$exit_code"
}

logger() {
  log_mock_call "logger" "$@"

  local output
  output="$(get_mock_output "logger")"
  if [[ -n "$output" ]]; then
    echo "$output"
  fi

  local exit_code
  exit_code="$(get_mock_exit_code "logger")"
  return "$exit_code"
}

chmod() {
  log_mock_call "chmod" "$@"

  if [[ "${MOCK_CHMOD_FAIL_ON_600:-}" == "1" ]] && [[ "$1" == "600" ]]; then
    echo "mock chmod failure for SSH key permissions" >&2
    return 1
  fi

  local output
  output="$(get_mock_output "chmod")"
  if [[ -n "$output" ]]; then
    echo "$output"
  fi

  local exit_code
  exit_code="$(get_mock_exit_code "chmod")"
  return "$exit_code"
}

stat() {
  log_mock_call "stat" "$@"

  local output
  output="$(get_mock_output "stat")"
  if [[ -n "$output" ]]; then
    echo "$output"
  else
    if [[ "$1" == "-c" && "$2" == "%a" ]]; then
      echo "600"
    elif [[ "$1" == "-f" && "$2" == "%Lp" ]]; then
      echo "600"
    fi
  fi

  local exit_code
  exit_code="$(get_mock_exit_code "stat")"
  return "$exit_code"
}

export -f log_mock_call get_mock_exit_code get_mock_output
export -f ssh uapi rsync curl jq logger chmod stat

setup_test_environment() {
  export TEST_ENVIRONMENT_INITIALIZED=1
  export CPANEL_USERNAME="testuser"
  export CPANEL_API_KEY="test_api_key_12345"
  export SERVER_IP_ADDRESS="192.0.2.1"
  export SSH_PRIVATE_KEY_PATH="${BATS_TEST_TMPDIR}/test_ssh_key"
  export SSH_PORT="22"
  export DB_USER="testuser_pguser"
  export DB_PASSWORD="test_pg_password"
  export LOCAL_POSTGRES_PASSWORD="local_pg_password"
  export GITHUB_PERSONAL_ACCESS_TOKEN="ghp_test123456789"
  export RESEND_API_KEY="re_test123456789"
  export CLERK_PUBLISHABLE_KEY="pk_test_123456789"
  export CLERK_SECRET_KEY="sk_test_123456789"
  export DOMAIN="ashlynantrobus.dev"

  # Create SSH key file for tests (required by simplified setup_ssh_key())
  touch "${SSH_PRIVATE_KEY_PATH}"
  chmod 600 "${SSH_PRIVATE_KEY_PATH}"

  # Create backend directory structure for upload_code validation
  local test_backend="${BATS_TEST_TMPDIR}/backend"
  mkdir -p "${test_backend}/src"
  touch "${test_backend}/pyproject.toml"

  # Override PROJECT_ROOT to point to test directory
  export PROJECT_ROOT="${BATS_TEST_TMPDIR}"
  mkdir -p "${BATS_TEST_TMPDIR}/monorepo/backend/src"
  touch "${BATS_TEST_TMPDIR}/monorepo/backend/pyproject.toml"

  # Initialize mocks to succeed silently by default
  set_mock_exit_code "logger" 0
  set_mock_output "logger" ""
  set_mock_exit_code "chmod" 0
  set_mock_output "chmod" ""
  set_mock_exit_code "stat" 0
  set_mock_output "stat" ""
}

unset_test_environment() {
  unset TEST_ENVIRONMENT_INITIALIZED
  unset CPANEL_USERNAME
  unset CPANEL_API_KEY
  unset SERVER_IP_ADDRESS
  unset SSH_PRIVATE_KEY_PATH
  unset SSH_PORT
  unset DB_USER
  unset DB_PASSWORD
  unset LOCAL_POSTGRES_PASSWORD
  unset GITHUB_PERSONAL_ACCESS_TOKEN
  unset RESEND_API_KEY
  unset CLERK_PUBLISHABLE_KEY
  unset CLERK_SECRET_KEY
  unset DOMAIN
}

is_windows() {
  [[ "${OS:-}" == "Windows_NT" ]]
}

is_linux() {
  [[ "$(uname -s)" == "Linux" ]]
}

is_macos() {
  [[ "$(uname -s)" == "Darwin" ]]
}

create_mock_uapi_success_response() {
  local data
  if [[ -n "${1:-}" ]]; then
    data="$1"
  else
    data="{}"
  fi
  cat <<EOF
{
  "status": 1,
  "errors": null,
  "messages": null,
  "metadata": {},
  "data": $data
}
EOF
}

create_mock_uapi_error_response() {
  local error_msg="$1"
  cat <<EOF
{
  "status": 0,
  "errors": ["$error_msg"],
  "messages": null,
  "metadata": {},
  "data": null
}
EOF
}

create_mock_database_exists_response() {
  local db_name="$1"
  create_mock_uapi_success_response "\"$db_name\""
}

create_mock_user_exists_response() {
  local username="$1"
  create_mock_uapi_success_response "\"$username\""
}

setup_mock_successful_database_creation() {
  set_mock_exit_code "uapi" 0
  set_mock_output "uapi" "$(create_mock_database_exists_response 'testuser_blogdb')"
}

setup_mock_failed_database_creation() {
  set_mock_exit_code "uapi" 1
  set_mock_output "uapi" "$(create_mock_uapi_error_response 'Database creation failed')"
}

setup_mock_successful_user_creation() {
  set_mock_exit_code "uapi" 0
  set_mock_output "uapi" "$(create_mock_user_exists_response 'testuser_pguser')"
}

setup_mock_failed_user_creation() {
  set_mock_exit_code "uapi" 1
  set_mock_output "uapi" "$(create_mock_uapi_error_response 'User creation failed')"
}

setup_mock_successful_ssh() {
  set_mock_exit_code "ssh" 0
  set_mock_output "ssh" ""
}

setup_mock_failed_ssh() {
  set_mock_exit_code "ssh" 255
  set_mock_output "ssh" "Connection refused"
}

setup_mock_successful_rsync() {
  set_mock_exit_code "rsync" 0
  set_mock_output "rsync" ""
}

setup_mock_failed_rsync() {
  set_mock_exit_code "rsync" 1
  set_mock_output "rsync" "rsync: failed to connect"
}

setup_mock_successful_health_check() {
  set_mock_exit_code "curl" 0
  set_mock_output "curl" '{"status": "healthy"}'
}

setup_mock_failed_health_check() {
  set_mock_exit_code "curl" 7
  set_mock_output "curl" "curl: (7) Failed to connect"
}

assert_exit_success() {
  local status="$1"
  if [[ "$status" -ne 0 ]]; then
    echo "Expected exit code 0, got $status" >&2
    return 1
  fi
}

assert_exit_failure() {
  local status="$1"
  if [[ "$status" -eq 0 ]]; then
    echo "Expected non-zero exit code, got 0" >&2
    return 1
  fi
}

assert_contains() {
  local haystack="$1"
  local needle="$2"

  if [[ "$haystack" != *"$needle"* ]]; then
    echo "Expected output to contain '$needle', but it didn't" >&2
    echo "Actual output: $haystack" >&2
    return 1
  fi
}

assert_not_contains() {
  local haystack="$1"
  local needle="$2"

  if [[ "$haystack" == *"$needle"* ]]; then
    echo "Expected output to not contain '$needle', but it did" >&2
    echo "Actual output: $haystack" >&2
    return 1
  fi
}

assert_file_exists() {
  local file="$1"
  if [[ ! -f "$file" ]]; then
    echo "Expected file to exist: $file" >&2
    return 1
  fi
}

assert_file_not_exists() {
  local file="$1"
  if [[ -f "$file" ]]; then
    echo "Expected file to not exist: $file" >&2
    return 1
  fi
}

assert_directory_exists() {
  local dir="$1"
  if [[ ! -d "$dir" ]]; then
    echo "Expected directory to exist: $dir" >&2
    return 1
  fi
}

assert_directory_not_exists() {
  local dir="$1"
  if [[ -d "$dir" ]]; then
    echo "Expected directory to not exist: $dir" >&2
    return 1
  fi
}

create_test_file() {
  local file="$1"
  local content="${2:-test content}"
  mkdir -p "$(dirname "$file")"
  echo "$content" > "$file"
}

create_test_directory() {
  local dir="$1"
  mkdir -p "$dir"
}

cleanup_test_files() {
  if [[ -n "${BATS_TEST_TMPDIR:-}" ]]; then
    rm -rf "${BATS_TEST_TMPDIR:?}"/*
  fi
}

verify_schema_compliance() {
  local json_output="$1"
  local required_fields="$2"

  for field in $required_fields; do
    if ! echo "$json_output" | command jq -e "has(\"$field\")" &>/dev/null; then
      echo "Expected JSON to have field '$field', but it's missing" >&2
      echo "Actual JSON: $json_output" >&2
      return 1
    fi
  done
}

load_fixture() {
  local fixture_name="$1"
  local fixtures_dir
  fixtures_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")/fixtures" && pwd)"
  cat "${fixtures_dir}/${fixture_name}"
}

setup_mock_failed_ssh_key_chmod() {
  export MOCK_CHMOD_FAIL_ON_600=1
  set_mock_exit_code "stat" 0
  set_mock_output "stat" ""
}

setup_mock_audit_logger_capture() {
  local shim_dir
  shim_dir="${BATS_TEST_TMPDIR}/logger_shim"
  mkdir -p "$shim_dir"

  # The deploy script is expected to use logger for audit logging.
  cat >"${shim_dir}/logger" <<EOF
#!/usr/bin/env bash
# Append all audit log lines to a test-local file for assertion.
echo "\$@" >>"${BATS_TEST_TMPDIR}/audit.log"
exit 0
EOF

  chmod +x "${shim_dir}/logger"
  export PATH="${shim_dir}:$PATH"
}
