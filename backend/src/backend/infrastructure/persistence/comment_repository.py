"""CommentRepository implementation for persistence layer.

This module provides the repository pattern implementation for Comment
aggregates, bridging between the domain layer and the database infrastructure
layer. Handles conversion between CommentModel (SQLModel table) and Comment
(domain aggregate).
"""

from datetime import UTC, datetime

from sqlalchemy import func
from sqlmodel import Session, col, select

from backend.domain.aggregates.comment import Comment
from backend.domain.value_objects.comment_text import CommentText
from backend.infrastructure.persistence.database import get_db
from backend.infrastructure.persistence.models import CommentModel


class CommentRepository:
    """Repository for Comment aggregate persistence operations.

    Implements the repository pattern to provide clean separation between
    domain logic and database infrastructure. Handles all CRUD operations
    and conversions between database models and domain aggregates.

    Attributes:
        session: Optional SQLModel Session for dependency injection.
                 If None, uses get_db() context manager.
    """

    def __init__(self, session: Session | None = None) -> None:
        """Initialize repository with optional session injection.

        Args:
            session: Optional SQLModel Session for testing or transactions.
                     If None, repository creates sessions via get_db().
        """
        self._session = session

    def save(self, comment: Comment) -> Comment:
        """Save or update comment in database.

        Handles both INSERT (when comment.id is None) and UPDATE (when
        comment.id exists). For updates, only mutable fields are written:
        text, updated_at, is_deleted, is_pending_moderation. Immutable
        fields (post_id, author_id, parent_id, created_at) are never
        overwritten.

        Args:
            comment: Comment aggregate to persist.

        Returns:
            Comment aggregate with database-assigned id on insert,
            or refreshed state on update.

        Raises:
            ValueError: If attempting to update a comment that does not
                exist in the database.
        """
        if self._session:
            return self._save_with_session(self._session, comment)

        for session in get_db():
            return self._save_with_session(session, comment)

        raise RuntimeError("Failed to obtain database session")

    def find_by_id(self, comment_id: int) -> Comment | None:
        """Find comment by primary key.

        Args:
            comment_id: Database primary key of the comment to look up.

        Returns:
            Comment aggregate if found, None otherwise.
        """
        if self._session:
            model = self._session.get(CommentModel, comment_id)
            return self._to_domain(model) if model else None

        for session in get_db():
            model = session.get(CommentModel, comment_id)
            return self._to_domain(model) if model else None

        return None

    def list_by_post(
        self, post_id: int, skip: int = 0, limit: int = 50
    ) -> list[Comment]:
        """List visible comments for a post (public view).

        Excludes soft-deleted comments (is_deleted=True) and comments
        pending moderation (is_pending_moderation=True). Results are
        ordered by created_at ASC (chronological order).

        Args:
            post_id: Primary key of the post whose comments to list.
            skip: Number of comments to skip for pagination (default: 0).
            limit: Maximum number of comments to return (default: 50).

        Returns:
            List of Comment aggregates, empty list if none found.
        """
        statement = (
            select(CommentModel)
            .where(
                CommentModel.post_id == post_id,
                CommentModel.is_deleted == False,  # noqa: E712
                CommentModel.is_pending_moderation == False,  # noqa: E712
            )
            .order_by(col(CommentModel.created_at).asc())
            .offset(skip)
            .limit(limit)
        )

        if self._session:
            models = self._session.exec(statement).all()
            return [self._to_domain(m) for m in models]

        for session in get_db():
            models = session.exec(statement).all()
            return [self._to_domain(m) for m in models]

        raise RuntimeError("Failed to obtain database session")

    def list_by_post_admin(
        self, post_id: int, skip: int = 0, limit: int = 50
    ) -> list[Comment]:
        """List all comments for a post including deleted and pending (admin).

        Returns every comment row for the given post regardless of deletion
        or moderation state. Ordered by created_at ASC.

        Args:
            post_id: Primary key of the post whose comments to list.
            skip: Number of comments to skip for pagination (default: 0).
            limit: Maximum number of comments to return (default: 50).

        Returns:
            List of Comment aggregates, empty list if none found.
        """
        statement = (
            select(CommentModel)
            .where(CommentModel.post_id == post_id)
            .order_by(col(CommentModel.created_at).asc())
            .offset(skip)
            .limit(limit)
        )

        if self._session:
            models = self._session.exec(statement).all()
            return [self._to_domain(m) for m in models]

        for session in get_db():
            models = session.exec(statement).all()
            return [self._to_domain(m) for m in models]

        raise RuntimeError("Failed to obtain database session")

    def find_by_author(
        self, author_id: int, limit: int = 10, offset: int = 0
    ) -> list[Comment]:
        """List all comments by a user ordered by created_at DESC.

        Returns every comment row for the given author regardless of
        deletion or moderation state, ordered newest first. Intended
        for the admin activity summary view.

        Args:
            author_id: Primary key of the comment author.
            limit: Maximum number of comments to return (default: 10).
            offset: Number of comments to skip (default: 0).

        Returns:
            List of Comment aggregates, empty list if none found.
        """
        statement = (
            select(CommentModel)
            .where(CommentModel.author_id == author_id)
            .order_by(col(CommentModel.created_at).desc())
            .limit(limit)
            .offset(offset)
        )

        if self._session:
            models = self._session.exec(statement).all()
            return [self._to_domain(m) for m in models]

        for session in get_db():
            models = session.exec(statement).all()
            return [self._to_domain(m) for m in models]

        raise RuntimeError("Failed to obtain database session")

    def count_by_author(self, author_id: int) -> int:
        """Count total comments posted by a user.

        Counts all rows for the given author regardless of deletion or
        moderation state, giving admins an accurate total activity count.

        Args:
            author_id: Primary key of the comment author.

        Returns:
            Total number of comments by the given author.
        """
        statement = (
            select(func.count())
            .select_from(CommentModel)
            .where(CommentModel.author_id == author_id)
        )

        if self._session:
            return self._session.exec(statement).one()

        for session in get_db():
            return session.exec(statement).one()

        raise RuntimeError("Failed to obtain database session")

    def list_all_admin(self, limit: int = 50, offset: int = 0) -> list[Comment]:
        """List all comments across all posts (admin view).

        Returns every comment row regardless of deletion or moderation state,
        ordered by created_at DESC (newest first).

        Args:
            limit: Maximum number of comments to return (default: 50).
            offset: Number of comments to skip for pagination (default: 0).

        Returns:
            List of Comment aggregates, empty list if none found.
        """
        statement = (
            select(CommentModel)
            .order_by(col(CommentModel.created_at).desc())
            .offset(offset)
            .limit(limit)
        )

        if self._session:
            models = self._session.exec(statement).all()
            return [self._to_domain(m) for m in models]

        for session in get_db():
            models = session.exec(statement).all()
            return [self._to_domain(m) for m in models]

        raise RuntimeError("Failed to obtain database session")

    def count_all_admin(self) -> int:
        """Count all comments across all posts.

        Returns:
            Total number of comment rows regardless of state.
        """
        statement = select(func.count()).select_from(CommentModel)

        if self._session:
            return self._session.exec(statement).one()

        for session in get_db():
            return session.exec(statement).one()

        raise RuntimeError("Failed to obtain database session")

    def hard_delete(self, comment_id: int) -> bool:
        """Remove comment row from database permanently (author self-delete).

        Args:
            comment_id: Primary key of the comment to remove.

        Returns:
            True if the row was found and deleted, False if not found.
        """
        if self._session:
            return self._hard_delete_with_session(self._session, comment_id)

        for session in get_db():
            return self._hard_delete_with_session(session, comment_id)

        raise RuntimeError("Failed to obtain database session")

    def soft_delete(self, comment_id: int) -> bool:
        """Set is_deleted=True on a comment, preserving text (admin delete).

        Args:
            comment_id: Primary key of the comment to soft-delete.

        Returns:
            True if the comment was found and flagged, False if not found.
        """
        if self._session:
            return self._soft_delete_with_session(self._session, comment_id)

        for session in get_db():
            return self._soft_delete_with_session(session, comment_id)

        raise RuntimeError("Failed to obtain database session")

    def _save_with_session(self, session: Session, comment: Comment) -> Comment:
        """Internal save method with session handling.

        Args:
            session: SQLModel Session to use.
            comment: Comment aggregate to persist.

        Returns:
            Comment aggregate with updated database state.

        Raises:
            ValueError: If attempting to update a non-existent comment.
        """
        if comment.id is None:
            model = self._to_model(comment)
            session.add(model)
            session.commit()
            session.refresh(model)
            return self._to_domain(model)

        existing = session.get(CommentModel, comment.id)
        if not existing:
            raise ValueError(f"Comment with id {comment.id} not found")

        existing.text = str(comment.text)
        existing.updated_at = comment.updated_at
        existing.is_deleted = comment.is_deleted
        existing.is_pending_moderation = comment.is_pending_moderation

        session.commit()
        session.refresh(existing)
        return self._to_domain(existing)

    def _hard_delete_with_session(
        self, session: Session, comment_id: int
    ) -> bool:
        """Internal hard-delete method with session handling.

        Args:
            session: SQLModel Session to use.
            comment_id: Primary key of the comment to remove.

        Returns:
            True if deleted, False if not found.
        """
        model = session.get(CommentModel, comment_id)
        if not model:
            return False

        session.delete(model)
        session.commit()
        return True

    def _soft_delete_with_session(
        self, session: Session, comment_id: int
    ) -> bool:
        """Internal soft-delete method with session handling.

        Args:
            session: SQLModel Session to use.
            comment_id: Primary key of the comment to flag as deleted.

        Returns:
            True if flagged, False if not found.
        """
        model = session.get(CommentModel, comment_id)
        if not model:
            return False

        model.is_deleted = True
        model.updated_at = datetime.now(UTC)
        session.commit()
        return True

    def _to_domain(self, model: CommentModel) -> Comment:
        """Convert CommentModel to Comment domain aggregate.

        Ensures all datetimes are timezone-aware by attaching UTC when the
        driver returns naive datetimes (e.g. MySQL, some SQLite configs).

        Args:
            model: CommentModel database table instance.

        Returns:
            Comment aggregate with all fields populated and UTC datetimes.
        """
        created_at = model.created_at
        if created_at.tzinfo is None:
            created_at = created_at.replace(tzinfo=UTC)

        updated_at = model.updated_at
        if updated_at.tzinfo is None:
            updated_at = updated_at.replace(tzinfo=UTC)

        return Comment(
            id=model.id,
            post_id=model.post_id,
            author_id=model.author_id,
            _text=CommentText(model.text),
            parent_id=model.parent_id,
            created_at=created_at,
            updated_at=updated_at,
            is_deleted=model.is_deleted,
            is_pending_moderation=model.is_pending_moderation,
        )

    def _to_model(self, comment: Comment) -> CommentModel:
        """Convert Comment domain aggregate to CommentModel.

        Args:
            comment: Comment domain aggregate to convert.

        Returns:
            CommentModel instance ready for persistence.
        """
        return CommentModel(
            id=comment.id,
            post_id=comment.post_id,
            author_id=comment.author_id,
            parent_id=comment.parent_id,
            text=str(comment.text),
            created_at=comment.created_at,
            updated_at=comment.updated_at,
            is_deleted=comment.is_deleted,
            is_pending_moderation=comment.is_pending_moderation,
        )
