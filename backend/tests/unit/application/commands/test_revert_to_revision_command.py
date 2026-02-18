"""Unit tests for RevertToRevisionCommand and handler.

This module defines comprehensive unit tests for the
revert_to_revision_command and handler following TDD Red phase
principles. Tests cover dataclass validation, handler orchestration,
authorization, and error scenarios.

Test Coverage:
- Command dataclass structure and validation (8 tests)
- Handler success path with full orchestration (4 tests)
- Authorization scenarios: owner, non-owner, admin (3 tests)
- Error scenarios: revision not found, GitHub failures (4 tests)
- Handler orchestration logic with mocked dependencies (5 tests)

Total: 24+ unit tests
"""

from datetime import UTC, datetime
from typing import Any
from unittest.mock import Mock
from uuid import uuid4

import pytest

from backend.domain.aggregates.post import Post
from backend.domain.aggregates.post_revision import PostRevision
from backend.domain.value_objects.commit_sha import CommitSHA
from backend.domain.value_objects.slug import Slug

try:
    from backend.application.commands.revert_to_revision_command import (
        RevertToRevisionCommand,
        revert_to_revision_handler,
    )
except ImportError:
    RevertToRevisionCommand = None  # type: ignore[misc,assignment]
    revert_to_revision_handler = None  # type: ignore[misc,assignment]


def test_command_dataclass_structure() -> None:
    """Verify RevertToRevisionCommand has required fields with correct types.

    This test ensures the command dataclass has exactly four required
    fields: slug (str), target_sha (str), author_id (int), and user_role (str).
    The dataclass must be properly defined with type hints for all fields.
    """
    command = RevertToRevisionCommand(
        slug="test-post",
        target_sha="abc123def456",
        author_id=1,
        user_role="author",
    )

    assert hasattr(command, "slug")
    assert hasattr(command, "target_sha")
    assert hasattr(command, "author_id")
    assert hasattr(command, "user_role")
    assert isinstance(command.slug, str)
    assert isinstance(command.target_sha, str)
    assert isinstance(command.author_id, int)
    assert isinstance(command.user_role, str)


def test_command_with_valid_values() -> None:
    """Verify command correctly assigns all field values.

    This test ensures that when creating a RevertToRevisionCommand with valid
    values, all fields are assigned correctly and can be accessed.
    """
    slug = "my-first-post"
    target_sha = "abc123def456"
    author_id = 42
    user_role = "author"

    command = RevertToRevisionCommand(
        slug=slug,
        target_sha=target_sha,
        author_id=author_id,
        user_role=user_role,
    )

    assert command.slug == slug
    assert command.target_sha == target_sha
    assert command.author_id == author_id
    assert command.user_role == user_role


def test_command_validates_slug_max_length() -> None:
    """Verify command rejects slug exceeding 1000 characters.

    This test ensures DoS protection via size constraints. Slug must not
    exceed 1000 characters to prevent memory exhaustion.
    """
    long_slug = "a" * 1001

    with pytest.raises(ValueError, match="slug.*1000.*characters"):
        RevertToRevisionCommand(
            slug=long_slug,
            target_sha="abc123",
            author_id=1,
            user_role="author",
        )


def test_command_validates_target_sha_max_length() -> None:
    """Verify command rejects target_sha exceeding 100 characters.

    This test ensures DoS protection via size constraints. GitHub SHAs
    are 40 chars (SHA-1) or 64 chars (SHA-256), so 100 is reasonable max.
    """
    long_sha = "a" * 101

    with pytest.raises(ValueError, match="target_sha.*100.*characters"):
        RevertToRevisionCommand(
            slug="test-post",
            target_sha=long_sha,
            author_id=1,
            user_role="author",
        )


def test_command_validates_empty_slug() -> None:
    """Verify command rejects empty slug.

    This test ensures basic validation. Empty slug is meaningless.
    """
    with pytest.raises(ValueError, match="slug.*empty"):
        RevertToRevisionCommand(
            slug="", target_sha="abc123", author_id=1, user_role="author"
        )


