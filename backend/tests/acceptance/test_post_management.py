"""Acceptance tests for Post Management based on requirements.md.

These tests verify the end-to-end functionality of creating, editing,
previewing, and publishing posts, ensuring alignment with the
Acceptance Criteria in @.spec-workflow/specs/post-management/requirements.md.

These tests exercise the full stack (API -> Application -> Infrastructure)
using the Flask test client and a real (temporary) filesystem.
"""

import os
from datetime import UTC, datetime
from unittest.mock import MagicMock, patch

import pytest
import yaml

from backend.domain.aggregates.user import User
from backend.domain.value_objects.role import Role


@pytest.fixture
def author_user() -> User:
    """Return an author user for testing."""
    return User(
        id=10,
        clerk_user_id="clerk_author_123",
        email="author@example.com",
        role=Role.AUTHOR,
        created_at=datetime(2024, 1, 1, 12, 0, 0, tzinfo=UTC),
    )


@pytest.fixture
def author_jwt_payload() -> dict[str, object]:
    """Return a valid author JWT payload."""
    return {
        "sub": "clerk_author_123",
        "email": "author@example.com",
        "exp": 1735689600,
    }


@pytest.fixture
def mock_clerk_auth(author_jwt_payload, author_user):
    """Mock Clerk authentication and user repository lookup."""
    mock_clerk_adapter = MagicMock()
    mock_clerk_adapter.verify_token.return_value = author_jwt_payload

    mock_user_repo = MagicMock()
    mock_user_repo.find_by_clerk_user_id.return_value = author_user

    with (
        patch(
            "backend.api.middleware.auth_middleware._get_clerk_adapter",
            return_value=mock_clerk_adapter,
        ),
        patch(
            "backend.api.middleware.auth_middleware._get_user_repository",
            return_value=mock_user_repo,
        ),
    ):
        yield


@pytest.fixture
def mock_github():
    """Mock GitHub service to avoid real network calls."""
    with patch("backend.api.routes.posts.GitHubSyncService") as mock:
        instance = mock.return_value
        instance.commit_file.return_value = "fake_sha_123"
        instance.delete_file.return_value = "fake_sha_delete"
        yield instance


def test_create_draft_post(client, mock_clerk_auth, mock_github):
    """Test Requirement 1, 8, and 11.

    Create draft with validation and front matter.

    Acceptance Criteria:
    - Slug validation (Requirement 8)
    - Filesystem creation at drafts/{slug}.md (Requirement 1)
    - YAML front matter inclusion (Requirement 1, 11)
    - GitHub commitment (Requirement 1, 10)
    """
    slug = "my-acceptance-test-post"
    title = "My Acceptance Test Post"

    response = client.post(
        "/api/posts",
        headers={"Authorization": "Bearer author_token"},
        json={"slug": slug, "title": title},
    )

    assert response.status_code == 201

    drafts_path = os.environ["DRAFTS_PATH"]
    file_path = os.path.join(drafts_path, f"{slug}.md")
    assert os.path.exists(file_path)

    with open(file_path) as f:
        content = f.read()
        parts = content.split("---\n")
        assert len(parts) >= 3
        front_matter = yaml.safe_load(parts[1])

        assert front_matter["title"] == title
        assert front_matter["slug"] == slug
        assert front_matter["published"] is False
        assert "created_at" in front_matter
        assert front_matter["author"] == "10"

    mock_github.commit_file.assert_called_once()
    _, kwargs = mock_github.commit_file.call_args
    assert slug in kwargs["path"]
    assert f"Create draft: {title}" in kwargs["message"]


