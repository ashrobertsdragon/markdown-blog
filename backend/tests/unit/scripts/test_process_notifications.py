"""Unit tests for process_notifications background job script."""

import logging
from unittest.mock import MagicMock, patch

import pytest

from scripts.process_notifications import main, parse_arguments

HANDLER_PATH = (
    "backend.application.commands.handlers"
    ".process_notifications_handler"
    ".handle_process_notifications"
)
RESEND_SETTINGS_PATH = "scripts.process_notifications.ResendSettings"
NOTIFICATION_REPO_PATH = "scripts.process_notifications.NotificationRepository"
POST_REPO_PATH = "scripts.process_notifications.PostRepository"
USER_REPO_PATH = "scripts.process_notifications.UserRepository"
COMMENT_REPO_PATH = "scripts.process_notifications.CommentRepository"
EMAIL_SENDER_PATH = "scripts.process_notifications.EmailSender"
ARGV_PATH = "sys.argv"
DEFAULT_ARGV = ["process_notifications.py"]


def _make_settings(
    api_key: str = "re_test_key",
    domain: str = "noreply@test.com",
    timeout: int = 10,
    max_retries: int = 3,
) -> MagicMock:
    """Build a mock ResendSettings instance."""
    settings = MagicMock()
    settings.RESEND_API_KEY = api_key
    settings.RESEND_DOMAIN = domain
    settings.RESEND_REQUEST_TIMEOUT = timeout
    settings.RESEND_MAX_RETRIES = max_retries
    return settings


def _make_summary(
    sent: int = 2,
    failed: int = 0,
    total: int = 2,
) -> dict[str, int]:
    """Build a handler summary result."""
    return {"sent": sent, "failed": failed, "total": total}


class TestExitCodes:
    """Script exits with appropriate codes."""

    def test_exits_zero_on_success(self) -> None:
        with (
            patch(ARGV_PATH, DEFAULT_ARGV),
            patch(RESEND_SETTINGS_PATH, return_value=_make_settings()),
            patch(NOTIFICATION_REPO_PATH),
            patch(POST_REPO_PATH),
            patch(USER_REPO_PATH),
            patch(COMMENT_REPO_PATH),
            patch(EMAIL_SENDER_PATH),
            patch(HANDLER_PATH, return_value=_make_summary()),
        ):
            with pytest.raises(SystemExit) as exc_info:
                main()

        assert exc_info.value.code == 0

    def test_exits_one_on_settings_error(self) -> None:
        with (
            patch(ARGV_PATH, DEFAULT_ARGV),
            patch(
                RESEND_SETTINGS_PATH,
                side_effect=ValueError("RESEND_API_KEY field required"),
            ),
        ):
            with pytest.raises(SystemExit) as exc_info:
                main()

        assert exc_info.value.code == 1

    def test_exits_one_on_unexpected_exception(self) -> None:
        with (
            patch(ARGV_PATH, DEFAULT_ARGV),
            patch(RESEND_SETTINGS_PATH, return_value=_make_settings()),
            patch(
                NOTIFICATION_REPO_PATH,
                side_effect=RuntimeError("DB connection failed"),
            ),
        ):
            with pytest.raises(SystemExit) as exc_info:
                main()

        assert exc_info.value.code == 1

    def test_exits_one_when_handler_raises(self) -> None:
        with (
            patch(ARGV_PATH, DEFAULT_ARGV),
            patch(RESEND_SETTINGS_PATH, return_value=_make_settings()),
            patch(NOTIFICATION_REPO_PATH),
            patch(POST_REPO_PATH),
            patch(USER_REPO_PATH),
            patch(COMMENT_REPO_PATH),
            patch(EMAIL_SENDER_PATH),
            patch(
                HANDLER_PATH,
                side_effect=Exception("Unexpected handler error"),
            ),
        ):
            with pytest.raises(SystemExit) as exc_info:
                main()

        assert exc_info.value.code == 1


