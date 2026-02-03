"""Posts API routes blueprint for post management operations."""

from flask import Blueprint, Response, g, jsonify, request

from backend.api.middleware.auth_middleware import require_auth, require_role
from backend.application.commands.create_draft_command import CreateDraftCommand
from backend.application.commands.delete_draft_command import DeleteDraftCommand
from backend.application.commands.handlers.create_draft_handler import (
    create_draft_handler,
)
from backend.application.commands.handlers.delete_draft_handler import (
    delete_draft_handler,
)
from backend.application.commands.handlers.publish_post_handler import (
    publish_post_handler,
)
from backend.application.commands.handlers.save_draft_handler import (
    save_draft_handler,
)
from backend.application.commands.handlers.unpublish_post_handler import (
    unpublish_post_handler,
)
from backend.application.commands.publish_post_command import PublishPostCommand
from backend.application.commands.save_draft_command import SaveDraftCommand
from backend.application.commands.unpublish_post_command import (
    UnpublishPostCommand,
)
from backend.application.queries.handlers.list_posts_query_handler import (
    list_posts_query_handler,
)
from backend.application.queries.list_posts_query import (
    ListPostsQuery,
    ListPostsResponse,
)
from backend.config import FileSystemSettings, GitHubSettings
from backend.domain.aggregates.post import Post
from backend.domain.value_objects.post_filter import PostFilter
from backend.domain.value_objects.slug import Slug
from backend.infrastructure.markdown.markdown_rendering_service import (
    MarkdownRenderingService,
)
from backend.infrastructure.persistence.filesystem_draft_repository import (
    FileSystemDraftRepository,
)
from backend.infrastructure.persistence.post_repository import PostRepository
from backend.infrastructure.rendering.html_sanitizer import HtmlSanitizer
from backend.infrastructure.versioning.github_sync_service import (
    GitHubSyncService,
)

posts_bp = Blueprint("posts", __name__, url_prefix="/api")

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


def _get_draft_repository() -> FileSystemDraftRepository:
    """Get FileSystemDraftRepository instance."""
    fs_settings = _get_filesystem_settings()
    return FileSystemDraftRepository(fs_settings.DRAFTS_PATH)


def _get_post_repository() -> PostRepository:
    """Get PostRepository instance."""
    return PostRepository()


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


class CreateDraftHandler:
    """Handler wrapper for create_draft_handler."""

    def handle(self, command: CreateDraftCommand) -> Post:
        """Handle CreateDraftCommand."""
        return create_draft_handler(
            command,
            _get_draft_repository(),
            _get_post_repository(),
            _get_github_service(),
        )


class SaveDraftHandler:
    """Handler wrapper for save_draft_handler."""

    def handle(self, command: SaveDraftCommand) -> None:
        """Handle SaveDraftCommand."""
        return save_draft_handler(
            command,
            _get_draft_repository(),
            _get_post_repository(),
            _get_github_service(),
        )


class PublishPostHandler:
    """Handler wrapper for publish_post_handler."""

    def handle(self, command: PublishPostCommand) -> Post:
        """Handle PublishPostCommand."""
        return publish_post_handler(
            command,
            _get_draft_repository(),
            _get_post_repository(),
            _get_markdown_service(),
            _get_sanitizer(),
            _get_github_service(),
        )


class UnpublishPostHandler:
    """Handler wrapper for unpublish_post_handler."""

    def handle(self, command: UnpublishPostCommand) -> Post:
        """Handle UnpublishPostCommand."""
        return unpublish_post_handler(
            command,
            _get_draft_repository(),
            _get_post_repository(),
            _get_github_service(),
        )


class DeleteDraftHandler:
    """Handler wrapper for delete_draft_handler."""

    def handle(self, command: DeleteDraftCommand) -> None:
        """Handle DeleteDraftCommand."""
        return delete_draft_handler(
            command,
            _get_draft_repository(),
            _get_post_repository(),
            _get_github_service(),
        )


class GetPostQueryHandler:
    """Handler for get post query."""

    def handle(self, slug: str) -> Post | None:
        """Handle get post query."""
        post_repo = _get_post_repository()
        return post_repo.find_by_slug(slug)


class ListPostsQueryHandler:
    """Handler wrapper for list_posts_query_handler."""

    def handle(self, query: ListPostsQuery) -> ListPostsResponse:
        """Handle ListPostsQuery."""
        return list_posts_query_handler(query, _get_post_repository())


def _get_create_draft_handler() -> CreateDraftHandler:
    """Get create_draft_handler wrapper."""
    return CreateDraftHandler()


def _get_save_draft_handler() -> SaveDraftHandler:
    """Get save_draft_handler wrapper."""
    return SaveDraftHandler()


def _get_publish_post_handler() -> PublishPostHandler:
    """Get publish_post_handler wrapper."""
    return PublishPostHandler()


def _get_unpublish_post_handler() -> UnpublishPostHandler:
    """Get unpublish_post_handler wrapper."""
    return UnpublishPostHandler()


def _get_delete_draft_handler() -> DeleteDraftHandler:
    """Get delete_draft_handler wrapper."""
    return DeleteDraftHandler()


