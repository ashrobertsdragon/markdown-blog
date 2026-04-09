"""Integration tests for unpublish_post_handler.

Tests the full handler orchestration using mock repositories and services.
The handler is responsible for:
  1. Loading the post by slug (atomic – raises on failure)
  2. Checking ownership / admin override
  3. Validating the post is currently published
  4. Calling post.unpublish() and persisting the result (atomic)
  5. Updating the draft file (best-effort)
  6. Committing to GitHub (best-effort)

All infrastructure dependencies are mocked so these tests run without a
database, filesystem, or network.

Test Coverage:
- Happy path: published post unpublished successfully
- NotFound: post doesn't exist → ValueError containing "not found"
- AlreadyUnpublished: post.published=False → ValueError containing "not currently published" / "already unpublished"
- Best-effort draft sync failure → handler succeeds, logs warning
- Best-effort GitHub sync failure → handler succeeds, logs warning
- Database persistence: saved post has published=False
- Draft sync: draft_repo.save() called with published=False draft
- GitHub sync: github_service.commit_file() called with correct path
"""

import logging
from datetime import UTC, datetime
from unittest.mock import Mock

import pytest

from backend.application.commands.handlers.unpublish_post_handler import (
    unpublish_post_handler,
)
from backend.application.commands.unpublish_post_command import (
    UnpublishPostCommand,
)
from backend.domain.aggregates.post import Post
from backend.domain.value_objects.slug import Slug


def _make_published_post(slug: str = "my-post", author_id: int = 1) -> Post:
    """Build a published Post aggregate for use in tests.

    Returns a Post with published=True and all required fields set so
    post.unpublish() can be called without precondition failures.
    """
    now = datetime.now(UTC)
    return Post(
        id=10,
        slug=Slug(slug),
        title="My Post",
        author_id=author_id,
        _html_content=None,
        published=True,
        published_at=now,
        created_at=now,
        updated_at=now,
    )


def _make_unpublished_post(slug: str = "my-post", author_id: int = 1) -> Post:
    """Build an already-unpublished Post aggregate for negative-path tests."""
    now = datetime.now(UTC)
    return Post(
        id=10,
        slug=Slug(slug),
        title="My Post",
        author_id=author_id,
        _html_content=None,
        published=False,
        published_at=None,
        created_at=now,
        updated_at=now,
    )


@pytest.fixture()
def post_repo() -> Mock:
    """Mock PostRepository with a published post ready for retrieval."""
    mock = Mock()
    published_post = _make_published_post()
    mock.find_by_slug.return_value = published_post
    mock.save.side_effect = lambda p: p
    return mock


@pytest.fixture()
def draft_repo() -> Mock:
    """Mock FileSystemDraftRepository returning a minimal DraftFile."""
    mock = Mock()
    draft = Mock()
    draft.title = "My Post"
    draft.published = True
    draft.to_markdown.return_value = (
        "---\ntitle: My Post\npublished: false\n---\n"
    )
    mock.find_by_slug.return_value = draft
    mock.save.return_value = None
    return mock


@pytest.fixture()
def github_service() -> Mock:
    """Mock GitHubSyncService returning a synthetic commit SHA."""
    mock = Mock()
    mock.commit_file.return_value = "abc123sha"
    return mock


@pytest.fixture()
def command() -> UnpublishPostCommand:
    """Standard unpublish command issued by an admin user."""
    return UnpublishPostCommand(
        slug="my-post",
        author_id=1,
        user_role="admin",
    )