def test_command_validates_empty_target_sha() -> None:
    """Verify command rejects empty target_sha.

    This test ensures basic validation. Empty target_sha is meaningless.
    """
    with pytest.raises(ValueError, match="target_sha.*empty"):
        RevertToRevisionCommand(
            slug="test-post", target_sha="", author_id=1, user_role="author"
        )


def test_command_validates_positive_author_id() -> None:
    """Verify command rejects non-positive author_id.

    This test ensures author_id validation. Author IDs must be positive
    integers since they reference database primary keys.
    """
    with pytest.raises(ValueError, match="author_id.*positive"):
        RevertToRevisionCommand(
            slug="test-post",
            target_sha="abc123",
            author_id=0,
            user_role="author",
        )


def test_command_validates_empty_user_role() -> None:
    """Verify command rejects empty user_role.

    This test ensures user_role validation. Role is required
    for authorization.
    """
    with pytest.raises(ValueError, match="user_role.*empty"):
        RevertToRevisionCommand(
            slug="test-post", target_sha="abc123", author_id=1, user_role=""
        )


def test_command_fields_are_immutable() -> None:
    """Verify command fields cannot be modified after creation.

    This test ensures the RevertToRevisionCommand is immutable by using
    frozen dataclass. Attempting to modify fields after construction
    should raise an error, preventing accidental mutation.
    """
    command = RevertToRevisionCommand(
        slug="test-post",
        target_sha="abc123",
        author_id=1,
        user_role="author",
    )

    with pytest.raises((AttributeError, TypeError)):
        command.slug = "modified-slug"  # type: ignore[misc]

    with pytest.raises((AttributeError, TypeError)):
        command.target_sha = "modified-sha"  # type: ignore[misc]


def test_command_repr_shows_all_fields() -> None:
    """Verify command repr includes all field values for debugging.

    This test ensures the string representation of the command shows all
    field values, which is useful for debugging and logging.
    """
    command = RevertToRevisionCommand(
        slug="test-post",
        target_sha="abc123def456",
        author_id=1,
        user_role="author",
    )

    repr_str = repr(command)

    assert "RevertToRevisionCommand" in repr_str
    assert "test-post" in repr_str
    assert "abc123def456" in repr_str
    assert "1" in repr_str
    assert "author" in repr_str


@pytest.fixture
def mock_post_repo() -> Mock:
    """Fixture providing mock PostRepository."""
    return Mock()


@pytest.fixture
def mock_revision_repo() -> Mock:
    """Fixture providing mock PostRevisionRepository."""
    return Mock()


@pytest.fixture
def mock_draft_repo() -> Mock:
    """Fixture providing mock FileSystemDraftRepository."""
    return Mock()


@pytest.fixture
def mock_github_service() -> Mock:
    """Fixture providing mock GitHubSyncService."""
    return Mock()


@pytest.fixture
def sample_post_fixture() -> Post:
    """Fixture providing a sample Post aggregate."""
    return Post(
        id=1,
        slug=Slug("test-post"),
        title="Test Post",
        author_id=42,
        _html_content=None,
        published=False,
        published_at=None,
        created_at=datetime(2025, 1, 1, 12, 0, 0, tzinfo=UTC),
        updated_at=datetime(2025, 1, 1, 12, 0, 0, tzinfo=UTC),
    )


@pytest.fixture
def sample_revision_fixture() -> PostRevision:
    """Fixture providing a sample PostRevision aggregate."""
    return PostRevision(
        id=uuid4(),
        post_id=1,
        commit_sha=CommitSHA("abc123def456789012345678901234567890abcd"),
        author_id=2,
        commit_message="Original commit message",
        markdown_content="# Old Content\n\nThis is the old version.",
        created_at=datetime(2025, 1, 1, 12, 0, 0, tzinfo=UTC),
        updated_at=datetime(2025, 1, 1, 12, 0, 0, tzinfo=UTC),
        is_revert=False,
    )


