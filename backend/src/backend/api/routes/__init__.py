"""API routes."""

from backend.api.routes.admin import admin_bp
from backend.api.routes.auth import auth_bp
from backend.api.routes.comments import admin_comments_bp, comments_bp
from backend.api.routes.health import health_bp
from backend.api.routes.images import images_bp
from backend.api.routes.notifications import notifications_bp
from backend.api.routes.posts import posts_bp
from backend.api.routes.revisions import revisions_bp
from backend.api.routes.test import test_bp
from backend.api.routes.users import users_bp

__all__ = [
    "admin_bp",
    "admin_comments_bp",
    "auth_bp",
    "comments_bp",
    "health_bp",
    "images_bp",
    "notifications_bp",
    "posts_bp",
    "revisions_bp",
    "test_bp",
    "users_bp",
]
