"""
wppsender/send_clipping.py

Sends the current clipping to one specific WhatsApp group via Selenium,
pasting into WhatsApp Web's own compose box exactly like a person would.

Deliberately minimal - no Postgres, no contact list, no batching, no
report generation, none of what wppsender/main.py + envio_funcoes.py (the
older mass-send automation this reuses Selenium mechanics from) did. Just:
read the clipping text -> open the group -> paste -> send.

The clipping text is rebuilt from output/results.json (the same data the
other four Clipping implementations - interface/tabs/clipping.py,
interface_qt/clipping_tab.py, outputs/whatsapp.py, interface_web/app.py's
/clipping route - format identically) via ProcessedPublication.from_dict,
so this always reflects whatever the last monitoring run actually found.

First run: WhatsApp Web will show a QR code to link the device - scan it
once with the phone that should send the messages. --user-data-dir below
persists that login, so later runs won't ask again.

Usage:
    python wppsender/send_clipping.py
        rebuilds the text from output/results.json (the shared file the
        last monitoring run - any interface - wrote)

    python wppsender/send_clipping.py --file caminho/para/texto.txt
        sends that file's contents verbatim instead - used by
        interface_web/app.py's "Enviar pro WhatsApp" button, so it sends
        exactly what that session's Clipping tab is showing rather than
        whatever's currently in the shared results.json
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime
from pathlib import Path
from time import sleep

import pyperclip
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.wait import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from core.processed_publication import ProcessedPublication  # noqa: E402

RESULTS_FILE = PROJECT_ROOT / "output" / "results.json"

# The group's direct-open link (web.whatsapp.com's own "accept" URL, not
# the chat.whatsapp.com marketing/redirect domain) - if the WhatsApp
# account running this script is already a member, this is expected to
# go straight to the existing conversation rather than showing a "join"
# screen.
GROUP_LINK = "https://web.whatsapp.com/accept?code=KBHiU8lahcYBgegWykdsBK&utm_campaign=wa_chat_v2"

CHROME_PROFILE_DIR = Path(__file__).resolve().parent / "chrome_profile"

LOAD_TIMEOUT = 90  # generous - covers a first-run QR-code scan


# ------------------------------------------------------------------
# Clipping text (same grouping/formatting as the other 4 implementations)
# ------------------------------------------------------------------

def build_clipping_text() -> str:
    if not RESULTS_FILE.exists():
        raise FileNotFoundError(
            f"{RESULTS_FILE} não existe - rode um monitoramento antes "
            "(pela interface web ou desktop) para gerar resultados."
        )

    data = json.loads(RESULTS_FILE.read_text(encoding="utf-8"))
    processed_publications = [ProcessedPublication.from_dict(item) for item in data]

    categories: dict[str, dict] = {}

    for processed in processed_publications:

        summary = ""
        for result in processed.results:
            if result.type == "summary":
                summary = result.value

        for result in processed.keyword_results():

            category = (
                result.metadata.get("category")
                or processed.publication.category
                or "Outros Temas"
            )
            emoji = result.metadata.get("emoji", "📌")

            bucket = categories.setdefault(category, {"emoji": emoji, "items": []})
            bucket["items"].append({
                "title": processed.publication.title,
                "source": processed.publication.source_name,
                "url": processed.publication.url,
                "summary": summary,
            })

    lines = [
        "📌 *Clipping – Radar Gualaxo*",
        f"📅 *{datetime.now().strftime('%d/%m/%Y')}*",
        "",
    ]

    for category, bucket in categories.items():
        lines.append(f"{bucket['emoji']} *{category}*")
        lines.append("")
        for item in bucket["items"]:
            lines.append(f"• {item['title']}")
            lines.append(f"   o Veículo: {item['source']}")
            lines.append(f"   o Link: {item['url']}")
            if item["summary"]:
                lines.append(f"   o Resumo: {item['summary']}")
            lines.append("")

    return "\n".join(lines)


# ------------------------------------------------------------------
# Selenium (mirrors envio_funcoes.py's proven abrir_conversa/enviar_item)
# ------------------------------------------------------------------

def open_group(driver) -> None:
    driver.get(GROUP_LINK)

    WebDriverWait(driver, LOAD_TIMEOUT).until(
        EC.presence_of_element_located((By.XPATH, "//footer"))
    )

    sleep(3)

    WebDriverWait(driver, LOAD_TIMEOUT).until(
        EC.presence_of_element_located((By.XPATH, '//div[@contenteditable="true"]'))
    )


def send_text(driver, texto: str) -> None:
    campo = WebDriverWait(driver, LOAD_TIMEOUT).until(
        EC.presence_of_element_located(
            (By.XPATH, '//div[@contenteditable="true"][@data-tab="10"]')
        )
    )

    pyperclip.copy(texto)
    campo.click()
    sleep(2)
    campo.send_keys(Keys.CONTROL, "v")
    sleep(2)
    campo.send_keys(Keys.ENTER)


# ------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--file",
        type=Path,
        default=None,
        help="Envia o conteúdo desse arquivo em vez de reconstruir a partir de output/results.json.",
    )
    args = parser.parse_args()

    if args.file is not None:
        texto = args.file.read_text(encoding="utf-8")
    else:
        texto = build_clipping_text()

    print(f"Clipping montado: {len(texto)} caracteres.")
    print("-" * 60)
    print(texto[:400])
    print("..." if len(texto) > 400 else "")
    print("-" * 60)

    options = Options()
    options.add_argument("--start-maximized")
    options.add_argument(f"--user-data-dir={CHROME_PROFILE_DIR}")
    options.add_argument("--profile-directory=Default")

    driver = webdriver.Chrome(options=options)

    try:
        print("Abrindo o grupo (se for a primeira vez, escaneie o QR code)...")
        open_group(driver)

        print("Enviando clipping...")
        send_text(driver, texto)

        sleep(3)
        print("Clipping enviado.")

    finally:
        sleep(5)
        driver.quit()


if __name__ == "__main__":
    main()
