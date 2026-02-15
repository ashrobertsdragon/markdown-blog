"""PostRevision aggregate representing point-in-time snapshot."""

from dataclasses import dataclass
from datetime import UTC, datetime
from uuid import UUID, uuid4

from backend.domain.value_objects.commit_sha import CommitSHA


@dataclass(frozen=True)
class PostRevision:
    """PostRevision aggregate representing point-in-time snapshot.

    Immutable snapshot of a post at a specific commit.

    Attributes:
        id: UUID primary key
        post_id: int foreign key to Post
        commit_sha: CommitSHA value object
        author_id: int foreign key to User
        commit_message: str (human-readable commit message)
        markdown_content: str (full markdown for diffs)
        created_at: datetime (UTC, when this revision was created)
        updated_at: datetime (UTC, when record was created/modified)
        is_revert: bool (True if this revision is a revert commit)
    """

    id: UUID
    post_id: int
    commit_sha: CommitSHA
    author_id: int
    commit_message: str
    markdown_content: str
    created_at: datetime
    updated_at: datetime
    is_revert: bool = False

    @classmethod
    def create(
        cls,
        post_id: int,
        commit_sha: str,
        author_id: int,
        commit_message: str,
        markdown_content: str,
        is_revert: bool = False,
    ) -> "PostRevision":
        """Factory method to create new PostRevision.

        Args:
            post_id: int foreign key to Post
            commit_sha: Raw SHA string to validate
            author_id: int foreign key to User
            commit_message: Human-readable commit message
            markdown_content: Full markdown content
            is_revert: Whether this revision is a revert commit

        Returns:
            New PostRevision instance

        Raises:
            ValueError: If post_id or author_id is None or not positive, or
                commit_message is empty
            TypeError: If post_id or author_id is not int, or
                commit_message/markdown_content is not string
        """
        if post_id is None:
            raise ValueError("post_id cannot be None")
        if not isinstance(post_id, int):
            raise TypeError("post_id must be an int")
        if post_id <= 0:
            raise ValueError("post_id must be positive")

        if author_id is None:
            raise ValueError("author_id cannot be None")
        if not isinstance(author_id, int):
            raise TypeError("author_id must be an int")
        if author_id <= 0:
            raise ValueError("author_id must be positive")

        if commit_message is None:
            raise TypeError("commit_message must be a string")
        if not isinstance(commit_message, str):
            raise TypeError("commit_message must be a string")
        if commit_message == "":
            raise ValueError("commit_message cannot be empty")

        if markdown_content is None:
            raise TypeError("markdown_content must be a string")
        if not isinstance(markdown_content, str):
            raise TypeError("markdown_content must be a string")

        commit_sha_obj = CommitSHA(commit_sha)

        now = datetime.now(UTC)

        return cls(
            id=uuid4(),
            post_id=post_id,
            commit_sha=commit_sha_obj,
            author_id=author_id,
            commit_message=commit_message,
            markdown_content=markdown_content,
            created_at=now,
            updated_at=now,
            is_revert=is_revert,
        )

    def get_markdown_content(self) -> str:
        """Get full markdown content for this revision.

        Returns:
            Full markdown content string
        """
        return self.markdown_content

    def get_commit_message(self) -> str:
        """Get human-readable commit message.

        Returns:
            Commit message string
        """
        return self.commit_message
