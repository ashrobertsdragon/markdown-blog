from pathlib import Path

import pytest

from backend.infrastructure.persistence.image_repository import (
    FileSystemImageRepository,
)


def test_save_creates_slug_directory_if_absent(tmp_path: Path) -> None:
    repo = FileSystemImageRepository(tmp_path)
    repo.save("my-post", "photo.jpg", b"data")
    assert (tmp_path / "my-post").is_dir()


def test_save_writes_file_to_slug_subdirectory(tmp_path: Path) -> None:
    repo = FileSystemImageRepository(tmp_path)
    repo.save("my-post", "photo.jpg", b"\xff\xd8\xff")
    assert (tmp_path / "my-post" / "photo.jpg").exists()


def test_save_returns_url_path(tmp_path: Path) -> None:
    repo = FileSystemImageRepository(tmp_path)
    url = repo.save("my-post", "photo.jpg", b"data")
    assert url == "/uploads/my-post/photo.jpg"


def test_save_persists_exact_bytes(tmp_path: Path) -> None:
    repo = FileSystemImageRepository(tmp_path)
    content = b"\x89PNG\r\n\x1a\n"
    repo.save("my-post", "image.png", content)
    stored = (tmp_path / "my-post" / "image.png").read_bytes()
    assert stored == content


def test_list_by_post_returns_sorted_urls(tmp_path: Path) -> None:
    repo = FileSystemImageRepository(tmp_path)
    repo.save("my-post", "zz.jpg", b"a")
    repo.save("my-post", "aa.png", b"b")
    repo.save("my-post", "mm.gif", b"c")
    urls = repo.list_by_post("my-post")
    assert urls == [
        "/uploads/my-post/aa.png",
        "/uploads/my-post/mm.gif",
        "/uploads/my-post/zz.jpg",
    ]


def test_list_by_post_returns_empty_list_for_absent_slug(
    tmp_path: Path,
) -> None:
    repo = FileSystemImageRepository(tmp_path)
    assert repo.list_by_post("no-such-post") == []


def test_list_by_post_returns_only_files_for_that_slug(tmp_path: Path) -> None:
    repo = FileSystemImageRepository(tmp_path)
    repo.save("post-a", "img.jpg", b"a")
    repo.save("post-b", "img.jpg", b"b")
    assert repo.list_by_post("post-a") == ["/uploads/post-a/img.jpg"]


def test_delete_removes_file(tmp_path: Path) -> None:
    repo = FileSystemImageRepository(tmp_path)
    repo.save("my-post", "photo.jpg", b"data")
    repo.delete("my-post", "photo.jpg")
    assert not (tmp_path / "my-post" / "photo.jpg").exists()


def test_delete_raises_file_not_found_for_missing_file(tmp_path: Path) -> None:
    repo = FileSystemImageRepository(tmp_path)
    with pytest.raises(FileNotFoundError):
        repo.delete("my-post", "ghost.jpg")


def test_save_overwrites_existing_file(tmp_path: Path) -> None:
    repo = FileSystemImageRepository(tmp_path)
    repo.save("my-post", "photo.jpg", b"first")
    repo.save("my-post", "photo.jpg", b"second")
    stored = (tmp_path / "my-post" / "photo.jpg").read_bytes()
    assert stored == b"second"


def test_list_by_post_excludes_subdirectories(tmp_path: Path) -> None:
    repo = FileSystemImageRepository(tmp_path)
    repo.save("my-post", "photo.jpg", b"data")
    nested = tmp_path / "my-post" / "subdir"
    nested.mkdir()
    urls = repo.list_by_post("my-post")
    assert urls == ["/uploads/my-post/photo.jpg"]


def test_delete_raises_for_path_outside_uploads(tmp_path: Path) -> None:
    uploads = tmp_path / "uploads"
    uploads.mkdir()
    repo = FileSystemImageRepository(uploads)
    with pytest.raises(ValueError, match="outside uploads"):
        repo.delete("..", "photo.jpg")
