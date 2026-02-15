"""Response formatters for API routes."""

from datetime import UTC, datetime

from backend.domain.aggregates.post_revision import PostRevision


def format_revision_dict(revision: PostRevision) -> dict:
    """Format PostRevision aggregate into JSON response object.

    Args:
        revision: PostRevision aggregate

    Returns:
        Dictionary with revision metadata
    """
    return {
        "id": str(revision.id),
        "commit_sha": str(revision.commit_sha),
        "short_sha": revision.commit_sha.short_sha,
        "author_id": str(revision.author_id),
        "timestamp": revision.created_at.isoformat(),
        "relative_time": format_relative_time(revision.created_at),
        "commit_message": revision.commit_message,
        "is_revert": revision.is_revert,
    }


def format_relative_time(dt: datetime) -> str:
    """Format datetime as relative time string.

    Args:
        dt: Datetime to format

    Returns:
        Human-readable relative time (e.g., "2 days ago")
    """
    now = datetime.now(UTC)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=UTC)

    diff = now - dt
    seconds = diff.total_seconds()

    if seconds < 60:
        return "just now"
    if seconds < 3600:
        minutes = int(seconds / 60)
        return f"{minutes} minute{'s' if minutes != 1 else ''} ago"
    if seconds < 86400:
        hours = int(seconds / 3600)
        return f"{hours} hour{'s' if hours != 1 else ''} ago"
    days = int(seconds / 86400)
    return f"{days} day{'s' if days != 1 else ''} ago"
