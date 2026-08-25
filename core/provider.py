"""
core/provider.py

Base Provider interface.

Providers are responsible only for collecting publications from a configured
Source.

Every Provider must return a list of Publication objects.
"""

from __future__ import annotations

from abc import ABC, abstractmethod

from core.publication import Publication
from core.source import Source


class Provider(ABC):
    """
    Abstract base class for all Providers.
    """

    @property
    @abstractmethod
    def name(self) -> str:
        """
        Provider identifier.

        Example:
            rss
            html
            api
            search
        """
        raise NotImplementedError

    # -------------------------------------------------------------

    @abstractmethod
    def collect(
        self,
        source: Source,
    ) -> list[Publication]:
        """
        Collects publications from the given source.

        Parameters
        ----------
        source : Source
            Configured monitoring source.

        Returns
        -------
        list[Publication]
        """

        raise NotImplementedError