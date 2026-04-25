"""Query and result types for the GetUserActivity use case.

This module defines the query input and structured result for fetching
a summary of a user's activity: total post and comment counts plus
the most recent posts and comments.
"""

from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True)
class GetUserActivityQuery:
    """Query requesting an activity summary for a single user.

    Attributes:
        user_id: Database primary key of the user to look up.
    """

    user_id: int


@dataclass(frozen=True)
class UserActivity:
    """Activity summary result returned by GetUserActivityHandler.

    Attributes:
        last_login: UTC timestamp of the user's last login, or None
            when the User aggregate does not yet track this field.
        posts_count: Total number of posts authored by the user.
        comments_count: Total number of comments posted by the user.
        recent_posts: Up to 5 most recent Post aggregates authored
            by the user, ordered newest first.
        recent_comments: Up to 10 most recent Comment aggregates
            posted by the user, ordered newest first.
    """

    last_login: datetime | None
    posts_count: int
    comments_count: int
    recent_posts: list
    recent_comments: list
