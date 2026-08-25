"""
processors/summary.py

Generates a simple extractive summary from a Publication.
"""

from core.result import Result


class SummaryProcessor:
    """
    Generates a basic summary from publication content.
    """

    # Standardized accessibility image-description marker used across
    # Brazilian institutional/NGO social posts (e.g. "PARA TODOS
    # VEREM: a imagem mostra..."). It's kept in publication.content -
    # on image-only posts it can be the only substantial text the
    # page has, so stripping it there risks dropping the publication
    # below the minimum content length entirely - but a photo caption
    # never gives context about the news itself, so it's excluded
    # here, at summary-sentence selection only.
    IGNORED_SUMMARY_PREFIXES = (
        "para todos verem",
        "pra todos verem",
    )

    # A short, fully-uppercase line (e.g. "APRESENTAÇÃO", "VEJA A
    # LISTA DOS SELECIONADOS") is presumed to be a heading/menu
    # label/UI caption rather than real prose - Brazilian institutional
    # sites consistently render these section labels in all caps.
    # Content is newline-joined per visual line by the extractor, so
    # a label like this has no "." separating it from the next real
    # sentence and would otherwise glue onto the front of it.
    #
    # This deliberately does NOT drop every short/unpunctuated line:
    # get_text() inserts a "\n" between *any* two tags, including
    # inline ones (a <strong>/<a> naming an entity mid-sentence), so
    # a mixed-case fragment like "Comitê do Rio Doce" can just as
    # easily be the un-punctuated middle of a real sentence as a
    # label - dropping those corrupts the sentence around them
    # instead of cleaning it up. Requiring all-caps avoids that.
    LABEL_MAX_LENGTH = 60

    def process(self, publication):

        content = publication.content

        if not content:

            return []

        prose_lines = [
            line
            for line in (raw.strip() for raw in content.split("\n"))
            if line
            and not line.lower().startswith(self.IGNORED_SUMMARY_PREFIXES)
            and not (
                len(line) < self.LABEL_MAX_LENGTH
                and line.isupper()
            )
        ]

        content = " ".join(prose_lines)

        if not content:

            return []


        sentences = [
            sentence.strip()
            for sentence in content.split(".")
            if len(sentence.strip()) > 50
        ]


        if not sentences:

            return []


        summary = ". ".join(
            sentences[:2]
        )


        return [

            Result(
                publication_id=publication.id,
                processor="summary",
                type="summary",
                value=summary[:500],
                metadata={
                    "length": len(summary)
                }
            )

        ]