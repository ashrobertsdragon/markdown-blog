"""Integration tests for CommentRepository CRUD operations."""

import pytest
from sqlmodel import Session, SQLModel, create_engine, select
from sqlmodel.pool import StaticPool

from backend.domain.aggregates.comment import Comment
from backend.infrastructure.persistence.comment_repository import (
    CommentRepository,
)
from backend.infrastructure.persistence.models import CommentModel, Post, User


@pytest.fixture(name="session")
def session_fixture():
    """Create in-memory SQLite database for testing."""
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    SQLModel.metadata.create_all(engine)
    try:
        with Session(engine) as session:
            yield session
    finally:
        engine.dispose()


@pytest.fixture
def test_user(session: Session) -> tuple[User, int]:
    """Create test user in database and return user with guaranteed ID."""
    user = User(email="test@example.com", role="authenticated")
    session.add(user)
    session.commit()
    session.refresh(user)
    assert user.id is not None
    return user, user.id


@pytest.fixture
def test_post(
    session: Session, test_user: tuple[User, int]
) -> tuple[Post, int]:
    """Create test post in database and return post with guaranteed ID."""
    _, user_id = test_user
    post = Post(
        slug="test-post",
        title="Test Post",
        html_content="<p>Test content</p>",
        published=False,
        author_id=user_id,
    )
    session.add(post)
    session.commit()
    session.refresh(post)
    assert post.id is not None
    return post, post.id


@pytest.fixture
def sample_comment() -> Comment:
    """Create sample Comment aggregate."""
    return Comment.create(post_id=1, author_id=1, text="Hello world")


class TestSave:
    """Test save operation for new inserts and updates."""

    def test_saves_new_comment(
        self,
        session: Session,
        test_post: tuple[Post, int],
        test_user: tuple[User, int],
        sample_comment: Comment,
    ) -> None:
        """Test that saving a new comment inserts a row with correct fields.

        Args:
            session: In-memory SQLite session.
            test_post: Tuple of Post and its database ID.
            test_user: Tuple of User and its database ID.
            sample_comment: Unsaved Comment aggregate fixture.
        """
        _, post_id = test_post
        _, user_id = test_user
        comment = Comment.create(
            post_id=post_id, author_id=user_id, text="Hello world"
        )
        repo = CommentRepository(session=session)

        saved = repo.save(comment)

        statement = select(CommentModel).where(CommentModel.id == saved.id)
        row = session.exec(statement).first()
        assert row is not None
        assert row.text == "Hello world"
        assert row.post_id == post_id
        assert row.author_id == user_id

    def test_save_assigns_id(
        self,
        session: Session,
        test_post: tuple[Post, int],
        test_user: tuple[User, int],
    ) -> None:
        """Test that save returns a Comment with a database-assigned id.

        Args:
            session: In-memory SQLite session.
            test_post: Tuple of Post and its database ID.
            test_user: Tuple of User and its database ID.
        """
        _, post_id = test_post
        _, user_id = test_user
        comment = Comment.create(
            post_id=post_id, author_id=user_id, text="Assign me"
        )
        repo = CommentRepository(session=session)

        saved = repo.save(comment)

        assert saved.id is not None

    def test_save_update_modifies_mutable_fields(
        self,
        session: Session,
        test_post: tuple[Post, int],
        test_user: tuple[User, int],
    ) -> None:
        """Test saving with existing id updates mutable fields.

        Args:
            session: In-memory SQLite session.
            test_post: Tuple of Post and its database ID.
            test_user: Tuple of User and its database ID.
        """
        _, post_id = test_post
        _, user_id = test_user
        repo = CommentRepository(session=session)
        comment = Comment.create(
            post_id=post_id, author_id=user_id, text="Original"
        )
        saved = repo.save(comment)

        saved.is_deleted = True
        updated = repo.save(saved)

        assert updated.is_deleted is True

    def test_save_update_preserves_immutable_fields(
        self,
        session: Session,
        test_post: tuple[Post, int],
        test_user: tuple[User, int],
    ) -> None:
        """Test update does not overwrite post_id, author_id, parent_id,
        or created_at.

        Args:
            session: In-memory SQLite session.
            test_post: Tuple of Post and its database ID.
            test_user: Tuple of User and its database ID.
        """
        _, post_id = test_post
        _, user_id = test_user
        repo = CommentRepository(session=session)
        comment = Comment.create(
            post_id=post_id, author_id=user_id, text="Immutable check"
        )
        saved = repo.save(comment)
        original_post_id = saved.post_id
        original_author_id = saved.author_id
        original_parent_id = saved.parent_id
        original_created_at = saved.created_at

        saved.is_deleted = True
        updated = repo.save(saved)

        assert updated.post_id == original_post_id
        assert updated.author_id == original_author_id
        assert updated.parent_id == original_parent_id
        assert updated.created_at == original_created_at

    def test_save_update_nonexistent_raises_valueerror(
        self,
        session: Session,
        test_post: tuple[Post, int],
        test_user: tuple[User, int],
    ) -> None:
        """Test updating a comment with a non-existent id raises ValueError.

        Args:
            session: In-memory SQLite session.
            test_post: Tuple of Post and its database ID.
            test_user: Tuple of User and its database ID.
        """
        _, post_id = test_post
        _, user_id = test_user
        repo = CommentRepository(session=session)
        comment = Comment.create(
            post_id=post_id, author_id=user_id, text="Ghost"
        )
        comment.id = 99999

        with pytest.raises(ValueError, match="99999"):
            repo.save(comment)


