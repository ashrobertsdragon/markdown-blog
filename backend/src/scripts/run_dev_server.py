import os

from backend.main import create_app


def main() -> None:
    """Run Flask development server."""
    app = create_app()
    testing = os.environ.get("FLASK_ENV") == "TESTING"
    app.run(debug=True, port=5555, use_reloader=not testing)


if __name__ == "__main__":
    main()
