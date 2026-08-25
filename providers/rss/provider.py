"""
providers/rss/provider.py

RSS Provider implementation.

Collects publications from RSS and Atom feeds and converts them into
Publication objects.
"""

from __future__ import annotations

from datetime import datetime
from email.utils import parsedate_to_datetime

import feedparser

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

                return entry.content[0].value.strip()

        if hasattr(entry, "summary"):

            return entry.summary.strip()

        if hasattr(entry, "description"):

            return entry.description.strip()

        return ""

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