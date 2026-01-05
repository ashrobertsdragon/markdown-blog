#!/usr/bin/env bats

load 'test_helper'

setup_file() {
  run "${BATS_TEST_DIRNAME}/../build.sh"
  assert_exit_success "$status"
}

teardown_file() {
  rm -rf "${BATS_TEST_DIRNAME}/../../build"
}

@test "build.sh creates the build directory" {
  assert_directory_exists "${BATS_TEST_DIRNAME}/../../build"
}

@test "build.sh creates the index.html file" {
  assert_file_exists "${BATS_TEST_DIRNAME}/../../build/index.html"
}

@test "build.sh creates the static directory" {
  assert_directory_exists "${BATS_TEST_DIRNAME}/../../build/static"
}

@test "build.sh creates static in the static directory" {
  run ls "${BATS_TEST_DIRNAME}/../../build/static"
  assert_contains "$output" ".js"
}
