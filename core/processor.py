"""
core/processor.py

Base Processor interface.

Processors analyze Publications and generate one or more Results.

Processors are independent from Providers, Outputs and the Pipeline.
"""

from __future__ import annotations

from abc import ABC, abstractmethod

from core.publication import Publication
from core.result import Result


class Processor(ABC):
    """
    Abstract base class for all Processors.

    A Processor receives a Publication and returns a list of Results.
    """

    @property
    @abstractmethod
    def name(self) -> str:
        """
        Processor identifier.

        Examples
        --------
        keyword
        regex
        ai
        sentiment
        """
        raise NotImplementedError

    # ------------------------------------------------------------------

    @property
    def description(self) -> str:
        """
        Optional processor description.
        """
        return ""

    # ------------------------------------------------------------------

    @abstractmethod
    def process(
        self,
        publication: Publication,
    ) -> list[Result]:
        """
        Processes a publication.

        Parameters
        ----------
        publication : Publication
            Publication to be analyzed.

        Returns
        -------
        list[Result]
            Results generated from the publication.
        """
        raise NotImplementedError