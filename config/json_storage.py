"""
config/json_storage.py

Generic JSON storage helper.

Provides common methods for loading and saving JSON files.
"""
import json
from pathlib import Path


BASE_PATH = Path(__file__).parent / "data"


def ensure_storage():

    BASE_PATH.mkdir(
        exist_ok=True
    )


def load_json(filename):

    ensure_storage()

    path = BASE_PATH / filename


    if not path.exists():

        path.write_text(
            "[]",
            encoding="utf-8"
        )


    with open(
        path,
        "r",
        encoding="utf-8"
    ) as file:

        return json.load(file)



def save_json(
    filename,
    data
):

    ensure_storage()

    path = BASE_PATH / filename


    with open(
        path,
        "w",
        encoding="utf-8"
    ) as file:

        json.dump(
            data,
            file,
            indent=4,
            ensure_ascii=False
        )