def test_handler_verifies_authorization_for_owner(
    sample_post_fixture: Post,
    sample_revision_fixture: PostRevision,
    mock_post_repo: Mock,
    mock_revision_repo: Mock,
    mock_draft_repo: Mock,
    mock_github_service: Mock,
) -> None:
    """Verify handler allows post owner to revert.

    This test ensures authorization check passes when author_id matches
    post.author_id. Owner should be able to revert their own posts.
    """
    mock_post_repo.find_by_slug.return_value = sample_post_fixture
    mock_revision_repo.find_by_sha.return_value = sample_revision_fixture
    mock_github_service.commit_file.return_value = (
        "def456789012345678901234567890123456789a"
    )
    mock_revision_repo.save.return_value = sample_revision_fixture

    command = RevertToRevisionCommand(
        slug="test-post",
        target_sha="abc123def456",
        author_id=42,
        user_role="author",
    )

    result = revert_to_revision_handler(
        command=command,
        post_repo=mock_post_repo,
        revision_repo=mock_revision_repo,
        draft_repo=mock_draft_repo,
        github_service=mock_github_service,
    )

    assert result is not None
    mock_post_repo.find_by_slug.assert_called_once()
    mock_revision_repo.find_by_sha.assert_called_once()


def test_handler_verifies_authorization_for_admin(
    sample_post_fixture: Post,
    sample_revision_fixture: PostRevision,
    mock_post_repo: Mock,
    mock_revision_repo: Mock,
    mock_draft_repo: Mock,
    mock_github_service: Mock,
) -> None:
    """Verify handler allows admin to revert any post.

    This test ensures authorization check passes when user_role is "admin",
    even if author_id doesn't match post.author_id. Admins can revert any post.
    """
    mock_post_repo.find_by_slug.return_value = sample_post_fixture
    mock_revision_repo.find_by_sha.return_value = sample_revision_fixture
    mock_github_service.commit_file.return_value = (
        "def456789012345678901234567890123456789a"
    )
    mock_revision_repo.save.return_value = sample_revision_fixture

    command = RevertToRevisionCommand(
        slug="test-post",
        target_sha="abc123def456",
        author_id=999,
        user_role="admin",
    )

    result = revert_to_revision_handler(
        command=command,
        post_repo=mock_post_repo,
        revision_repo=mock_revision_repo,
        draft_repo=mock_draft_repo,
        github_service=mock_github_service,
    )

    assert result is not None


def test_handler_rejects_unauthorized_user(
    sample_post_fixture: Post,
    mock_post_repo: Mock,
    mock_revision_repo: Mock,
    mock_draft_repo: Mock,
    mock_github_service: Mock,
) -> None:
    """Verify handler rejects revert attempt by non-owner, non-admin.

    This test ensures authorization check fails when author_id doesn't match
    post.author_id AND user_role is not "admin". Should raise ValueError.
    """
    mock_post_repo.find_by_slug.return_value = sample_post_fixture

    command = RevertToRevisionCommand(
        slug="test-post",
        target_sha="abc123def456",
        author_id=999,
        user_role="author",
    )

    with pytest.raises(ValueError, match="[Nn]ot authorized|[Uu]nauthorized"):
        revert_to_revision_handler(
            command=command,
            post_repo=mock_post_repo,
            revision_repo=mock_revision_repo,
            draft_repo=mock_draft_repo,
            github_service=mock_github_service,
        )


def test_handler_raises_error_when_post_not_found(
    mock_post_repo: Mock,
    mock_revision_repo: Mock,
    mock_draft_repo: Mock,
    mock_github_service: Mock,
) -> None:
    """Verify handler raises error when post doesn't exist.

    This test ensures the handler raises ValueError when PostRepository
    returns None for the given slug.
    """
    mock_post_repo.find_by_slug.return_value = None

    command = RevertToRevisionCommand(
        slug="nonexistent-post",
        target_sha="abc123",
        author_id=1,
        user_role="author",
    )

    with pytest.raises(ValueError, match="[Pp]ost.*not found"):
        revert_to_revision_handler(
            command=command,
            post_repo=mock_post_repo,
            revision_repo=mock_revision_repo,
            draft_repo=mock_draft_repo,
            github_service=mock_github_service,
        )