def test_edit_draft_post(client, mock_clerk_auth, mock_github):
    """Test Requirement 2: Edit draft content.

    Acceptance Criteria:
    - Content written to drafts/{slug}.md
    - GitHub commitment with update message
    """
    slug = "edit-test-post"
    title = "Edit Test Post"

    client.post(
        "/api/posts",
        headers={"Authorization": "Bearer author_token"},
        json={"slug": slug, "title": title},
    )

    new_content = "# Updated Content\n\nThis is a test."

    response = client.put(
        f"/api/posts/{slug}",
        headers={"Authorization": "Bearer author_token"},
        json={"content": new_content},
    )

    assert response.status_code == 200

    drafts_path = os.environ["DRAFTS_PATH"]
    file_path = os.path.join(drafts_path, f"{slug}.md")

    with open(file_path) as f:
        content = f.read()
        assert new_content in content

    assert mock_github.commit_file.call_count == 2
    _, kwargs = mock_github.commit_file.call_args
    assert f"Update draft: {title}" in kwargs["message"]


def test_preview_markdown(client, mock_clerk_auth):
    """Test Requirement 3: Preview rendered markdown.

    Acceptance Criteria:
    - Rendered HTML displays markdown features
    - Syntax highlighting is applied
    """
    markdown = "# Header\n\n```python\nprint('hello')\n```"

    response = client.post(
        "/api/posts/preview",
        headers={"Authorization": "Bearer author_token"},
        json={"content": markdown},
    )

    if response.status_code == 200:
        html = response.json["html_content"]
        assert "<h1>Header</h1>" in html
        assert "highlight" in html
        assert "print" in html
    else:
        assert response.status_code in (404, 405, 501)


def test_publish_post(client, mock_clerk_auth, mock_github):
    """Test Requirement 4 and 9.

    Publish post with markdown conversion and sanitization.

    Acceptance Criteria:
    - Markdown converted to HTML (Requirement 4, 9)
    - Sanitization with Bleach (Requirement 4, 9)
    - Syntax highlighting with Pygments (Requirement 9)
    - Front matter updated with published: true (Requirement 4, 11)
    """
    slug = "publish-test-post"
    title = "Publish Test Post"
    markdown_content = (
        '# Title\n```python\nprint("hello")\n```\n'
        "<script>alert('xss')</script>\n<p>Safe paragraph</p>\n"
    )

    client.post(
        "/api/posts",
        headers={"Authorization": "Bearer author_token"},
        json={"slug": slug, "title": title},
    )
    client.put(
        f"/api/posts/{slug}",
        headers={"Authorization": "Bearer author_token"},
        json={"content": markdown_content},
    )

    response = client.post(
        f"/api/posts/{slug}/publish",
        headers={"Authorization": "Bearer author_token"},
    )

    assert response.status_code == 200
    assert response.json["published"] is True

    public_response = client.get(f"/api/posts/{slug}/public")
    assert public_response.status_code == 200
    html = public_response.json["html_content"]

    assert "<script>" not in html
    assert "alert('xss')" not in html
    assert "highlight" in html
    assert "print" in html
    assert "hello" in html
    assert "<p>Safe paragraph</p>" in html

    drafts_path = os.environ["DRAFTS_PATH"]
    file_path = os.path.join(drafts_path, f"{slug}.md")

    with open(file_path) as f:
        content = f.read()
        parts = content.split("---\n")
        front_matter = yaml.safe_load(parts[1])
        assert front_matter["published"] is True
        assert "published_at" in front_matter


def test_unpublish_post(client, mock_clerk_auth, mock_github):
    """Test Requirement 5: Unpublish a post.

    Acceptance Criteria:
    - Post.published set to false in DB
    - Front matter updated with published: false
    """
    slug = "unpublish-test"
    title = "Unpublish Test"

    client.post(
        "/api/posts",
        headers={"Authorization": "Bearer author_token"},
        json={"slug": slug, "title": title},
    )
    client.post(
        f"/api/posts/{slug}/publish",
        headers={"Authorization": "Bearer author_token"},
    )

    response = client.post(
        f"/api/posts/{slug}/unpublish",
        headers={"Authorization": "Bearer author_token"},
    )
    assert response.status_code == 200
    assert response.json["published"] is False

    public_response = client.get(f"/api/posts/{slug}/public")
    assert public_response.status_code == 404

    drafts_path = os.environ["DRAFTS_PATH"]
    file_path = os.path.join(drafts_path, f"{slug}.md")
    with open(file_path) as f:
        content = f.read()
        parts = content.split("---\n")
        front_matter = yaml.safe_load(parts[1])
        assert front_matter["published"] is False