def _get_get_post_query_handler() -> GetPostQueryHandler:
    """Get post query handler."""
    return GetPostQueryHandler()


def _get_list_posts_query_handler() -> ListPostsQueryHandler:
    """Get list_posts_query_handler wrapper."""
    return ListPostsQueryHandler()


@posts_bp.route("/posts", methods=["POST"])
@require_auth
@require_role("author")
def create_draft() -> tuple[Response, int]:
    """Create new draft post.

    Expects JSON body with slug and title. Creates draft in filesystem,
    commits to GitHub, and persists metadata to database.

    Returns:
        JSON response with created post and 201 status.

    Raises:
        400: Invalid slug, missing fields, or duplicate slug.
        401: Missing or invalid authentication.
        403: User lacks author role.
    """
    data = request.get_json()

    if not data:
        return jsonify({"error": "Request body must be JSON"}), 400

    slug = data.get("slug")
    title = data.get("title")

    if not slug:
        return jsonify({"error": "Missing required field: slug"}), 400

    if not title:
        return jsonify({"error": "Missing required field: title"}), 400

    try:
        slug_obj = Slug(slug)
        if str(slug_obj) != slug:
            error_msg = (
                "Invalid slug format. Slug must be lowercase "
                f"alphanumeric with hyphens only. Got: '{slug}', "
                f"expected: '{slug_obj}'"
            )
            return jsonify({"error": error_msg}), 400
    except ValueError as e:
        return jsonify({"error": str(e)}), 400

    try:
        command = CreateDraftCommand(
            slug=slug, title=title, author_id=g.current_user.id
        )
        handler = _get_create_draft_handler()
        post = handler.handle(command)
        return jsonify(post.to_dict()), 201
    except ValueError as e:
        error_msg = str(e).lower()
        if "not found" in error_msg:
            return jsonify({"error": str(e)}), 404
        if "another author" in error_msg or "cannot edit" in error_msg:
            return jsonify({"error": str(e)}), 403
        return jsonify({"error": str(e)}), 400
    except Exception as e:
        return jsonify({"error": f"Internal server error: {e}"}), 500


@posts_bp.route("/posts/<slug>", methods=["GET"])
@require_auth
def get_draft(slug: str) -> tuple[Response, int]:
    """Get draft by slug.

    Retrieves draft metadata from database. Authors can only access their
    own drafts unless they have admin role.

    Args:
        slug: Post slug identifier.

    Returns:
        JSON response with post data and 200 status.

    Raises:
        401: Missing or invalid authentication.
        403: User cannot access this post.
        404: Post not found.
    """
    try:
        handler = _get_get_post_query_handler()
        post = handler.handle(slug)

        if post is None:
            return jsonify({"error": "Post not found"}), 404

        if (
            post.author_id != g.current_user.id
            and g.current_user.role.value != "admin"
        ):
            return jsonify(
                {"error": "Cannot access another author's post"}
            ), 403

        return jsonify(post.to_dict()), 200
    except ValueError as e:
        error_msg = str(e).lower()
        if "not found" in error_msg:
            return jsonify({"error": str(e)}), 404
        return jsonify({"error": str(e)}), 400
    except Exception as e:
        return jsonify({"error": f"Internal server error: {e}"}), 500


@posts_bp.route("/posts/<slug>", methods=["PUT"])
@require_auth
def save_draft(slug: str) -> tuple[Response, int]:
    """Save draft content.

    Updates draft markdown content in filesystem and commits to GitHub.
    Authors can only edit their own drafts unless they have admin role.

    Args:
        slug: Post slug identifier.

    Returns:
        JSON response with updated post and 200 status.

    Raises:
        400: Missing content field.
        401: Missing or invalid authentication.
        403: User cannot edit this post.
        404: Post not found.
    """
    data = request.get_json(silent=True)

    if data is None:
        return jsonify({"error": "Request body must be JSON"}), 400

    content = data.get("content")

    if content is None:
        return jsonify({"error": "Missing required field: content"}), 400

    try:
        command = SaveDraftCommand(
            slug=slug,
            content=content,
            author_id=g.current_user.id,
            user_role=g.current_user.role.value,
        )
        handler = _get_save_draft_handler()
        handler.handle(command)

        return jsonify(
            {"message": "Draft saved successfully", "slug": slug}
        ), 200
    except ValueError as e:
        error_msg = str(e).lower()
        if "not found" in error_msg:
            return jsonify({"error": str(e)}), 404
        if "another author" in error_msg or "cannot edit" in error_msg:
            return jsonify({"error": str(e)}), 403
        return jsonify({"error": str(e)}), 400
    except Exception as e:
        return jsonify({"error": f"Internal server error: {e}"}), 500


