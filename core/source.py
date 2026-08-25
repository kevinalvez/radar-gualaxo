"""
core/source.py

Represents a monitored information source.

A Source only stores configuration and metadata required by a Provider.
It does not perform collection or processing.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field, asdict
from typing import Any
from uuid import uuid4


@dataclass(slots=True)
class Source:
    """
    Represents a configured monitoring source.
    """

    name: str
    provider: str
    url: str

    enabled: bool = True
    category: str | None = None
    description: str | None = None
    tags: list[str] = field(default_factory=list)

    config: dict[str, Any] = field(default_factory=dict)

    id: str = field(default_factory=lambda: str(uuid4()))

    # ------------------------------------------------------------------
    # Utility Methods
    # ------------------------------------------------------------------

    def to_dict(self) -> dict[str, Any]:
        """Converts the Source into a dictionary."""
        return asdict(self)

    # ------------------------------------------------------------------

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Source":
        """Creates a Source from a dictionary."""
        return cls(**data)

    # ------------------------------------------------------------------

    def to_json(
        self,
        indent: int = 4,
        ensure_ascii: bool = False,
    ) -> str:
        """Serializes the Source to JSON."""

        return json.dumps(
            self.to_dict(),
            indent=indent,
            ensure_ascii=ensure_ascii,
        )

    # ------------------------------------------------------------------

    def __str__(self) -> str:
        return (
            f"Source("
            f"name='{self.name}', "
            f"provider='{self.provider}')"
        )