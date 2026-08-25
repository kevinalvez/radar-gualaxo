"""
c_monitor

Application entry point.
"""

from config.keywords import load_keywords
from config.sources import load_sources

from core.pipeline import Pipeline

from processors.keyword import KeywordProcessor

from providers.rss import RSSProvider

from outputs.json import JsonOutput
from outputs.csv import CsvOutput

from interface_qt.app import start
from outputs.whatsapp import WhatsAppOutput


def main() -> None:

    print("=" * 60)
    print("Radar Gualaxo")
    print("=" * 60)

    sources = load_sources()

    if not sources:

        print("No sources configured.")
        return

    keywords = load_keywords()

    if not keywords:

        print("No keywords configured.")
        return

    providers = {
        "rss": RSSProvider(),
    }

    processors = [
        KeywordProcessor(keywords),
    ]

    outputs = [

        JsonOutput(
            "reports/results.json"
        ),

        CsvOutput(
            "reports/results.csv"
        ),

        WhatsAppOutput(
            "reports/clipping_whatsapp.txt"
        )

    ]

    pipeline = Pipeline(
        providers=providers,
        processors=processors,
        outputs=outputs,
    )

    processed = pipeline.run(
        sources=sources,
    )

    print()

    print(
        f"Processed publications: {len(processed)}"
    )

    print("Done.")


if __name__ == "__main__":

    start()