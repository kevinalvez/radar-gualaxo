"""
processors/keyword.py

Keyword Processor.

Searches configured keywords within a Publication and returns Results.
"""

from __future__ import annotations

from core.processor import Processor
from core.publication import Publication
from core.result import Result
import re

class KeywordProcessor(Processor):

    def __init__(
        self,
        keywords: list,
    ) -> None:

        self.keywords = []

        for keyword in keywords:

            if isinstance(keyword, str):

                self.keywords.append(
                    {
                        "keyword": keyword,
                        "enabled": True,
                        "category": None,
                        "emoji": "📌"
                    }
                )


            elif isinstance(keyword, dict):

                if keyword.get(
                    "enabled",
                    True
                ):

                    self.keywords.append(
                        keyword
                    )


    @property
    def name(self) -> str:
        return "keyword"


    @property
    def description(self) -> str:
        return (
            "Searches configured keywords "
            "inside publication text."
        )


    def process(
        self,
        publication: Publication,
    ) -> list[Result]:
        """
        Processes a publication looking for keyword matches.
        """

        results: list[Result] = []

        paragraphs = self._split_paragraphs(
            publication.content
        )

        for paragraph in paragraphs:

            paragraph_lower = paragraph.lower()

            for keyword_config in self.keywords:

                keyword = keyword_config["keyword"]

                if not self._match_keyword(keyword, paragraph_lower):
                    continue

                results.append(
                    Result(
                        publication_id=publication.id,
                        processor=self.name,
                        type="keyword",
                        value=keyword,
                        metadata={
                            "excerpt": paragraph,
                            "category": keyword_config.get("category"),
                            "emoji": keyword_config.get("emoji", "📌"),
                        },
                    )
                )

        return results

    def _split_paragraphs(
        self,
        text: str,
    ) -> list[str]:

        return [
            paragraph.strip()
            for paragraph in text.split("\n")
            if paragraph.strip()
        ]
    # ------------------------------------------------------------------

    def _match_keyword(
        self,
        keyword: str,
        text: str,
    ) -> bool:

        keyword = keyword.strip()

        if not keyword:
            return False

        text = text.lower()

        if (
            keyword.startswith('"')
            and keyword.endswith('"')
        ):
            expression = keyword[1:-1].lower()
            return expression in text

        keyword_words = self._tokenize(keyword)
        text_words = set(self._tokenize(text))

        return all(
            word in text_words
            for word in keyword_words
        )


    # ------------------------------------------------------------------

    def _tokenize(
        self,
        text: str,
    ) -> list[str]:
        """
        Splits text into alphanumeric tokens.
        """

        return re.findall(
            r"\w+",
            text.lower(),
        )