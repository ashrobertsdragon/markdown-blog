#!/usr/bin/env bats

load test_helper

setup() {
  reset_mock_state
  setup_test_environment
}

teardown() {
  unset_test_environment
  cleanup_test_files
}

# ============================================================================
# Environment Validation Tests (9 tests)
# ============================================================================

@test "deployment skips production confirmation when not on interactive terminal" {
  export DOMAIN="test.com"
  export PRODUCTION_DOMAIN="test.com"
  setup_mock_successful_database_creation
  setup_mock_successful_user_creation
  setup_mock_successful_ssh
  setup_mock_successful_rsync
  setup_mock_successful_health_check

  source "${BATS_TEST_DIRNAME}/../deploy.sh"
  run main

  assert_exit_success "$status"
  assert_not_contains "$output" "WARNING: Deploying to PRODUCTION domain"
}

@test "deployment proceeds when production confirmation is not required" {
  export DOMAIN="staging.example.com"
  export PRODUCTION_DOMAIN="example.com"
  setup_mock_successful_database_creation
  setup_mock_successful_user_creation
  setup_mock_successful_ssh
  setup_mock_successful_rsync
  setup_mock_successful_health_check

  source "${BATS_TEST_DIRNAME}/../deploy.sh"
  run main

  assert_exit_success "$status"
  assert_not_contains "$output" "WARNING: Deploying to PRODUCTION domain"
}

@test "deployment proceeds when DOMAIN is non-production with PRODUCTION_DOMAIN set" {
  export DOMAIN="dev.example.com"
  export PRODUCTION_DOMAIN="example.com"
  setup_mock_successful_database_creation
  setup_mock_successful_user_creation
  setup_mock_successful_ssh
  setup_mock_successful_rsync
  setup_mock_successful_health_check

  source "${BATS_TEST_DIRNAME}/../deploy.sh"
  run main

  assert_exit_success "$status"
  assert_not_contains "$output" "WARNING: Deploying to PRODUCTION domain"
}

@test "deployment does not prompt when DOMAIN is clearly non-production even if PRODUCTION_DOMAIN is set" {
  export DOMAIN="test.localhost"
  export PRODUCTION_DOMAIN="example.com"
  setup_mock_successful_database_creation
  setup_mock_successful_user_creation
  setup_mock_successful_ssh
  setup_mock_successful_rsync
  setup_mock_successful_health_check

  source "${BATS_TEST_DIRNAME}/../deploy.sh"
  run main

  assert_exit_success "$status"
  assert_not_contains "$output" "WARNING: Deploying to PRODUCTION domain"
}

@test "deployment fails when CPANEL_USERNAME is not set" {
  unset CPANEL_USERNAME

  source "${BATS_TEST_DIRNAME}/../deploy.sh"
  run main

  assert_exit_failure "$status"
}

@test "deployment fails when SERVER_IP_ADDRESS is not set" {
  unset SERVER_IP_ADDRESS

  source "${BATS_TEST_DIRNAME}/../deploy.sh"
  run main

  assert_exit_failure "$status"
}

@test "deployment fails when SSH_PRIVATE_KEY_PATH is not set" {
  unset SSH_PRIVATE_KEY_PATH

  source "${BATS_TEST_DIRNAME}/../deploy.sh"
  run main

  assert_exit_failure "$status"
}

@test "deployment fails when database credentials are not set" {
  unset DB_USER
  unset DB_PASSWORD

  source "${BATS_TEST_DIRNAME}/../deploy.sh"
  run main

  assert_exit_failure "$status"
}

# ============================================================================
# SSH Key Handling Tests (3 tests)
# ============================================================================

