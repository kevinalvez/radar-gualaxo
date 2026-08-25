"""
outputs/json.py

JSON Output implementation.
"""

from __future__ import annotations

import json
from pathlib import Path

from core.output import Output
from core.processed_publication import ProcessedPublication


class JsonOutput(Output):
    """
    Exports processed publications to a JSON file.
    """

    @property
    def name(self) -> str:
        return "json"

    # ------------------------------------------------------------------

    @property
    def description(self) -> str:
        return "Exports processed publications to a JSON file."

    # ------------------------------------------------------------------

    def export(
        self,
        processed_publications: list[ProcessedPublication],
    ) -> None:
        """
        Exports processed publications to JSON.
        """

        self._ensure_directory()

        data = [
            processed.deduplicated().to_dict()
            for processed in processed_publications
        ]

        with open(
            self.target,
            "w",
            encoding="utf-8",
        ) as file:

            json.dump(
                data,
                file,
                indent=4,
                ensure_ascii=False,
            )

    # ------------------------------------------------------------------

    def _ensure_directory(self) -> None:
        """
        Creates the destination directory if it does not exist.
        """

        Path(self.target).parent.mkdir(
            parents=True,
            exist_ok=True,
        )