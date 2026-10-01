"""
interface_streamlit/app.py

Streamlit interface - reuses core/, providers/, processors/, outputs/,
config/ and integrations/ unchanged, same principle interface_web/ and
interface_qt/ already follow: only this presentation layer is new.

Run locally:
    streamlit run interface_streamlit/app.py

Secrets (DATABASE_URL, GREEN_API_*) come from Streamlit's own secrets
mechanism - a local .streamlit/secrets.toml, or the Secrets panel on
Streamlit Community Cloud - copied into os.environ once, below, before
config/db.py or integrations/green_api.py ever read them. Those modules
only ever look at plain environment variables, so they work the same way
whether this app, scripts/run_scheduled.py (GitHub Actions) or a plain
.env (local dev) is what set them.
"""

from __future__ import annotations

import os
import sys
from datetime import date, datetime, timedelta
from pathlib import Path

import streamlit as st

# `streamlit run interface_streamlit/app.py` only puts this file's own
# folder on sys.path, not the repo root - without this, config/, core/,
# providers/ etc. aren't importable (ModuleNotFoundError on Streamlit Cloud).
_ROOT = str(Path(__file__).resolve().parent.parent)
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

# st.secrets is lazy - a missing secrets.toml only raises on first key
# access, so the whole loop has to be inside the try (falls back to .env).
try:
    for _key in ("DATABASE_URL", "GREEN_API_ID_INSTANCE", "GREEN_API_TOKEN", "GREEN_API_CHAT_ID"):
        if _key in st.secrets and _key not in os.environ:
            os.environ[_key] = str(st.secrets[_key])
except Exception:
    pass

from config.keywords import add_keyword, load_keywords, remove_keyword
from config.schedule import load_schedule, save_schedule
from config.sources import add_source, load_sources, remove_source, update_source
from core.pipeline import Pipeline
from core.source import Source
from integrations.green_api import GreenApiError, send_whatsapp_message
from outputs.whatsapp import WhatsAppOutput
from processors.keyword import KeywordProcessor
from processors.summary import SummaryProcessor
from providers.html.provider import HTMLProvider
from providers.rss.provider import RSSProvider

st.set_page_config(page_title="Radar Gualaxo", page_icon="📡", layout="wide")

PERIOD_LABELS = {
    "24h": "Últimas 24 horas",
    "7_days": "Últimos 7 dias",
    "30_days": "Últimos 30 dias",
    "custom": "Período específico",
}


def _create_pipeline(keywords: list[str]) -> Pipeline:

    providers = {"rss": RSSProvider(), "html": HTMLProvider()}
    processors = [KeywordProcessor(keywords), SummaryProcessor()]

    return Pipeline(providers, processors, outputs=[])


def _period_picker(key_prefix: str, default_period: str = "7_days") -> dict:
    """
    Renders the period radio + (when "custom" is picked) two date
    inputs, and returns a Pipeline-ready date_filter dict - shared by the
    Busca and Agendamento tabs, same options both already had in
    interface_web/app.py.
    """

    period = st.radio(
        "Período",
        options=list(PERIOD_LABELS),
        format_func=lambda value: PERIOD_LABELS[value],
        index=list(PERIOD_LABELS).index(default_period),
        key=f"{key_prefix}_period",
        horizontal=True,
    )

    if period != "custom":
        return {"period": period}

    today = date.today()

    col1, col2 = st.columns(2)

    with col1:
        start = st.date_input("Data inicial", value=today - timedelta(days=7), key=f"{key_prefix}_start")

    with col2:
        end = st.date_input("Data final", value=today, key=f"{key_prefix}_end")

    return {
        "period": "custom",
        "start_date": start.strftime("%d/%m/%Y"),
        "end_date": end.strftime("%d/%m/%Y"),
    }


st.title("📡 Radar Gualaxo")


@st.cache_data(ttl=30, show_spinner=False)
def _load_sources_cached() -> list[dict]:
    return load_sources()