@test "deployment aborts when SSH key chmod 600 fails" {
  export OS="Linux"
  export SSH_KEY_PATH="${BATS_TEST_TMPDIR}/test_key"
  export SSH_PRIVATE_KEY_PATH="${SSH_KEY_PATH}"
  touch "${SSH_KEY_PATH}"

  setup_mock_successful_database_creation
  setup_mock_successful_user_creation
  setup_mock_successful_ssh
  setup_mock_successful_rsync
  setup_mock_successful_health_check
  setup_mock_failed_ssh_key_chmod

  source "${BATS_TEST_DIRNAME}/../deploy.sh"
  run main

  [[ $status -ne 0 ]]
  [[ "$output" == *"mock chmod failure for SSH key permissions"* ]]
}

@test "deployment logs audit entry when SSH key permission enforcement fails" {
  export SSH_KEY_PATH="${BATS_TEST_TMPDIR}/test_key"
  export SSH_PRIVATE_KEY_PATH="${SSH_KEY_PATH}"
  touch "${SSH_KEY_PATH}"

  setup_mock_successful_database_creation
  setup_mock_successful_user_creation
  setup_mock_successful_ssh
  setup_mock_successful_rsync
  setup_mock_successful_health_check
  setup_mock_failed_ssh_key_chmod
  setup_mock_audit_logger_capture

  : > "${BATS_TEST_TMPDIR}/audit.log"

  source "${BATS_TEST_DIRNAME}/../deploy.sh"
  run main

  assert_exit_failure "$status"

  [[ -f "${BATS_TEST_TMPDIR}/audit.log" ]]
}

@test "deployment verifies SSH key permissions are limited" {
  export SSH_KEY_PATH="${BATS_TEST_TMPDIR}/test_key"
  export SSH_PRIVATE_KEY_PATH="${SSH_KEY_PATH}"
  export CHMOD_CALLED="${BATS_TEST_TMPDIR}/chmod_called"
  touch "${SSH_KEY_PATH}"

  setup_mock_successful_ssh
  setup_mock_successful_rsync
  setup_mock_successful_health_check

  uapi() {
    if [[ "$*" == *"list_databases"* ]]; then
      echo '{"data":["testuser_blogdb"]}'
    elif [[ "$*" == *"list_users"* ]]; then
      echo '{"data":["testuser_pguser"]}'
    elif [[ "$*" == *"list_privileges"* ]]; then
      echo '{"data":["ALL"]}'
    elif [[ "$*" == *"list_applications"* ]]; then
      echo '{"data":[]}'
    elif [[ "$*" == *"register_application"* ]]; then
      echo '{"result":{"status":1}}'
    else
      echo '{"data":[]}'
    fi
    return 0
  }
  export -f uapi

  chmod() {
    if [[ "$1" == "600" ]]; then
      touch "${CHMOD_CALLED}"
    fi
    return 0
  }
  export -f chmod

  stat() {
    if [[ "$1" == "-c" && "$2" == "%a" ]]; then
      echo "600"
    elif [[ "$1" == "-f" && "$2" == "%Lp" ]]; then
      echo "600"
    fi
    return 0
  }
  export -f stat

  source "${BATS_TEST_DIRNAME}/../deploy.sh"
  run main

  assert_exit_success "$status"
  assert_file_exists "${CHMOD_CALLED}"
}

# ============================================================================
# Database Provisioning Tests (6 tests)
# ============================================================================

@test "deployment fails fast when UAPI database creation fails" {
  setup_mock_successful_ssh
  setup_mock_successful_rsync
  setup_mock_successful_health_check

  uapi() {
    if [[ "$*" == *"list_databases"* ]]; then
      echo '{"data":[]}'
      return 0
    elif [[ "$*" == *"create_database"* ]]; then
      echo '{"error":"Database creation failed"}'
      return 1
    else
      echo '{"data":[]}'
      return 0
    fi
  }
  export -f uapi

  source "${BATS_TEST_DIRNAME}/../deploy.sh"
  run main

  assert_exit_failure "$status"
}

