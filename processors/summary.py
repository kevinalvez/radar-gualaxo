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

    # Soft cap on the final summary's length. Sentences are added one at a
    # time up to this limit rather than concatenating a fixed sentence
    # count and hard-slicing the result - a fixed slice would cut mid-word
    # whenever the selected sentences happened to add up to more than this,
    # producing a summary that visibly stops mid-sentence.
    MAX_SUMMARY_LENGTH = 500
    MAX_SENTENCES = 2

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


        selected = []
        length = 0

        for sentence in sentences:

            separator_length = 2 if selected else 0  # ". "

            if selected and length + separator_length + len(sentence) > self.MAX_SUMMARY_LENGTH:

                break

            selected.append(sentence)
            length += separator_length + len(sentence)

            if len(selected) >= self.MAX_SENTENCES:

                break

        if not selected:

            selected = [sentences[0]]

        summary = ". ".join(selected)

        if not summary.endswith((".", "!", "?")):

            summary += "."

        if len(summary) > self.MAX_SUMMARY_LENGTH:

            # A single sentence alone exceeds the cap - truncate at the
            # last full word instead of mid-word, and mark it as cut off.
            summary = summary[:self.MAX_SUMMARY_LENGTH].rsplit(" ", 1)[0].rstrip(",.;:") + "..."


        return [

            Result(
                publication_id=publication.id,
                processor="summary",
                type="summary",
                value=summary,
                metadata={
                    "length": len(summary)
                }
            )

        ]