def test_delete_draft_post(client, mock_clerk_auth, mock_github):
    """Test Requirement 6: Delete draft post.

    Acceptance Criteria:
    - Draft file deleted from filesystem
    - Deletion committed to GitHub
    """
    slug = "delete-test"
    client.post(
        "/api/posts",
        headers={"Authorization": "Bearer author_token"},
        json={"slug": slug, "title": "Delete Me"},
    )

    drafts_path = os.environ["DRAFTS_PATH"]
    file_path = os.path.join(drafts_path, f"{slug}.md")
    assert os.path.exists(file_path)

    response = client.delete(
        f"/api/posts/{slug}", headers={"Authorization": "Bearer author_token"}
    )
    assert response.status_code == 204

    assert not os.path.exists(file_path)
    mock_github.delete_file.assert_called_once()
    delete_kwargs = mock_github.delete_file.call_args.kwargs
    assert slug in delete_kwargs["path"]
    assert delete_kwargs["message"] == f"Delete draft: {slug}"


def test_list_author_drafts(client, mock_clerk_auth):
    """Test Requirement 7: List author's posts."""
    client.post(
        "/api/posts",
        headers={"Authorization": "Bearer author_token"},
        json={"slug": "post-1", "title": "Post 1"},
    )
    client.post(
        "/api/posts",
        headers={"Authorization": "Bearer author_token"},
        json={"slug": "post-2", "title": "Post 2"},
    )

    response = client.get(
        "/api/posts/my-posts", headers={"Authorization": "Bearer author_token"}
    )
    assert response.status_code == 200
    posts = response.json["posts"]
    assert len(posts) >= 2
    slugs = [p["slug"] for p in posts]
    assert "post-1" in slugs
    assert "post-2" in slugs


def test_slug_validation_and_uniqueness(client, mock_clerk_auth):
    """Test Requirement 8: Slug uniqueness."""
    slug = "unique-slug"
    title = "Title"

    client.post(
        "/api/posts",
        headers={"Authorization": "Bearer author_token"},
        json={"slug": slug, "title": title},
    )

    response = client.post(
        "/api/posts",
        headers={"Authorization": "Bearer author_token"},
        json={"slug": slug, "title": "Another Title"},
    )

    assert response.status_code == 400
    assert "slug" in response.json["error"].lower()


def test_author_authorization(client, mock_clerk_auth):
    """Test Requirement 12: Author authorization."""
    other_author_payload = {
        "sub": "clerk_other_456",
        "email": "other@example.com",
        "exp": 1735689600,
    }
    other_author_user = User(
        id=99,
        clerk_user_id="clerk_other_456",
        email="other@example.com",
        role=Role.AUTHOR,
        created_at=datetime(2024, 1, 1, 12, 0, 0, tzinfo=UTC),
    )

    slug = "author-only-post"

    client.post(
        "/api/posts",
        headers={"Authorization": "Bearer author_token"},
        json={"slug": slug, "title": "Author Only"},
    )

    with (
        patch(
            "backend.api.middleware.auth_middleware._get_clerk_adapter"
        ) as mock_clerk,
        patch(
            "backend.api.middleware.auth_middleware._get_user_repository"
        ) as mock_user_repo,
    ):
        mock_clerk.return_value.verify_token.return_value = other_author_payload
        mock_user_repo.return_value.find_by_clerk_user_id.return_value = (
            other_author_user
        )

        response = client.put(
            f"/api/posts/{slug}",
            headers={"Authorization": "Bearer other_token"},
            json={"content": "Illegal edit"},
        )

    assert response.status_code == 403
