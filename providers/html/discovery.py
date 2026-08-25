"""
providers/html/discovery.py

Discovers crawlable links from an HTML page.
"""

from __future__ import annotations

from urllib.parse import urldefrag, urljoin

from bs4 import BeautifulSoup

from .filters import (
    is_valid_url,
    looks_like_article,
    same_domain,
    same_section,
)


class LinkDiscovery:

    """
    Responsible for extracting valid links from HTML.
    """

    def discover(

        self,

        base_url: str,

        soup: BeautifulSoup,

    ) -> list[str]:
        """
        Discovers crawlable links, restricted to the source's own
        domain, and returns them ordered by priority: links in the
        same site section as base_url come first (since a section
        page's link soup commonly includes unrelated articles from
        other sections, e.g. sports or economy, which would
        otherwise crowd out the relevant ones under max_pages),
        then other article-like links, then everything else.
        """

        candidates = []

        visited = {
            base_url.rstrip("/")
        }

        for anchor in soup.find_all("a", href=True):

            href = anchor["href"].strip()

            absolute = urljoin(
                base_url,
                href,
            )

            # The fragment doesn't change what gets downloaded, so
            # strip it before validation/dedup (otherwise "/x/" and
            # "/x/#" are treated as two different pages).
            absolute, _fragment = urldefrag(absolute)

            if not is_valid_url(absolute):
                continue

            if not same_domain(absolute, base_url):
                continue

            normalized = absolute.rstrip("/")

            if normalized in visited:
                continue

            visited.add(normalized)

            candidates.append(absolute)

        def priority(url: str) -> int:

            in_section = same_section(url, base_url)
            article = looks_like_article(url)

            if in_section and article:
                return 0

            if in_section:
                return 1

            if article:
                return 2

            return 3

        return sorted(
            candidates,
            key=priority,
        )