def test_handler_raises_error_when_revision_not_found(
    sample_post_fixture: Post,
    mock_post_repo: Mock,
    mock_revision_repo: Mock,
    mock_draft_repo: Mock,
    mock_github_service: Mock,
) -> None:
    """Verify handler raises error when revision doesn't exist.

    This test ensures the handler raises ValueError when PostRevisionRepository
    returns None for the given commit SHA.
    """
    mock_post_repo.find_by_slug.return_value = sample_post_fixture
    mock_revision_repo.find_by_sha.return_value = None

    command = RevertToRevisionCommand(
        slug="test-post",
        target_sha="nonexistent_sha",
        author_id=42,
        user_role="author",
    )

    with pytest.raises(ValueError, match="[Rr]evision.*not found"):
        revert_to_revision_handler(
            command=command,
            post_repo=mock_post_repo,
            revision_repo=mock_revision_repo,
            draft_repo=mock_draft_repo,
            github_service=mock_github_service,
        )


def test_handler_writes_markdown_to_filesystem(
    sample_post_fixture: Post,
    sample_revision_fixture: PostRevision,
    mock_post_repo: Mock,
    mock_revision_repo: Mock,
    mock_draft_repo: Mock,
    mock_github_service: Mock,
) -> None:
    """Verify handler writes reverted markdown to filesystem.

    This test ensures the handler calls draft_repo.find_by_slug and
    draft_repo.save with the markdown content from the target revision.
    """
    mock_draft_file = Mock()
    mock_draft_file.slug = "test-post"
    mock_draft_file.title = "Test Post"
    mock_draft_file.author = "test_author"
    mock_draft_file.published = False
    mock_draft_file.created_at = datetime(2025, 1, 1, 12, 0, 0, tzinfo=UTC)
    mock_draft_file.published_at = None
    mock_draft_file.tags = []

    mock_post_repo.find_by_slug.return_value = sample_post_fixture
    mock_revision_repo.find_by_sha.return_value = sample_revision_fixture
    mock_draft_repo.find_by_slug.return_value = mock_draft_file
    mock_github_service.commit_file.return_value = (
        "def456789012345678901234567890123456789a"
    )
    mock_revision_repo.save.return_value = sample_revision_fixture

    command = RevertToRevisionCommand(
        slug="test-post",
        target_sha="abc123def456789012345678901234567890abcd",
        author_id=42,
        user_role="author",
    )

    revert_to_revision_handler(
        command=command,
        post_repo=mock_post_repo,
        revision_repo=mock_revision_repo,
        draft_repo=mock_draft_repo,
        github_service=mock_github_service,
    )

    mock_draft_repo.find_by_slug.assert_called_once_with("test-post")
    mock_draft_repo.save.assert_called_once()
    saved_draft = mock_draft_repo.save.call_args[0][0]
    assert saved_draft.content == sample_revision_fixture.markdown_content


def test_handler_commits_to_github_with_revert_message(
    sample_post_fixture: Post,
    sample_revision_fixture: PostRevision,
    mock_post_repo: Mock,
    mock_revision_repo: Mock,
    mock_draft_repo: Mock,
    mock_github_service: Mock,
) -> None:
    """Verify handler creates GitHub commit with revert message.

    This test ensures the handler calls github_service.commit_file with
    a commit message indicating this is a revert operation.
    Expected format: "Revert to {short_sha}: {original_message}"
    """
    mock_post_repo.find_by_slug.return_value = sample_post_fixture
    mock_revision_repo.find_by_sha.return_value = sample_revision_fixture
    mock_github_service.commit_file.return_value = (
        "def456789012345678901234567890123456789a"
    )
    mock_revision_repo.save.return_value = sample_revision_fixture

    command = RevertToRevisionCommand(
        slug="test-post",
        target_sha="abc123def456",
        author_id=42,
        user_role="author",
    )

    revert_to_revision_handler(
        command=command,
        post_repo=mock_post_repo,
        revision_repo=mock_revision_repo,
        draft_repo=mock_draft_repo,
        github_service=mock_github_service,
    )

    mock_github_service.commit_file.assert_called_once()
    call_args = mock_github_service.commit_file.call_args[1]
    commit_message = str(call_args)
    assert "revert" in commit_message.lower() or "Revert" in commit_message


