import pytest

from backend.domain.value_objects.slug import Slug


def test_slug_converts_uppercase_to_lowercase() -> None:
    slug = Slug("My-Post")
    assert str(slug) == "my-post"


def test_slug_converts_spaces_to_hyphens() -> None:
    slug = Slug("my first post")
    assert str(slug) == "my-first-post"


def test_slug_removes_special_characters() -> None:
    slug = Slug("post@123!")
    assert str(slug) == "post123"


def test_slug_collapses_multiple_consecutive_hyphens() -> None:
    slug = Slug("my--post")
    assert str(slug) == "my-post"


def test_slug_strips_leading_and_trailing_hyphens() -> None:
    slug = Slug("-my-post-")
    assert str(slug) == "my-post"


def test_slug_passes_through_already_normalized_value() -> None:
    slug = Slug("my-post")
    assert str(slug) == "my-post"


def test_slug_handles_mixed_complexity_normalization() -> None:
    slug = Slug("My FIRST!! Post...")
    assert str(slug) == "my-first-post"


def test_slug_preserves_numbers() -> None:
    slug = Slug("post-123-abc")
    assert str(slug) == "post-123-abc"


def test_slug_raises_valueerror_for_empty_string() -> None:
    with pytest.raises(ValueError, match="Slug cannot be empty"):
        Slug("")


def test_slug_raises_valueerror_for_whitespace_only() -> None:
    with pytest.raises(ValueError, match="Slug cannot be empty"):
        Slug("   ")


def test_slug_raises_valueerror_for_length_exceeding_200_chars() -> None:
    long_slug = "a" * 201
    with pytest.raises(ValueError, match="Slug cannot exceed 200 characters"):
        Slug(long_slug)


def test_slug_raises_valueerror_for_special_chars_only() -> None:
    with pytest.raises(ValueError, match="Slug cannot be empty"):
        Slug("@#$%^&*()")


def test_slug_raises_typeerror_for_none_input() -> None:
    with pytest.raises(TypeError):
        Slug(None)  # type: ignore[arg-type]


def test_slug_value_cannot_be_changed_after_creation() -> None:
    slug = Slug("my-post")
    with pytest.raises(AttributeError):
        slug.value = "new-value"  # type: ignore[misc]


def test_slug_instances_are_hashable() -> None:
    slug1 = Slug("my-post")
    slug2 = Slug("another-post")
    slug_set = {slug1, slug2}
    assert len(slug_set) == 2
    assert slug1 in slug_set
    assert slug2 in slug_set


def test_slug_instances_can_be_used_as_dict_keys() -> None:
    slug1 = Slug("my-post")
    slug2 = Slug("another-post")
    slug_dict = {slug1: "value1", slug2: "value2"}
    assert slug_dict[slug1] == "value1"
    assert slug_dict[slug2] == "value2"


def test_slug_str_returns_normalized_value() -> None:
    slug = Slug("my-post")
    assert str(slug) == "my-post"


def test_slug_repr_shows_proper_representation() -> None:
    slug = Slug("my-post")
    assert repr(slug) == "Slug(value='my-post')"


def test_slug_equality_comparison_works_correctly() -> None:
    slug1 = Slug("my-post")
    slug2 = Slug("MY-POST")
    slug3 = Slug("different-post")

    assert slug1 == slug2
    assert slug1 != slug3
    assert slug2 != slug3


def test_slug_accepts_maximum_length_of_200_chars() -> None:
    max_slug = "a" * 200
    slug = Slug(max_slug)
    assert len(str(slug)) == 200
    assert str(slug) == max_slug


def test_slug_accepts_single_character() -> None:
    slug = Slug("a")
    assert str(slug) == "a"


def test_slug_accepts_numeric_only_value() -> None:
    slug = Slug("123")
    assert str(slug) == "123"