class TestFindById:
    """Test find_by_id query."""

    def test_find_by_id_returns_comment(
        self,
        session: Session,
        test_post: tuple[Post, int],
        test_user: tuple[User, int],
    ) -> None:
        """Test find_by_id returns the correct Comment aggregate after save.

        Args:
            session: In-memory SQLite session.
            test_post: Tuple of Post and its database ID.
            test_user: Tuple of User and its database ID.
        """
        _, post_id = test_post
        _, user_id = test_user
        repo = CommentRepository(session=session)
        comment = Comment.create(
            post_id=post_id, author_id=user_id, text="Find me"
        )
        saved = repo.save(comment)
        assert saved.id is not None
        saved_id = saved.id

        found = repo.find_by_id(saved_id)

        assert found is not None
        assert found.id == saved_id
        assert str(found.text) == "Find me"

    def test_find_by_id_returns_none_for_missing(
        self, session: Session
    ) -> None:
        """Test that find_by_id returns None for a non-existent id.

        Args:
            session: In-memory SQLite session.
        """
        repo = CommentRepository(session=session)

        found = repo.find_by_id(9999)

        assert found is None


class TestListByPost:
    """Test list_by_post public-facing query with visibility filters."""

    def test_list_by_post_returns_comments(
        self,
        session: Session,
        test_post: tuple[Post, int],
        test_user: tuple[User, int],
    ) -> None:
        """Test that list_by_post returns all visible comments for a post.

        Args:
            session: In-memory SQLite session.
            test_post: Tuple of Post and its database ID.
            test_user: Tuple of User and its database ID.
        """
        _, post_id = test_post
        _, user_id = test_user
        repo = CommentRepository(session=session)
        repo.save(
            Comment.create(post_id=post_id, author_id=user_id, text="First")
        )
        repo.save(
            Comment.create(post_id=post_id, author_id=user_id, text="Second")
        )

        comments = repo.list_by_post(post_id)

        assert len(comments) == 2

    def test_list_by_post_excludes_deleted(
        self,
        session: Session,
        test_post: tuple[Post, int],
        test_user: tuple[User, int],
    ) -> None:
        """Test that list_by_post hides soft-deleted comments.

        Args:
            session: In-memory SQLite session.
            test_post: Tuple of Post and its database ID.
            test_user: Tuple of User and its database ID.
        """
        _, post_id = test_post
        _, user_id = test_user
        repo = CommentRepository(session=session)
        deleted = repo.save(
            Comment.create(post_id=post_id, author_id=user_id, text="Gone")
        )
        repo.save(
            Comment.create(post_id=post_id, author_id=user_id, text="Visible")
        )
        deleted.is_deleted = True
        repo.save(deleted)

        comments = repo.list_by_post(post_id)

        assert len(comments) == 1
        assert str(comments[0].text) == "Visible"

    def test_list_by_post_excludes_pending_moderation(
        self,
        session: Session,
        test_post: tuple[Post, int],
        test_user: tuple[User, int],
    ) -> None:
        """Test that list_by_post hides comments pending moderation.

        Args:
            session: In-memory SQLite session.
            test_post: Tuple of Post and its database ID.
            test_user: Tuple of User and its database ID.
        """
        _, post_id = test_post
        _, user_id = test_user
        repo = CommentRepository(session=session)
        pending = repo.save(
            Comment.create(post_id=post_id, author_id=user_id, text="Spam?")
        )
        repo.save(
            Comment.create(post_id=post_id, author_id=user_id, text="Clean")
        )
        pending.is_pending_moderation = True
        repo.save(pending)

        comments = repo.list_by_post(post_id)

        assert len(comments) == 1
        assert str(comments[0].text) == "Clean"

    def test_list_by_post_ordered_chronologically(
        self,
        session: Session,
        test_post: tuple[Post, int],
        test_user: tuple[User, int],
    ) -> None:
        """Test list_by_post returns comments in ascending created_at order.

        Args:
            session: In-memory SQLite session.
            test_post: Tuple of Post and its database ID.
            test_user: Tuple of User and its database ID.
        """
        _, post_id = test_post
        _, user_id = test_user
        repo = CommentRepository(session=session)
        first = repo.save(
            Comment.create(post_id=post_id, author_id=user_id, text="Alpha")
        )
        second = repo.save(
            Comment.create(post_id=post_id, author_id=user_id, text="Beta")
        )

        comments = repo.list_by_post(post_id)

        assert comments[0].id == first.id
        assert comments[1].id == second.id

    def test_list_by_post_pagination(
        self,
        session: Session,
        test_post: tuple[Post, int],
        test_user: tuple[User, int],
    ) -> None:
        """Test list_by_post respects skip and limit pagination parameters.

        Args:
            session: In-memory SQLite session.
            test_post: Tuple of Post and its database ID.
            test_user: Tuple of User and its database ID.
        """
        _, post_id = test_post
        _, user_id = test_user
        repo = CommentRepository(session=session)
        for i in range(5):
            repo.save(
                Comment.create(
                    post_id=post_id,
                    author_id=user_id,
                    text=f"Comment {i}",
                )
            )

        page = repo.list_by_post(post_id, skip=2, limit=2)

        assert len(page) == 2

    def test_list_by_post_excludes_other_posts(
        self,
        session: Session,
        test_user: tuple[User, int],
    ) -> None:
        """Test list_by_post only returns comments belonging to the
        requested post.

        Args:
            session: In-memory SQLite session.
            test_user: Tuple of User and its database ID.
        """
        _, user_id = test_user
        post1 = Post(
            slug="post-one",
            title="Post One",
            html_content="<p>One</p>",
            published=False,
            author_id=user_id,
        )
        post2 = Post(
            slug="post-two",
            title="Post Two",
            html_content="<p>Two</p>",
            published=False,
            author_id=user_id,
        )
        session.add(post1)
        session.add(post2)
        session.commit()
        session.refresh(post1)
        session.refresh(post2)
        assert post1.id is not None
        assert post2.id is not None

        repo = CommentRepository(session=session)
        repo.save(
            Comment.create(
                post_id=post1.id, author_id=user_id, text="For post 1"
            )
        )
        repo.save(
            Comment.create(
                post_id=post2.id, author_id=user_id, text="For post 2"
            )
        )

        comments = repo.list_by_post(post1.id)

        assert len(comments) == 1
        assert str(comments[0].text) == "For post 1"


