"""
providers/html/cleaners.py

Utilities for cleaning HTML documents before extracting text.
"""

from __future__ import annotations

from bs4 import BeautifulSoup
from bs4 import Comment


class HTMLCleaner:

    """
    Removes visual and navigation elements that do not
    belong to the publication content.
    """

    TAGS_TO_REMOVE = {

        "script",
        "style",
        "noscript",

        "svg",
        "canvas",

        "iframe",

        "footer",

        "header",

        "nav",

        "aside",

        "form",

        "button",

        "input",

        "select",

        "option",

    }

    # Author bio/byline boxes from common WordPress plugins/themes.
    # These commonly repeat the exact same paragraph (the reporter's
    # bio) across every article on a site, and that bio can mention
    # anything - a university name, a hometown - that happens to
    # match a monitored keyword with nothing to do with the article's
    # actual subject. Matched by CSS class substring since the exact
    # class includes generated IDs (e.g. "box-post-id-4424").
    BOILERPLATE_SELECTORS = [

        '[class*="pp-multiple-authors"]',

        '[class*="author-box"]',

        '[class*="author-bio"]',

        '[class*="td-post-author"]',

        # Elementor's "Posts" widget (a "related"/"latest posts"
        # block): each teaser's title/excerpt lives in this class.
        # Same problem as the author box - a teaser for a completely
        # different, unrelated article can end up glued onto the
        # real article's extracted text, and its headline can match
        # a keyword having nothing to do with the actual article.
        '[class*="elementor-post__text"]',

    ]

    # ---------------------------------------------------------

    def clean(
        self,
        soup: BeautifulSoup,
    ) -> BeautifulSoup:

        soup = BeautifulSoup(
            str(soup),
            "html.parser",
        )

        self.remove_comments(soup)

        self.remove_tags(soup)

        self.remove_hidden(soup)

        self.remove_boilerplate(soup)

        return soup

    # ---------------------------------------------------------

    def remove_tags(
        self,
        soup,
    ):

        for tag in soup.find_all(
            self.TAGS_TO_REMOVE
        ):

            tag.decompose()

    # ---------------------------------------------------------

    def remove_comments(
        self,
        soup,
    ):

        for comment in soup.find_all(
            string=lambda text:
            isinstance(text, Comment)
        ):

            comment.extract()

    # ---------------------------------------------------------

    def remove_hidden(
        self,
        soup,
    ):

        hidden = soup.select(

            "[hidden],"

            "[aria-hidden='true'],"

            "[style*='display:none']"

        )

        for tag in hidden:

            tag.decompose()

    # ---------------------------------------------------------

    def remove_boilerplate(
        self,
        soup,
    ):

        for selector in self.BOILERPLATE_SELECTORS:

            for tag in soup.select(selector):

                tag.decompose()