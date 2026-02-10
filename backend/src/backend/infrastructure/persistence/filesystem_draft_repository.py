"""Filesystem-based draft repository implementation.

This module provides the FileSystemDraftRepository for persisting blog post
drafts to the filesystem with YAML front matter. Part of the Content Management
bounded context infrastructure layer.
"""

from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path

import yaml

from backend.domain.value_objects.slug import Slug


@dataclass
class DraftFile:
    """Represents a draft file with YAML front matter and markdown content.

    This class encapsulates the serialization and deserialization of draft
    files to/from the filesystem format with YAML front matter.

    Attributes:
        slug: URL-safe identifier for the draft
        title: Post title
        author: Author identifier (clerk_user_id)
        content: Markdown content of the post
        published: Whether the post is published
        created_at: UTC timestamp when draft was created
        published_at: UTC timestamp when published (None if unpublished)
        tags: List of tags for categorization
    """

    slug: str
    title: str
    author: str
    content: str
    published: bool
    created_at: datetime
    published_at: datetime | None = None
    tags: list[str] = field(default_factory=list)

    def to_markdown(self) -> str:
        """Serialize draft to markdown with YAML front matter.

        Returns:
            str: Formatted markdown file content with YAML front matter

        Example:
            ---
            title: My Post
            author: user123
            created_at: '2026-01-19T12:00:00+00:00'
            published: false
            tags:
            - python
            ---

            Post content here.
        """
        front_matter = {
            "slug": self.slug,
            "title": self.title,
            "author": self.author,
            "created_at": self.created_at.isoformat(),
            "published": self.published,
            "tags": self.tags,
        }

        if self.published_at:
            front_matter["published_at"] = self.published_at.isoformat()

        yaml_str = yaml.dump(front_matter, default_flow_style=False)
        return f"---\n{yaml_str}---\n\n{self.content}"

    @classmethod
    def from_markdown(cls, content: str, slug: str) -> "DraftFile":
        """Parse markdown with YAML front matter into a DraftFile.

        Args:
            content: Raw markdown file content with YAML front matter
            slug: Slug identifier for the draft

        Returns:
            DraftFile: Parsed draft file instance

        Raises:
            ValueError: If front matter is missing or malformed
        """
        if not content.startswith("---"):
            raise ValueError("Invalid draft file: missing front matter")

        parts = content.split("---", 2)
        if len(parts) < 3:
            raise ValueError("Invalid draft file: missing front matter")

        front_matter_str = parts[1]
        markdown_content = parts[2].strip() if len(parts) > 2 else ""

        front_matter = yaml.safe_load(front_matter_str)

        created_at = front_matter.get("created_at")
        if isinstance(created_at, str):
            created_at = datetime.fromisoformat(created_at)

        published_at = front_matter.get("published_at")
        if isinstance(published_at, str):
            published_at = datetime.fromisoformat(published_at)

        return cls(
            slug=slug,
            title=front_matter.get("title", ""),
            author=front_matter.get("author", ""),
            content=markdown_content,
            published=front_matter.get("published", False),
            created_at=created_at,
            published_at=published_at,
            tags=front_matter.get("tags", []),
        )


class FileSystemDraftRepository:
    """Repository for managing draft files on the filesystem.

    This repository handles CRUD operations for blog post drafts stored as
    markdown files with YAML front matter. Files are stored at
    drafts/{slug}.md.

    Attributes:
        drafts_path: Path to the directory containing draft files
    """

    def __init__(self, drafts_path: Path) -> None:
        """Initialize the repository with a drafts directory.

        Args:
            drafts_path: Path to the drafts directory (created if missing)
        """
        self.drafts_path = Path(drafts_path)
        self.drafts_path.mkdir(exist_ok=True, parents=True)

    def save(self, draft: DraftFile) -> None:
        """Write draft to filesystem.

        Args:
            draft: DraftFile instance to save

        Raises:
            ValueError: If slug contains invalid characters
        """
        safe_slug = str(Slug(draft.slug))
        file_path = self.drafts_path / f"{safe_slug}.md"
        file_path.write_text(draft.to_markdown(), encoding="utf-8")

    def find_by_slug(self, slug: str) -> DraftFile | None:
        """Read draft from filesystem by slug.

        Args:
            slug: Slug identifier for the draft

        Returns:
            DraftFile if found, None otherwise

        Raises:
            ValueError: If slug contains invalid characters
        """
        safe_slug = str(Slug(slug))
        file_path = self.drafts_path / f"{safe_slug}.md"
        if not file_path.exists():
            return None

        content = file_path.read_text(encoding="utf-8")
        return DraftFile.from_markdown(content, slug=safe_slug)

    def delete(self, slug: str) -> None:
        """Delete draft file from filesystem.

        This operation is idempotent - succeeds even if file doesn't exist.

        Args:
            slug: Slug identifier for the draft to delete

        Raises:
            ValueError: If slug contains invalid characters
        """
        safe_slug = str(Slug(slug))
        file_path = self.drafts_path / f"{safe_slug}.md"
        if file_path.exists():
            file_path.unlink()

    def list_by_author(self, author: str) -> list[DraftFile]:
        """List all drafts by a specific author.

        Args:
            author: Author identifier to filter by

        Returns:
            List of DraftFile instances for the given author
        """
        drafts = []
        for md_file in self.drafts_path.glob("*.md"):
            content = md_file.read_text(encoding="utf-8")
            slug = md_file.stem
            draft = DraftFile.from_markdown(content, slug=slug)
            if draft.author == author:
                drafts.append(draft)
        return drafts
