"""
integrations/green_api.py

Sends the clipping text to a WhatsApp group via Green API
(https://green-api.com) - a hosted, REST-based WhatsApp Web client.
Replaces wppsender/send_clipping.py's Selenium automation: same end
result (clipping text delivered to one fixed WhatsApp group), but a
plain HTTP call with no browser/display needed, so this runs fine from
Streamlit Community Cloud or a GitHub Actions runner.

Green API's free Developer plan is limited to 3 distinct chats/month
(see https://green-api.com/en/docs/about-tariffs/) - sending to a single
fixed group, as this project does, uses only one of those.

Needs three environment variables (see .env.example):
    GREEN_API_ID_INSTANCE  - the instance id from the Green API console
    GREEN_API_TOKEN        - the instance's API token
    GREEN_API_CHAT_ID      - the target chat id (a group id looks like
                              "120363041234567890@g.us", an individual
                              contact like "5531999999999@c.us")
"""

from __future__ import annotations

import os

import requests

API_BASE = "https://api.green-api.com"


class GreenApiError(RuntimeError):
    """Raised when Green API rejects a request or the required env vars are missing."""


def _config() -> tuple[str, str, str]:

    id_instance = os.environ.get("GREEN_API_ID_INSTANCE")
    token = os.environ.get("GREEN_API_TOKEN")
    chat_id = os.environ.get("GREEN_API_CHAT_ID")

    if not id_instance or not token or not chat_id:
        raise GreenApiError(
            "GREEN_API_ID_INSTANCE, GREEN_API_TOKEN e GREEN_API_CHAT_ID "
            "precisam estar configurados (.env local, Secrets do app no "
            "Streamlit Cloud, ou Secrets do repositório no GitHub Actions)."
        )

    return id_instance, token, chat_id


def send_whatsapp_message(text: str, chat_id: str | None = None) -> dict:
    """
    Sends `text` to the configured WhatsApp chat (or `chat_id`, overriding
    GREEN_API_CHAT_ID for this one call). Returns Green API's parsed JSON
    response (carries its own idMessage on success). Raises GreenApiError
    on a non-2xx response or missing configuration.
    """

    id_instance, token, default_chat_id = _config()

    url = f"{API_BASE}/waInstance{id_instance}/sendMessage/{token}"

    response = requests.post(
        url,
        json={
            "chatId": chat_id or default_chat_id,
            "message": text,
        },
        timeout=30,
    )

    if not response.ok:
        raise GreenApiError(
            f"Green API retornou {response.status_code}: {response.text}"
        )

    return response.json()