class TestArgumentParsing:
    """CLI argument flags are parsed and forwarded to the command."""

    def test_default_batch_limit_is_100(self) -> None:
        args = parse_arguments([])
        assert args.batch_limit == 100

    def test_default_max_retries_is_3(self) -> None:
        args = parse_arguments([])
        assert args.max_retries == 3

    def test_custom_batch_limit(self) -> None:
        args = parse_arguments(["--batch-limit", "50"])
        assert args.batch_limit == 50

    def test_custom_max_retries(self) -> None:
        args = parse_arguments(["--max-retries", "5"])
        assert args.max_retries == 5

    def test_batch_limit_passed_to_command(self) -> None:
        captured_command: dict = {}

        def capture_call(command, **kwargs) -> dict[str, int]:
            captured_command["command"] = command
            return _make_summary()

        with (
            patch(
                ARGV_PATH,
                ["process_notifications.py", "--batch-limit", "25"],
            ),
            patch(RESEND_SETTINGS_PATH, return_value=_make_settings()),
            patch(NOTIFICATION_REPO_PATH),
            patch(POST_REPO_PATH),
            patch(USER_REPO_PATH),
            patch(COMMENT_REPO_PATH),
            patch(EMAIL_SENDER_PATH),
            patch(HANDLER_PATH, side_effect=capture_call),
        ):
            with pytest.raises(SystemExit):
                main()

        assert captured_command["command"].batch_limit == 25

    def test_max_retries_passed_to_command(self) -> None:
        captured_command: dict = {}

        def capture_call(command, **kwargs) -> dict[str, int]:
            captured_command["command"] = command
            return _make_summary()

        with (
            patch(
                ARGV_PATH,
                ["process_notifications.py", "--max-retries", "7"],
            ),
            patch(RESEND_SETTINGS_PATH, return_value=_make_settings()),
            patch(NOTIFICATION_REPO_PATH),
            patch(POST_REPO_PATH),
            patch(USER_REPO_PATH),
            patch(COMMENT_REPO_PATH),
            patch(EMAIL_SENDER_PATH),
            patch(HANDLER_PATH, side_effect=capture_call),
        ):
            with pytest.raises(SystemExit):
                main()

        assert captured_command["command"].max_retries == 7


class TestDependencyInitialization:
    """All dependencies are properly instantiated."""

    def test_email_sender_configured_from_settings(self) -> None:
        settings = _make_settings(
            api_key="re_abc123",
            domain="mail@blog.com",
            timeout=15,
            max_retries=5,
        )
        mock_sender_cls = MagicMock()

        with (
            patch(ARGV_PATH, DEFAULT_ARGV),
            patch(RESEND_SETTINGS_PATH, return_value=settings),
            patch(NOTIFICATION_REPO_PATH),
            patch(POST_REPO_PATH),
            patch(USER_REPO_PATH),
            patch(COMMENT_REPO_PATH),
            patch(EMAIL_SENDER_PATH, mock_sender_cls),
            patch(HANDLER_PATH, return_value=_make_summary()),
        ):
            with pytest.raises(SystemExit):
                main()

        mock_sender_cls.assert_called_once_with(
            api_key="re_abc123",
            domain="mail@blog.com",
            timeout=15,
            max_retries=5,
        )

    def test_all_repositories_instantiated(self) -> None:
        mock_notification_repo = MagicMock()
        mock_post_repo = MagicMock()
        mock_user_repo = MagicMock()
        mock_comment_repo = MagicMock()

        with (
            patch(ARGV_PATH, DEFAULT_ARGV),
            patch(RESEND_SETTINGS_PATH, return_value=_make_settings()),
            patch(NOTIFICATION_REPO_PATH, mock_notification_repo),
            patch(POST_REPO_PATH, mock_post_repo),
            patch(USER_REPO_PATH, mock_user_repo),
            patch(COMMENT_REPO_PATH, mock_comment_repo),
            patch(EMAIL_SENDER_PATH),
            patch(HANDLER_PATH, return_value=_make_summary()),
        ):
            with pytest.raises(SystemExit):
                main()

        mock_notification_repo.assert_called_once()
        mock_post_repo.assert_called_once()
        mock_user_repo.assert_called_once()
        mock_comment_repo.assert_called_once()