class TestListByPostAdmin:
    """Test list_by_post_admin query that bypasses visibility filters."""

    def test_list_by_post_admin_includes_deleted(
        self,
        session: Session,
        test_post: tuple[Post, int],
        test_user: tuple[User, int],
    ) -> None:
        """Test that list_by_post_admin returns soft-deleted comments.

        Args:
            session: In-memory SQLite session.
            test_post: Tuple of Post and its database ID.
            test_user: Tuple of User and its database ID.
        """
        _, post_id = test_post
        _, user_id = test_user
        repo = CommentRepository(session=session)
        deleted = repo.save(
            Comment.create(post_id=post_id, author_id=user_id, text="Deleted")
        )
        deleted.is_deleted = True
        repo.save(deleted)

        comments = repo.list_by_post_admin(post_id)

        assert any(c.is_deleted for c in comments)

    def test_list_by_post_admin_includes_pending(
        self,
        session: Session,
        test_post: tuple[Post, int],
        test_user: tuple[User, int],
    ) -> None:
        """Test list_by_post_admin returns comments pending moderation.

        Args:
            session: In-memory SQLite session.
            test_post: Tuple of Post and its database ID.
            test_user: Tuple of User and its database ID.
        """
        _, post_id = test_post
        _, user_id = test_user
        repo = CommentRepository(session=session)
        pending = repo.save(
            Comment.create(post_id=post_id, author_id=user_id, text="Pending")
        )
        pending.is_pending_moderation = True
        repo.save(pending)

        comments = repo.list_by_post_admin(post_id)

        assert any(c.is_pending_moderation for c in comments)


