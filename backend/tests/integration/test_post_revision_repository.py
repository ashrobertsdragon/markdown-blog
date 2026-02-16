"""Integration tests for PostRevisionRepository CRUD operations."""

from uuid import uuid4

import pytest
from sqlmodel import Session, SQLModel, create_engine, select
from sqlmodel.pool import StaticPool

from backend.domain.aggregates.post_revision import PostRevision
from backend.infrastructure.persistence.models import (
    Post,
    PostRevisionModel,
    User,
)
from backend.infrastructure.persistence.post_revision_repository import (
    PostRevisionRepository,
)


@pytest.fixture(name="session")
def session_fixture():
    """Create in-memory SQLite database for testing."""
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    SQLModel.metadata.create_all(engine)
    with Session(engine) as session:
        yield session


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
def sample_revision() -> PostRevision:
    """Create sample PostRevision aggregate."""
    return PostRevision.create(
        post_id=1,
        commit_sha="a1b2c3d4e5f6a7b8c9d0e1f2a3b4c5d6e7f8a9b0",
        author_id=2,
        commit_message="Initial commit",
        markdown_content="# Test Post\n\nThis is test content.",
        is_revert=False,
    )


class TestSave:
    """Test save operation."""

    def test_saves_new_revision(
        self,
        session: Session,
        test_post: tuple[Post, int],
        test_user: tuple[User, int],
        sample_revision: PostRevision,
    ) -> None:
        """Test saving a new revision to database."""
        _, post_id = test_post
        _, user_id = test_user
        repo = PostRevisionRepository(session=session)

        repo.save(sample_revision, post_id, user_id)

        statement = select(PostRevisionModel).where(
            PostRevisionModel.id == sample_revision.id
        )
        saved = session.exec(statement).first()
        assert saved is not None
        assert saved.commit_sha == sample_revision.commit_sha.value
        assert saved.commit_message == sample_revision.commit_message

    def test_duplicate_post_and_sha_raises_error(
        self,
        session: Session,
        test_post: tuple[Post, int],
        test_user: tuple[User, int],
        sample_revision: PostRevision,
    ) -> None:
        """Test that duplicate (post_id, commit_sha) raises ValueError."""
        _, post_id = test_post
        _, user_id = test_user
        repo = PostRevisionRepository(session=session)

        repo.save(sample_revision, post_id, user_id)

        duplicate = PostRevision.create(
            post_id=sample_revision.post_id,
            commit_sha=sample_revision.commit_sha.value,
            author_id=sample_revision.author_id,
            commit_message="Duplicate commit",
            markdown_content="Different content",
        )

        with pytest.raises(ValueError, match="Duplicate revision"):
            repo.save(duplicate, post_id, user_id)


class TestGetById:
    """Test get_by_id query."""

    def test_fetches_existing_revision(
        self,
        session: Session,
        test_post: tuple[Post, int],
        test_user: tuple[User, int],
        sample_revision: PostRevision,
    ) -> None:
        """Test fetching revision by UUID."""
        _, post_id = test_post
        _, user_id = test_user
        repo = PostRevisionRepository(session=session)
        repo.save(sample_revision, post_id, user_id)

        fetched = repo.get_by_id(sample_revision.id)

        assert fetched is not None
        assert fetched.id == sample_revision.id
        assert fetched.commit_sha.value == sample_revision.commit_sha.value

    def test_returns_none_for_nonexistent_id(
        self, session: Session, sample_revision: PostRevision
    ) -> None:
        """Test that nonexistent ID returns None."""
        repo = PostRevisionRepository(session=session)

        fetched = repo.get_by_id(uuid4())

        assert fetched is None


class TestGetByPostAndSha:
    """Test get_by_post_and_sha query."""

    def test_fetches_by_post_and_sha(
        self,
        session: Session,
        test_post: tuple[Post, int],
        test_user: tuple[User, int],
        sample_revision: PostRevision,
    ) -> None:
        """Test fetching revision by post_id and commit_sha."""
        _, post_id = test_post
        _, user_id = test_user
        repo = PostRevisionRepository(session=session)
        repo.save(sample_revision, post_id, user_id)

        fetched = repo.get_by_post_and_sha(
            post_id, sample_revision.commit_sha.value
        )

        assert fetched is not None
        assert fetched.id == sample_revision.id
        assert fetched.commit_sha.value == sample_revision.commit_sha.value

    def test_returns_none_for_nonexistent_pair(
        self,
        session: Session,
        test_post: tuple[Post, int],
        sample_revision: PostRevision,
    ) -> None:
        """Test that nonexistent (post_id, commit_sha) returns None."""
        _, post_id = test_post
        repo = PostRevisionRepository(session=session)

        fetched = repo.get_by_post_and_sha(
            post_id, "nonexistent000000000000000000000000000000000000"
        )

        assert fetched is None


class TestListByPost:
    """Test list_by_post pagination query."""

    def test_lists_revisions_for_post(
        self,
        session: Session,
        test_post: tuple[Post, int],
        test_user: tuple[User, int],
    ) -> None:
        """Test listing revisions for a post."""
        _, post_id = test_post
        _, user_id = test_user
        repo = PostRevisionRepository(session=session)

        rev1 = PostRevision.create(
            post_id=1,
            commit_sha="a" * 40,
            author_id=2,
            commit_message="First commit",
            markdown_content="# First",
        )
        rev2 = PostRevision.create(
            post_id=1,
            commit_sha="b" * 40,
            author_id=2,
            commit_message="Second commit",
            markdown_content="# Second",
        )

        repo.save(rev1, post_id, user_id)
        repo.save(rev2, post_id, user_id)

        revisions = repo.list_by_post(post_id, skip=0, limit=10)

        assert len(revisions) == 2
        assert revisions[0].commit_sha.value == "b" * 40
        assert revisions[1].commit_sha.value == "a" * 40

    def test_pagination_skip_and_limit(
        self,
        session: Session,
        test_post: tuple[Post, int],
        test_user: tuple[User, int],
    ) -> None:
        """Test pagination with skip and limit."""
        _, post_id = test_post
        _, user_id = test_user
        repo = PostRevisionRepository(session=session)

        for i in range(5):
            rev = PostRevision.create(
                post_id=1,
                commit_sha=f"{i}" * 40,
                author_id=2,
                commit_message=f"Commit {i}",
                markdown_content=f"# Content {i}",
            )
            repo.save(rev, post_id, user_id)

        revisions = repo.list_by_post(post_id, skip=2, limit=2)

        assert len(revisions) == 2


class TestDelete:
    """Test delete operation."""

    def test_deletes_existing_revision(
        self,
        session: Session,
        test_post: tuple[Post, int],
        test_user: tuple[User, int],
        sample_revision: PostRevision,
    ) -> None:
        """Test deleting a revision."""
        _, post_id = test_post
        _, user_id = test_user
        repo = PostRevisionRepository(session=session)
        repo.save(sample_revision, post_id, user_id)

        repo.delete(sample_revision.id)

        fetched = repo.get_by_id(sample_revision.id)
        assert fetched is None

    def test_delete_nonexistent_does_not_error(self, session: Session) -> None:
        """Test that deleting nonexistent revision does not error."""
        repo = PostRevisionRepository(session=session)

        repo.delete(uuid4())