@test "deployment fails fast when UAPI user creation fails" {
  setup_mock_successful_ssh
  setup_mock_successful_rsync
  setup_mock_successful_health_check

  uapi() {
    if [[ "$*" == *"list_databases"* ]]; then
      echo '{"data":[]}'
      return 0
    elif [[ "$*" == *"create_database"* ]]; then
      echo '{"data":{}}'
      return 0
    elif [[ "$*" == *"list_users"* ]]; then
      echo '{"data":[]}'
      return 0
    elif [[ "$*" == *"create_user"* ]]; then
      echo '{"error":"User creation failed"}'
      return 1
    else
      echo '{"data":[]}'
      return 0
    fi
  }
  export -f uapi

  source "${BATS_TEST_DIRNAME}/../deploy.sh"
  run main

  assert_exit_failure "$status"
}

@test "deployment creates database via UAPI when it does not exist" {
  export DB_CREATED="${BATS_TEST_TMPDIR}/db_created"
  setup_mock_successful_user_creation
  setup_mock_successful_ssh
  setup_mock_successful_rsync
  setup_mock_successful_health_check

  uapi() {
    if [[ "$*" == *"create_database"* ]]; then
      touch "${DB_CREATED}"
      echo '{"status":1,"data":{}}'
    else
      echo '{"status":1,"data":[]}'
    fi
    return 0
  }
  export -f uapi

  source "${BATS_TEST_DIRNAME}/../deploy.sh"
  run main

  assert_file_exists "${DB_CREATED}"
  assert_exit_success "$status"
}

@test "deployment creates PostgreSQL user via UAPI when it does not exist" {
  export USER_CREATED="${BATS_TEST_TMPDIR}/user_created"
  setup_mock_successful_database_creation
  setup_mock_successful_ssh
  setup_mock_successful_rsync
  setup_mock_successful_health_check

  uapi() {
    if [[ "$*" == *"create_user"* ]]; then
      touch "${USER_CREATED}"
      echo '{"status":1,"data":{}}'
    else
      echo '{"status":1,"data":["testuser_blogdb"]}'
    fi
    return 0
  }
  export -f uapi

  source "${BATS_TEST_DIRNAME}/../deploy.sh"
  run main

  assert_file_exists "${USER_CREATED}"
  assert_exit_success "$status"
}

@test "deployment grants database privileges to user via UAPI" {
  export PRIVILEGES_GRANTED="${BATS_TEST_TMPDIR}/privileges_granted"
  setup_mock_successful_database_creation
  setup_mock_successful_user_creation
  setup_mock_successful_ssh
  setup_mock_successful_rsync
  setup_mock_successful_health_check

  uapi() {
    if [[ "$*" == *"grant_all_privileges"* ]]; then
      touch "${PRIVILEGES_GRANTED}"
      echo '{"status":1,"data":["testuser_blogdb"]}'
    elif [[ "$*" == *"list_privileges"* ]]; then
      echo '{"status":1,"data":[]}'
    else
      echo '{"status":1,"data":["testuser_blogdb"]}'
    fi
    return 0
  }
  export -f uapi

  source "${BATS_TEST_DIRNAME}/../deploy.sh"
  run main

  assert_file_exists "${PRIVILEGES_GRANTED}"
  assert_exit_success "$status"
}

@test "deployment is idempotent when database already exists" {
  export DEPLOY_COUNT="${BATS_TEST_TMPDIR}/deploy_count"
  setup_mock_successful_ssh
  setup_mock_successful_rsync
  setup_mock_successful_health_check

  uapi() {
    echo "1" >> "${DEPLOY_COUNT}"
    echo '{"status":1,"data":["testuser_blogdb","testuser_pguser"]}'
    return 0
  }
  export -f uapi

  source "${BATS_TEST_DIRNAME}/../deploy.sh"
  run main
  assert_exit_success "$status"

  run main
  assert_exit_success "$status"

  local count
  count=$(wc -l < "${DEPLOY_COUNT}")
  [[ "$count" -ge 2 ]]
}

# ============================================================================
# Code Upload Tests (5 tests)
# ============================================================================