class TestUnpublishPostHandlerHappyPath:
    """Tests for the success path of unpublish_post_handler."""

    def test_returns_post_with_published_false(
        self,
        command: UnpublishPostCommand,
        post_repo: Mock,
        draft_repo: Mock,
        github_service: Mock,
    ) -> None:
        """Verify handler returns the post with published=False.

        After a successful unpublish the returned Post aggregate must
        reflect the new state so callers can serialise it directly into
        the HTTP response without a second database read.
        """
        result = unpublish_post_handler(
            command=command,
            post_repo=post_repo,
            draft_repo=draft_repo,
            github_service=github_service,
        )

        assert result.published is False

    def test_updated_at_is_changed(
        self,
        command: UnpublishPostCommand,
        post_repo: Mock,
        draft_repo: Mock,
        github_service: Mock,
    ) -> None:
        """Verify post.updated_at is refreshed by the unpublish operation.

        Post.unpublish() sets updated_at to datetime.now(UTC). The returned
        post must carry that fresh timestamp so the database record stays
        consistent with what is visible to the user.
        """
        original_post = _make_published_post()
        original_updated_at = original_post.updated_at
        post_repo.find_by_slug.return_value = original_post

        result = unpublish_post_handler(
            command=command,
            post_repo=post_repo,
            draft_repo=draft_repo,
            github_service=github_service,
        )

        assert result.updated_at >= original_updated_at

    def test_post_saved_to_repository(
        self,
        command: UnpublishPostCommand,
        post_repo: Mock,
        draft_repo: Mock,
        github_service: Mock,
    ) -> None:
        """Verify handler calls post_repo.save() exactly once.

        The database persist step is atomic: if save() is never called
        the post remains published in the database while appearing
        unpublished to callers, which is an inconsistency.
        """
        unpublish_post_handler(
            command=command,
            post_repo=post_repo,
            draft_repo=draft_repo,
            github_service=github_service,
        )

        post_repo.save.assert_called_once()

    def test_saved_post_has_published_false(
        self,
        command: UnpublishPostCommand,
        post_repo: Mock,
        draft_repo: Mock,
        github_service: Mock,
    ) -> None:
        """Verify the post passed to save() has published=False.

        Checking the return value of save() is not sufficient; the
        argument must already have published=False so the repository
        writes the correct state.
        """
        saved_posts: list[Post] = []

        def save_with_capture(p: Post) -> Post:
            saved_posts.append(p)
            return p

        post_repo.save.side_effect = save_with_capture

        unpublish_post_handler(
            command=command,
            post_repo=post_repo,
            draft_repo=draft_repo,
            github_service=github_service,
        )

        assert len(saved_posts) == 1
        assert saved_posts[0].published is False


class TestUnpublishPostHandlerNotFound:
    """Tests for the case where the target post does not exist."""

    def test_raises_value_error_when_post_not_found(
        self,
        command: UnpublishPostCommand,
        post_repo: Mock,
        draft_repo: Mock,
        github_service: Mock,
    ) -> None:
        """Verify handler raises ValueError when find_by_slug returns None.

        The handler must not attempt to unpublish a post that doesn't
        exist. The error message must contain "not found" so API middleware
        can map it to an appropriate HTTP 404 response.
        """
        post_repo.find_by_slug.return_value = None

        with pytest.raises(ValueError, match="not found"):
            unpublish_post_handler(
                command=command,
                post_repo=post_repo,
                draft_repo=draft_repo,
                github_service=github_service,
            )

    def test_save_not_called_when_post_not_found(
        self,
        command: UnpublishPostCommand,
        post_repo: Mock,
        draft_repo: Mock,
        github_service: Mock,
    ) -> None:
        """Verify no persistence occurs when the post is missing.

        If find_by_slug returns None the handler must fail fast before
        touching the database or filesystem.
        """
        post_repo.find_by_slug.return_value = None

        with pytest.raises(ValueError):
            unpublish_post_handler(
                command=command,
                post_repo=post_repo,
                draft_repo=draft_repo,
                github_service=github_service,
            )

        post_repo.save.assert_not_called()
        github_service.commit_file.assert_not_called()


class TestUnpublishPostHandlerAlreadyUnpublished:
    """Tests for the case where the post is already unpublished."""

    def test_raises_value_error_when_already_unpublished(
        self,
        command: UnpublishPostCommand,
        post_repo: Mock,
        draft_repo: Mock,
        github_service: Mock,
    ) -> None:
        """Verify handler raises ValueError when post.published is False.

        Idempotent unpublish is not supported: calling unpublish on an
        already-unpublished post is a caller error. The message must
        indicate the post is not currently published so API callers can
        return a meaningful error to users.
        """
        post_repo.find_by_slug.return_value = _make_unpublished_post()

        with pytest.raises(
            ValueError, match="not currently published|already unpublished"
        ):
            unpublish_post_handler(
                command=command,
                post_repo=post_repo,
                draft_repo=draft_repo,
                github_service=github_service,
            )

    def test_save_not_called_when_already_unpublished(
        self,
        command: UnpublishPostCommand,
        post_repo: Mock,
        draft_repo: Mock,
        github_service: Mock,
    ) -> None:
        """Verify no write operations occur when post is already unpublished.

        The handler must short-circuit before any mutation step when the
        precondition check fails.
        """
        post_repo.find_by_slug.return_value = _make_unpublished_post()

        with pytest.raises(ValueError):
            unpublish_post_handler(
                command=command,
                post_repo=post_repo,
                draft_repo=draft_repo,
                github_service=github_service,
            )

        post_repo.save.assert_not_called()


