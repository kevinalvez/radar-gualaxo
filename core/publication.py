"""
core/publication.py

Domain entity representing any content collected by the monitoring platform.

Every Provider must return one or more Publication objects, regardless of
whether the content originated from RSS, HTML, API, PDF, Search, YouTube,
or any future source.

The Publication is the central entity of the application and must remain
independent from Providers, Processors and Outputs.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field, asdict
from datetime import datetime
from typing import Any
from uuid import uuid4


@dataclass(slots=True)
class Publication:
    """
    Represents a collected publication.

    This object travels through the entire processing pipeline.
    """

    title: str
    content: str
    source_id: str
    source_name: str
    url: str

    publication_date: datetime | None = None
    author: str | None = None
    category: str | None = None

    # True for pages that are inherently undated by nature (FAQ,
    # institutional "transparência"/"governança" pages, terms of
    # use, ...) rather than dated content a Provider simply failed to
    # extract a date from. Populated by the Provider that classified
    # the page this way (e.g. HTMLProvider via
    # providers/html/filters.looks_like_static_reference) - Pipeline
    # consumes this generically without knowing how it was decided,
    # same pattern as `category`.
    is_static_reference: bool = False

    attachments: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)

    id: str = field(default_factory=lambda: str(uuid4()))
    collected_at: datetime = field(default_factory=datetime.utcnow)

    # ------------------------------------------------------------------
    # Utility Methods
    # ------------------------------------------------------------------

    def contains(self, term: str, case_sensitive: bool = False) -> bool:
        """
        Checks whether a term exists in the title or content.

        Parameters
        ----------
        term : str
            Search term.
        case_sensitive : bool
            Enables case-sensitive search.

        Returns
        -------
        bool
        """

        if case_sensitive:
            return term in self.title or term in self.content

        term = term.lower()

        return (
            term in self.title.lower()
            or term in self.content.lower()
        )

    # ------------------------------------------------------------------

    def content_hash(self) -> str:
        """
        Generates a SHA-256 hash based on title + content, deliberately
        excluding the URL.

        Used for duplicate detection across a monitoring run: the same
        piece of content is often reachable through more than one URL
        (query-string variants, legacy path aliases, or the same page
        crawled independently from two different configured sources) -
        title + content is what actually identifies "the same
        publication", not the specific URL it happened to be fetched
        from.
        """

        text = f"{self.title}|{self.content}"

        return hashlib.sha256(
            text.encode("utf-8")
        ).hexdigest()

    # ------------------------------------------------------------------

    def to_dict(self) -> dict[str, Any]:
        """
        Converts the Publication into a dictionary.
        """

        data = asdict(self)

        if self.publication_date:
            data["publication_date"] = self.publication_date.isoformat()

        data["collected_at"] = self.collected_at.isoformat()

        return data

    # ------------------------------------------------------------------

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Publication":
        """
        Creates a Publication from a dictionary.
        """

        data = data.copy()

        if data.get("publication_date"):
            data["publication_date"] = datetime.fromisoformat(
                data["publication_date"]
            )

        if data.get("collected_at"):
            data["collected_at"] = datetime.fromisoformat(
                data["collected_at"]
            )

        return cls(**data)

    # ------------------------------------------------------------------

    def to_json(
        self,
        indent: int = 4,
        ensure_ascii: bool = False,
    ) -> str:
        """
        Serializes the Publication to JSON.
        """

        return json.dumps(
            self.to_dict(),
            indent=indent,
            ensure_ascii=ensure_ascii,
        )

    # ------------------------------------------------------------------

    def __str__(self) -> str:
        return (
            f"Publication("
            f"title='{self.title}', "
            f"source='{self.source_name}')"
        )