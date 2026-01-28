"""PostRepository implementation for persistence layer.

This module provides the repository pattern implementation for Post aggregates,
bridging between the domain layer and the database infrastructure layer.
Handles conversion between SQLModel Post table and domain Post aggregate.
"""

from datetime import UTC

from sqlalchemy.exc import IntegrityError
from sqlmodel import Session, col, select

from backend.domain.aggregates.post import Post as DomainPost
from backend.domain.value_objects.html_content import HtmlContent
from backend.domain.value_objects.slug import Slug
from backend.infrastructure.persistence.database import get_db
from backend.infrastructure.persistence.models import Post as PostModel


class PostRepository:
    """Repository for Post aggregate persistence operations.

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

    def save(self, post: DomainPost) -> DomainPost:
        """Save or update post in database.

        Handles both INSERT (when post.id is None) and UPDATE (when
        post.id exists). For inserts, assigns database-generated ID to
        returned aggregate. For updates, preserves created_at timestamp
        for audit trail integrity.

        Args:
            post: DomainPost aggregate to persist

        Returns:
            DomainPost aggregate with updated ID and database state

        Raises:
            ValueError: If attempting to update non-existent post or
                slug conflict
            IntegrityError: If duplicate slug constraint violated
        """
        if self._session:
            return self._save_with_session(self._session, post)

        for session in get_db():
            return self._save_with_session(session, post)

        raise RuntimeError("Failed to obtain database session")

    def find_by_slug(self, slug: str) -> DomainPost | None:
        """Find post by slug.

        Uses indexed query on slug column for fast lookup.
        Converts database model to domain aggregate if found.

        Args:
            slug: URL-safe post identifier

        Returns:
            DomainPost aggregate if found, None otherwise
        """
        statement = select(PostModel).where(PostModel.slug == slug)

        if self._session:
            post_model = self._session.exec(statement).first()
            if post_model:
                return self._to_domain(post_model)
            return None

        for session in get_db():
            post_model = session.exec(statement).first()
            if post_model:
                return self._to_domain(post_model)
            return None

        return None

    def find_by_author(
        self, author_id: int, limit: int = 50, offset: int = 0
    ) -> list[DomainPost]:
        """List posts by author with pagination.

        Returns posts ordered by created_at DESC (newest first).
        Applies LIMIT and OFFSET for pagination support.

        Args:
            author_id: User ID of post author
            limit: Maximum number of posts to return (default: 50)
            offset: Number of posts to skip (default: 0)

        Returns:
            List of DomainPost aggregates, empty list if no posts found
        """
        statement = (
            select(PostModel)
            .where(PostModel.author_id == author_id)
            .order_by(col(PostModel.created_at).desc())
            .limit(limit)
            .offset(offset)
        )

        if self._session:
            post_models = self._session.exec(statement).all()
            return [self._to_domain(model) for model in post_models]

        for session in get_db():
            post_models = session.exec(statement).all()
            return [self._to_domain(model) for model in post_models]

        raise RuntimeError("Failed to obtain database session")

    def list_published(
        self, limit: int = 50, offset: int = 0
    ) -> list[DomainPost]:
        """List published posts with pagination.

        Returns posts where published=True ordered by created_at DESC.
        Applies LIMIT and OFFSET for pagination support.

        Args:
            limit: Maximum number of posts to return (default: 50)
            offset: Number of posts to skip (default: 0)

        Returns:
            List of DomainPost aggregates, empty list if no posts found
        """
        statement = (
            select(PostModel)
            .where(PostModel.published)
            .order_by(col(PostModel.created_at).desc())
            .limit(limit)
            .offset(offset)
        )

        if self._session:
            post_models = self._session.exec(statement).all()
            return [self._to_domain(model) for model in post_models]

        for session in get_db():
            post_models = session.exec(statement).all()
            return [self._to_domain(model) for model in post_models]

        raise RuntimeError("Failed to obtain database session")

    def find_by_id(self, post_id: int) -> DomainPost | None:
        """Find post by primary key ID.

        Uses efficient primary key lookup via session.get().
        Converts database model to domain aggregate if found.

        Args:
            post_id: Database primary key

        Returns:
            DomainPost aggregate if found, None otherwise
        """
        if self._session:
            post_model = self._session.get(PostModel, post_id)
            if post_model:
                return self._to_domain(post_model)
            return None

        for session in get_db():
            post_model = session.get(PostModel, post_id)
            if post_model:
                return self._to_domain(post_model)
            return None

        return None

    def delete(self, post_id: int) -> bool:
        """Remove post from database.

        Args:
            post_id: Database primary key of post to delete

        Returns:
            True if post was deleted, False if post not found
        """
        if self._session:
            return self._delete_with_session(self._session, post_id)

        for session in get_db():
            return self._delete_with_session(session, post_id)

        raise RuntimeError("Failed to obtain database session")

    def _delete_with_session(self, session: Session, post_id: int) -> bool:
        """Internal delete method with session handling.

        Args:
            session: SQLModel Session to use
            post_id: Database primary key of post to delete

        Returns:
            True if post was deleted, False if post not found
        """
        post_model = session.get(PostModel, post_id)
        if not post_model:
            return False

        session.delete(post_model)
        session.commit()
        return True

    def _save_with_session(
        self, session: Session, post: DomainPost
    ) -> DomainPost:
        """Internal save method with session handling.

        Args:
            session: SQLModel Session to use
            post: DomainPost aggregate to persist

        Returns:
            DomainPost aggregate with updated database state

        Raises:
            ValueError: If attempting to update non-existent post or
                slug conflict
        """
        try:
            if post.id is None:
                post_model = self._to_model(post)
                session.add(post_model)
                session.commit()
                session.refresh(post_model)
                return self._to_domain(post_model)

            existing_model = session.get(PostModel, post.id)
            if not existing_model:
                raise ValueError(f"Post with id {post.id} not found")

            existing_model.slug = post.slug.value
            existing_model.title = post.title
            existing_model.author_id = post.author_id
            existing_model.published_html = (
                post.html_content.value if post.html_content else ""
            )
            existing_model.published = post.published
            existing_model.created_at = post.created_at
            existing_model.updated_at = post.updated_at

            session.commit()
            session.refresh(existing_model)
            return self._to_domain(existing_model)

        except IntegrityError as e:
            session.rollback()
            raise ValueError(
                f"Post with slug '{post.slug.value}' already exists"
            ) from e

    def _to_domain(self, post_model: PostModel) -> DomainPost:
        """Convert PostModel to DomainPost aggregate.

        Performs infrastructure-to-domain conversion with slug
        string-to-value-object and html string-to-value-object
        transformations. Preserves all timestamps for audit trail
        integrity. Ensures timezone-aware datetimes by adding UTC
        timezone if missing.

        Args:
            post_model: SQLModel Post table instance

        Returns:
            DomainPost aggregate with converted value objects
        """
        created_at = post_model.created_at
        if created_at.tzinfo is None:
            created_at = created_at.replace(tzinfo=UTC)

        updated_at = post_model.updated_at
        if updated_at.tzinfo is None:
            updated_at = updated_at.replace(tzinfo=UTC)

        html_content = (
            HtmlContent(post_model.published_html)
            if post_model.published_html
            else None
        )

        return DomainPost(
            id=post_model.id,
            slug=Slug(post_model.slug),
            title=post_model.title,
            author_id=post_model.author_id or 0,
            _html_content=html_content,
            published=post_model.published,
            published_at=None,
            created_at=created_at,
            updated_at=updated_at,
        )

    def _to_model(self, domain_post: DomainPost) -> PostModel:
        """Convert DomainPost aggregate to PostModel.

        Performs domain-to-infrastructure conversion with slug
        value-object-to-string and html value-object-to-string
        transformations. Preserves all timestamps for database storage.

        Args:
            domain_post: Domain Post aggregate

        Returns:
            SQLModel Post table instance ready for persistence
        """
        return PostModel(
            id=domain_post.id,
            slug=domain_post.slug.value,
            title=domain_post.title,
            published_html=(
                domain_post.html_content.value
                if domain_post.html_content
                else ""
            ),
            published=domain_post.published,
            author_id=domain_post.author_id,
            created_at=domain_post.created_at,
            updated_at=domain_post.updated_at,
        )
