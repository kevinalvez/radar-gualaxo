"""
core/result.py

Domain entity representing a processing result generated from a Publication.

A Result is produced by a Processor and represents a single occurrence,
such as a keyword match, regex match, AI classification or any future
processing output.

Results are independent from Providers, Outputs and the Pipeline.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field, asdict
from typing import Any
from uuid import uuid4


@dataclass(slots=True)
class Result:
    """
    Represents a processing result generated from a Publication.
    """

    publication_id: str
    processor: str
    type: str
    value: str

    score: float = 1.0

    metadata: dict[str, Any] = field(default_factory=dict)

    id: str = field(default_factory=lambda: str(uuid4()))

    # ------------------------------------------------------------------
    # Utility Methods
    # ------------------------------------------------------------------

    def to_dict(self) -> dict[str, Any]:
        """
        Converts the Result into a dictionary.
        """
        return asdict(self)

    # ------------------------------------------------------------------

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Result":
        """
        Creates a Result from a dictionary.
        """
        return cls(**data)

    # ------------------------------------------------------------------

    def to_json(
        self,
        indent: int = 4,
        ensure_ascii: bool = False,
    ) -> str:
        """
        Serializes the Result to JSON.
        """

        return json.dumps(
            self.to_dict(),
            indent=indent,
            ensure_ascii=ensure_ascii,
        )

    # ------------------------------------------------------------------

    def __str__(self) -> str:
        return (
            f"Result("
            f"processor='{self.processor}', "
            f"type='{self.type}', "
            f"value='{self.value}')"
        )