"""Email template constants and definitions for Resend integration.

Defines template alias constants, variable name constants, and the full
TEMPLATE_DEFINITIONS registry used by the provisioning script to register
templates with the Resend API.

Part of the Notification bounded context infrastructure layer.
"""

TEMPLATE_REPLY_NOTIFICATION = "reply-notification"
TEMPLATE_MENTION_NOTIFICATION = "mention-notification"

REPLY_AUTHOR = "REPLY_AUTHOR"
POST_TITLE = "POST_TITLE"
ORIGINAL_COMMENT = "ORIGINAL_COMMENT"
REPLY_EXCERPT = "REPLY_EXCERPT"
POST_URL = "POST_URL"
UNSUBSCRIBE_URL = "UNSUBSCRIBE_URL"
MENTION_AUTHOR = "MENTION_AUTHOR"
MENTION_CONTEXT = "MENTION_CONTEXT"

TEMPLATE_DEFINITIONS: dict[str, dict[str, str]] = {
    TEMPLATE_REPLY_NOTIFICATION: {
        "name": "Reply Notification",
        "subject": "New reply to your comment on {{{POST_TITLE}}}",
        "html": (
            "<html><body>"
            "<p>Hi there,</p>"
            "<p>{{{REPLY_AUTHOR}}} replied to your comment on "
            "<strong>{{{POST_TITLE}}}</strong>.</p>"
            "<blockquote>{{{REPLY_EXCERPT}}}</blockquote>"
            '<p><a href="{{{POST_URL}}}">View the reply</a></p>'
            '<p><small><a href="{{{UNSUBSCRIBE_URL}}}">'
            "Unsubscribe</a></small></p>"
            "</body></html>"
        ),
    },
    TEMPLATE_MENTION_NOTIFICATION: {
        "name": "Mention Notification",
        "subject": "You were mentioned on {{{POST_TITLE}}}",
        "html": (
            "<html><body>"
            "<p>Hi there,</p>"
            "<p>{{{MENTION_AUTHOR}}} mentioned you in a comment on "
            "<strong>{{{POST_TITLE}}}</strong>.</p>"
            "<blockquote>{{{MENTION_CONTEXT}}}</blockquote>"
            '<p><a href="{{{POST_URL}}}">View the comment</a></p>'
            '<p><small><a href="{{{UNSUBSCRIBE_URL}}}">'
            "Unsubscribe</a></small></p>"
            "</body></html>"
        ),
    },
}
