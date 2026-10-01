"""
providers/html/filters.py

Utilities for validating and filtering discovered URLs.
"""

from __future__ import annotations

import re
from urllib.parse import urlparse


IGNORED_SCHEMES = {
    "mailto",
    "javascript",
    "tel",
}


IGNORED_EXTENSIONS = {
    ".pdf",
    ".zip",
    ".rar",
    ".7z",
    ".jpg",
    ".jpeg",
    ".png",
    ".gif",
    ".svg",
    ".mp4",
    ".mp3",
    ".xls",
    ".xlsx",
    ".doc",
    ".docx",
    ".ppt",
    ".pptx",
}


IGNORED_PATHS = {

    "/login",
    "/logout",
    "/contato",
    "/contatos",
    "/contato/",
    "/facebook",
    "/instagram",
    "/twitter",
    "/linkedin",
    "/youtube",

}


# Paths that point to listing/index pages rather than individual articles.
LISTING_PATH_PREFIXES = {
    "/categoria",
    "/category",
    "/tag",
    "/tags",
    "/autor",
    "/author",
    "/busca",
    "/search",
    "/newsletter",
    "/assine",
    "/assinatura",
    "/cadastro",
    "/sobre",
    "/about",
    "/termos",
    "/privacidade",
    "/anuncie",
    "/publicidade",
    "/rss",
    "/feed",
    "/podcast",
    "/pagina",
    "/page",
}

# Matches a year/month(/day) segment typical of news article URLs,
# e.g. /2026/08/07/ or /2026/08/.
ARTICLE_DATE_PATTERN = re.compile(
    r"/(19|20)\d{2}/\d{1,2}(/\d{1,2})?(/|$)"
)


def is_valid_url(url: str) -> bool:

    """
    Returns True if the URL is worth crawling.
    """

    if not url:
        return False

    url = url.strip()

    if url == "#":
        return False

    parsed = urlparse(url)

    if parsed.scheme in IGNORED_SCHEMES:
        return False

    lower = url.lower()

    for ext in IGNORED_EXTENSIONS:

        if lower.endswith(ext):
            return False

    for path in IGNORED_PATHS:

        if parsed.path.startswith(path):
            return False

    return True


def same_domain(url: str, base_url: str) -> bool:
    """
    Returns True if url and base_url share the same domain.
    """

    return (
        urlparse(url).netloc.lower()
        == urlparse(base_url).netloc.lower()
    )


def _top_level_segment(url: str) -> str:

    segments = urlparse(url).path.strip("/").split("/")

    return segments[0] if segments else ""


def same_section(url: str, base_url: str) -> bool:
    """
    Returns True if url shares the same top-level path segment
    (site section) as base_url, e.g. both under "/valedoaco/".

    News sites commonly mix links from unrelated sections (sports,
    economy...) into a section page's link soup; those links can
    still look like articles by URL shape, so this is used to give
    same-section links priority over merely article-shaped ones.
    """

    base_section = _top_level_segment(base_url)

    if not base_section:
        return False

    return _top_level_segment(url) == base_section


def is_listing_path(path: str) -> bool:
    """
    Returns True if path looks like an index/listing page
    (category, tag, author, search, ...) rather than an article.

    Matches on the first path segment only (e.g. "/tag/rio-doce"
    matches "/tag"), not a raw string prefix - a plain startswith()
    would also match a genuine article slug that happens to begin
    with the same letters, e.g. "/newsletter-sobre-o-acordo-do-rio-doce"
    incorrectly matching "/newsletter".
    """

    segments = path.strip("/").split("/")
    first_segment = f"/{segments[0].lower()}" if segments and segments[0] else ""

    return first_segment in LISTING_PATH_PREFIXES


def looks_like_article(url: str) -> bool:
    """
    Heuristic that returns True if url looks like an individual
    article page rather than a listing/section page.

    Considered article-like when the path contains a date segment
    (common in news URLs) or when its last segment is a long,
    hyphen-separated slug (typical of a slugified headline).
    """

    parsed = urlparse(url)
    path = parsed.path

    if is_listing_path(path):
        return False

    if ARTICLE_DATE_PATTERN.search(path):
        return True

    last_segment = path.rstrip("/").rsplit("/", 1)[-1]

    return last_segment.count("-") >= 3