class TestUnpublishPostHandlerAuthorization:
    """Tests for ownership and role-based authorization checks."""

    def test_non_owner_non_admin_raises_value_error(
        self,
        post_repo: Mock,
        draft_repo: Mock,
        github_service: Mock,
    ) -> None:
        """Verify handler raises ValueError when a non-owner, non-admin requests unpublish.

        A user with role "author" who does not own the post must be rejected
        before any mutation occurs. The error signals a 403-class caller error
        rather than a data integrity problem.
        """
        post_repo.find_by_slug.return_value = _make_published_post(author_id=2)
        command = UnpublishPostCommand(
            slug="my-post", author_id=1, user_role="author"
        )

        with pytest.raises(ValueError):
            unpublish_post_handler(
                command=command,
                post_repo=post_repo,
                draft_repo=draft_repo,
                github_service=github_service,
            )

    def test_admin_can_unpublish_another_authors_post(
        self,
        post_repo: Mock,
        draft_repo: Mock,
        github_service: Mock,
    ) -> None:
        """Verify an admin can unpublish a post they do not own.

        Admins must have the ability to moderate any post regardless of
        authorship. The returned post must reflect the unpublished state.
        """
        post_repo.find_by_slug.return_value = _make_published_post(author_id=2)
        command = UnpublishPostCommand(
            slug="my-post", author_id=1, user_role="admin"
        )

        result = unpublish_post_handler(
            command=command,
            post_repo=post_repo,
            draft_repo=draft_repo,
            github_service=github_service,
        )

        assert result.published is False


class TestUnpublishPostHandlerBestEffortSync:
    """Tests for best-effort draft and GitHub sync failure handling."""

    def test_draft_sync_failure_does_not_raise(
        self,
        command: UnpublishPostCommand,
        post_repo: Mock,
        github_service: Mock,
    ) -> None:
        """Verify handler succeeds when draft_repo.save() raises OSError.

        Draft file updates are best-effort: an OSError (e.g. permissions,
        disk full) must not roll back the database unpublish. The post is
        considered successfully unpublished once saved to the database.
        """
        failing_draft_repo = Mock()
        draft = Mock()
        draft.title = "My Post"
        draft.published = True
        draft.to_markdown.return_value = "---\ntitle: My Post\n---\n"
        failing_draft_repo.find_by_slug.return_value = draft
        failing_draft_repo.save.side_effect = OSError("disk full")

        result = unpublish_post_handler(
            command=command,
            post_repo=post_repo,
            draft_repo=failing_draft_repo,
            github_service=github_service,
        )

        assert result.published is False

    def test_draft_sync_failure_logs_warning(
        self,
        command: UnpublishPostCommand,
        post_repo: Mock,
        github_service: Mock,
        caplog: pytest.LogCaptureFixture,
    ) -> None:
        """Verify a warning is emitted when draft file update fails.

        Operators must be able to detect desynchronised draft files from
        log output without the error surfacing to the HTTP caller.
        """
        failing_draft_repo = Mock()
        draft = Mock()
        draft.title = "My Post"
        draft.published = True
        draft.to_markdown.return_value = "---\ntitle: My Post\n---\n"
        failing_draft_repo.find_by_slug.return_value = draft
        failing_draft_repo.save.side_effect = OSError("disk full")

        with caplog.at_level(logging.WARNING):
            unpublish_post_handler(
                command=command,
                post_repo=post_repo,
                draft_repo=failing_draft_repo,
                github_service=github_service,
            )

        warning_messages = [
            r.message for r in caplog.records if r.levelno >= logging.WARNING
        ]
        assert any(
            "my-post" in m or "draft" in m.lower() for m in warning_messages
        )

    def test_github_sync_failure_does_not_raise(
        self,
        command: UnpublishPostCommand,
        post_repo: Mock,
        draft_repo: Mock,
    ) -> None:
        """Verify handler succeeds when github_service.commit_file() raises.

        GitHub commits are best-effort. A network error, rate limit, or
        auth failure must not undo the database unpublish. The caller
        receives the unpublished post regardless.
        """
        failing_github = Mock()
        failing_github.commit_file.side_effect = Exception("GitHub unavailable")

        result = unpublish_post_handler(
            command=command,
            post_repo=post_repo,
            draft_repo=draft_repo,
            github_service=failing_github,
        )

        assert result.published is False

    def test_github_sync_failure_logs_warning(
        self,
        command: UnpublishPostCommand,
        post_repo: Mock,
        draft_repo: Mock,
        caplog: pytest.LogCaptureFixture,
    ) -> None:
        """Verify a warning is emitted when GitHub commit fails.

        GitHub sync failures must appear in logs so operators can trigger
        a manual resync without surfacing the failure to end users.
        """
        failing_github = Mock()
        failing_github.commit_file.side_effect = Exception("GitHub unavailable")

        with caplog.at_level(logging.WARNING):
            unpublish_post_handler(
                command=command,
                post_repo=post_repo,
                draft_repo=draft_repo,
                github_service=failing_github,
            )

        warning_messages = [
            r.message for r in caplog.records if r.levelno >= logging.WARNING
        ]
        assert any(
            "github" in m.lower() or "commit" in m.lower() or "my-post" in m
            for m in warning_messages
        )

    def test_github_not_called_when_draft_save_fails(
        self,
        command: UnpublishPostCommand,
        post_repo: Mock,
        github_service: Mock,
    ) -> None:
        """Verify github_service.commit_file() is never called when draft_repo.save() raises.

        If saving the draft file fails, committing potentially stale or
        partially-written content to GitHub is unsafe. The handler must
        abort the GitHub step rather than propagating inconsistent data
        to the version control backup.
        """
        failing_draft_repo = Mock()
        draft = Mock()
        draft.title = "My Post"
        draft.published = True
        draft.to_markdown.return_value = "---\ntitle: My Post\n---\n"
        failing_draft_repo.find_by_slug.return_value = draft
        failing_draft_repo.save.side_effect = OSError("disk full")

        unpublish_post_handler(
            command=command,
            post_repo=post_repo,
            draft_repo=failing_draft_repo,
            github_service=github_service,
        )

        github_service.commit_file.assert_not_called()

    def test_both_sync_failures_handler_still_returns_post(
        self,
        command: UnpublishPostCommand,
        post_repo: Mock,
    ) -> None:
        """Verify handler returns the post even when both sync steps fail.

        Both the draft file update and the GitHub commit can fail
        simultaneously (e.g. during infrastructure outage) without the
        handler raising. The database state is the source of truth.
        """
        failing_draft_repo = Mock()
        draft = Mock()
        draft.title = "My Post"
        draft.published = True
        draft.to_markdown.return_value = ""
        failing_draft_repo.find_by_slug.return_value = draft
        failing_draft_repo.save.side_effect = OSError("disk full")

        failing_github = Mock()
        failing_github.commit_file.side_effect = Exception("network error")

        result = unpublish_post_handler(
            command=command,
            post_repo=post_repo,
            draft_repo=failing_draft_repo,
            github_service=failing_github,
        )

        assert result is not None
        assert result.published is False


