"""
providers/rss/provider.py

RSS Provider implementation.

Collects publications from RSS and Atom feeds and converts them into
Publication objects.
"""

from __future__ import annotations

from datetime import datetime
from email.utils import parsedate_to_datetime
import re

import feedparser
from bs4 import BeautifulSoup

from core.provider import Provider
from core.publication import Publication
from core.source import Source


class RSSProvider(Provider):
    """
    Provider implementation for RSS and Atom feeds.
    """

    USER_AGENT = (
        "c-monitor/1.0 "
        "(https://github.com/your-project)"
    )

    # Block-level tags used to split a feed entry's HTML into separate
    # lines (see _html_to_text) - same idea as HTMLProvider's own
    # BLOCK_TAGS, kept independent since feed content is a standalone
    # fragment, not a full page needing HTMLCleaner/ContentExtractor.
    BLOCK_TAGS = (
        "p", "div", "li", "h1", "h2", "h3", "h4", "h5", "h6",
        "blockquote",
    )

    # Marker used to later split a block's text back apart at each
    # <br> - replacing <br> with this before get_text(" ") lets inline
    # tags (e.g. <strong> naming an entity mid-sentence) stay joined
    # by a plain space while a <br> still acts as a real line break.
    # Same approach as HTMLProvider's own BR_SPLIT_MARKER.
    BR_SPLIT_MARKER = "␞"

    # ------------------------------------------------------------------

    @property
    def name(self) -> str:
        return "rss"

    # ------------------------------------------------------------------

    @property
    def description(self) -> str:
        return "Collects publications from RSS and Atom feeds."

    # ------------------------------------------------------------------

    def collect(
        self,
        source: Source,
    ) -> list[Publication]:
        """
        Collects publications from an RSS/Atom feed.

        Parameters
        ----------
        source : Source

        Returns
        -------
        list[Publication]
        """

        feed = feedparser.parse(
            source.url,
            agent=self.USER_AGENT,
        )

        publications: list[Publication] = []

        for entry in feed.entries:

            publication = Publication(
                title=self._get_title(entry),
                content=self._get_content(entry),

                source_id=source.id,
                source_name=source.name,

                url=self._get_url(entry),

                publication_date=self._get_date(entry),

                author=self._get_author(entry),

                # Feed entries don't carry a topic category; fall
                # back to the source's configured category.
                category=source.category,

                metadata={
                    "tags": self._get_tags(entry)
                }
            )

            publications.append(publication)

        return publications

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _get_title(self, entry) -> str:

        return getattr(
            entry,
            "title",
            "",
        ).strip()

    # ------------------------------------------------------------------

    def _get_url(self, entry) -> str:

        return getattr(
            entry,
            "link",
            "",
        ).strip()

    # ------------------------------------------------------------------

    def _get_author(self, entry) -> str | None:

        author = getattr(
            entry,
            "author",
            None,
        )

        if author:
            author = author.strip()

        return author

    # ------------------------------------------------------------------

    def _get_content(self, entry) -> str:

        if hasattr(entry, "content"):

            if entry.content:

                return self._html_to_text(entry.content[0].value)

        if hasattr(entry, "summary"):

            return self._html_to_text(entry.summary)

        if hasattr(entry, "description"):

            return self._html_to_text(entry.description)

        return ""

    # ------------------------------------------------------------------

    def _html_to_text(self, value: str) -> str:
        """
        Feed entries commonly carry raw HTML markup in their content/
        summary/description field (e.g. "<p>...</p>", a "<pb>" page-
        break tag some CMS export pipelines emit) rather than plain
        text. Left as-is, that markup leaked straight into
        Publication.content and from there into keyword-match excerpts
        and generated summaries. Strips it down to block-level plain
        text instead, mirroring HTMLProvider's own block-level
        extraction so paragraph boundaries (KeywordProcessor and
        SummaryProcessor both split content on "\\n") are preserved
        rather than collapsing into one run-on line.
        """

        if not value:
            return ""

        value = value.strip()

        if "<" not in value:
            return value

        soup = BeautifulSoup(value, "html.parser")

        for tag in soup.find_all(["script", "style"]):
            tag.decompose()

        for br in soup.find_all("br"):
            br.replace_with(self.BR_SPLIT_MARKER)

        blocks = soup.find_all(self.BLOCK_TAGS)

        if not blocks:
            text = soup.get_text(" ", strip=True)
            lines = [
                self._normalize_chunk(chunk)
                for chunk in text.split(self.BR_SPLIT_MARKER)
            ]
            return "\n".join(line for line in lines if line)

        lines = []

        for block in blocks:

            if block.find(self.BLOCK_TAGS):
                continue

            text = block.get_text(" ", strip=True)

            for chunk in text.split(self.BR_SPLIT_MARKER):

                chunk = self._normalize_chunk(chunk)

                if chunk:
                    lines.append(chunk)

        return "\n".join(lines)

    # ------------------------------------------------------------------

    @staticmethod
    def _normalize_chunk(chunk: str) -> str:
        """
        Collapses whitespace and drops the stray space left before
        punctuation whenever an inline tag ends right before it (e.g.
        get_text(" ") joining "...Rio Doce</strong>, ao..." leaves
        "Rio Doce , ao" instead of "Rio Doce, ao") - same fix as
        HTMLProvider's own text extraction.
        """

        chunk = " ".join(chunk.split())

        return re.sub(r"\s+([,.;:!?])", r"\1", chunk)

    # ------------------------------------------------------------------

    def _get_tags(self, entry) -> list[str]:

        tags = getattr(
            entry,
            "tags",
            [],
        )

        return [
            tag.term
            for tag in tags
            if hasattr(tag, "term")
        ]

    # ------------------------------------------------------------------

    def _get_date(
        self,
        entry,
    ) -> datetime | None:

        value = getattr(
            entry,
            "published",
            None,
        )

        if value is None:

            value = getattr(
                entry,
                "updated",
                None,
            )

        if value is None:
            return None

        try:

            return parsedate_to_datetime(
                value
            )

        except Exception:

            return None