@st.cache_data(ttl=30, show_spinner=False)
def _load_keywords_cached() -> list[str]:
    return load_keywords()


def _invalidate_config_cache() -> None:
    """Call after any add/remove/update so the next rerun shows it immediately."""
    _load_sources_cached.clear()
    _load_keywords_cached.clear()


tab_busca, tab_resultados, tab_clipping, tab_config, tab_agendamento = st.tabs(
    ["Busca", "Resultados", "Clipping", "Configuração", "Agendamento"]
)

all_sources = _load_sources_cached()
all_keywords = _load_keywords_cached()
enabled_sources = [source for source in all_sources if source.get("enabled", True)]

# ----------------------------------------------------------------------
# Busca
# ----------------------------------------------------------------------
with tab_busca:

    selected_keywords = st.multiselect(
        "Keywords", options=all_keywords, default=all_keywords
    )

    source_rows = [
        {
            "Selecionar": True,
            "Nome": source["name"],
            "Categoria": source.get("category") or "",
            "URL": source["url"],
        }
        for source in enabled_sources
    ]

    edited_rows = st.data_editor(
        source_rows,
        hide_index=True,
        use_container_width=True,
        disabled=["Nome", "Categoria", "URL"],
        column_config={"Selecionar": st.column_config.CheckboxColumn()},
    )

    date_filter = _period_picker("busca")

    if st.button("▶️ Executar", type="primary"):

        selected_names = {row["Nome"] for row in edited_rows if row["Selecionar"]}
        sources = [Source.from_dict(s) for s in enabled_sources if s["name"] in selected_names]

        if not selected_keywords:
            st.error("Selecione ao menos uma keyword.")
        elif not sources:
            st.error("Selecione ao menos uma fonte.")
        else:
            progress = st.progress(0.0, text="Iniciando...")

            def _on_progress(done, total):
                progress.progress(done / total, text=f"{done}/{total} fontes processadas")

            with st.spinner("Coletando e processando publicações..."):
                pipeline = _create_pipeline(selected_keywords)
                processed = pipeline.run(sources, date_filter=date_filter, on_progress=_on_progress)

            matched = [item for item in processed if item.keyword_results()]

            st.session_state["processed"] = processed
            st.session_state["matched"] = matched

            progress.empty()
            st.success(f"Concluído: {len(matched)} publicações com match, de {len(processed)} coletadas.")

# ----------------------------------------------------------------------
# Resultados
# ----------------------------------------------------------------------
with tab_resultados:

    matched = st.session_state.get("matched")

    if not matched:
        st.info("Rode uma busca na aba Busca primeiro.")
    else:
        rows = []

        for item in matched:
            kw_results = item.keyword_results()
            summary = next((r.value for r in item.results if r.type == "summary"), "")
            category = kw_results[0].metadata.get("category") or item.publication.category or "Outros Temas"

            rows.append({
                "Título": item.publication.title,
                "Veículo": item.publication.source_name,
                "Categoria": category,
                "Data": item.publication.publication_date.strftime("%d/%m/%Y %H:%M")
                if item.publication.publication_date else "",
                "Keywords": ", ".join(sorted({r.value for r in kw_results})),
                "Resumo": summary,
                "Link": item.publication.url,
            })

        st.dataframe(rows, use_container_width=True, hide_index=True)

# ----------------------------------------------------------------------
# Clipping
# ----------------------------------------------------------------------
with tab_clipping:

    matched = st.session_state.get("matched")

    if not matched:
        st.info("Rode uma busca na aba Busca primeiro.")
    else:
        clipping_text = WhatsAppOutput(target="").build_message(matched)

        st.text_area("Texto do clipping", value=clipping_text, height=400)

        col1, col2 = st.columns(2)

        with col1:
            st.download_button(
                "⬇️ Baixar .txt",
                data=clipping_text,
                file_name=f"clipping-{datetime.now().strftime('%Y-%m-%d')}.txt",
            )

        with col2:
            if st.button("📲 Enviar pro WhatsApp (Green API)"):
                try:
                    send_whatsapp_message(clipping_text)
                    st.success("Clipping enviado.")
                except GreenApiError as error:
                    st.error(str(error))

