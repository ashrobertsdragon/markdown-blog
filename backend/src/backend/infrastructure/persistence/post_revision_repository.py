"""PostRevisionRepository for database persistence."""

import datetime as dt
from uuid import UUID

from sqlalchemy.exc import IntegrityError
from sqlmodel import Session, col, select

from backend.domain.aggregates.post_revision import PostRevision
from backend.domain.value_objects.commit_sha import CommitSHA
from backend.infrastructure.persistence.database import get_db
from backend.infrastructure.persistence.models import PostRevisionModel


class PostRevisionRepository:
    """Repository for PostRevision aggregates."""

    def __init__(self, session: Session | None = None) -> None:
        """Initialize repository with optional session for testing.

        Args:
            session: Optional SQLModel session for testing (mocked or in-memory)
        """
        self.session = session

    def save(
        self, post_revision: PostRevision, post_id: int, author_id: int
    ) -> None:
        """Save PostRevision aggregate to database.

        Args:
            post_revision: Domain PostRevision aggregate
            post_id: Database integer ID for Post (maps from UUID)
            author_id: Database integer ID for User (maps from UUID)

        Raises:
            ValueError: If duplicate (post_id, commit_sha) exists
        """
        model = self._to_model(post_revision, post_id, author_id)

        if self.session:
            session = self.session
            try:
                session.add(model)
                session.commit()
                session.refresh(model)
            except IntegrityError as e:
                session.rollback()
                raise ValueError(
                    "Duplicate revision for post and commit SHA"
                ) from e
        else:
            for session in get_db():
                try:
                    session.add(model)
                    session.commit()
                    session.refresh(model)
                except IntegrityError as e:
                    session.rollback()
                    raise ValueError(
                        "Duplicate revision for post and commit SHA"
                    ) from e

    def get_by_id(
        self, revision_id: UUID, post_uuid: UUID, author_uuid: UUID
    ) -> PostRevision | None:
        """Fetch single revision by UUID.

        Args:
            revision_id: UUID of the revision
            post_uuid: UUID of the post (for domain aggregate)
            author_uuid: UUID of the author (for domain aggregate)

        Returns:
            PostRevision domain aggregate or None if not found
        """
        if self.session:
            session = self.session
            statement = select(PostRevisionModel).where(
                PostRevisionModel.id == revision_id
            )
            model = session.exec(statement).first()
            if model:
                return self._to_domain(model, post_uuid, author_uuid)
            return None
        else:
            for session in get_db():
                statement = select(PostRevisionModel).where(
                    PostRevisionModel.id == revision_id
                )
                model = session.exec(statement).first()
                if model:
                    return self._to_domain(model, post_uuid, author_uuid)
                return None
        return None

    def get_by_post_and_sha(
        self,
        post_id: int,
        commit_sha: str,
        post_uuid: UUID,
        author_uuid: UUID,
    ) -> PostRevision | None:
        """Fetch revision by post_id + commit_sha (unique pair).

        Args:
            post_id: Database integer ID for Post
            commit_sha: Git commit SHA string
            post_uuid: UUID of the post (for domain aggregate)
            author_uuid: UUID of the author (for domain aggregate)

        Returns:
            PostRevision domain aggregate or None if not found
        """
        if self.session:
            session = self.session
            statement = select(PostRevisionModel).where(
                PostRevisionModel.post_id == post_id,
                PostRevisionModel.commit_sha == commit_sha,
            )
            model = session.exec(statement).first()
            if model:
                return self._to_domain(model, post_uuid, author_uuid)
            return None
        else:
            for session in get_db():
                statement = select(PostRevisionModel).where(
                    PostRevisionModel.post_id == post_id,
                    PostRevisionModel.commit_sha == commit_sha,
                )
                model = session.exec(statement).first()
                if model:
                    return self._to_domain(model, post_uuid, author_uuid)
                return None
        return None

    def list_by_post(
        self,
        post_id: int,
        post_uuid: UUID,
        author_uuid: UUID,
        skip: int = 0,
        limit: int = 10,
    ) -> list[PostRevision]:
        """Fetch revisions for a post (paginated, newest first).

        Args:
            post_id: Database integer ID for Post
            post_uuid: UUID of the post (for domain aggregate)
            author_uuid: UUID of the author (for domain aggregate)
            skip: Number of records to skip (for pagination)
            limit: Maximum number of records to return

        Returns:
            List of PostRevision domain aggregates
        """
        if self.session:
            session = self.session
            statement = (
                select(PostRevisionModel)
                .where(PostRevisionModel.post_id == post_id)
                .order_by(col(PostRevisionModel.created_at).desc())
                .offset(skip)
                .limit(limit)
            )
            models = session.exec(statement).all()
            return [
                self._to_domain(model, post_uuid, author_uuid)
                for model in models
            ]
        else:
            for session in get_db():
                statement = (
                    select(PostRevisionModel)
                    .where(PostRevisionModel.post_id == post_id)
                    .order_by(col(PostRevisionModel.created_at).desc())
                    .offset(skip)
                    .limit(limit)
                )
                models = session.exec(statement).all()
                return [
                    self._to_domain(model, post_uuid, author_uuid)
                    for model in models
                ]
        return []

    def delete(self, revision_id: UUID) -> None:
        """Delete PostRevision (soft delete pattern).

        Args:
            revision_id: UUID of the revision to delete
        """
        if self.session:
            session = self.session
            statement = select(PostRevisionModel).where(
                PostRevisionModel.id == revision_id
            )
            model = session.exec(statement).first()
            if model:
                session.delete(model)
                session.commit()
        else:
            for session in get_db():
                statement = select(PostRevisionModel).where(
                    PostRevisionModel.id == revision_id
                )
                model = session.exec(statement).first()
                if model:
                    session.delete(model)
                    session.commit()

    def _to_model(
        self,
        aggregate: PostRevision,
        post_id: int,
        author_id: int,
    ) -> PostRevisionModel:
        """Convert domain aggregate to SQLModel.

        Args:
            aggregate: PostRevision domain aggregate
            post_id: Database integer ID for Post
            author_id: Database integer ID for User

        Returns:
            PostRevisionModel for database persistence
        """
        return PostRevisionModel(
            id=aggregate.id,
            post_id=post_id,
            commit_sha=aggregate.commit_sha.value,
            author_id=author_id,
            commit_message=aggregate.commit_message,
            markdown_content=aggregate.markdown_content,
            created_at=aggregate.created_at,
            updated_at=aggregate.updated_at,
            is_revert=aggregate.is_revert,
            attempt_count=0,
        )

    def _to_domain(
        self,
        model: PostRevisionModel,
        post_uuid: UUID,
        author_uuid: UUID,
    ) -> PostRevision:
        """Convert SQLModel to domain aggregate.

        Args:
            model: PostRevisionModel from database
            post_uuid: UUID of the post (for domain aggregate)
            author_uuid: UUID of the author (for domain aggregate)

        Returns:
            PostRevision domain aggregate

        Raises:
            ValueError: If model.id is None
        """
        if model.id is None:
            raise ValueError("PostRevisionModel must have an ID")

        created_at = model.created_at
        if created_at.tzinfo is None:
            created_at = created_at.replace(tzinfo=dt.UTC)

        updated_at = model.updated_at
        if updated_at.tzinfo is None:
            updated_at = updated_at.replace(tzinfo=dt.UTC)

        return PostRevision(
            id=model.id,
            post_id=post_uuid,
            commit_sha=CommitSHA(model.commit_sha),
            author_id=author_uuid,
            commit_message=model.commit_message,
            markdown_content=model.markdown_content,
            created_at=created_at,
            updated_at=updated_at,
            is_revert=model.is_revert,
        )
