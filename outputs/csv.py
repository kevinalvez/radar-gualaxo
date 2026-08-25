"""
outputs/csv.py

CSV Output implementation.
"""

from __future__ import annotations

import csv
from pathlib import Path

from core.output import Output
from core.processed_publication import ProcessedPublication


class CsvOutput(Output):
    """
    Exports processed publications to a CSV file.

    Each Result is exported as a separate row.
    """

    @property
    def name(self) -> str:
        return "csv"

    # ------------------------------------------------------------------

    @property
    def description(self) -> str:
        return "Exports processed publications to a CSV file."

    # ------------------------------------------------------------------

    def export(
        self,
        processed_publications: list[ProcessedPublication],
    ) -> None:

        self._ensure_directory()

        with open(
            self.target,
            "w",
            newline="",
            encoding="utf-8",
        ) as file:

            writer = csv.writer(file)

            writer.writerow([
                "Keyword",
                "Source",
                "Title",
                "Publication Date",
                "Author",
                "URL",
                "Excerpt",
            ])

            for processed in processed_publications:

                publication = processed.publication
        
                for result in processed.keyword_results():

                    writer.writerow([
                        result.value,
                        publication.source_name,
                        publication.title,
                        publication.publication_date,
                        publication.author,
                        publication.url,
                        result.metadata.get(
                            "excerpt",
                            ""
                        ),
                    ])

    # ------------------------------------------------------------------

    def _ensure_directory(self) -> None:

        Path(self.target).parent.mkdir(
            parents=True,
            exist_ok=True,
        )