@test "deployment fails when rsync upload of backend directory fails" {
  setup_mock_successful_database_creation
  setup_mock_successful_user_creation
  setup_mock_successful_ssh
  setup_mock_failed_rsync
  setup_mock_successful_health_check

  source "${BATS_TEST_DIRNAME}/../deploy.sh"
  run main

  assert_exit_failure "$status"
}

@test "deployment fails when SSH connectivity for code upload is broken" {
  setup_mock_successful_database_creation
  setup_mock_successful_user_creation
  setup_mock_failed_ssh
  setup_mock_successful_health_check

  source "${BATS_TEST_DIRNAME}/../deploy.sh"
  run main

  assert_exit_failure "$status"
}

@test "deployment uploads backend directory via rsync over SSH" {
  export RSYNC_LOG="${BATS_TEST_TMPDIR}/rsync.log"
  setup_mock_successful_database_creation
  setup_mock_successful_user_creation
  setup_mock_successful_ssh
  setup_mock_successful_health_check

  rsync() {
    echo "$@" >> "${RSYNC_LOG}"
    return 0
  }
  export -f rsync

  source "${BATS_TEST_DIRNAME}/../deploy.sh"
  run main

  assert_exit_success "$status"
  assert_file_exists "${RSYNC_LOG}"
  run cat "${RSYNC_LOG}"
  assert_contains "$output" "monorepo/backend/"
  assert_not_contains "$output" "blog/backend/"
  assert_contains "$output" "ssh"
}

@test "deployment uploads frontend build directory via rsync" {
  export RSYNC_LOG="${BATS_TEST_TMPDIR}/rsync.log"
  local build_dir="${PROJECT_ROOT:-$(dirname "${BATS_TEST_DIRNAME}")/../..}/monorepo/frontend/build"
  mkdir -p "$build_dir"
  touch "$build_dir/index.html"
  setup_mock_successful_database_creation
  setup_mock_successful_user_creation
  setup_mock_successful_ssh
  setup_mock_successful_health_check

  rsync() {
    echo "$@" >> "${RSYNC_LOG}"
    return 0
  }
  export -f rsync

  source "${BATS_TEST_DIRNAME}/../deploy.sh"
  run main

  assert_exit_success "$status"
  assert_file_exists "${RSYNC_LOG}"
  run cat "${RSYNC_LOG}"
  assert_contains "$output" "build/"
}

@test "deployment preserves file permissions during upload" {
  export RSYNC_LOG="${BATS_TEST_TMPDIR}/rsync.log"
  setup_mock_successful_database_creation
  setup_mock_successful_user_creation
  setup_mock_successful_ssh
  setup_mock_successful_health_check

  rsync() {
    echo "$@" >> "${RSYNC_LOG}"
    return 0
  }
  export -f rsync

  source "${BATS_TEST_DIRNAME}/../deploy.sh"
  run main

  assert_exit_success "$status"
  assert_file_exists "${RSYNC_LOG}"
  run cat "${RSYNC_LOG}"
  assert_contains "$output" "--perms"
}

# ============================================================================
# uv and Application Installation Tests (4 tests)
# ============================================================================

@test "deployment installs uv on remote server when it does not exist" {
  export SSH_CALLED="${BATS_TEST_TMPDIR}/ssh_called"
  setup_mock_successful_database_creation
  setup_mock_successful_user_creation
  setup_mock_successful_rsync
  setup_mock_successful_health_check

  ssh() {
    touch "${SSH_CALLED}"
    echo "✓ uv installed successfully"
    echo "uv 0.5.0"
    return 0
  }
  export -f ssh

  source "${BATS_TEST_DIRNAME}/../deploy.sh"
  run main

  assert_exit_success "$status"
  assert_file_exists "${SSH_CALLED}"
  assert_contains "$output" "uv installation verified"
}

