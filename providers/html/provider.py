"""
providers/html/provider.py

HTML Provider implementation.

Responsible for crawling HTML pages and converting them
into Publication objects.
"""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor, as_completed
import re

import requests

from bs4 import BeautifulSoup

from core.provider import Provider

from .discovery import LinkDiscovery
from datetime import datetime

from core.publication import Publication
from .extractor import ContentExtractor
from .cleaners import HTMLCleaner
from .filters import looks_like_static_reference

class HTMLProvider(Provider):

    """
    Collects publications from HTML websites.
    """

    DEFAULT_HEADERS = {

        "User-Agent": (

            "Mozilla/5.0 "

            "(Windows NT 10.0; Win64; x64) "

            "AppleWebKit/537.36 "

            "(KHTML, like Gecko) "

            "Chrome/138.0 Safari/537.36"

        )

    }

    def __init__(

        self,

        timeout: int = 20,

        max_pages: int = 60,

        page_concurrency: int = 8,

    ):
        """
        max_pages is a safety cap on how many candidate pages get
        downloaded per source per run, not a relevance filter -
        relevance/recency is handled downstream by Pipeline's
        date_filter. It can be overridden per source via
        source.config["max_pages"].

        page_concurrency caps how many of those pages are downloaded
        at once (moderate by default - fast enough to matter without
        hitting a single site with too many simultaneous requests).
        """

        self.timeout = timeout

        self.max_pages = max_pages

        self.page_concurrency = page_concurrency

        self.session = requests.Session()

        self.session.headers.update(

            self.DEFAULT_HEADERS

        )

        self.discovery = LinkDiscovery()

        self.cleaner = HTMLCleaner()
        
        self.extractor = ContentExtractor()

    # ------------------------------------------------------------------

    @property
    def name(self) -> str:
        """
        Provider identifier.
        """
        return "html"
    # ------------------------------------------------------------------

    def _download(
        self,
        url: str,
    ) -> BeautifulSoup | None:
        """
        Downloads an HTML page and returns a BeautifulSoup object.

        Returns None if the page cannot be downloaded.
        """

        try:

            response = self.session.get(
                url,
                timeout=self.timeout,
                allow_redirects=True,
            )

            response.raise_for_status()

            content_type = response.headers.get(
                "Content-Type",
                ""
            )

            if "text/html" not in content_type:
                return None

            # Charset declared in the HTTP header -> trust it. Otherwise hand
            # BeautifulSoup the raw bytes so it reads the page's own
            # <meta charset> (apparent_encoding guessed wrong on some
            # sites, e.g. CAPTA -> "organizaĂ§Ăľes").
            if "charset=" in content_type.lower():

                return BeautifulSoup(
                    response.text,
                    "html.parser",
                )

            return BeautifulSoup(
                response.content,
                "html.parser",
            )

        except Exception as e:
            print(f"[HTML] {url} -> {e}")
            return None

        # ------------------------------------------------------------------

    def collect(
        self,
        source,
    ):

        """
        Crawls a website and returns Publications.
        """

        publications = []

        home = self._download(
            source.url
        )

        if home is None:
            return publications

        links = self.discovery.discover(

            source.url,

            home,

        )

        if not links:

            links = [
                source.url
            ]

        max_pages = source.config.get(
            "max_pages",
            self.max_pages,
        )

        links = links[
            : max_pages
        ]

        links = list(dict.fromkeys(links))

        # Pages are independent downloads, so fetching several at once
        # (bounded by page_concurrency) cuts wall-clock time a lot
        # compared to one request at a time - requests.Session is safe
        # to share across threads for this.
        with ThreadPoolExecutor(max_workers=self.page_concurrency) as executor:

            futures = [
                executor.submit(self._collect_page, source, link)
                for link in links
            ]

            for future in as_completed(futures):

                publication = future.result()

                if publication is not None:

                    publications.append(
                        publication
                    )

        return publications

    # ------------------------------------------------------------------

    def _collect_page(

        self,

        source,

        url,

    ):

        soup = self._download(
            url
        )

        if soup is None:
            return None

        clean = self.cleaner.clean(
            soup
        )

        content_node, is_article = self.extractor.extract(clean, url)

        if content_node is None or not is_article:
            return None

        content = self._extract_text(content_node)

        publication_date = self._extract_publication_date(
            soup, content
        )

        if len(content) < 100:
            return None

        title = self._extract_title(
            soup,
            source,
        )

        # WordPress archive (category/tag listing) pages - "Arquivos
        # Guia BHAZ", "Meio Ambiente Arquivos - Portal Agro2" - slip past
        # the extractor's listing check on some themes.
        if self.ARCHIVE_TITLE_PATTERN.search(title):
            return None

        # Prefer the page's own category metadata; fall back to the
        # source's configured category (e.g. the topic tag assigned
        # when the source was registered) when the page doesn't
        # expose one - most institutional/government pages don't.
        category = self._extract_category(soup) or source.category

        publication = Publication(

            title=title,

            content=content,

            source_id=source.id,

            source_name=source.name,

            url=url,

            publication_date=publication_date,

            author=None,

            category=category,

            is_static_reference=looks_like_static_reference(url),
        )

        return publication

    # ------------------------------------------------------------------

    ARCHIVE_TITLE_PATTERN = re.compile(
        r"^Arquivos\s|\sArquivos(\s*[-–|»]|$)"
    )

    def _extract_title(

        self,

        soup,

        source,

    ):

        title = self._extract_meta_title(soup, source)

        # Some sites cut their own og:title/<title> at a fixed length
        # (O Brasilianista: 60 chars, "...no mercado brasile") while the
        # <h1> keeps the full headline - prefer the <h1> when it's that
        # same headline, just longer.
        h1 = soup.find("h1")

        if h1:

            headline = h1.get_text(" ", strip=True)
            prefix = title.rstrip(" .…")

            if (
                prefix
                and len(headline) > len(prefix)
                and headline.startswith(prefix)
            ):
                return headline

        return title

    def _extract_meta_title(

        self,

        soup,

        source,

    ):

        og = soup.find(

            "meta",

            property="og:title",

        )

        if og:

            value = og.get(
                "content"
            )

            # Checking truthiness before stripping isn't enough: a
            # whitespace-only value (e.g. "\n") is truthy as a raw
            # string but becomes empty once stripped, which used to
            # slip through here instead of falling through to the
            # next candidate below.
            if value and value.strip():
                return value.strip()

        if soup.title:

            value = soup.title.string

            if value and value.strip():

                return value.strip()

        h1 = soup.find("h1")

        if h1:

            value = h1.get_text(
                strip=True
            )

            if value:
                return value

        return source.name

    # ------------------------------------------------------------------

    # Block-level tags used to split extracted text into lines (see
    # _iter_block_texts). Inline tags (a, strong, em, span, ...) are
    # deliberately excluded: get_text("\n") inserts a newline between
    # *any* two tags, including an inline one naming an entity mid-
    # sentence (e.g. "...um Comitê Gestor, denominado <strong>Comitê
    # do Rio Doce</strong>, ao qual compete...") - which fragmented
    # that single sentence into three separate "lines" and broke both
    # keyword-match excerpts and the summary built from them.
    BLOCK_TAGS = (
        "p", "div", "li", "h1", "h2", "h3", "h4", "h5", "h6",
        "blockquote", "tr", "td", "th", "figcaption", "article",
        "section",
    )

    # Marker used to later split a block's text back apart at each
    # <br> - a WYSIWYG-authored block commonly uses <br> instead of
    # separate <p> tags for what's really two distinct lines (e.g. a
    # bold section label like "APRESENTAÇÃO" followed by "<br>" then
    # the actual paragraph, both inside one <p>). Unlike an inline
    # tag naming an entity mid-sentence, a <br> is exactly the DOM's
    # own signal that this is an intentional line break, so it's
    # honored as one here despite everything else inline being kept
    # joined. Unlikely to collide with real article text.
    BR_SPLIT_MARKER = "␞"

    def _iter_block_texts(self, node):
        """
        Yields one text chunk per block-level element actually
        holding text (a "leaf" - no nested block-level descendant,
        so a paragraph isn't yielded twice via its own wrapping div),
        further split at any <br> within it. Falls back to the whole
        node if it contains no block tag at all (e.g. bare text with
        only inline markup).
        """

        candidates = node.find_all(self.BLOCK_TAGS)

        if not candidates:

            for chunk in self._block_text(node):
                yield chunk

            return

        for element in candidates:

            if element.find(self.BLOCK_TAGS):
                continue

            for chunk in self._block_text(element):
                yield chunk

    def _block_text(self, element):

        for br in element.find_all("br"):
            br.replace_with(self.BR_SPLIT_MARKER)

        text = element.get_text(" ", strip=True)

        for chunk in text.split(self.BR_SPLIT_MARKER):

            chunk = chunk.strip()

            if chunk:
                yield chunk

    # ------------------------------------------------------------------

    def _extract_text(

        self,

        node,

    ):

        lines_source = list(
            self._iter_block_texts(node)
        )

        ignored = {

            "facebook",

            "instagram",

            "youtube",

            "linkedin",

            "twitter",

            "compartilhar",

            "tweetar",

            "curtir",

            "voltar",

            "menu",

            "pesquisar",

            "acesse",

            "clique aqui",

            # Instagram's own auto-generated embed caption (e.g. "Um
            # post compartilhado por Site X (@handle)") - boilerplate
            # from the embed widget itself, not the article's text.
            "compartilhado por",

            # Generic Brazilian news-site UI/footer boilerplate: a
            # comment-section prompt, a "related articles" section
            # header (whose actual teasers may carry an unrelated
            # keyword match if a site-specific structural removal
            # doesn't catch them), and a legal notice that often
            # repeats the outlet's own name/slogan right after it.
            "deixe um comentário",

            "leia também",

            "todos os direitos reservados",

            # Site-specific tagline (Diário do Rio Doce) describing
            # the outlet itself in the third person - narrower than
            # the generic phrases above, but still safe: this exact
            # wording would never appear as a real sentence inside an
            # article's own body text.
            "as notícias do vale do rio doce",

            # Audio-player widget boilerplate (e.g. BNDES's "áudio-
            # release" embed): the prompt/caption around the player
            # and the browser's own <audio> fallback text, none of
            # which describes the actual news.
            "ouça aqui o áudio-release",

            "your browser does not support the audio element",

        }

        # Byline/date/reading-time metadata line (e.g. "Publicado em
        # 14/07/2026 às 11:02", "Atualizado em ...", "6 min de
        # leitura") - always a short standalone line right after the
        # headline, never the start of real article prose.
        ignored_prefixes = (

            "publicado em",

            "atualizado em",

        )

        lines = []

        visited = set()

        for line in lines_source:

            line = " ".join(
                line.split()
            )

            # Joining an inline tag's text back into its surrounding
            # sentence with a plain space (see _iter_block_texts)
            # leaves a stray space before any punctuation that
            # immediately followed it in the source (e.g. "Restaura
            # Rio Doce , lançado" instead of "Restaura Rio Doce,
            # lançado") - harmless to the text's meaning, but not how
            # the sentence actually reads.
            line = re.sub(r"\s+([,.;:!?])", r"\1", line)

            if len(line) < 5:
                continue

            # Copyright/legal notice lines (e.g. "© 2023 Site Name")
            # essentially never appear in genuine article prose, and
            # commonly repeat the outlet's own name - which can
            # collide with an unrelated keyword just because it
            # happens to be part of the site's brand name.
            if "©" in line:
                continue

            # Footer-style lines (e.g. "| As notícias do Vale do Rio
            # Doce." or "| Todos os direitos reservados.") often carry
            # the same risk (site tagline/legal text) without a "©"
            # symbol. Real article prose never starts a line with a
            # bare pipe character, so this is a safe, generic tell.
            if line.startswith("|"):
                continue

            lower = line.lower()

            if lower.startswith(ignored_prefixes):
                continue

            # "X min de leitura" (a reading-time estimate widget) -
            # matched as a whole-line pattern rather than a substring
            # so it can't collide with the word "leitura" appearing
            # naturally inside real prose.
            if re.fullmatch(r"\d+\s*min\s+de\s+leitura", lower):
                continue

            if any(word in lower for word in ignored):
                continue

            if line in visited:
                continue

            visited.add(
                line
            )

            lines.append(
                line
            )

        return "\n".join(lines[:300])

    # ------------------------------------------------------------------

    # Trigger words that mean "this is when the piece was published/
    # launched", used only to find the right LINE to look for a date
    # in - not matched against the date itself. Deliberately excludes
    # words like "prazo"/"divulgação dos selecionados" that name a
    # *different* date (a deadline, a results-announcement date) that
    # would be wrong to report as when the page itself was published.
    DATE_TRIGGER_WORDS = ("publicado", "publicação", "lançamento", "divulgado")

    MONTH_NAMES = {
        "janeiro": 1, "fevereiro": 2, "março": 3, "abril": 4,
        "maio": 5, "junho": 6, "julho": 7, "agosto": 8,
        "setembro": 9, "outubro": 10, "novembro": 11, "dezembro": 12,
    }

    LONG_DATE_PATTERN = re.compile(
        r"(\d{1,2})\s+de\s+([a-zçã]+)\s+de\s+(\d{4})", re.IGNORECASE
    )
    SHORT_DATE_PATTERN = re.compile(r"(\d{2})/(\d{2})/(\d{4})")

    def _extract_date_from_text(self, content):
        """
        Fallback for pages with no <meta>/<time> date at all, but that
        do state their own publish/launch date in visible text (e.g.
        an edital's "Lançamento do edital: 26 de julho de 2024") -
        common on institutional sites that don't expose the usual
        article metadata. Only lines naming DATE_TRIGGER_WORDS are
        checked, so a date mentioned elsewhere in the body text (an
        unrelated historical event, a deadline) isn't mistaken for the
        page's own publish date.
        """

        for line in content.split("\n"):

            lower = line.lower()

            if not any(word in lower for word in self.DATE_TRIGGER_WORDS):
                continue

            match = self.LONG_DATE_PATTERN.search(line)

            if match:

                day, month_name, year = match.groups()
                month = self.MONTH_NAMES.get(month_name.lower())

                if month:

                    try:
                        return datetime(int(year), month, int(day))
                    except ValueError:
                        pass

            match = self.SHORT_DATE_PATTERN.search(line)

            if match:

                day, month, year = match.groups()

                try:
                    return datetime(int(year), int(month), int(day))
                except ValueError:
                    pass

        return None

    def _extract_publication_date(
        self,
        soup,
        content: str = "",
    ):

        meta = soup.find(
            "meta",
            property="article:published_time"
        )

        if meta:

            value = meta.get(
                "content"
            )

            if value:

                try:
                    return datetime.fromisoformat(
                        value.replace(
                            "Z",
                            "+00:00"
                        )
                    )

                except Exception:
                    pass

        time_tag = soup.find("time")

        if (
            time_tag
            and time_tag.get("datetime")
        ):

            try:

                return datetime.fromisoformat(
                    time_tag["datetime"]
                )

            except Exception:
                pass

        return self._extract_date_from_text(content)

    # ------------------------------------------------------------------

    def _extract_category(
        self,
        soup,
    ):

        meta = soup.find(
            "meta",
            property="article:section"
        )

        if meta:

            value = meta.get(
                "content"
            )

            # WordPress' default "Uncategorized" says nothing - let the
            # caller fall back to the source's own configured category.
            if value and value.strip().lower() not in (
                "uncategorized",
                "sem categoria",
            ):
                return value.strip()

        return None