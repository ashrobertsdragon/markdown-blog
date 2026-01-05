#!/usr/bin/env -S uv run --script
import hashlib
import html
import sys
from pathlib import Path

INDEX_DIR = Path("/var/www/ashlab/package")


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            h.update(chunk)
    return h.hexdigest()


def main(package: str) -> None:
    package_dir = INDEX_DIR / package
    if not package_dir.exists():
        raise FileNotFoundError(package_dir)
    files = sorted(
        f
        for f in package_dir.iterdir()
        if f.is_file() and not f.name.endswith(".html")
    )

    lines = [
        "<!DOCTYPE html>",
        "<html>",
        "  <body>",
    ]

    for f in files:
        digest = sha256(f)
        name = html.escape(f.name)
        lines.append(f'    <a href="{name}#sha256={digest}">{name}</a><br>')

    lines += [
        "  </body>",
        "</html>",
    ]

    (package_dir / "index.html").write_text("\n".join(lines), encoding="utf-8")


if __name__ == "__main__":
    package = sys.argv[1]
    main(package)