class TestHandlerInvocation:
    """Handler is called with correct dependencies."""

    def test_handler_called_with_all_dependencies(self) -> None:
        mock_notification_repo_instance = MagicMock()
        mock_post_repo_instance = MagicMock()
        mock_user_repo_instance = MagicMock()
        mock_comment_repo_instance = MagicMock()
        mock_email_sender_instance = MagicMock()

        captured: dict = {}

        def capture_call(**kwargs) -> dict[str, int]:
            captured.update(kwargs)
            return _make_summary()

        with (
            patch(ARGV_PATH, DEFAULT_ARGV),
            patch(RESEND_SETTINGS_PATH, return_value=_make_settings()),
            patch(
                NOTIFICATION_REPO_PATH,
                return_value=mock_notification_repo_instance,
            ),
            patch(POST_REPO_PATH, return_value=mock_post_repo_instance),
            patch(USER_REPO_PATH, return_value=mock_user_repo_instance),
            patch(
                COMMENT_REPO_PATH,
                return_value=mock_comment_repo_instance,
            ),
            patch(
                EMAIL_SENDER_PATH,
                return_value=mock_email_sender_instance,
            ),
            patch(HANDLER_PATH, side_effect=capture_call),
        ):
            with pytest.raises(SystemExit):
                main()

        assert captured["notification_repo"] is mock_notification_repo_instance
        assert captured["post_repo"] is mock_post_repo_instance
        assert captured["user_repo"] is mock_user_repo_instance
        assert captured["comment_repo"] is mock_comment_repo_instance
        assert captured["email_sender"] is mock_email_sender_instance

    def test_handler_return_value_used_for_logging(
        self, caplog: pytest.LogCaptureFixture
    ) -> None:
        summary = _make_summary(sent=5, failed=1, total=6)

        with (
            patch(ARGV_PATH, DEFAULT_ARGV),
            patch(RESEND_SETTINGS_PATH, return_value=_make_settings()),
            patch(NOTIFICATION_REPO_PATH),
            patch(POST_REPO_PATH),
            patch(USER_REPO_PATH),
            patch(COMMENT_REPO_PATH),
            patch(EMAIL_SENDER_PATH),
            patch(HANDLER_PATH, return_value=summary),
        ):
            with caplog.at_level(
                logging.INFO,
                logger="scripts.process_notifications",
            ):
                with pytest.raises(SystemExit):
                    main()

        log_text = caplog.text
        assert "sent=5" in log_text
        assert "failed=1" in log_text
        assert "total=6" in log_text


class TestLogging:
    """Logging emits appropriate messages without PII."""

    def test_logs_info_on_success(
        self, caplog: pytest.LogCaptureFixture
    ) -> None:
        with (
            patch(ARGV_PATH, DEFAULT_ARGV),
            patch(RESEND_SETTINGS_PATH, return_value=_make_settings()),
            patch(NOTIFICATION_REPO_PATH),
            patch(POST_REPO_PATH),
            patch(USER_REPO_PATH),
            patch(COMMENT_REPO_PATH),
            patch(EMAIL_SENDER_PATH),
            patch(HANDLER_PATH, return_value=_make_summary()),
        ):
            with caplog.at_level(
                logging.INFO,
                logger="scripts.process_notifications",
            ):
                with pytest.raises(SystemExit):
                    main()

        assert any(r.levelno == logging.INFO for r in caplog.records)

    def test_logs_error_on_configuration_failure(
        self, caplog: pytest.LogCaptureFixture
    ) -> None:
        with (
            patch(ARGV_PATH, DEFAULT_ARGV),
            patch(
                RESEND_SETTINGS_PATH,
                side_effect=Exception("config error"),
            ),
        ):
            with caplog.at_level(
                logging.ERROR,
                logger="scripts.process_notifications",
            ):
                with pytest.raises(SystemExit):
                    main()

        assert any(r.levelno >= logging.ERROR for r in caplog.records)

    def test_no_api_key_in_logs(self, caplog: pytest.LogCaptureFixture) -> None:
        api_key_value = "re_super_secret_key"
        settings = _make_settings(api_key=api_key_value)

        with (
            patch(ARGV_PATH, DEFAULT_ARGV),
            patch(RESEND_SETTINGS_PATH, return_value=settings),
            patch(NOTIFICATION_REPO_PATH),
            patch(POST_REPO_PATH),
            patch(USER_REPO_PATH),
            patch(COMMENT_REPO_PATH),
            patch(EMAIL_SENDER_PATH),
            patch(HANDLER_PATH, return_value=_make_summary()),
        ):
            with caplog.at_level(
                logging.DEBUG,
                logger="scripts.process_notifications",
            ):
                with pytest.raises(SystemExit):
                    main()

        assert api_key_value not in caplog.text
