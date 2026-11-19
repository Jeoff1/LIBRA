"""Read the goodbooks-10k CSVs. Shared by import_books and train_recommender.

In this dataset, books.csv's `book_id` column is the Goodreads ID; it is what
book_tags.csv calls `goodreads_book_id`. (books.csv's `id` column is a separate
1-10000 numbering used by ratings.csv, which we don't use.)
"""

import re
from pathlib import Path

import pandas as pd
from django.conf import settings
from django.core.management.base import CommandError

TOP_TAGS = 10

# Tags that describe a reader's shelf rather than the book: "to-read",
# "owned", "kindle", "read-in-2015", "my-books" and so on. Matched as whole
# hyphen-separated words, plus any tag containing a digit.
_SHELF_WORDS = (
    "to|read|reads|reading|re|currently|favou?rites?|own|owned|kindle|"
    "e-?books?|audio|audiobooks?|library|wish|buy|default|shelf|dnf|i|my"
)
_SHELF_TAG = re.compile(rf"(^|-)({_SHELF_WORDS})(-|$)|\d")
_SHELF_EXACT = {"-", "books", "book-club"}


def is_shelf_tag(name: str) -> bool:
    return name in _SHELF_EXACT or bool(_SHELF_TAG.search(name))


def data_path(filename: str) -> Path:
    path = Path(settings.DATA_DIR) / filename
    if not path.exists():
        raise CommandError(
            f"{path} not found. Download goodbooks-10k from Kaggle and extract "
            "it into data/ (see README)."
        )
    return path


def read_books() -> pd.DataFrame:
    """books.csv with the columns we use, renamed to match the Book model."""
    books = pd.read_csv(
        data_path("books.csv"),
        dtype={"isbn": "string", "language_code": "string"},
        usecols=[
            "book_id",
            "isbn",
            "authors",
            "original_publication_year",
            "title",
            "language_code",
            "average_rating",
            "image_url",
        ],
    )
    return books.rename(
        columns={
            "book_id": "goodreads_book_id",
            "original_publication_year": "publication_year",
        }
    )


def top_tags(n: int = TOP_TAGS) -> pd.Series:
    """Each book's n most-used tags, most used first, skipping shelf tags.

    Returns a Series of lists, indexed by goodreads_book_id.
    """
    book_tags = pd.read_csv(data_path("book_tags.csv"))
    tags = pd.read_csv(data_path("tags.csv"), keep_default_na=False)
    tags = tags[~tags["tag_name"].map(is_shelf_tag)]

    tagged = book_tags[book_tags["count"] > 0].merge(tags, on="tag_id")
    # A few (book, tag) pairs appear twice; add their counts together.
    tagged = tagged.groupby(["goodreads_book_id", "tag_name"], as_index=False)[
        "count"
    ].sum()
    tagged = tagged.sort_values(
        ["goodreads_book_id", "count", "tag_name"], ascending=[True, False, True]
    )
    return (
        tagged.groupby("goodreads_book_id")
        .head(n)
        .groupby("goodreads_book_id")["tag_name"]
        .agg(list)
    )


def clean_isbn(value) -> str:
    """ISBNs lost their leading zeros in the CSV (61120081 -> 0061120081)."""
    if pd.isna(value):
        return ""
    return str(value).strip().zfill(10)
