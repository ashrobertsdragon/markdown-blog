"""Revisions API routes blueprint for revision tracking operations."""

import logging
from datetime import UTC, datetime

from flask import Blueprint, Response, g, jsonify, request

from backend.api.middleware.auth_middleware import require_auth
from backend.application.commands.revert_to_revision_command import (
    RevertToRevisionCommand,
    revert_to_revision_handler,
)
from backend.application.queries.compare_revisions_query import (
    CompareRevisionsQuery,
    compare_revisions_handler,
)
from backend.application.queries.get_revision_history_query import (
    GetRevisionHistoryQuery,
    get_revision_history_handler,
)
from backend.application.queries.get_revision_query import (
    GetRevisionQuery,
    get_revision_handler,
)
from backend.config import FileSystemSettings, GitHubSettings
from backend.domain.aggregates.post_revision import PostRevision
from backend.infrastructure.markdown.markdown_rendering_service import (
    MarkdownRenderingService,
)
from backend.infrastructure.persistence.filesystem_draft_repository import (
    FileSystemDraftRepository,
)
from backend.infrastructure.persistence.post_repository import PostRepository
from backend.infrastructure.persistence.post_revision_repository import (
    PostRevisionRepository,
)
from backend.infrastructure.rendering.html_sanitizer import HtmlSanitizer
from backend.infrastructure.versioning.diff_service import DiffService
from backend.infrastructure.versioning.github_sync_service import (
    GitHubSyncService,
)

revisions_bp = Blueprint("revisions", __name__)
logger = logging.getLogger(__name__)

_filesystem_settings: FileSystemSettings | None = None
_github_settings: GitHubSettings | None = None


def _get_filesystem_settings() -> FileSystemSettings:
    """Lazily initialize FileSystemSettings instance."""
    global _filesystem_settings
    if _filesystem_settings is None:
        _filesystem_settings = FileSystemSettings()
    return _filesystem_settings


def _get_github_settings() -> GitHubSettings:
    """Lazily initialize GitHubSettings instance."""
    global _github_settings
    if _github_settings is None:
        _github_settings = GitHubSettings()
    return _github_settings


def _get_post_repository() -> PostRepository:
    """Get PostRepository instance."""
    return PostRepository()


def _get_revision_repository() -> PostRevisionRepository:
    """Get PostRevisionRepository instance."""
    return PostRevisionRepository()


def _get_draft_repository() -> FileSystemDraftRepository:
    """Get FileSystemDraftRepository instance."""
    fs_settings = _get_filesystem_settings()
    return FileSystemDraftRepository(fs_settings.DRAFTS_PATH)


def _get_github_service() -> GitHubSyncService:
    """Get GitHubSyncService instance."""
    gh_settings = _get_github_settings()
    return GitHubSyncService(
        gh_settings.GITHUB_TOKEN,
        gh_settings.GITHUB_OWNER,
        gh_settings.GITHUB_REPO,
    )


def _get_markdown_service() -> MarkdownRenderingService:
    """Get MarkdownRenderingService instance."""
    return MarkdownRenderingService()


def _get_sanitizer() -> HtmlSanitizer:
    """Get HtmlSanitizer instance."""
    return HtmlSanitizer()


def _get_diff_service() -> DiffService:
    """Get DiffService instance."""
    return DiffService()


def _format_revision_dict(revision: PostRevision) -> dict:
    """Format PostRevision aggregate into JSON response object.

    Args:
        revision: PostRevision aggregate

    Returns:
        Dictionary with revision metadata
    """
    return {
        "id": str(revision.id),
        "commit_sha": str(revision.commit_sha),
        "short_sha": revision.commit_sha.short_sha,
        "author_id": str(revision.author_id),
        "timestamp": revision.created_at.isoformat(),
        "relative_time": _format_relative_time(revision.created_at),
        "commit_message": revision.commit_message,
        "is_revert": revision.is_revert,
    }


def _format_relative_time(dt: datetime) -> str:
    """Format datetime as relative time string.

    Args:
        dt: Datetime to format

    Returns:
        Human-readable relative time (e.g., "2 days ago")
    """
    now = datetime.now(UTC)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=UTC)

    diff = now - dt
    seconds = diff.total_seconds()

    if seconds < 60:
        return "just now"
    if seconds < 3600:
        minutes = int(seconds / 60)
        return f"{minutes} minute{'s' if minutes != 1 else ''} ago"
    if seconds < 86400:
        hours = int(seconds / 3600)
        return f"{hours} hour{'s' if hours != 1 else ''} ago"
    days = int(seconds / 86400)
    return f"{days} day{'s' if days != 1 else ''} ago"


