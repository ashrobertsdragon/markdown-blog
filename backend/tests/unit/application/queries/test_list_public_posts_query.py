import pytest
from backend.application.queries.list_public_posts_query import (
    ListPublicPostsQuery,
)


def test_list_public_posts_query_valid_params():
    query = ListPublicPostsQuery(page=1, limit=50)
    assert query.page == 1
    assert query.limit == 50


def test_list_public_posts_query_invalid_page():
    with pytest.raises(ValueError, match="page must be 1 or greater"):
        ListPublicPostsQuery(page=0, limit=20)

    with pytest.raises(ValueError, match="page must be 1 or greater"):
        ListPublicPostsQuery(page=-1, limit=20)


def test_list_public_posts_query_invalid_limit():
    with pytest.raises(ValueError, match="limit must be between 1 and 100"):
        ListPublicPostsQuery(page=1, limit=0)

    with pytest.raises(ValueError, match="limit must be between 1 and 100"):
        ListPublicPostsQuery(page=1, limit=101)