class TestHardDelete:
    """Test hard_delete permanent row removal."""

    def test_hard_delete_removes_row(
        self,
        session: Session,
        test_post: tuple[Post, int],
        test_user: tuple[User, int],
    ) -> None:
        """Test hard_delete causes find_by_id to return None for the
        deleted comment.

        Args:
            session: In-memory SQLite session.
            test_post: Tuple of Post and its database ID.
            test_user: Tuple of User and its database ID.
        """
        _, post_id = test_post
        _, user_id = test_user
        repo = CommentRepository(session=session)
        saved = repo.save(
            Comment.create(post_id=post_id, author_id=user_id, text="Delete me")
        )
        assert saved.id is not None

        repo.hard_delete(saved.id)

        assert repo.find_by_id(saved.id) is None

    def test_hard_delete_returns_true_when_found(
        self,
        session: Session,
        test_post: tuple[Post, int],
        test_user: tuple[User, int],
    ) -> None:
        """Test that hard_delete returns True when the comment exists.

        Args:
            session: In-memory SQLite session.
            test_post: Tuple of Post and its database ID.
            test_user: Tuple of User and its database ID.
        """
        _, post_id = test_post
        _, user_id = test_user
        repo = CommentRepository(session=session)
        saved = repo.save(
            Comment.create(post_id=post_id, author_id=user_id, text="Present")
        )
        assert saved.id is not None

        result = repo.hard_delete(saved.id)

        assert result is True

    def test_hard_delete_returns_false_when_not_found(
        self, session: Session
    ) -> None:
        """Test that hard_delete returns False for a non-existent id.

        Args:
            session: In-memory SQLite session.
        """
        repo = CommentRepository(session=session)

        result = repo.hard_delete(9999)

        assert result is False


class TestSoftDelete:
    """Test soft_delete flag-based deletion."""

    def test_soft_delete_sets_is_deleted_flag(
        self,
        session: Session,
        test_post: tuple[Post, int],
        test_user: tuple[User, int],
    ) -> None:
        """Test soft_delete sets is_deleted to True on the persisted comment.

        Args:
            session: In-memory SQLite session.
            test_post: Tuple of Post and its database ID.
            test_user: Tuple of User and its database ID.
        """
        _, post_id = test_post
        _, user_id = test_user
        repo = CommentRepository(session=session)
        saved = repo.save(
            Comment.create(
                post_id=post_id, author_id=user_id, text="Soft delete me"
            )
        )
        assert saved.id is not None

        repo.soft_delete(saved.id)
        found = repo.find_by_id(saved.id)

        assert found is not None
        assert found.is_deleted is True

    def test_soft_delete_preserves_text(
        self,
        session: Session,
        test_post: tuple[Post, int],
        test_user: tuple[User, int],
    ) -> None:
        """Test that soft_delete preserves the comment text after flagging.

        Args:
            session: In-memory SQLite session.
            test_post: Tuple of Post and its database ID.
            test_user: Tuple of User and its database ID.
        """
        _, post_id = test_post
        _, user_id = test_user
        repo = CommentRepository(session=session)
        saved = repo.save(
            Comment.create(
                post_id=post_id, author_id=user_id, text="Keep my text"
            )
        )
        assert saved.id is not None

        repo.soft_delete(saved.id)
        found = repo.find_by_id(saved.id)

        assert found is not None
        assert str(found.text) == "Keep my text"

    def test_soft_delete_returns_true_when_found(
        self,
        session: Session,
        test_post: tuple[Post, int],
        test_user: tuple[User, int],
    ) -> None:
        """Test that soft_delete returns True when the comment exists.

        Args:
            session: In-memory SQLite session.
            test_post: Tuple of Post and its database ID.
            test_user: Tuple of User and its database ID.
        """
        _, post_id = test_post
        _, user_id = test_user
        repo = CommentRepository(session=session)
        saved = repo.save(
            Comment.create(post_id=post_id, author_id=user_id, text="Present")
        )
        assert saved.id is not None

        result = repo.soft_delete(saved.id)

        assert result is True

    def test_soft_delete_returns_false_when_not_found(
        self, session: Session
    ) -> None:
        """Test that soft_delete returns False for a non-existent id.

        Args:
            session: In-memory SQLite session.
        """
        repo = CommentRepository(session=session)

        result = repo.soft_delete(9999)

        assert result is False

    def test_soft_delete_hides_from_list_by_post(
        self,
        session: Session,
        test_post: tuple[Post, int],
        test_user: tuple[User, int],
    ) -> None:
        """Test list_by_post no longer returns a comment after soft_delete.

        Args:
            session: In-memory SQLite session.
            test_post: Tuple of Post and its database ID.
            test_user: Tuple of User and its database ID.
        """
        _, post_id = test_post
        _, user_id = test_user
        repo = CommentRepository(session=session)
        saved = repo.save(
            Comment.create(post_id=post_id, author_id=user_id, text="Hide me")
        )
        assert saved.id is not None

        repo.soft_delete(saved.id)
        comments = repo.list_by_post(post_id)

        assert all(c.id != saved.id for c in comments)