@revisions_bp.route("/<slug>/revisions", methods=["GET"])
@require_auth
def list_revisions(slug: str) -> tuple[Response, int]:
    """List paginated revisions for a post.

    Fetches revision history with optional pagination. Returns most recent
    first, includes author info and commit messages.

    Query parameters:
        skip: Records to skip (0-10000, default 0)
        limit: Records per page (1-100, default 10)

    Returns:
        JSON response with revisions, total_count, has_more

    Raises:
        400: Invalid skip/limit parameters
        401: Missing or invalid authentication
        404: Post not found
    """
    logger.info(f"Fetching revisions for post: {slug}")

    skip = request.args.get("skip", 0, type=int)
    limit = request.args.get("limit", 10, type=int)

    if not 0 <= skip <= 10000:
        return jsonify({"error": "skip must be between 0 and 10000"}), 400

    if not 1 <= limit <= 100:
        return jsonify({"error": "limit must be between 1 and 100"}), 400

    post_repo = _get_post_repository()
    post = post_repo.find_by_slug(slug)

    if post is None:
        return jsonify({"error": f"Post '{slug}' not found"}), 404

    if post.id is None:
        return jsonify({"error": f"Post '{slug}' has no ID"}), 500

    # Authorization: only author or admin can view revision history
    if post.author_id != g.current_user.id and g.current_user.role != "admin":
        return jsonify({"error": "Not authorized to view revisions"}), 403

    try:
        query = GetRevisionHistoryQuery(
            post_id=post.id,
            skip=skip,
            limit=limit,
        )
        response = get_revision_history_handler(
            query,
            _get_revision_repository(),
        )

        return jsonify(
            {
                "revisions": [
                    _format_revision_dict(rev) for rev in response.revisions
                ],
                "total_count": response.total_count,
                "has_more": response.has_more,
            }
        ), 200

    except ValueError as e:
        return jsonify({"error": str(e)}), 400
    except Exception as e:
        logger.exception(
            "Unexpected error in list_revisions",
            exc_info=e,
            extra={"slug": slug, "skip": skip, "limit": limit},
        )
        raise


@revisions_bp.route("/<slug>/revisions/<sha>", methods=["GET"])
@require_auth
def get_revision(slug: str, sha: str) -> tuple[Response, int]:
    """Get single revision by SHA.

    Retrieves a specific revision with rendered HTML content. Returns
    both markdown and sanitized HTML versions of the content.

    Returns:
        JSON response with revision data, markdown_content, html_content

    Raises:
        400: Invalid SHA format
        401: Missing or invalid authentication
        404: Post or revision not found
    """
    logger.info(f"Fetching revision {sha[:7]} for post: {slug}")

    if not sha:
        return jsonify({"error": "SHA cannot be empty"}), 400

    if len(sha) > 100:
        return jsonify(
            {"error": f"SHA length {len(sha)} exceeds maximum of 100"}
        ), 400

    post_repo = _get_post_repository()
    post = post_repo.find_by_slug(slug)

    if post is None:
        return jsonify({"error": f"Post '{slug}' not found"}), 404

    if post.id is None:
        return jsonify({"error": f"Post '{slug}' has no ID"}), 500

    # Authorization: only author or admin can view revision details
    if post.author_id != g.current_user.id and g.current_user.role != "admin":
        return jsonify({"error": "Not authorized to view revisions"}), 403

    try:
        query = GetRevisionQuery(post_id=post.id, commit_sha=sha)
        response = get_revision_handler(
            query,
            _get_revision_repository(),
            _get_markdown_service(),
            _get_sanitizer(),
        )

        # Determine if this is the most recent revision by querying
        revision_repo = _get_revision_repository()
        recent_revisions, _ = revision_repo.find_by_post_id(
            post_id=post.id, skip=0, limit=1
        )
        is_current = len(recent_revisions) > 0 and str(
            recent_revisions[0].commit_sha
        ) == str(response.revision.commit_sha)

        return jsonify(
            {
                "id": str(response.revision.id),
                "commit_sha": str(response.revision.commit_sha),
                "short_sha": response.revision.commit_sha.short_sha,
                "author_id": str(response.revision.author_id),
                "timestamp": response.revision.created_at.isoformat(),
                "commit_message": response.revision.commit_message,
                "markdown_content": response.markdown_content,
                "html_content": response.html_content,
                "is_current": is_current,
                "is_revert": response.revision.is_revert,
            }
        ), 200

    except ValueError as e:
        error_msg = str(e).lower()
        if "not found" in error_msg:
            return jsonify({"error": str(e)}), 404
        return jsonify({"error": str(e)}), 400
    except Exception as e:
        logger.exception(
            "Unexpected error in get_revision",
            exc_info=e,
            extra={"slug": slug, "sha": sha},
        )
        raise


