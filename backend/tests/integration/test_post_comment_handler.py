"""Integration tests for handle_post_comment.

Tests the full interaction between the handler, RateLimitService, and
SpamCheckService using real service instances.
"""

from unittest.mock import Mock

import pytest

from backend.application.commands.handlers.post_comment_handler import (
    handle_post_comment,
)
from backend.application.commands.post_comment_command import PostCommentCommand
from backend.domain.aggregates.comment import Comment
from backend.exceptions import RateLimitExceededError
from backend.infrastructure.moderation.rate_limit_service import (
    RateLimitService,
)
from backend.infrastructure.moderation.spam_check_service import (
    SpamCheckService,
)
from backend.infrastructure.persistence.comment_repository import (
    CommentRepository,
)

_IP = "127.0.0.1"
_SPAM_TEXT = (
    "Buy now! https://spam.example.com/a "
    "https://spam.example.com/b "
    "https://spam.example.com/c"
)
_CLEAN_TEXT = "Great post, thanks for sharing."


@pytest.fixture()
def rate_limit_service() -> RateLimitService:
    """Provide a fresh RateLimitService capped at 5 per window."""
    return RateLimitService(window_seconds=60, max_per_window=5)


@pytest.fixture()
def spam_check_service() -> SpamCheckService:
    """Provide a SpamCheckService with no extra patterns."""
    return SpamCheckService()


@pytest.fixture()
def comment_repository() -> Mock:
    """Provide a CommentRepository mock whose save() returns its argument."""
    repo = Mock(spec=CommentRepository)
    repo.save.side_effect = lambda comment: comment
    return repo


def _make_command(
    *,
    post_id: int = 1,
    author_id: int = 1,
    text: str = _CLEAN_TEXT,
    ip_address: str = _IP,
    is_admin: bool = False,
) -> PostCommentCommand:
    """Build a PostCommentCommand with sensible defaults."""
    return PostCommentCommand(
        post_id=post_id,
        author_id=author_id,
        text=text,
        ip_address=ip_address,
        is_admin=is_admin,
    )


def test_handler_returns_comment_on_success(
    rate_limit_service: RateLimitService,
    spam_check_service: SpamCheckService,
    comment_repository: Mock,
) -> None:
    """Handler returns a Comment with correct post_id, author_id, and text."""
    command = _make_command(post_id=7, author_id=3, text="Hello world.")

    result = handle_post_comment(
        command, rate_limit_service, spam_check_service, comment_repository
    )

    assert isinstance(result, Comment)
    assert result.post_id == 7
    assert result.author_id == 3
    assert str(result.text) == "Hello world."
    assert result.id is None


def test_handler_enforces_rate_limit(
    rate_limit_service: RateLimitService,
    spam_check_service: SpamCheckService,
    comment_repository: Mock,
) -> None:
    """The sixth submission within the window raises RateLimitExceededError."""
    for i in range(5):
        handle_post_comment(
            _make_command(text=f"Comment {i}"),
            rate_limit_service,
            spam_check_service,
            comment_repository,
        )

    with pytest.raises(RateLimitExceededError):
        handle_post_comment(
            _make_command(text="One too many"),
            rate_limit_service,
            spam_check_service,
            comment_repository,
        )


def test_handler_flags_spam_for_moderation(
    rate_limit_service: RateLimitService,
    spam_check_service: SpamCheckService,
    comment_repository: Mock,
) -> None:
    """Text with 3+ URLs scores >= 50 and is flagged for moderation."""
    command = _make_command(text=_SPAM_TEXT)

    result = handle_post_comment(
        command, rate_limit_service, spam_check_service, comment_repository
    )

    assert result.is_pending_moderation is True


def test_handler_allows_clean_comment_through_without_moderation(
    rate_limit_service: RateLimitService,
    spam_check_service: SpamCheckService,
    comment_repository: Mock,
) -> None:
    """Plain text with no spam signals is not flagged for moderation."""
    command = _make_command(text=_CLEAN_TEXT)

    result = handle_post_comment(
        command, rate_limit_service, spam_check_service, comment_repository
    )

    assert result.is_pending_moderation is False


def test_handler_allows_admin_to_bypass_rate_limit(
    rate_limit_service: RateLimitService,
    spam_check_service: SpamCheckService,
    comment_repository: Mock,
) -> None:
    """Admin submissions are never blocked, even beyond the normal window."""
    for i in range(10):
        result = handle_post_comment(
            _make_command(text=f"Admin comment {i}", is_admin=True),
            rate_limit_service,
            spam_check_service,
            comment_repository,
        )
        assert isinstance(result, Comment)


def test_handler_raises_for_invalid_post_id(
    rate_limit_service: RateLimitService,
    spam_check_service: SpamCheckService,
) -> None:
    """PostCommentCommand with post_id=0 raises ValueError on construction."""
    with pytest.raises(ValueError, match="post_id"):
        PostCommentCommand(
            post_id=0,
            author_id=1,
            text=_CLEAN_TEXT,
            ip_address=_IP,
        )
