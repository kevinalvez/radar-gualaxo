"""
config/keywords.py

Keyword configuration manager.

Responsible for loading, saving and managing keyword profiles.
"""

from config.json_storage import (
    load_json,
    save_json
)


FILE = "keywords.json"


def load_keywords():

    return load_json(
        FILE
    )


def save_keywords(
    keywords
):

    save_json(
        FILE,
        keywords
    )


def add_keyword(
    keyword: dict
):

    keywords = load_keywords()

    if keyword not in keywords:

        keywords.append(
            keyword
        )

        save_keywords(
            keywords
        )


def remove_keyword(
    keyword_name: str
):

    keywords = load_keywords()

    keywords = [
        item
        for item in keywords
        if item != keyword_name
    ]

    save_keywords(
        keywords
    )


def update_keyword(
    old_name,
    new_keyword
):

    keywords = load_keywords()

    for index, item in enumerate(keywords):

        if item == old_name:

            keywords[index] = new_keyword

            break


    save_keywords(
        keywords
    )