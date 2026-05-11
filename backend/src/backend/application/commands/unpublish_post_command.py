from dataclasses import dataclass


@dataclass(frozen=True)
class UnpublishPostCommand:
    """Command to unpublish a published post.

    Immutable command encapsulating the intent to convert a published post back
    to draft status. Validation deferred to handler (domain and business logic).

    Attributes:
        post_id: The post's primary key (avoids a redundant slug lookup).
        author_id: ID of the user attempting to unpublish the post
        user_role: Role of the user (for admin override)
    """

    post_id: int
    author_id: int
    user_role: str

    def __post_init__(self) -> None:
        """Validate input constraints.

        Raises:
            ValueError: If post_id is not positive.
            ValueError: If author_id is not positive.
            ValueError: If user_role is empty.
        """
        if self.post_id <= 0:
            raise ValueError("post_id must be a positive integer")
        if self.author_id <= 0:
            raise ValueError("author_id must be a positive integer")
        if not self.user_role:
            raise ValueError("user_role cannot be empty")