# Splits a URL into path/query "words" - literal "/" plus its
# URL-encoded form (some CMS platforms, e.g. an IBM WebSphere Portal
# site, route through a query string like
# "...?urile=wcm%3apath%3a%2Fhome%2Ftransparencia%2Fgovernanca" instead
# of a clean REST-ish path, so the marker word only shows up between
# %2F-encoded separators, not urlparse(url).path segments).
_URL_WORD_SPLIT = re.compile(r"[/?&=:.]|%2f", re.IGNORECASE)

# Reference/institutional content that's undated by nature (not a
# Provider failing to find a date) - a FAQ or "governança" page
# describes something ongoing, it isn't "news published on day X".
# Matched as a whole word between URL separators, not a raw substring
# search, so a real headline slug that happens to contain one of these
# as part of a longer compound word (e.g.
# ".../nova-lei-de-governanca-corporativa") isn't caught by accident.
#
# Deliberately excludes "transparencia": on BNDES's own site it's the
# name of the *entire section* every Fundo Rio Doce page lives under
# (including genuinely dated content like an edital), not a marker of
# any specific page's type - matching it flagged real dated pages as
# static reference right along with the actual FAQ/overview ones.
STATIC_REFERENCE_URL_MARKERS = {
    "perguntas-frequentes",
    "faq",
    "governanca",
    "ferramentas-ministerios",
    "termos-de-uso",
    "termo-de-uso",
    "politica-de-privacidade",
    "quem-somos",
}


# Site utility/institutional pages that are never news, whatever keyword
# their header/footer happens to contain (e.g. a city hall's "Hino e
# Bandeira" page matching "Mariana" just from the site's own name).
# Matched as whole URL words like STATIC_REFERENCE_URL_MARKERS, so
# "/m9auth/login" is caught too (IGNORED_PATHS only checks the start of
# the path).
UTILITY_URL_MARKERS = {
    "login",
    "logout",
    "cadastro",
    "assine",
    "newsletter",
    "privacidade",
    "politica-de-privacidade",
    "politica-de-cookies",
    "cookies",
    "termos",
    "termos-de-uso",
    "termo-de-uso",
    "politica-de-privacidade-e-termo-de-uso",
    "politica-anticorrupcao",
    "sobre",
    "sobre-nos",
    "quem-somos",
    "expediente",
    "anuncie",
    "publicidade",
    "seja-um-colunista",
    "fale-conosco",
    "contato",
    "contatos",
    "trabalhe-conosco",
    "acessibilidade",
    # Common fixed pages of Brazilian city hall portals.
    "hino-e-bandeira",
    "telefones-uteis",
    "dados-demograficos",
    "nota-fiscal-eletronica",
    "portal-do-contribuinte",
    "todos-distritos",
}

# "/page/124/", "/pagina/3" - pagination of a listing, never an article.
PAGINATION_PATTERN = re.compile(r"/(page|pagina)/\d+(/|$)", re.IGNORECASE)

# A single, hyphen-free, purely alphabetic path segment ("/esportes",
# "/cidades", "/historico", "/secretarias") is a site section or fixed
# page, not a slugified headline.
SECTION_PATH_PATTERN = re.compile(r"/[a-zà-ú]+/?", re.IGNORECASE)


def is_non_content_url(url: str) -> bool:
    """
    Returns True if a discovered link can be skipped outright: the site
    root, pagination, a section page or a utility/institutional page
    (see UTILITY_URL_MARKERS). Unlike is_listing_path(), which only
    lowers a link's crawl priority, these are never downloaded.
    """

    parsed = urlparse(url)
    path = parsed.path

    if path in ("", "/"):
        return True

    if PAGINATION_PATTERN.search(path):
        return True

    if not parsed.query and SECTION_PATH_PATTERN.fullmatch(path):
        return True

    words = _URL_WORD_SPLIT.split(url.lower())

    return any(word in UTILITY_URL_MARKERS for word in words)


def looks_like_static_reference(url: str) -> bool:
    """
    Returns True if the URL's own shape marks it as an inherently
    undated institutional/reference page (see STATIC_REFERENCE_URL_MARKERS)
    rather than a dated piece of content.
    """

    words = _URL_WORD_SPLIT.split(url.lower())

    return any(word in STATIC_REFERENCE_URL_MARKERS for word in words)