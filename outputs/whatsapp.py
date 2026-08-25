"""
outputs/whatsapp.py

WhatsApp friendly clipping output.

Generates formatted text ready to copy and paste into WhatsApp.
"""

from __future__ import annotations

from datetime import datetime
from pathlib import Path

from core.output import Output
from core.processed_publication import ProcessedPublication


class WhatsAppOutput(Output):
    """
    Generates a WhatsApp formatted clipping report.
    """

    @property
    def name(self) -> str:
        return "whatsapp"

    # -------------------------------------------------------------

    @property
    def description(self) -> str:
        return (
            "Generates formatted clipping text "
            "compatible with WhatsApp."
        )

    # -------------------------------------------------------------

    def export(
        self,
        processed_publications: list[ProcessedPublication],
    ) -> None:

        self._ensure_directory()

        content = self._build_message(
            processed_publications
        )

        with open(
            self.target,
            "w",
            encoding="utf-8",
        ) as file:

            file.write(content)

    # -------------------------------------------------------------

    def _build_message(
        self,
        publications,
    ):

        today = datetime.now()

        lines = []


        lines.append(
            "📌 *Clipping – Radar Gualaxo*"
        )

        lines.append(
            f"📅 *{today.strftime('%d/%m/%Y')}*"
        )

        lines.append("")


        categories = {}


        for processed in publications:

            publication = processed.publication


            for result in processed.keyword_results():

                category = (
                    result.metadata.get("category")
                    or publication.category
                    or "Outros Temas"
                )

                emoji = result.metadata.get(
                    "emoji",
                    "📌"
                )


                if category not in categories:

                    categories[category] = {
                        "emoji": emoji,
                        "items": []
                    }


                categories[category]["items"].append(
                    {
                        "title": publication.title,
                        "source": publication.source_name,
                        "url": publication.url
                    }
                )


        for category, data in categories.items():


            lines.append(
                f"{data['emoji']} *{category}*"
            )

            lines.append("")


            for item in data["items"]:


                lines.append(
                    f"• {item['title']}"
                )

                lines.append(
                    f"   o Veículo: {item['source']}"
                )

                lines.append(
                    f"   o Link: {item['url']}"
                )

                lines.append("")


        return "\n".join(lines)

    # -------------------------------------------------------------

    def _ensure_directory(self):

        Path(
            self.target
        ).parent.mkdir(
            parents=True,
            exist_ok=True
        )