def test_handler_creates_revision_with_is_revert_flag(
    sample_post_fixture: Post,
    sample_revision_fixture: PostRevision,
    mock_post_repo: Mock,
    mock_revision_repo: Mock,
    mock_draft_repo: Mock,
    mock_github_service: Mock,
) -> None:
    """Verify handler creates PostRevision record with is_revert=True.

    This test ensures the handler calls revision_repo.save with a new
    PostRevision where is_revert=True to distinguish reverts from
    normal commits.
    """
    mock_draft_file = Mock()
    mock_draft_file.slug = "test-post"
    mock_draft_file.title = "Test Post"
    mock_draft_file.author = "test_author"
    mock_draft_file.published = False
    mock_draft_file.created_at = datetime(2025, 1, 1, 12, 0, 0, tzinfo=UTC)
    mock_draft_file.published_at = None
    mock_draft_file.tags = []

    mock_post_repo.find_by_slug.return_value = sample_post_fixture
    mock_revision_repo.find_by_sha.return_value = sample_revision_fixture
    mock_draft_repo.find_by_slug.return_value = mock_draft_file
    mock_github_service.commit_file.return_value = (
        "def456789012345678901234567890123456789a"
    )
    mock_revision_repo.save.return_value = sample_revision_fixture

    command = RevertToRevisionCommand(
        slug="test-post",
        target_sha="abc123def456789012345678901234567890abcd",
        author_id=42,
        user_role="author",
    )

    revert_to_revision_handler(
        command=command,
        post_repo=mock_post_repo,
        revision_repo=mock_revision_repo,
        draft_repo=mock_draft_repo,
        github_service=mock_github_service,
    )

    mock_revision_repo.save.assert_called_once()
    saved_revision = mock_revision_repo.save.call_args.kwargs["post_revision"]
    assert saved_revision.is_revert is True


def test_handler_returns_new_revision(
    sample_post_fixture: Post,
    sample_revision_fixture: PostRevision,
    mock_post_repo: Mock,
    mock_revision_repo: Mock,
    mock_draft_repo: Mock,
    mock_github_service: Mock,
) -> None:
    """Verify handler returns the newly created PostRevision.

    This test ensures the handler returns a PostRevision aggregate
    representing the revert commit.
    """
    mock_post_repo.find_by_slug.return_value = sample_post_fixture
    mock_revision_repo.find_by_sha.return_value = sample_revision_fixture
    mock_github_service.commit_file.return_value = (
        "def456789012345678901234567890123456789a"
    )
    mock_revision_repo.save.return_value = sample_revision_fixture

    command = RevertToRevisionCommand(
        slug="test-post",
        target_sha="abc123def456",
        author_id=42,
        user_role="author",
    )

    result = revert_to_revision_handler(
        command=command,
        post_repo=mock_post_repo,
        revision_repo=mock_revision_repo,
        draft_repo=mock_draft_repo,
        github_service=mock_github_service,
    )

    assert isinstance(result, PostRevision)
    assert result.is_revert is True


