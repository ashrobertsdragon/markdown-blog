import pytest
from backend.domain.value_objects.comment_text import CommentText


def test_comment_text_stores_text_string() -> None:
    comment_text = CommentText("hello")
    assert comment_text.value == "hello"


def test_comment_text_value_cannot_be_changed_after_creation() -> None:
    comment_text = CommentText("hello")
    with pytest.raises(AttributeError):
        comment_text.value = "changed"  # type: ignore[misc]


def test_comment_text_instances_are_hashable() -> None:
    ct1 = CommentText("hello")
    ct2 = CommentText("world")
    ct_set = {ct1, ct2}
    assert len(ct_set) == 2
    assert ct1 in ct_set
    assert ct2 in ct_set


def test_comment_text_instances_can_be_used_as_dict_keys() -> None:
    ct1 = CommentText("hello")
    ct2 = CommentText("world")
    ct_dict = {ct1: "value1", ct2: "value2"}
    assert ct_dict[ct1] == "value1"
    assert ct_dict[ct2] == "value2"


def test_comment_text_equality_comparison_works() -> None:
    ct1 = CommentText("hello")
    ct2 = CommentText("hello")
    ct3 = CommentText("world")
    assert ct1 == ct2
    assert ct1 != ct3


def test_comment_text_accepts_minimum_length_of_1_char() -> None:
    ct = CommentText("a")
    assert ct.value == "a"


def test_comment_text_accepts_maximum_length_of_5000_chars() -> None:
    ct = CommentText("a" * 5000)
    assert len(ct.value) == 5000


def test_comment_text_raises_valueerror_for_empty_string() -> None:
    with pytest.raises(ValueError, match="empty"):
        CommentText("")


def test_comment_text_raises_valueerror_for_whitespace_only() -> None:
    with pytest.raises(ValueError, match="empty"):
        CommentText("   ")


def test_comment_text_raises_valueerror_for_length_exceeding_5000_chars() -> (
    None
):
    with pytest.raises(ValueError, match="5000"):
        CommentText("a" * 5001)


def test_comment_text_raises_typeerror_for_none_input() -> None:
    with pytest.raises(TypeError):
        CommentText(None)  # type: ignore[arg-type]


def test_comment_text_preserves_special_characters() -> None:
    ct = CommentText("!@#$%^&*()")
    assert ct.value == "!@#$%^&*()"


def test_comment_text_preserves_unicode() -> None:
    ct = CommentText("こんにちは")
    assert ct.value == "こんにちは"


def test_comment_text_preserves_whitespace_and_newlines() -> None:
    ct = CommentText("line1\nline2")
    assert ct.value == "line1\nline2"


def test_comment_text_preserves_url_content() -> None:
    text = "Visit https://example.com for more"
    ct = CommentText(text)
    assert ct.value == text


def test_comment_text_str_returns_text() -> None:
    ct = CommentText("hello")
    assert str(ct) == "hello"


def test_comment_text_repr_shows_proper_representation() -> None:
    ct = CommentText("hello")
    assert repr(ct) == "CommentText(value='hello')"


def test_comment_text_accepts_text_at_exactly_5000_chars() -> None:
    ct = CommentText("x" * 5000)
    assert len(ct.value) == 5000
