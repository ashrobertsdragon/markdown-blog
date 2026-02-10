"""HTML sanitization using Bleach allowlist-based approach.

This module implements HTML sanitization to prevent XSS attacks in
user-generated content. It uses an allowlist approach with Bleach to
strip dangerous tags, attributes, and protocols while preserving safe
HTML formatting.

Requirements implemented:
- 9.3: HTML sanitized with Bleach (allowlist approach)
- 9.4: script, style, iframe, object tags removed
- 9.5: Only allowed tags preserved
- 9.6: External links have rel="nofollow noreferrer"
- 9.7: Images restricted to src, alt, title attributes
"""

import re
from collections.abc import Iterator, MutableMapping
from typing import Any

import bleach
from bleach.sanitizer import BleachSanitizerFilter, Cleaner


class SensitiveClassFilter(BleachSanitizerFilter):
    """Filter for html5lib to strip sensitive class prefixes."""

    def __init__(
        self,
        source: Any,
        prefixes: tuple[str, ...],
    ) -> None:
        """Initialize filter."""
        super().__init__(source)
        self.prefixes = prefixes

    def __iter__(self) -> Iterator[dict]:
        """Iterate over tokens and filter class attributes."""
        for token in self.source:
            if token["type"] in ("StartTag", "EmptyTag"):
                attrs = token["data"]
                if isinstance(attrs, dict):
                    for attr_key, attr_value in list(attrs.items()):
                        if attr_key[1] == "class":
                            classes = attr_value.split()
                            filtered = [
                                c
                                for c in classes
                                if not any(
                                    c.startswith(p) for p in self.prefixes
                                )
                            ]
                            if not filtered:
                                del attrs[attr_key]
                            else:
                                attrs[attr_key] = " ".join(filtered)
            yield token


class HtmlSanitizer:
    """Sanitizes HTML content using allowlist-based filtering."""

    ALLOWED_TAGS = [
        "p",
        "h1",
        "h2",
        "h3",
        "h4",
        "h5",
        "h6",
        "a",
        "img",
        "ul",
        "ol",
        "li",
        "code",
        "pre",
        "strong",
        "em",
        "blockquote",
        "br",
        "hr",
        "table",
        "thead",
        "tbody",
        "tr",
        "th",
        "td",
        "span",
        "div",
    ]

    ALLOWED_ATTRIBUTES = {
        "a": ["href", "title", "rel"],
        "img": ["src", "alt", "title"],
        "div": ["class"],
        "span": ["class"],
    }

    ALLOWED_PROTOCOLS = ["http", "https", "mailto"]

    SENSITIVE_CLASS_PREFIXES = (
        "js-",
        "admin-",
        "tracking-",
        "track-",
        "analytics-",
        "experiment-",
    )

    def __init__(self) -> None:
        """Initialize the sanitizer with a configured Bleach Cleaner."""

        def filter_factory(source: Any) -> SensitiveClassFilter:
            return SensitiveClassFilter(source, self.SENSITIVE_CLASS_PREFIXES)

        self._cleaner = Cleaner(
            tags=self.ALLOWED_TAGS,
            attributes=self.ALLOWED_ATTRIBUTES,
            protocols=self.ALLOWED_PROTOCOLS,
            filters=[filter_factory],
            strip=True,
        )

    def sanitize(self, html: str) -> str:
        """Sanitize HTML using Bleach allowlist."""
        preprocessed = self._remove_dangerous_tags_with_content(html)

        cleaned = self._cleaner.clean(preprocessed)

        linkified = bleach.linkify(
            cleaned,
            callbacks=[self._add_rel_nofollow],
            skip_tags=["pre", "code"],
        )

        return str(linkified)

    def _remove_dangerous_tags_with_content(self, html: str) -> str:
        """Remove dangerous tags and their entire contents.

        This method removes script and style tags along with everything
        inside them, as these tags can contain executable code or styles
        that should not be preserved even as text content.

        Args:
            html: The HTML string to preprocess.

        Returns:
            HTML string with script and style tags and their contents
            completely removed.
        """
        html = re.sub(
            r"<script[^>]*?>.*?</script>",
            "",
            html,
            flags=re.IGNORECASE | re.DOTALL,
        )

        html = re.sub(
            r"<style[^>]*?>.*?</style>",
            "",
            html,
            flags=re.IGNORECASE | re.DOTALL,
        )

        return html

    def _add_rel_nofollow(
        self,
        attrs: MutableMapping[tuple[str | None, str], str],
        new: bool = False,
    ) -> MutableMapping[tuple[str | None, str], str]:
        """Bleach linkify callback to add nofollow to external links.

        This callback is used by bleach.linkify() to modify link attributes.
        It adds rel="nofollow noreferrer" to external links (http/https)
        while leaving relative, anchor, and mailto links unchanged.

        Args:
            attrs: Dictionary of link attributes from Bleach. Keys are
                   tuples of (namespace, name) where namespace is optional.
            new: Whether this is a newly created link (unused, required by
                 Bleach callback signature).

        Returns:
            Modified attributes dictionary with rel attribute added for
            external links.
        """
        href_key: tuple[str | None, str] = (None, "href")
        rel_key: tuple[str | None, str] = (None, "rel")

        href = attrs.get(href_key, "")

        if isinstance(href, str) and href.startswith(("http://", "https://")):
            rel_value = attrs.get(rel_key, "")

            if isinstance(rel_value, str):
                rel_parts = set(rel_value.split()) if rel_value else set()
            else:
                rel_parts = set()

            rel_parts.add("nofollow")
            rel_parts.add("noreferrer")

            attrs[rel_key] = " ".join(sorted(rel_parts))

        return attrs