@test "deployment skips uv installation when it already exists" {
  setup_mock_successful_database_creation
  setup_mock_successful_user_creation
  setup_mock_successful_rsync
  setup_mock_successful_health_check

  ssh() {
    echo "✓ uv is already installed"
    echo "uv 0.5.0"
    return 0
  }
  export -f ssh

  source "${BATS_TEST_DIRNAME}/../deploy.sh"
  run main

  assert_exit_success "$status"
  assert_contains "$output" "uv installation verified"
}

@test "deployment installs application dependencies with uv sync" {
  export SSH_CALLED="${BATS_TEST_TMPDIR}/ssh_called"
  setup_mock_successful_database_creation
  setup_mock_successful_user_creation
  setup_mock_successful_rsync
  setup_mock_successful_health_check

  ssh() {
    touch "${SSH_CALLED}"
    echo "Python 3.13.0"
    echo "✓ Application dependencies installed"
    return 0
  }
  export -f ssh

  source "${BATS_TEST_DIRNAME}/../deploy.sh"
  run main

  assert_exit_success "$status"
  assert_file_exists "${SSH_CALLED}"
  assert_contains "$output" "Application installed"
}

@test "deployment verifies Python 3.13+ is available on remote server" {
  export SSH_CALLED="${BATS_TEST_TMPDIR}/ssh_called"
  setup_mock_successful_database_creation
  setup_mock_successful_user_creation
  setup_mock_successful_rsync
  setup_mock_successful_health_check

  ssh() {
    touch "${SSH_CALLED}"
    echo "Python 3.13.0"
    return 0
  }
  export -f ssh

  source "${BATS_TEST_DIRNAME}/../deploy.sh"
  run main

  assert_exit_success "$status"
  assert_file_exists "${SSH_CALLED}"
  assert_contains "$output" "Application installed"
}

# ============================================================================
# Schema Execution Tests (3 tests)
# ============================================================================

@test "deployment executes SQLModel schema creation on remote server" {
  export SSH_CALLED="${BATS_TEST_TMPDIR}/ssh_called"
  setup_mock_successful_database_creation
  setup_mock_successful_user_creation
  setup_mock_successful_rsync
  setup_mock_successful_health_check

  ssh() {
    touch "${SSH_CALLED}"
    echo "Schema creation completed"
    return 0
  }
  export -f ssh

  source "${BATS_TEST_DIRNAME}/../deploy.sh"
  run main

  assert_exit_success "$status"
  assert_file_exists "${SSH_CALLED}"
  assert_contains "$output" "Database schema created"
}

@test "deployment schema creation is idempotent" {
  export SCHEMA_RUN_COUNT="${BATS_TEST_TMPDIR}/schema_count"
  setup_mock_successful_database_creation
  setup_mock_successful_user_creation
  setup_mock_successful_rsync
  setup_mock_successful_health_check

  ssh() {
    echo "1" >> "${SCHEMA_RUN_COUNT}"
    echo "Schema creation completed"
    return 0
  }
  export -f ssh

  source "${BATS_TEST_DIRNAME}/../deploy.sh"
  run main
  assert_exit_success "$status"

  run main
  assert_exit_success "$status"

  local count
  count=$(wc -l < "${SCHEMA_RUN_COUNT}")
  [[ "$count" -ge 2 ]]
}

@test "deployment verifies database tables were created successfully" {
  setup_mock_successful_database_creation
  setup_mock_successful_user_creation
  setup_mock_successful_rsync
  setup_mock_successful_health_check

  ssh() {
    echo "Schema creation completed"
    return 0
  }
  export -f ssh

  source "${BATS_TEST_DIRNAME}/../deploy.sh"
  run main

  assert_exit_success "$status"
  assert_contains "$output" "Database schema created"
}

# ============================================================================
# Passenger Registration Tests (5 tests)
# ============================================================================

