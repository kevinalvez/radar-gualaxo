"""
config/sources.py

Source configuration manager.

Responsible for loading and saving monitored sources.
"""
"""
config/sources.py

Source configuration manager.

Responsible for loading and saving monitored sources.
"""

from config.json_storage import (
    load_json,
    save_json,
)


FILE = "sources.json"



def load_sources():

    return load_json(
        FILE
    )



def save_sources(
    sources
):

    save_json(
        FILE,
        sources
    )



def add_source(
    source: dict
):

    sources = load_sources()


    if not isinstance(
        source,
        dict
    ):
        raise ValueError(
            "Source must be a dictionary."
        )


    # evita duplicidade por URL

    exists = any(

        item.get("url") == source.get("url")

        for item in sources

        if isinstance(item, dict)

    )


    if not exists:

        sources.append(
            source
        )

        save_sources(
            sources
        )



def remove_source(
    source_name
):

    sources = load_sources()


    sources = [

        source

        for source in sources

        if source.get("name") != source_name

    ]


    save_sources(
        sources
    )



def update_source(
    old_name,
    new_source
):

    sources = load_sources()


    for index, source in enumerate(
        sources
    ):

        if source.get("name") == old_name:

            sources[index] = new_source

            save_sources(
                sources
            )

            return