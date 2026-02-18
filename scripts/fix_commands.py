#!/usr/bin/env python3
"""Fix command instantiations to include author_id and user_role parameters."""

import re
from pathlib import Path


def fix_save_draft_command(content: str) -> str:
    """Add author_id and user_role to SaveDraftCommand."""
    pattern = r"(SaveDraftCommand\s*\(\s*slug=[^,]+,\s*content=[^,)]+)(\s*\))"
    replacement = r'\1,\n        author_id=1,\n        user_role="author",\n    \2'
    return re.sub(pattern, replacement, content)


def fix_delete_draft_command(content: str) -> str:
    """Add author_id and user_role to DeleteDraftCommand."""
    pattern = r"(DeleteDraftCommand\s*\(\s*slug=[^,)]+)(\s*\))"
    replacement = r'\1, author_id=1, user_role="author"\2'
    return re.sub(pattern, replacement, content)


def fix_publish_post_command(content: str) -> str:
    """Add author_id and user_role to PublishPostCommand."""
    pattern = r"(PublishPostCommand\s*\(\s*slug=[^,)]+)(\s*\))"
    replacement = r'\1, author_id=1, user_role="author"\2'
    return re.sub(pattern, replacement, content)


def fix_unpublish_post_command(content: str) -> str:
    """Add author_id and user_role to UnpublishPostCommand."""
    pattern = r"(UnpublishPostCommand\s*\(\s*slug=[^,)]+)(\s*\))"
    replacement = r'\1, author_id=1, user_role="author"\2'
    return re.sub(pattern, replacement, content)


def fix_file(file_path: Path) -> None:
    """Fix all command instantiations in a file."""
    content = file_path.read_text()
    original = content

    content = fix_save_draft_command(content)
    content = fix_delete_draft_command(content)
    content = fix_publish_post_command(content)
    content = fix_unpublish_post_command(content)

    if content != original:
        file_path.write_text(content)
        print(f"Fixed: {file_path}")
    else:
        print(f"No changes: {file_path}")


def main() -> None:
    """Fix all test files."""
    test_files = [
        "tests/integration/application/handlers/test_save_draft_handler_integration.py",
        "tests/unit/application/commands/handlers/test_delete_draft_handler.py",
        "tests/unit/application/commands/handlers/test_publish_post_handler.py",
        "tests/unit/application/commands/handlers/test_unpublish_post_handler.py",
        "tests/unit/application/commands/test_delete_draft_command.py",
        "tests/unit/application/commands/test_publish_post_command.py",
        "tests/unit/application/commands/test_unpublish_post_command.py",
        "tests/unit/application/handlers/test_save_draft_handler.py",
        "tests/unit/test_save_draft_command.py",
    ]

    for file_name in test_files:
        file_path = Path(file_name)
        if file_path.exists():
            fix_file(file_path)
        else:
            print(f"Not found: {file_path}")


if __name__ == "__main__":
    main()