@posts_bp.route("/posts/<slug>", methods=["DELETE"])
@require_auth
def delete_draft(slug: str) -> tuple[Response, int]:
    """Delete draft post.

    Deletes draft from filesystem, database, and GitHub. Cannot delete
    published posts. Authors can only delete their own drafts unless admin.

    Args:
        slug: Post slug identifier.

    Returns:
        Empty response with 204 status.

    Raises:
        400: Post is published (must unpublish first).
        401: Missing or invalid authentication.
        403: User cannot delete this post.
        404: Post not found.
    """
    try:
        command = DeleteDraftCommand(
            slug=slug,
            author_id=g.current_user.id,
            user_role=g.current_user.role.value,
        )
        handler = _get_delete_draft_handler()
        handler.handle(command)
        return Response("", status=204), 204
    except ValueError as e:
        error_msg = str(e).lower()
        if "not found" in error_msg:
            return jsonify({"error": str(e)}), 404
        if "published" in error_msg:
            return jsonify({"error": str(e)}), 400
        if "another author" in error_msg or "cannot delete" in error_msg:
            return jsonify({"error": str(e)}), 403
        return jsonify({"error": str(e)}), 400
    except RuntimeError as e:
        return jsonify({"error": str(e)}), 500
    except Exception as e:
        return jsonify({"error": f"Internal server error: {e}"}), 500


@posts_bp.route("/posts/<slug>/publish", methods=["POST"])
@require_auth
def publish_post(slug: str) -> tuple[Response, int]:
    """Publish draft post.

    Renders markdown to HTML, sanitizes it, and marks post as published.
    Updates database, filesystem, and GitHub.

    Args:
        slug: Post slug identifier.

    Returns:
        JSON response with published post and 200 status.

    Raises:
        400: Post already published.
        401: Missing or invalid authentication.
        403: User cannot publish this post.
        404: Post not found.
    """
    try:
        command = PublishPostCommand(
            slug=slug,
            author_id=g.current_user.id,
            user_role=g.current_user.role.value,
        )
        handler = _get_publish_post_handler()
        post = handler.handle(command)
        return jsonify(post.to_dict()), 200
    except ValueError as e:
        error_msg = str(e).lower()
        if "not found" in error_msg:
            return jsonify({"error": str(e)}), 404
        if "another author" in error_msg or "cannot publish" in error_msg:
            return jsonify({"error": str(e)}), 403
        if "already published" in error_msg:
            return jsonify({"error": str(e)}), 400
        return jsonify({"error": str(e)}), 400
    except Exception as e:
        return jsonify({"error": f"Internal server error: {e}"}), 500


@posts_bp.route("/posts/<slug>/unpublish", methods=["POST"])
@require_auth
def unpublish_post(slug: str) -> tuple[Response, int]:
    """Unpublish published post.

    Marks post as unpublished (hidden from public). Updates database,
    filesystem, and GitHub. Admins can unpublish any post.

    Args:
        slug: Post slug identifier.

    Returns:
        JSON response with unpublished post and 200 status.

    Raises:
        400: Post not published.
        401: Missing or invalid authentication.
        403: User cannot unpublish this post.
        404: Post not found.
    """
    try:
        command = UnpublishPostCommand(
            slug=slug,
            author_id=g.current_user.id,
            user_role=g.current_user.role.value,
        )
        handler = _get_unpublish_post_handler()
        post = handler.handle(command)
        return jsonify(post.to_dict()), 200
    except ValueError as e:
        error_msg = str(e).lower()
        if "not found" in error_msg:
            return jsonify({"error": str(e)}), 404
        if "another author" in error_msg or "cannot unpublish" in error_msg:
            return jsonify({"error": str(e)}), 403
        return jsonify({"error": str(e)}), 400
    except Exception as e:
        return jsonify({"error": f"Internal server error: {e}"}), 500


@posts_bp.route("/my-posts", methods=["GET"])
@require_auth
def list_my_posts() -> tuple[Response, int]:
    """List authenticated user's posts.

    Supports filtering by publication status and pagination via query params.

    Query parameters:
        filter: 'all', 'drafts', or 'published' (default: 'all').
        page: Page number, 1-indexed (default: 1).
        limit: Posts per page, 1-100 (default: 20).

    Returns:
        JSON response with posts list, pagination metadata, and 200 status.

    Raises:
        400: Invalid query parameters.
        401: Missing or invalid authentication.
    """
    try:
        filter_param = request.args.get("filter", "all")
        page = int(request.args.get("page", 1))
        limit = int(request.args.get("limit", 20))

        filter_map = {
            "all": PostFilter.ALL,
            "drafts": PostFilter.DRAFTS,
            "published": PostFilter.PUBLISHED,
        }

        post_filter = filter_map.get(filter_param)
        if post_filter is None:
            error_msg = (
                f"Invalid filter: {filter_param}. Use all/drafts/published"
            )
            return jsonify({"error": error_msg}), 400

        query = ListPostsQuery(
            author_id=g.current_user.id,
            filter=post_filter,
            page=page,
            limit=limit,
        )

        handler = _get_list_posts_query_handler()
        response = handler.handle(query)

        return (
            jsonify(
                {
                    "posts": [post.to_dict() for post in response.posts],
                    "total_count": response.total_count,
                    "total_pages": response.total_pages,
                    "page": response.current_page,
                    "limit": response.limit,
                }
            ),
            200,
        )
    except ValueError as e:
        return jsonify({"error": str(e)}), 400
    except Exception as e:
        return jsonify({"error": f"Internal server error: {e}"}), 500