# ----------------------------------------------------------------------
# Configuração
# ----------------------------------------------------------------------
with tab_config:

    col_sources, col_keywords = st.columns(2)

    with col_sources:
        st.subheader("Fontes")

        st.dataframe(
            [
                {
                    "Nome": s["name"],
                    "Provider": s["provider"],
                    "Categoria": s.get("category") or "",
                    "Habilitada": s.get("enabled", True),
                    "URL": s["url"],
                }
                for s in all_sources
            ],
            use_container_width=True,
            hide_index=True,
        )

        with st.form("add_source_form", clear_on_submit=True):
            st.markdown("**Adicionar fonte**")
            name = st.text_input("Nome")
            url = st.text_input("URL")
            provider = st.selectbox("Provider", ["rss", "html"])
            category = st.text_input("Categoria")
            description = st.text_input("Descrição")

            if st.form_submit_button("Adicionar"):
                if name and url:
                    add_source({
                        "name": name,
                        "provider": provider,
                        "url": url,
                        "enabled": True,
                        "category": category,
                        "description": description,
                    })
                    _invalidate_config_cache()
                    st.rerun()
                else:
                    st.error("Nome e URL são obrigatórios.")

        source_names = [s["name"] for s in all_sources]

        if source_names:
            with st.form("manage_source_form"):
                st.markdown("**Gerenciar fonte existente**")
                target_name = st.selectbox("Fonte", source_names)
                target = next(s for s in all_sources if s["name"] == target_name)
                new_enabled = st.checkbox("Habilitada", value=target.get("enabled", True))

                remove_col, save_col = st.columns(2)
                save_clicked = save_col.form_submit_button("Salvar")
                remove_clicked = remove_col.form_submit_button("Remover", type="secondary")

                if save_clicked:
                    update_source(target_name, {**target, "enabled": new_enabled})
                    _invalidate_config_cache()
                    st.rerun()

                if remove_clicked:
                    remove_source(target_name)
                    _invalidate_config_cache()
                    st.rerun()

    with col_keywords:
        st.subheader("Keywords")

        st.dataframe({"Keyword": all_keywords}, use_container_width=True, hide_index=True)

        with st.form("add_keyword_form", clear_on_submit=True):
            new_keyword = st.text_input("Nova keyword")

            if st.form_submit_button("Adicionar"):
                if new_keyword:
                    add_keyword(new_keyword)
                    _invalidate_config_cache()
                    st.rerun()

        if all_keywords:
            with st.form("remove_keyword_form"):
                keyword_to_remove = st.selectbox("Remover keyword", all_keywords)

                if st.form_submit_button("Remover"):
                    remove_keyword(keyword_to_remove)
                    _invalidate_config_cache()
                    st.rerun()

# ----------------------------------------------------------------------
# Agendamento
# ----------------------------------------------------------------------
with tab_agendamento:

    st.caption(
        "O horário/periodicidade de disparo é definido no cron do GitHub "
        "Actions (.github/workflows/orquestracao.yml). Aqui você escolhe "
        "só O QUE uma execução automática roda: quais keywords, quais "
        "fontes e qual período de busca."
    )

    schedule = load_schedule()

    with st.form("schedule_form"):

        schedule_keywords = st.multiselect(
            "Keywords", options=all_keywords, default=schedule.get("keywords") or []
        )

        schedule_source_names = st.multiselect(
            "Fontes",
            options=[s["name"] for s in enabled_sources],
            default=schedule.get("sources") or [],
        )

        schedule_date_filter = _period_picker(
            "agendamento", default_period=schedule.get("period") or "7_days"
        )

        if st.form_submit_button("💾 Salvar agendamento"):
            save_schedule({
                **schedule,
                "keywords": schedule_keywords,
                "sources": schedule_source_names,
                **schedule_date_filter,
            })
            st.success("Agendamento salvo.")
            st.rerun()
