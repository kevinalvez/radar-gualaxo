"""
providers/html/extractor.py

Extracts the main content node from an HTML document and judges
whether it actually holds a single article, as opposed to a listing
or hub page (e.g. a "latest news" module or a live-updates page).
"""

from __future__ import annotations

from urllib.parse import urlparse

from bs4 import BeautifulSoup

from .filters import is_listing_path


class ContentExtractor:

    """
    Identifies the main content container and classifies it as a
    single article or not.
    """

    # Selectors that specifically denote a single post/article. When
    # one of these matches, we trust the result is one article.
    STRONG_SELECTORS = [

        "article",

        ".post",

        ".post-content",

        ".entry-content",

        ".article-content",

        # tagDiv's "Newspaper"/Newsmag WordPress theme (widely used by
        # Brazilian news sites) - the actual post body, as opposed to
        # the theme's own <article class="tdb_templates"> page-layout
        # wrapper (see _longest_match's tdb_templates exclusion below).
        ".tdb_single_content",

        ".td-post-content",

    ]

    # Generic containers that could just as easily wrap a listing or
    # hub page (e.g. a "latest news" module) as a single article.
    # A match here needs the extra listing checks below.
    WEAK_SELECTORS = [

        "main",

        "[role='main']",

        ".content",

        ".article",

        ".news",

        ".noticia",

        ".texto",

        ".texto-noticia",

        "#content",

        "#main",

        # Elementor (a common WordPress page builder) wraps every
        # widget's content in this generic class, including a
        # single post's body when the theme doesn't use a dedicated
        # ".entry-content"/".post-content". It's generic enough to
        # also match unrelated widgets, so it only wins via the
        # length comparison in extract(), same as the other weak
        # selectors.
        ".elementor-widget-container",

    ]

    # Minimum number of h2/h3/h4 headings, each linking to another
    # page, for a generically-matched content node to be treated as
    # a listing/hub page instead of a single article. Below this,
    # or with fewer linked headings than this, it's presumed to be
    # one document's own subheadings (see _is_listing).
    LISTING_HEADING_THRESHOLD = 3

    # Heading count so high that a page is almost certainly a
    # directory/listing regardless of whether headings link out
    # (e.g. a staff directory with no per-entry links).
    LISTING_EXTREME_HEADING_COUNT = 20

    # Some component-grid sites (React/Next.js "card" layouts) render
    # every teaser as a plain styled <div> - no h2/h3/h4, no real
    # <a href> at all (navigation happens via an onClick handler in
    # JS that never appears in the static HTML this provider fetches).
    # Neither the heading-based nor the link-based check above can see
    # that pattern. What's still visible is the repetition itself:
    # this many sibling elements sharing the exact same tag+class
    # combination, each holding a teaser-sized chunk of its own text.
    # A single article has no reason to repeat an identical class
    # combination this many times.
    CARD_REPETITION_THRESHOLD = 5

    # A repeated card's own text has to fall in this range to count:
    # long enough to be a real headline+excerpt (not a badge/tag chip
    # repeated in a taxonomy widget), short enough to be one teaser
    # rather than, say, a repeated multi-paragraph FAQ answer.
    CARD_TEXT_LENGTH_RANGE = (30, 1000)

    # How much longer a weak-selector match must be than the
    # strong-selector match to be trusted over it (see extract()).
    # A weak container - especially a broad page-builder wrapper -
    # commonly contains the real article *plus* a "related posts"
    # block right below it, which alone can make it ~10-20% longer
    # than the article without actually being wrong. A genuinely
    # wrong strong match (a teaser card instead of the real article)
    # is dramatically shorter than the real thing in practice
    # (observed 8x-60x), so this threshold sits comfortably between
    # the two.
    WEAK_OVERRIDE_RATIO = 2.0

    # When the URL itself is a known listing pattern (category/tag/
    # author/...), a strong-selector match is only trusted if it's at
    # least this long. A page that's structurally a listing has no
    # real article to find in the first place, so a *short* strong
    # match there (observed 90-270 chars in practice) is reliably
    # just a teaser card, not evidence of a genuine article the URL
    # shape got wrong about. A long strong match is left alone - nothing
    # here second-guesses a substantial, confidently-matched article.
    STRONG_MATCH_LISTING_URL_MIN_LENGTH = 500

    # ----------------------------------------------------------

    def extract(

        self,

        soup: BeautifulSoup,

        url: str | None = None,

    ):
        """
        Returns (node, is_article).

        `is_article` is True when the winning node came from a
        selector that specifically denotes a single article, or when
        it came from a generic container that doesn't look like a
        listing page (see _is_listing). A strong-selector match is
        normally trusted regardless of the URL - except when the URL
        is itself a known listing pattern and the match is short (see
        STRONG_MATCH_LISTING_URL_MIN_LENGTH).
        """

        strong_node, strong_length = self._longest_match(
            soup, self.STRONG_SELECTORS
        )
        weak_node, weak_length = self._longest_match(
            soup, self.WEAK_SELECTORS
        )

        url_is_listing = bool(url) and is_listing_path(urlparse(url).path)

        strong_trusted = strong_node is not None and not (
            url_is_listing
            and strong_length < self.STRONG_MATCH_LISTING_URL_MIN_LENGTH
        )

        # A "strong" selector (article, .entry-content, ...) can
        # still match the wrong thing - e.g. a page builder (like
        # Elementor) that reuses the same tag/class for both the real
        # article and short "related posts" teaser cards elsewhere on
        # the page. When that happens, a generic container ends up
        # holding far more text than the strong match, which is a
        # reliable enough signal that it's the real content. But a
        # weak container is also often just a wider wrapper *around*
        # the correct strong match (article + a "related posts" strip
        # glued right after it), so only a substantially longer weak
        # match (see WEAK_OVERRIDE_RATIO) overrides the strong one -
        # a marginally longer weak match is presumed to be that kind
        # of wrapper, not evidence the strong match was wrong.
        if (
            strong_trusted
            and weak_length <= strong_length * self.WEAK_OVERRIDE_RATIO
        ):
            return strong_node, True

        if weak_node is not None:
            return weak_node, not self._is_listing(weak_node, url)

        if strong_node is not None:
            return strong_node, strong_trusted

        node = soup.body or soup

        return node, not self._is_listing(node, url)

    # ----------------------------------------------------------

    @staticmethod
    def _longest_match(soup, selectors):
        """
        Returns (node, text_length) for the element with the most
        text among all elements matching any of the given selectors,
        or (None, 0) if none match.

        Many WordPress-style themes reuse the same tag/class for
        both the actual article body and "related posts" teaser
        cards elsewhere on the page (e.g. every teaser is itself an
        `<article>`). Taking the first match in selector order can
        silently grab a teaser instead of the real content, so all
        candidates are compared and the longest one - virtually
        always the real article body - wins.
        """

        best = None
        best_length = 0

        for selector in selectors:

            for node in soup.select(selector):

                # A selector (e.g. "#content"/"#main") can end up
                # matching <body> itself if a site happens to put
                # that id/class directly on it. That's not a content
                # region - it's the entire page, chrome included - so
                # treating it as a match would defeat every other
                # heuristic here (it would "win" by sheer length
                # while dragging in nav bars, headers, footers, etc.
                # that TAGS_TO_REMOVE already stripped by tag but
                # that live in un-tagged wrapper divs).
                if node.name in ("body", "html"):
                    continue

                # tagDiv's "Newspaper"/Newsmag theme builds an entire
                # single-post PAGE as one WPBakery-composed layout
                # definition, wrapped in <article class="tdb_templates">
                # - breadcrumbs, sidebar "trending headlines" and "Mais
                # Lidas" widgets, and the real post body all together,
                # not the post itself. Because it structurally contains
                # the real content plus everything else, a plain
                # "article" match here is *always* longer than the
                # theme's own dedicated content selector
                # (.tdb_single_content/.td-post-content) - "longest
                # wins" would otherwise pick this wrapper every time.
                classes = node.get("class") or []
                if "tdb_templates" in classes:
                    continue

                length = len(node.get_text(strip=True))

                if length > best_length:
                    best = node
                    best_length = length

        return best, best_length

    # ----------------------------------------------------------

    @classmethod
    def _has_repeated_card_grid(cls, node) -> bool:
        """
        Detects a listing built as a grid of styled <div> "cards"
        with no semantic heading tags and no real <a href> - see
        CARD_REPETITION_THRESHOLD for why this check exists.
        """

        groups: dict[tuple, list] = {}

        for el in node.find_all(True, class_=True):

            key = (el.name, tuple(el.get("class")))

            groups.setdefault(key, []).append(el)

        low, high = cls.CARD_TEXT_LENGTH_RANGE

        for elements in groups.values():

            if len(elements) < cls.CARD_REPETITION_THRESHOLD:
                continue

            lengths = [
                len(el.get_text(strip=True))
                for el in elements
            ]

            if all(low <= length <= high for length in lengths):
                return True

        return False

    # ----------------------------------------------------------

    def _is_listing(self, node, url: str | None = None) -> bool:
        """
        Detects "hub" pages (e.g. a live-updates or "latest news"
        page) that list several headlines linking to other articles
        rather than containing a single article.

        A single document (e.g. a public notice or terms-of-use
        page) can also be broken into many sections with headings,
        so raw heading count alone isn't enough - a share/like
        toolbar or a PDF attachment link often sits right next to
        every section heading too, so "is there a link nearby" isn't
        enough either. What actually distinguishes a listing is that
        each heading *is itself* the label of a link to another
        page - so that's what's checked here, with a heading-count
        fallback for pages so long (directories, sitemaps) that this
        would never plausibly be a single document regardless.

        The URL's own shape is checked first: a category/tag/author/
        search page (e.g. "/category/cidades/") is reliably a listing
        regardless of how many headings its sidebar/widgets produce -
        some CMS themes reuse the same generic sidebar across every
        category page, which doesn't carry enough headings to trip
        the content-based check below on its own.
        """

        if url and is_listing_path(urlparse(url).path):
            return True

        if self._has_repeated_card_grid(node):
            return True

        headings = node.find_all(["h2", "h3", "h4"])

        if len(headings) >= self.LISTING_EXTREME_HEADING_COUNT:
            return True

        if len(headings) < self.LISTING_HEADING_THRESHOLD:
            return False

        linked_headings = sum(
            1
            for heading in headings
            if self._heading_is_link(heading)
        )

        return linked_headings >= self.LISTING_HEADING_THRESHOLD

    # ----------------------------------------------------------

    # How many levels up from a heading to look for an enclosing <a>
    # wrapper (e.g. <a class="card"><div><h3>Title</h3></div></a>,
    # a common "whole card is a link" pattern). Deliberately checks
    # only whether each ancestor *itself* is an <a> - not whether
    # a link exists anywhere in its subtree, which would also match
    # unrelated siblings (share buttons, PDF links) sitting near the
    # heading under the same wrapper without it being a teaser link.
    HEADING_LINK_ANCESTOR_DEPTH = 4

    @classmethod
    def _heading_is_link(cls, heading) -> bool:
        """
        Returns True if the heading itself is the label of a link to
        another page, as opposed to a section title within a single
        document. Ignores in-page anchors, mailto and javascript
        links, since those commonly sit near headings (share
        buttons, tables of contents) without indicating a
        teaser/listing pattern.
        """

        anchor = heading.find("a", href=True)

        if anchor is None:

            ancestor = heading.parent
            depth = 0

            while ancestor is not None and depth < cls.HEADING_LINK_ANCESTOR_DEPTH:

                if ancestor.name == "a" and ancestor.get("href"):
                    anchor = ancestor
                    break

                ancestor = ancestor.parent
                depth += 1

        if anchor is None:
            return False

        href = anchor["href"].strip()

        return not (
            href.startswith("#")
            or href.startswith("mailto:")
            or href.startswith("javascript:")
        )