@revisions_bp.route("/<slug>/revisions/<sha1>/diff/<sha2>", methods=["GET"])
@require_auth
def compare_revisions(slug: str, sha1: str, sha2: str) -> tuple[Response, int]:
    """Compare two revisions and generate diff.

    Generates a line-by-line diff between two revisions identified by
    their commit SHAs.

    Returns:
        JSON response with from_revision, to_revision, diff_lines

    Raises:
        400: Invalid SHA format
        401: Missing or invalid authentication
        404: Post or either revision not found
    """
    logger.info(
        f"Comparing revisions for post {slug}: {sha1[:7]} -> {sha2[:7]}"
    )

    if not sha1:
        return jsonify({"error": "from_sha cannot be empty"}), 400

    if not sha2:
        return jsonify({"error": "to_sha cannot be empty"}), 400

    if len(sha1) > 100:
        return jsonify(
            {"error": f"from_sha length {len(sha1)} exceeds maximum of 100"}
        ), 400

    if len(sha2) > 100:
        return jsonify(
            {"error": f"to_sha length {len(sha2)} exceeds maximum of 100"}
        ), 400

    post_repo = _get_post_repository()
    post = post_repo.find_by_slug(slug)

    if post is None:
        return jsonify({"error": f"Post '{slug}' not found"}), 404

    if post.id is None:
        return jsonify({"error": f"Post '{slug}' has no ID"}), 500

    # Authorization: only author or admin can compare revisions
    if post.author_id != g.current_user.id and g.current_user.role != "admin":
        return jsonify({"error": "Not authorized to view revisions"}), 403

    try:
        query = CompareRevisionsQuery(
            post_id=post.id,
            from_sha=sha1,
            to_sha=sha2,
        )
        response = compare_revisions_handler(
            query,
            _get_revision_repository(),
            _get_diff_service(),
        )

        return jsonify(
            {
                "from_revision": {
                    "sha": str(response.from_revision.commit_sha),
                    "short_sha": response.from_revision.commit_sha.short_sha,
                    "timestamp": response.from_revision.created_at.isoformat(),
                    "author_id": str(response.from_revision.author_id),
                },
                "to_revision": {
                    "sha": str(response.to_revision.commit_sha),
                    "short_sha": response.to_revision.commit_sha.short_sha,
                    "timestamp": response.to_revision.created_at.isoformat(),
                    "author_id": str(response.to_revision.author_id),
                },
                "diff_lines": response.diff_lines,
            }
        ), 200

    except ValueError as e:
        error_msg = str(e).lower()
        if "not found" in error_msg:
            return jsonify({"error": str(e)}), 404
        return jsonify({"error": str(e)}), 400
    except Exception as e:
        logger.exception(
            "Unexpected error in compare_revisions",
            exc_info=e,
            extra={"slug": slug, "sha1": sha1, "sha2": sha2},
        )
        raise


@revisions_bp.route("/<slug>/revert", methods=["POST"])
@require_auth
def revert_to_revision(slug: str) -> tuple[Response, int]:
    """Revert post to a previous revision.

    Restores post content to a previous state identified by commit SHA.
    Creates a new commit with revert message. Only authors and admins
    can revert.

    Request body:
        {
            "target_sha": "abc123..."
        }

    Returns:
        JSON response with success, message, new_commit_sha, redirect_url

    Raises:
        400: Missing or invalid target_sha
        401: Missing or invalid authentication
        403: User not authorized (not author, not admin)
        404: Post or revision not found
    """
    data = request.get_json()

    if not data:
        return jsonify({"error": "Request body must be JSON"}), 400

    target_sha = data.get("target_sha")

    if not target_sha:
        return jsonify({"error": "Missing required field: target_sha"}), 400

    if len(target_sha) > 100:
        return jsonify(
            {
                "error": (
                    f"target_sha length {len(target_sha)} exceeds "
                    f"maximum of 100"
                )
            }
        ), 400

    logger.info(f"Revert request for post '{slug}' to SHA {target_sha[:7]}")

    try:
        command = RevertToRevisionCommand(
            slug=slug,
            target_sha=target_sha,
            author_id=g.current_user.id,
            user_role=g.current_user.role,
        )
        new_revision = revert_to_revision_handler(
            command,
            _get_post_repository(),
            _get_revision_repository(),
            _get_draft_repository(),
            _get_github_service(),
        )

        return jsonify(
            {
                "success": True,
                "message": f"Post reverted to {target_sha[:7]}",
                "new_commit_sha": new_revision.commit_sha,
                "redirect_url": f"/edit/{slug}",
            }
        ), 200

    except ValueError as e:
        error_msg = str(e).lower()
        if "not found" in error_msg:
            return jsonify({"error": str(e)}), 404
        if "not authorized" in error_msg:
            return jsonify({"error": str(e)}), 403
        return jsonify({"error": str(e)}), 400
    except RuntimeError as e:
        logger.error(f"Runtime error in revert: {e}")
        return jsonify({"error": str(e)}), 500
    except Exception as e:
        logger.exception(
            "Unexpected error in revert_to_revision",
            exc_info=e,
            extra={
                "slug": slug,
                "target_sha": target_sha,
                "author_id": g.current_user.id,
            },
        )
        raise
