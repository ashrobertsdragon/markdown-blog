"""Unit tests for handle_reply_to_comment.

Tests handler orchestration: parent validation, rate limiting, spam
detection, and Comment aggregate creation. Repository and services are
mocked to isolate the handler logic.
"""

from unittest.mock import Mock

import pytest

from backend.application.commands.handlers.reply_to_comment_handler import (
    handle_reply_to_comment,
)
from backend.application.commands.reply_to_comment_command import (
    ReplyToCommentCommand,
)
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

_IP = "10.0.0.1"
_CLEAN_TEXT = "This is a thoughtful reply."
_SPAM_TEXT = (
    "Buy now! https://spam.example.com/a "
    "https://spam.example.com/b "
    "https://spam.example.com/c"
)


@pytest.fixture()
def rate_service() -> RateLimitService:
    """Fresh RateLimitService with a 5-per-window cap."""
    return RateLimitService(window_seconds=60, max_per_window=5)


@pytest.fixture()
def spam_service() -> SpamCheckService:
    """SpamCheckService with no extra patterns."""
    return SpamCheckService()


@pytest.fixture()
def parent_comment() -> Comment:
    """A persisted parent comment on post 1."""
    c = Comment.create(post_id=1, author_id=99, text="Original comment")
    c.id = 10
    return c


@pytest.fixture()
def mock_repo(parent_comment: Comment) -> Mock:
    """CommentRepository mock returning the parent comment by default."""
    repo = Mock(spec=CommentRepository)
    repo.find_by_id.return_value = parent_comment
    repo.save.side_effect = lambda comment: comment
    return repo


def _make(
    *,
    post_id: int = 1,
    parent_comment_id: int = 10,
    author_id: int = 5,
    text: str = _CLEAN_TEXT,
    ip_address: str = _IP,
    is_admin: bool = False,
) -> ReplyToCommentCommand:
    return ReplyToCommentCommand(
        post_id=post_id,
        parent_comment_id=parent_comment_id,
        author_id=author_id,
        text=text,
        ip_address=ip_address,
        is_admin=is_admin,
    )


def test_handler_returns_reply_comment(
    rate_service: RateLimitService,
    spam_service: SpamCheckService,
    mock_repo: Mock,
) -> None:
    """Handler returns (Comment, parent_author_id) tuple; id=None on reply."""
    cmd = _make()

    comment, parent_author_id = handle_reply_to_comment(
        cmd, rate_service, spam_service, mock_repo
    )

    assert isinstance(comment, Comment)
    assert comment.parent_id == 10
    assert comment.post_id == 1
    assert comment.author_id == 5
    assert comment.id is None
    assert parent_author_id == 99


def test_handler_raises_when_parent_not_found(
    rate_service: RateLimitService,
    spam_service: SpamCheckService,
) -> None:
    """ValueError raised when parent comment does not exist."""
    repo = Mock(spec=CommentRepository)
    repo.find_by_id.return_value = None

    with pytest.raises(ValueError, match="not found"):
        handle_reply_to_comment(
            _make(parent_comment_id=999),
            rate_service,
            spam_service,
            repo,
        )


def test_handler_raises_when_parent_belongs_to_different_post(
    rate_service: RateLimitService,
    spam_service: SpamCheckService,
) -> None:
    """ValueError raised when parent comment belongs to a different post."""
    wrong_post_comment = Comment.create(
        post_id=999, author_id=1, text="Other post comment"
    )
    wrong_post_comment.id = 10
    repo = Mock(spec=CommentRepository)
    repo.find_by_id.return_value = wrong_post_comment

    with pytest.raises(ValueError, match="does not belong"):
        handle_reply_to_comment(
            _make(post_id=1, parent_comment_id=10),
            rate_service,
            spam_service,
            repo,
        )


def test_handler_flags_spam_reply(
    rate_service: RateLimitService,
    spam_service: SpamCheckService,
    mock_repo: Mock,
) -> None:
    """Spam reply is flagged for moderation."""
    comment, parent_author_id = handle_reply_to_comment(
        _make(text=_SPAM_TEXT), rate_service, spam_service, mock_repo
    )

    assert comment.is_pending_moderation is True
    assert parent_author_id == 99


def test_handler_enforces_rate_limit(
    rate_service: RateLimitService,
    spam_service: SpamCheckService,
    mock_repo: Mock,
) -> None:
    """Sixth submission within the window raises RateLimitExceededError."""
    for i in range(5):
        handle_reply_to_comment(
            _make(text=f"Reply {i}"), rate_service, spam_service, mock_repo
        )

    with pytest.raises(RateLimitExceededError):
        handle_reply_to_comment(
            _make(text="One too many"), rate_service, spam_service, mock_repo
        )


def test_handler_admin_bypasses_rate_limit(
    rate_service: RateLimitService,
    spam_service: SpamCheckService,
    mock_repo: Mock,
) -> None:
    """Admin submissions bypass rate limiting."""
    for i in range(10):
        comment, parent_author_id = handle_reply_to_comment(
            _make(text=f"Admin reply {i}", is_admin=True),
            rate_service,
            spam_service,
            mock_repo,
        )
        assert isinstance(comment, Comment)
        assert parent_author_id == 99
