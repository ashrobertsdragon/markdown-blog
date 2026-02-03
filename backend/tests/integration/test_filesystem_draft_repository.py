"""Integration tests for FileSystemDraftRepository with real filesystem.

This module defines comprehensive integration tests for the
FileSystemDraftRepository following TDD Red phase principles. These tests use
temporary directories to test real filesystem interactions.

Test Coverage:
- CRUD operations: save, find_by_slug, delete, list_by_author
- Edge cases: path safety, UTF-8 encoding, special characters
- Error conditions: missing files, malformed YAML
- Idempotency: delete on non-existent files

Total: 13 integration tests
"""

from datetime import UTC, datetime
from pathlib import Path

from backend.infrastructure.persistence.filesystem_draft_repository import (
    DraftFile,
    FileSystemDraftRepository,
)


def test_repository_saves_draft_to_filesystem(tmp_path: Path) -> None:
    """Verify save() creates file at drafts/{slug}.md."""
    repo = FileSystemDraftRepository(tmp_path)

    draft = DraftFile(
        slug="my-first-post",
        title="My First Post",
        author="alice",
        content="This is my first blog post.",
        published=False,
        created_at=datetime(2026, 1, 19, 12, 0, 0, tzinfo=UTC),
        tags=["intro"],
    )

    repo.save(draft)

    file_path = tmp_path / "my-first-post.md"
    assert file_path.exists()
    assert file_path.is_file()

    content = file_path.read_text(encoding="utf-8")
    assert "title: My First Post" in content
    assert "author: alice" in content
    assert "This is my first blog post." in content


def test_repository_find_by_slug_reads_file(tmp_path: Path) -> None:
    """Verify find_by_slug() reads and parses file correctly."""
    repo = FileSystemDraftRepository(tmp_path)

    original = DraftFile(
        slug="test-find",
        title="Test Find",
        author="bob",
        content="Content to find.",
        published=False,
        created_at=datetime(2026, 1, 19, 12, 0, 0, tzinfo=UTC),
    )

    repo.save(original)

    retrieved = repo.find_by_slug("test-find")

    assert retrieved is not None
    assert retrieved.slug == "test-find"
    assert retrieved.title == "Test Find"
    assert retrieved.author == "bob"
    assert retrieved.content == "Content to find."
    assert retrieved.published is False


def test_repository_find_by_slug_returns_none_if_not_found(
    tmp_path: Path,
) -> None:
    """Verify find_by_slug() returns None for missing file."""
    repo = FileSystemDraftRepository(tmp_path)

    result = repo.find_by_slug("non-existent-post")

    assert result is None


def test_repository_delete_removes_file(tmp_path: Path) -> None:
    """Verify delete() removes file from filesystem."""
    repo = FileSystemDraftRepository(tmp_path)

    draft = DraftFile(
        slug="to-delete",
        title="Delete Me",
        author="charlie",
        content="This will be deleted.",
        published=False,
        created_at=datetime(2026, 1, 19, 12, 0, 0, tzinfo=UTC),
    )

    repo.save(draft)
    file_path = tmp_path / "to-delete.md"
    assert file_path.exists()

    repo.delete("to-delete")

    assert not file_path.exists()


def test_repository_delete_idempotent(tmp_path: Path) -> None:
    """Verify delete() succeeds even if file doesn't exist."""
    repo = FileSystemDraftRepository(tmp_path)

    repo.delete("never-existed")


def test_repository_list_by_author_filters_correctly(tmp_path: Path) -> None:
    """Verify list_by_author() returns only matching author's drafts."""
    repo = FileSystemDraftRepository(tmp_path)

    draft1 = DraftFile(
        slug="alice-post-1",
        title="Alice Post 1",
        author="alice",
        content="Content 1",
        published=False,
        created_at=datetime(2026, 1, 19, 12, 0, 0, tzinfo=UTC),
    )

    draft2 = DraftFile(
        slug="bob-post-1",
        title="Bob Post 1",
        author="bob",
        content="Content 2",
        published=False,
        created_at=datetime(2026, 1, 19, 13, 0, 0, tzinfo=UTC),
    )

    draft3 = DraftFile(
        slug="alice-post-2",
        title="Alice Post 2",
        author="alice",
        content="Content 3",
        published=False,
        created_at=datetime(2026, 1, 19, 14, 0, 0, tzinfo=UTC),
    )

    repo.save(draft1)
    repo.save(draft2)
    repo.save(draft3)

    alice_drafts = repo.list_by_author("alice")

    assert len(alice_drafts) == 2
    slugs = {draft.slug for draft in alice_drafts}
    assert slugs == {"alice-post-1", "alice-post-2"}


def test_repository_creates_drafts_directory_on_init(tmp_path: Path) -> None:
    """Verify __init__() creates directory if missing."""
    drafts_path = tmp_path / "new_drafts"
    assert not drafts_path.exists()

    FileSystemDraftRepository(drafts_path)

    assert drafts_path.exists()
    assert drafts_path.is_dir()