def test_handler_propagates_github_service_errors(
    sample_post_fixture: Post,
    sample_revision_fixture: PostRevision,
    mock_post_repo: Mock,
    mock_revision_repo: Mock,
    mock_draft_repo: Mock,
    mock_github_service: Mock,
) -> None:
    """Verify handler propagates GitHub service failures.

    This test ensures the handler doesn't swallow GitHub API errors.
    If commit_file fails, the error should propagate to the caller.
    """
    mock_post_repo.find_by_slug.return_value = sample_post_fixture
    mock_revision_repo.find_by_sha.return_value = sample_revision_fixture
    mock_github_service.commit_file.side_effect = RuntimeError(
        "GitHub API error"
    )

    command = RevertToRevisionCommand(
        slug="test-post",
        target_sha="abc123def456",
        author_id=42,
        user_role="author",
    )

    with pytest.raises(RuntimeError, match="GitHub API error"):
        revert_to_revision_handler(
            command=command,
            post_repo=mock_post_repo,
            revision_repo=mock_revision_repo,
            draft_repo=mock_draft_repo,
            github_service=mock_github_service,
        )


def test_handler_orchestration_step_order(
    sample_post_fixture: Post,
    sample_revision_fixture: PostRevision,
    mock_post_repo: Mock,
    mock_revision_repo: Mock,
    mock_draft_repo: Mock,
    mock_github_service: Mock,
) -> None:
    """Verify handler executes orchestration steps in correct order.

    This test ensures the handler follows the documented orchestration order:
    1. Load post
    2. Verify authorization
    3. Load target revision
    4. Load draft file
    5. Save draft to filesystem
    6. Commit to GitHub
    7. Create revision record
    """
    mock_draft_file = Mock()
    mock_draft_file.slug = "test-post"
    mock_draft_file.title = "Test Post"
    mock_draft_file.author = "test_author"
    mock_draft_file.published = False
    mock_draft_file.created_at = datetime(2025, 1, 1, 12, 0, 0, tzinfo=UTC)
    mock_draft_file.published_at = None
    mock_draft_file.tags = []

    call_order: list[str] = []

    def track_post_repo_call(*args: Any, **kwargs: Any) -> Post:
        call_order.append("post_repo.find_by_slug")
        return sample_post_fixture

    def track_revision_repo_find(*args: Any, **kwargs: Any) -> PostRevision:
        call_order.append("revision_repo.find_by_sha")
        return sample_revision_fixture

    def track_draft_repo_find(*args: Any, **kwargs: Any) -> Mock:
        call_order.append("draft_repo.find_by_slug")
        return mock_draft_file

    def track_draft_repo_save(*args: Any, **kwargs: Any) -> None:
        call_order.append("draft_repo.save")

    def track_github_call(*args: Any, **kwargs: Any) -> str:
        call_order.append("github_service.commit_file")
        return "def456789012345678901234567890123456789a"

    def track_revision_repo_save(*args: Any, **kwargs: Any) -> None:
        call_order.append("revision_repo.save")

    mock_post_repo.find_by_slug.side_effect = track_post_repo_call
    mock_revision_repo.find_by_sha.side_effect = track_revision_repo_find
    mock_draft_repo.find_by_slug.side_effect = track_draft_repo_find
    mock_draft_repo.save.side_effect = track_draft_repo_save
    mock_github_service.commit_file.side_effect = track_github_call
    mock_revision_repo.save.side_effect = track_revision_repo_save

    command = RevertToRevisionCommand(
        slug="test-post",
        target_sha="abc123def456789012345678901234567890abcd",
        author_id=42,
        user_role="author",
    )

    revert_to_revision_handler(
        command=command,
        post_repo=mock_post_repo,
        revision_repo=mock_revision_repo,
        draft_repo=mock_draft_repo,
        github_service=mock_github_service,
    )

    assert call_order.index("post_repo.find_by_slug") < call_order.index(
        "revision_repo.find_by_sha"
    )
    assert call_order.index("revision_repo.find_by_sha") < call_order.index(
        "draft_repo.find_by_slug"
    )
    assert call_order.index("draft_repo.find_by_slug") < call_order.index(
        "draft_repo.save"
    )
    assert call_order.index("draft_repo.save") < call_order.index(
        "github_service.commit_file"
    )
    assert call_order.index("github_service.commit_file") < call_order.index(
        "revision_repo.save"
    )
