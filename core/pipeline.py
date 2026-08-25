"""
core/pipeline.py

Pipeline orchestrator.

The Pipeline coordinates Providers, Processors and Outputs without containing
any collection, processing or export logic.
"""

from __future__ import annotations
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timedelta, timezone
from typing import Callable
from core.processed_publication import ProcessedPublication
from core.provider import Provider
from core.processor import Processor
from core.output import Output
from core.source import Source


class Pipeline:
    """
    Coordinates the monitoring workflow.
    """

    # How many sources are collected from at once. Collection is
    # network-bound (each source may itself download several pages
    # concurrently - see HTMLProvider.page_concurrency), so running a
    # moderate number of sources in parallel cuts total run time a lot
    # without hammering too many different sites at once.
    SOURCE_CONCURRENCY = 4

    def __init__(
        self,
        providers: dict[str, Provider],
        processors: list[Processor],
        outputs: list[Output],
    ) -> None:

        self.providers = providers
        self.processors = processors
        self.outputs = outputs

    # -------------------------------------------------------------

    def run(
        self,
        sources: list[Source],
        date_filter: dict | None = None,
        on_progress: Callable[[int, int], None] | None = None,
    ) -> list[ProcessedPublication]:
        """
        Executes the monitoring pipeline.

        on_progress, when given, is called as on_progress(current, total)
        after each source finishes (current is 1-based), so a caller can
        show run progress without the Pipeline knowing anything about how
        that's displayed.

        Publications are de-duplicated by content_hash() (title + content,
        not URL) across the *entire* run, not just within one source's own
        collect() call - the same piece of content is often reachable
        through more than one URL (query-string variants, legacy path
        aliases, or independently discovered by two different configured
        sources), and a raw list[dict.fromkeys(...)] within a single
        Provider call can't catch that.

        Collection itself (provider.collect + filter_by_date, both
        network-bound and independent per source) runs on up to
        SOURCE_CONCURRENCY sources at once. Building ProcessedPublications
        (de-dup + running processors) happens back on the calling thread as
        each source's collection finishes, so seen_hashes/
        processed_publications never need locking.
        """

        processed_publications: list[ProcessedPublication] = []
        seen_hashes: set[str] = set()
        total = len(sources)
        completed = 0

        with ThreadPoolExecutor(max_workers=self.SOURCE_CONCURRENCY) as executor:

            futures = {
                executor.submit(self._collect_source, source, date_filter): source
                for source in sources
            }

            for future in as_completed(futures):

                publications = future.result()

                for publication in publications:

                    content_hash = publication.content_hash()

                    if content_hash in seen_hashes:
                        continue

                    seen_hashes.add(content_hash)

                    processed = ProcessedPublication(
                        publication=publication
                    )

                    for processor in self.processors:
                        processed.extend_results(
                            processor.process(publication)
                        )

                    processed_publications.append(processed)

                completed += 1

                if on_progress:
                    on_progress(completed, total)

        for output in self.outputs:
            output.export(processed_publications)

        return processed_publications

    def _collect_source(self, source: Source, date_filter: dict | None):
        """
        Collects and date-filters publications for a single source.
        Runs inside a worker thread (see run()) - no shared state is
        touched here.
        """

        provider = self.providers.get(source.provider)

        if provider is None:
            raise ValueError(
                f"No provider registered for '{source.provider}'."
            )

        publications = provider.collect(source)

        return self.filter_by_date(publications, date_filter)

    # Relative periods map straight to how far back "now" the limit sits.
    RELATIVE_PERIODS = {
        "24h": timedelta(hours=24),
        "7_days": timedelta(days=7),
        "30_days": timedelta(days=30),
    }

    def filter_by_date(
        self,
        publications,
        date_filter,
    ):
        """
        Filters publications according to the selected period.

        A publication whose date couldn't be extracted is kept by
        default rather than dropped: most institutional/government
        sources expose no machine-readable publish date at all, and
        silently excluding everything from them - regardless of whether
        it actually matched a keyword - defeats the point of monitoring
        them. The date filter narrows down publications we *can* place
        in time; it isn't a relevance filter.

        The one exception is `publication.is_static_reference` (a FAQ,
        "transparência"/"governança" page, terms of use, ...) - that
        flag means the page is undated *by nature*, not because a
        Provider merely failed to find its date, so keeping it in every
        date-filtered search regardless of period would be misleading
        rather than a safety margin. Those are excluded once a specific
        period is requested, same as anything genuinely outside the
        range.
        """

        if not date_filter:
            return publications

        period = date_filter.get("period")

        if period in self.RELATIVE_PERIODS:

            now = datetime.now(timezone.utc)
            limit = now - self.RELATIVE_PERIODS[period]

            return [
                publication
                for publication in publications
                if self._on_or_after(publication, limit)
            ]

        if period == "custom":

            start = date_filter.get("start_date")
            end = date_filter.get("end_date")

            if not start or not end:
                return publications

            start_date = datetime.strptime(
                start, "%d/%m/%Y"
            ).replace(tzinfo=timezone.utc)

            end_date = datetime.strptime(
                end, "%d/%m/%Y"
            ).replace(tzinfo=timezone.utc)

            # include the entire final day
            end_date = end_date.replace(hour=23, minute=59, second=59)

            return [
                publication
                for publication in publications
                if self._within_range(publication, start_date, end_date)
            ]

        return publications

    def _on_or_after(self, publication, limit) -> bool:

        normalized = self.normalize_datetime(publication.publication_date)

        if normalized is None:
            return not publication.is_static_reference

        return normalized >= limit

    def _within_range(self, publication, start, end) -> bool:

        normalized = self.normalize_datetime(publication.publication_date)

        if normalized is None:
            return not publication.is_static_reference

        return start <= normalized <= end

    def normalize_datetime(
        self,
        value: datetime | None,
    ) -> datetime | None:

        if value is None:
            return None

        if value.tzinfo is None:

            return value.replace(
                tzinfo=timezone.utc
            )

        return value.astimezone(
            timezone.utc
        )