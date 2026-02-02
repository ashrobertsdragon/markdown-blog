"""PostFilter enum for filtering posts by publication status."""

from enum import Enum


class PostFilter(Enum):
    """Filter options for listing posts by publication state.

    Provides filter types for queries to return drafts, published posts,
    or all posts regardless of publication status. Used in list queries
    to control which posts are returned from the repository.
    """

    DRAFTS = "drafts"
    PUBLISHED = "published"
    ALL = "all"
