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

@test "upload_code checks correct frontend build path" {
  run grep 'monorepo/build' "${BATS_TEST_DIRNAME}/../deploy.sh"

  assert_exit_success "$status"
  assert_contains "$output" "monorepo/build"
}

@test "upload_code uses correct frontend source path" {
  mkdir -p "${PROJECT_ROOT}/monorepo/build"
  touch "${PROJECT_ROOT}/monorepo/build/index.html"

  export RSYNC_LOG="${BATS_TEST_TMPDIR}/rsync_calls.log"
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
  assert_contains "$output" "monorepo/build/"
  assert_not_contains "$output" "monorepo/frontend/build/"
}

@test "run_schema sets DB_HOST environment variable" {
  run sed -n '/^run_schema()/,/^}/p' "${BATS_TEST_DIRNAME}/../deploy.sh"

  assert_exit_success "$status"
  assert_contains "$output" "export DB_HOST="
}

@test "run_schema sets all required database environment variables" {
  local function_source
  function_source=$(sed -n '/^run_schema()/,/^}/p' "${BATS_TEST_DIRNAME}/../deploy.sh")

  local required_exported_vars=(
    "DB_HOST"
    "DB_NAME"
    "DB_USER"
    "FLASK_ENV"
  )

  for var in "${required_exported_vars[@]}"; do
    if ! echo "$function_source" | grep -q "export ${var}="; then
      echo "ERROR: run_schema missing export for ${var}" >&2
      return 1
    fi
  done

  # DB_PASSWORD should be set inline with the command, not exported
  if ! echo "$function_source" | grep -q 'DB_PASSWORD="${DB_PASSWORD}" uv run create-schema'; then
    echo "ERROR: run_schema missing inline DB_PASSWORD assignment" >&2
    return 1
  fi

  # Verify DB_PASSWORD is NOT exported globally
  if echo "$function_source" | grep -q "export DB_PASSWORD="; then
    echo "ERROR: run_schema should NOT export DB_PASSWORD globally (security issue)" >&2
    return 1
  fi

  return 0
}

@test "run_schema uses standard env var names without CPANEL prefix" {
  local function_source
  function_source=$(sed -n '/^run_schema()/,/^}/p' "${BATS_TEST_DIRNAME}/../deploy.sh")

  run grep 'export CPANEL_DB_HOST=' <<<"$function_source"
  assert_exit_failure "$status"

  run grep 'export CPANEL_DB_NAME=' <<<"$function_source"
  assert_exit_failure "$status"

  run grep 'export DB_HOST=' <<<"$function_source"
  assert_exit_success "$status"

  run grep 'export DB_NAME=' <<<"$function_source"
  assert_exit_success "$status"
}
