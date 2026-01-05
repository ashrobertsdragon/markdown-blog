from backend.main import create_app


def main() -> None:
    """Run Flask development server."""
    app = create_app()
    app.run(debug=True)


if __name__ == "__main__":
    main()
