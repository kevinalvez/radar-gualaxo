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

            for keyword_config in self.keywords:

                keyword = keyword_config["keyword"]

                # Original casing is passed on purpose - see
                # _match_proper_noun.
                if not self._match_keyword(keyword, paragraph):
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

        original_text = text

        text = text.lower()

        if (
            keyword.startswith('"')
            and keyword.endswith('"')
        ):
            expression = keyword[1:-1]

            # Capitalized phrase = proper noun: "Rio Doce" (the river)
            # must not match "cágado de rio doce" (any freshwater river).
            # Only an all-lowercase occurrence is rejected, since the
            # press often writes "barragem de Fundão" in lowercase-start.
            if expression != expression.lower():

                pattern = re.compile(re.escape(expression), re.IGNORECASE)

                return any(
                    match.group() != match.group().lower()
                    for match in pattern.finditer(original_text)
                )

            return expression.lower() in text

        keyword_words = self._tokenize(keyword)

        if len(keyword_words) == 1 and keyword[0].isupper():
            return self._match_proper_noun(keyword, original_text)
        text_words = set(self._tokenize(text))

        return all(
            word in text_words
            for word in keyword_words
        )


    # ------------------------------------------------------------------

    # A capitalized word right after the match ("Mariana Furtado",
    # "Thiago Augusto Vale Lauria") - all-caps acronyms like "MG" don't
    # count, so "Mariana MG" still matches.
    _NEXT_NAME_PATTERN = re.compile(r"\s+[A-ZÀ-Ý][a-zà-ÿ]+")

    def _match_proper_noun(
        self,
        keyword: str,
        text: str,
    ) -> bool:
        """
        Single capitalized keyword (a place/company: "Mariana", "Vale").
        An occurrence immediately followed by another capitalized word
        is part of a person's name, not the place/company, so it's
        skipped - "Suplente: Mariana Furtado Guimarães" doesn't match,
        "Prefeitura de Mariana" or "Mariana recebe..." does.
        """

        pattern = re.compile(
            rf"\b{re.escape(keyword)}\b",
            re.IGNORECASE,
        )

        for match in pattern.finditer(text):

            if self._NEXT_NAME_PATTERN.match(text, match.end()):
                continue

            return True

        return False

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