def test_repository_saves_file_with_utf8_encoding(tmp_path: Path) -> None:
    """Verify files written with UTF-8 encoding."""
    repo = FileSystemDraftRepository(tmp_path)

    draft = DraftFile(
        slug="unicode-test",
        title="Unicode Test 中文 한글 日本語",
        author="dave",
        content="Content with emoji: 🚀 ✨ 💻",
        published=False,
        created_at=datetime(2026, 1, 19, 12, 0, 0, tzinfo=UTC),
    )

    repo.save(draft)

    retrieved = repo.find_by_slug("unicode-test")

    assert retrieved is not None
    assert retrieved.title == "Unicode Test 中文 한글 日本語"
    assert retrieved.content == "Content with emoji: 🚀 ✨ 💻"


def test_repository_prevents_path_traversal(tmp_path: Path) -> None:
    """Verify slug='../escape-attempt' is normalized and saved safely."""
    repo = FileSystemDraftRepository(tmp_path)

    draft = DraftFile(
        slug="../escape-attempt",
        title="Escape",
        author="hacker",
        content="Malicious content",
        published=False,
        created_at=datetime(2026, 1, 19, 12, 0, 0, tzinfo=UTC),
    )

    repo.save(draft)

    parent_path = tmp_path.parent / "escape-attempt.md"
    assert not parent_path.exists()

    safe_path = tmp_path / "escape-attempt.md"
    assert safe_path.exists()

    assert safe_path.resolve().is_relative_to(tmp_path.resolve())


def test_repository_update_overwrites_existing_file(tmp_path: Path) -> None:
    """Verify save() on existing slug overwrites the file."""
    repo = FileSystemDraftRepository(tmp_path)

    original = DraftFile(
        slug="update-test",
        title="Original Title",
        author="eve",
        content="Original content",
        published=False,
        created_at=datetime(2026, 1, 19, 12, 0, 0, tzinfo=UTC),
    )

    repo.save(original)

    updated = DraftFile(
        slug="update-test",
        title="Updated Title",
        author="eve",
        content="Updated content",
        published=True,
        created_at=datetime(2026, 1, 19, 12, 0, 0, tzinfo=UTC),
        published_at=datetime(2026, 1, 19, 14, 0, 0, tzinfo=UTC),
    )

    repo.save(updated)

    retrieved = repo.find_by_slug("update-test")

    assert retrieved is not None
    assert retrieved.title == "Updated Title"
    assert retrieved.content == "Updated content"
    assert retrieved.published is True


def test_repository_list_by_author_empty_when_no_matches(
    tmp_path: Path,
) -> None:
    """Verify list_by_author() returns empty list when no matches."""
    repo = FileSystemDraftRepository(tmp_path)

    draft = DraftFile(
        slug="alice-post",
        title="Alice Post",
        author="alice",
        content="Content",
        published=False,
        created_at=datetime(2026, 1, 19, 12, 0, 0, tzinfo=UTC),
    )

    repo.save(draft)

    bob_drafts = repo.list_by_author("bob")

    assert bob_drafts == []


def test_repository_handles_special_chars_in_content(tmp_path: Path) -> None:
    """Verify special characters in markdown content are preserved."""
    repo = FileSystemDraftRepository(tmp_path)

    draft = DraftFile(
        slug="special-content",
        title="Special Content",
        author="frank",
        content='Code: `print("hello")` and **bold** text.\n\n---\n\nMore.',
        published=False,
        created_at=datetime(2026, 1, 19, 12, 0, 0, tzinfo=UTC),
    )

    repo.save(draft)

    retrieved = repo.find_by_slug("special-content")

    assert retrieved is not None
    assert retrieved.content == draft.content


def test_repository_roundtrip_preserves_all_fields(tmp_path: Path) -> None:
    """Verify save→find_by_slug roundtrip preserves all data."""
    repo = FileSystemDraftRepository(tmp_path)

    original = DraftFile(
        slug="roundtrip-test",
        title="Round Trip Test",
        author="grace",
        content="Full content\nwith\nmultiple\nlines",
        published=True,
        created_at=datetime(2026, 1, 19, 10, 0, 0, tzinfo=UTC),
        published_at=datetime(2026, 1, 19, 12, 0, 0, tzinfo=UTC),
        tags=["test", "roundtrip"],
    )

    repo.save(original)
    retrieved = repo.find_by_slug("roundtrip-test")

    assert retrieved is not None
    assert retrieved.slug == original.slug
    assert retrieved.title == original.title
    assert retrieved.author == original.author
    assert retrieved.content == original.content
    assert retrieved.published == original.published
    assert retrieved.created_at == original.created_at
    assert retrieved.published_at == original.published_at
    assert retrieved.tags == original.tags