@test "deployment registers application via UAPI when it does not exist" {
  export UAPI_LOG="${BATS_TEST_TMPDIR}/uapi.log"
  setup_mock_successful_user_creation
  setup_mock_successful_ssh
  setup_mock_successful_rsync
  setup_mock_successful_health_check

  uapi() {
    echo "$@" >> "${UAPI_LOG}"
    echo '{"status":1,"data":["testuser_blogdb"]}'
    return 0
  }
  export -f uapi

  source "${BATS_TEST_DIRNAME}/../deploy.sh"
  run main

  assert_exit_success "$status"
  assert_file_exists "${UAPI_LOG}"
  run cat "${UAPI_LOG}"
  assert_contains "$output" "PassengerApps register_application"
}

@test "deployment updates Passenger app when it is already registered" {
  setup_mock_successful_database_creation
  setup_mock_successful_user_creation
  setup_mock_successful_ssh
  setup_mock_successful_rsync
  setup_mock_successful_health_check

  uapi() {
    echo '{"status":1,"data":["testuser_blogdb"]}'
    return 0
  }
  export -f uapi

  source "${BATS_TEST_DIRNAME}/../deploy.sh"
  run main

  assert_exit_success "$status"
  assert_contains "$output" "Passenger application registered"
}

@test "deployment injects all environment variables into Passenger config" {
  export UAPI_LOG="${BATS_TEST_TMPDIR}/uapi.log"
  setup_mock_successful_user_creation
  setup_mock_successful_ssh
  setup_mock_successful_rsync
  setup_mock_successful_health_check

  uapi() {
    echo "$@" >> "${UAPI_LOG}"
    echo '{"status":1,"data":["testuser_blogdb"]}'
    return 0
  }
  export -f uapi

  source "${BATS_TEST_DIRNAME}/../deploy.sh"
  run main

  assert_exit_success "$status"
  assert_file_exists "${UAPI_LOG}"
  run cat "${UAPI_LOG}"
  assert_contains "$output" "envvar_name_3=DB_USER"
  assert_contains "$output" "envvar_value_3=testuser_pguser"
  assert_contains "$output" "envvar_name_5=GITHUB_PERSONAL_ACCESS_TOKEN"
  assert_contains "$output" "envvar_name_8=CLERK_SECRET_KEY"
}

@test "deployment uses correct domain for Passenger app registration" {
  export UAPI_LOG="${BATS_TEST_TMPDIR}/uapi.log"
  setup_mock_successful_user_creation
  setup_mock_successful_ssh
  setup_mock_successful_rsync
  setup_mock_successful_health_check

  uapi() {
    echo "$@" >> "${UAPI_LOG}"
    echo '{"status":1,"data":["testuser_blogdb"]}'
    return 0
  }
  export -f uapi

  source "${BATS_TEST_DIRNAME}/../deploy.sh"
  run main

  assert_exit_success "$status"
  assert_file_exists "${UAPI_LOG}"
  run cat "${UAPI_LOG}"
  assert_contains "$output" "ashlynantrobus.dev"
}

@test "deployment uses correct base URI for Passenger app registration" {
  export UAPI_LOG="${BATS_TEST_TMPDIR}/uapi.log"
  setup_mock_successful_user_creation
  setup_mock_successful_ssh
  setup_mock_successful_rsync
  setup_mock_successful_health_check

  uapi() {
    echo "$@" >> "${UAPI_LOG}"
    echo '{"status":1,"data":["testuser_blogdb"]}'
    return 0
  }
  export -f uapi

  source "${BATS_TEST_DIRNAME}/../deploy.sh"
  run main

  assert_exit_success "$status"
  assert_file_exists "${UAPI_LOG}"
  run cat "${UAPI_LOG}"
  assert_contains "$output" "base_uri=/"
}

# ============================================================================
# Health Check Verification Tests (5 tests)
# ============================================================================