class TestUnpublishPostHandlerSyncIntegration:
    """Tests verifying correct arguments are forwarded to sync dependencies."""

    def test_draft_repo_save_called_with_published_false(
        self,
        command: UnpublishPostCommand,
        post_repo: Mock,
        draft_repo: Mock,
        github_service: Mock,
    ) -> None:
        """Verify draft_repo.save() receives the draft with published=False.

        The handler must mutate the draft's published flag before
        persisting it. Saving an un-mutated draft leaves the markdown
        front matter out of sync with the database.
        """
        unpublish_post_handler(
            command=command,
            post_repo=post_repo,
            draft_repo=draft_repo,
            github_service=github_service,
        )

        draft_repo.save.assert_called_once()
        saved_draft = draft_repo.save.call_args[0][0]
        assert saved_draft.published is False

    def test_github_commit_file_called_with_correct_path(
        self,
        command: UnpublishPostCommand,
        post_repo: Mock,
        draft_repo: Mock,
        github_service: Mock,
    ) -> None:
        """Verify github_service.commit_file() receives the correct draft path.

        The path argument must follow the convention `drafts/{slug}.md`
        so the GitHub repository layout remains consistent with the
        filesystem layout.
        """
        unpublish_post_handler(
            command=command,
            post_repo=post_repo,
            draft_repo=draft_repo,
            github_service=github_service,
        )

        github_service.commit_file.assert_called_once()
        call_kwargs = github_service.commit_file.call_args
        path_arg = call_kwargs[1].get("path") or call_kwargs[0][0]
        assert path_arg == "drafts/my-post.md"

    def test_github_not_called_when_draft_missing(
        self,
        command: UnpublishPostCommand,
        post_repo: Mock,
        github_service: Mock,
    ) -> None:
        """Verify GitHub commit is skipped when draft file is absent.

        If the draft file has been deleted or never existed the handler
        cannot build valid markdown content for a commit, so the GitHub
        step must be skipped entirely rather than committing empty content.
        """
        no_draft_repo = Mock()
        no_draft_repo.find_by_slug.return_value = None

        unpublish_post_handler(
            command=command,
            post_repo=post_repo,
            draft_repo=no_draft_repo,
            github_service=github_service,
        )

        github_service.commit_file.assert_not_called()

    def test_db_save_failure_propagates(
        self,
        command: UnpublishPostCommand,
        post_repo: Mock,
        draft_repo: Mock,
        github_service: Mock,
    ) -> None:
        """Verify handler re-raises exceptions from post_repo.save().

        Database persistence is atomic: if save() raises, the caller must
        see the exception so the HTTP layer can return a 500 rather than
        silently reporting success while the post remains published in the
        database.
        """
        post_repo.save.side_effect = Exception("db error")

        with pytest.raises(Exception, match="db error"):
            unpublish_post_handler(
                command=command,
                post_repo=post_repo,
                draft_repo=draft_repo,
                github_service=github_service,
            )
