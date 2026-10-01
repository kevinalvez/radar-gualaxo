from core.pipeline import Pipeline
from core.source import Source

from config.sources import load_sources

from providers.rss.provider import RSSProvider
from providers.html.provider import HTMLProvider
from processors.keyword import KeywordProcessor
from processors.summary import SummaryProcessor

from outputs.csv import CsvOutput
from outputs.json import JsonOutput


class MonitoringController:

    def __init__(
        self,
        configuration,
        logs,
        notebook,
        results,
        clipping,
    ):

        self.configuration = configuration
        self.logs = logs
        self.notebook = notebook
        self.results = results
        self.clipping = clipping

    # -----------------------------------------------------

    def run_monitor(self):

        keywords = (
            self.configuration
            .get_selected_keywords()
        )

        period = (
            self.configuration
            .get_selected_period()
        )

        if not keywords:

            self.logs.write(
                "Nenhuma keyword selecionada\n"
            )

            return

        self.logs.write(
            f"Keywords: {keywords}\n"
        )

        sources = self.build_sources()

        for source in sources:

            self.logs.write(
                f"SOURCE => {source.name} | "
                f"{source.provider} | "
                f"{source.url}\n"
            )

        self.logs.write(
            f"Sources carregadas: {len(sources)}\n"
        )

        pipeline = self.create_pipeline(
            keywords
        )

        try:

            self.logs.write(
                f"Executando pipeline com "
                f"{len(sources)} fontes\n"
            )

            processed = pipeline.run(
                sources,
                period
            )

            self.logs.write(
                f"Pipeline retornou "
                f"{len(processed)} publicações\n"
            )

            for item in processed:

                self.logs.write(
                    f"{item.publication.title} | "
                    f"{item.publication.publication_date} | "
                    f"resultados={len(item.results)}\n"
                )

            self.logs.write(
                f"Publicações processadas: "
                f"{len(processed)}\n"
            )

            self.results.show_results(
                processed
            )

            self.clipping.set_results(
                processed
            )

            self.notebook.select(
                self.results
            )

        except Exception as error:

            self.logs.write(
                f"Erro: {error}\n"
            )

    # -----------------------------------------------------

    def build_sources(self):

        configured = load_sources()

        sources = []

        for item in configured:

            if isinstance(item, dict):

                if not item.get(
                    "enabled",
                    True,
                ):
                    continue

                sources.append(
                    Source.from_dict(item)
                )

            else:

                sources.append(
                    Source(
                        name=item,
                        provider="rss",
                        url=item,
                    )
                )

        return sources

    # -----------------------------------------------------

    def create_pipeline(
        self,
        keywords,
    ):

        providers = {
            "rss": RSSProvider(),
            "html": HTMLProvider(),
        }

        processors = [
            KeywordProcessor(
                keywords
            ),
            SummaryProcessor()
        ]

        outputs = [

            # CsvOutput(
            #     "output/results.csv"
            # ),

            JsonOutput(
                "output/results.json"
            )

        ]

        return Pipeline(
            providers,
            processors,
            outputs,
        )

    # -----------------------------------------------------
