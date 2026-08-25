"""
core/output.py

Base Output interface.

Outputs are responsible for exporting processed publications to external
targets such as files, databases or remote services.

Outputs do not collect or process information.
"""

from __future__ import annotations

from abc import ABC, abstractmethod

from core.processed_publication import ProcessedPublication



class Output(ABC):
    """
    Abstract base class for all Outputs.

    An Output receives processed publications and exports them to a
    configured target.
    """

    def __init__(self, target: str) -> None:
        """
        Parameters
        ----------
        target : str
            Export target.

            Examples:
                reports/results.json
                reports/results.csv
                postgresql://user:password@host/database
                s3://bucket/path/
        """
        self.target = target

    # ------------------------------------------------------------------

    @property
    @abstractmethod
    def name(self) -> str:
        """
        Output identifier.

        Examples
        --------
        json
        csv
        postgres
        """
        raise NotImplementedError

    # ------------------------------------------------------------------

    @property
    def description(self) -> str:
        """
        Optional output description.
        """
        return ""

    # ------------------------------------------------------------------

    @abstractmethod
    def export(
        self,
        processed_publications: list[ProcessedPublication],
    ) -> None:
        """
        Exports processed publications.

        Parameters
        ----------
        processed_publications : list[ProcessedPublication]
            Processed publications to export.
        """
        raise NotImplementedError