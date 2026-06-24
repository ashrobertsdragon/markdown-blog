import pytest

from backend.domain.value_objects.image_filename import ImageFilename


def test_image_filename_accepts_valid_jpeg() -> None:
    fn = ImageFilename("photo.jpg")
    assert fn.value == "photo.jpg"


def test_image_filename_accepts_valid_jpeg_long_extension() -> None:
    fn = ImageFilename("photo.jpeg")
    assert fn.value == "photo.jpeg"


def test_image_filename_accepts_valid_png() -> None:
    fn = ImageFilename("image.png")
    assert fn.value == "image.png"


def test_image_filename_accepts_valid_gif() -> None:
    fn = ImageFilename("animation.gif")
    assert fn.value == "animation.gif"


def test_image_filename_accepts_valid_webp() -> None:
    fn = ImageFilename("graphic.webp")
    assert fn.value == "graphic.webp"


def test_image_filename_removes_spaces_from_stem() -> None:
    fn = ImageFilename("my photo.jpg")
    assert fn.value == "myphoto.jpg"


def test_image_filename_raises_on_forward_slash() -> None:
    with pytest.raises(ValueError, match="path separators"):
        ImageFilename("../../etc/passwd.jpg")


def test_image_filename_raises_on_double_dot() -> None:
    with pytest.raises(ValueError, match="path separators"):
        ImageFilename("../secret.jpg")


def test_image_filename_raises_on_invalid_extension() -> None:
    with pytest.raises(ValueError, match="extension"):
        ImageFilename("script.exe")


def test_image_filename_raises_on_txt_extension() -> None:
    with pytest.raises(ValueError, match="extension"):
        ImageFilename("file.txt")


def test_image_filename_raises_when_length_exceeds_100_chars() -> None:
    long_name = "a" * 97 + ".jpg"
    assert len(long_name) == 101
    with pytest.raises(ValueError, match="100"):
        ImageFilename(long_name)


def test_image_filename_accepts_exactly_100_chars() -> None:
    name = "a" * 96 + ".jpg"
    assert len(name) == 100
    fn = ImageFilename(name)
    assert len(fn.value) == 100


def test_image_filename_value_returns_sanitized_string() -> None:
    fn = ImageFilename("my_photo-123.png")
    assert fn.value == "my_photo-123.png"


def test_image_filename_extension_property_returns_dot_plus_ext() -> None:
    fn = ImageFilename("photo.jpg")
    assert fn.extension == ".jpg"


def test_image_filename_extension_property_for_png() -> None:
    fn = ImageFilename("diagram.png")
    assert fn.extension == ".png"


def test_image_filename_extension_property_for_jpeg() -> None:
    fn = ImageFilename("shot.jpeg")
    assert fn.extension == ".jpeg"


def test_image_filename_preserves_underscores_in_stem() -> None:
    fn = ImageFilename("my_cool_image.webp")
    assert fn.value == "my_cool_image.webp"


def test_image_filename_preserves_hyphens_in_stem() -> None:
    fn = ImageFilename("my-cool-image.gif")
    assert fn.value == "my-cool-image.gif"


def test_image_filename_preserves_uppercase_in_stem() -> None:
    fn = ImageFilename("MyPhoto.png")
    assert fn.value == "MyPhoto.png"


def test_image_filename_extension_normalized_to_lowercase() -> None:
    fn = ImageFilename("Photo.JPG")
    assert fn.extension == ".jpg"
    assert fn.value.endswith(".jpg")


def test_image_filename_raises_for_empty_string() -> None:
    with pytest.raises(ValueError):
        ImageFilename("")


def test_image_filename_raises_for_no_extension() -> None:
    with pytest.raises(ValueError, match="extension"):
        ImageFilename("photowithoutext")


def test_image_filename_cannot_be_modified_after_creation() -> None:
    fn = ImageFilename("photo.jpg")
    with pytest.raises(AttributeError):
        fn.value = "other.jpg"  # type: ignore[misc]


def test_image_filename_instances_are_hashable() -> None:
    fn1 = ImageFilename("a.jpg")
    fn2 = ImageFilename("b.png")
    fn_set = {fn1, fn2}
    assert len(fn_set) == 2
    assert fn1 in fn_set


def test_image_filename_equal_instances_are_equal() -> None:
    fn1 = ImageFilename("photo.jpg")
    fn2 = ImageFilename("photo.jpg")
    assert fn1 == fn2


def test_image_filename_str_returns_value() -> None:
    fn = ImageFilename("photo.jpg")
    assert str(fn) == "photo.jpg"


def test_image_filename_removes_special_chars_from_stem() -> None:
    fn = ImageFilename("my@photo!.jpg")
    assert fn.value == "myphoto.jpg"