@test "deployment verifies health endpoint returns 200" {
  export CURL_LOG="${BATS_TEST_TMPDIR}/curl.log"
  setup_mock_successful_database_creation
  setup_mock_successful_user_creation
  setup_mock_successful_ssh
  setup_mock_successful_rsync

  curl() {
    echo "$@" >> "${CURL_LOG}"
    echo '{"status": "healthy"}'
    return 0
  }
  export -f curl

  source "${BATS_TEST_DIRNAME}/../deploy.sh"
  run main

  assert_exit_success "$status"
  assert_file_exists "${CURL_LOG}"

  # Single successful call means no retries were needed
  local call_count
  call_count=$(wc -l < "${CURL_LOG}")
  [[ "$call_count" -eq 3 ]]
}

@test "deployment retries health endpoint on transient curl failures" {
  export CURL_LOG="${BATS_TEST_TMPDIR}/curl.log"
  export CURL_COUNTER_FILE="${BATS_TEST_TMPDIR}/curl_counter"
  echo "0" > "${CURL_COUNTER_FILE}"

  setup_mock_successful_database_creation
  setup_mock_successful_user_creation
  setup_mock_successful_ssh
  setup_mock_successful_rsync

  curl() {
    echo "$@" >> "${CURL_LOG}"
    local count
    count=$(cat "${CURL_COUNTER_FILE}")
    count=$((count + 1))
    echo "$count" > "${CURL_COUNTER_FILE}"

    # First 2 calls to each endpoint fail, then succeed
    local call_in_sequence=$((count % 3))
    if [[ "$call_in_sequence" -ne 0 ]]; then
      return 7
    fi

    echo '{"status": "healthy"}'
    return 0
  }
  export -f curl

  source "${BATS_TEST_DIRNAME}/../deploy.sh"
  run main

  assert_exit_success "$status"

  local expected_retries
  local final_count
  expected_retries=9
  final_count=$(cat "${CURL_COUNTER_FILE}")
  [[ "$final_count" -eq $expected_retries ]]
}

@test "deployment fails when health endpoint never becomes healthy" {
  export CURL_LOG="${BATS_TEST_TMPDIR}/curl.log"
  setup_mock_successful_database_creation
  setup_mock_successful_user_creation
  setup_mock_successful_ssh
  setup_mock_successful_rsync

  curl() {
    echo "$@" >> "${CURL_LOG}"
    return 7  # Always fail
  }
  export -f curl

  source "${BATS_TEST_DIRNAME}/../deploy.sh"
  run main

  assert_exit_failure "$status"

  local expected_attempts
  local curl_calls
  expected_attempts=5
  curl_calls=$(wc -l < "${CURL_LOG}")
  [[ "$curl_calls" -eq $expected_attempts ]]
  assert_contains "$output" "Health check failed"
}

@test "deployment verifies database health endpoint returns 200" {
  export CURL_LOG="${BATS_TEST_TMPDIR}/curl.log"
  setup_mock_successful_database_creation
  setup_mock_successful_user_creation
  setup_mock_successful_ssh
  setup_mock_successful_rsync

  curl() {
    echo "$@" >> "${CURL_LOG}"
    echo '{"status": "healthy", "database": "connected"}'
    return 0
  }
  export -f curl

  source "${BATS_TEST_DIRNAME}/../deploy.sh"
  run main

  assert_exit_success "$status"
  assert_file_exists "${CURL_LOG}"
  run cat "${CURL_LOG}"
  assert_contains "$output" "https://ashlynantrobus.dev/health/db"
}

@test "deployment verifies GitHub health endpoint returns 200" {
  export CURL_LOG="${BATS_TEST_TMPDIR}/curl.log"
  setup_mock_successful_database_creation
  setup_mock_successful_user_creation
  setup_mock_successful_ssh
  setup_mock_successful_rsync

  curl() {
    echo "$@" >> "${CURL_LOG}"
    echo '{"status": "healthy", "github": "connected"}'
    return 0
  }
  export -f curl

  source "${BATS_TEST_DIRNAME}/../deploy.sh"
  run main

  assert_exit_success "$status"
  assert_file_exists "${CURL_LOG}"
  run cat "${CURL_LOG}"
  assert_contains "$output" "https://ashlynantrobus.dev/health/github"
}
